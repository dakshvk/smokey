'''Detection queue where very detection is written to disk before any attempt to send it 
Nothing is lost to a crash, reboot, or long outage
Rows are makerd sent rather than deleted so there is an audit trail of what the device saw and when'''

import json 
import sqlite3
import uuid # gives detections their own unique id 
from datetime import datetime, timezone 

SCHEMA = '''
CREATE TABLE IF NOT EXISTS detections (
    id          TEXT PRIMARY KEY,   -- client-generated, for idempotency         
    camera      TEXT NOT NULL,      -- ISO8601 UTC, when the frame was taken
    captured_at TEXT NOT NULL, 
    confidence  REAL NOT NULL, 
    bbox        TEXT,               -- JSON [x1, y1, x2, y2] in full-frame px
    image_path  TEXT,               -- local copy of the triggering frame
    status      TEXT NOT NULL DEFAULT 'pending',    -- pending | sent 
    attempts    INTEGER NOT NULL DEFAULT 0, 
    last_error  TEXT, 
    created_at  TEXT NOT NULL 
    ); 
CREATE INDEX IF NOT EXISTS idx_pending ON detections(status, created_at);
'''
# creates db index asking for the status and ordering by time 

def _now() -> str: 
    return datetime.now(timezone.utc).isoformat() 
# gets current time in utc returns as a standard string 

class Outbox: 
    def __init__(self, path: str = 'outbox.db', max_rows: int = 50_000):
        self.max_rows = max_rows 
        self.db = sqlite3.connect(path, isolation_level=None) # opens sqlite db creating outbox.db
        # autocommit mode & db connection 
        self.db.row_factory = sqlite3.Row # makes sure rows are returned neatly 
        self.db.execute('PRAGMA journal_mode=WAL') # enables write-ahead logging so record changes in log before applying it to the main db
        # helps handle crashes and restarts safely 
        self.db.execute('PRAGMA synchronous=FULL') # priortize durability over speed 
        self.db.executescript(SCHEMA) # creates db structure 

    def add(self,camera: str, captured_at: str, confidence: float, bbox: list | None = None,
            image_path: str | None = None ):
        '''Function adds a detection to outbox.db 
        id is generated HERE 
        POST succeeds but response is lost retry carries the same id which the server can recognize as a repat'''
        det_id = str(uuid.uuid4()) # generates random uuid
        # inserts into db
        self.db.execute(
            'INSERT INTO detections '
            '(id, camera, captured_at, confidence, bbox, image_path, created_at) '
            'VALUES (?,?,?,?,?,?,?)',
            (det_id, camera, captured_at, confidence, 
             json.dumps(bbox) if bbox else None, # converts to json otherwise stores None
            image_path, _now())) # records when row was created 
        self._trim() # trims the db if we go past max_rows 
        return det_id # finally gives det_id of newly added detection 

    def pending(self, limit: int = 20) -> list[sqlite3.Row]:
        '''Retrives detections that haven't been sucessfully sent 
        aka stays pending so we retry'''
        return self.db.execute( # gets all columns from detections where status is pending 
            "SELECT * FROM detections WHERE status='pending' "
            'ORDER BY created_at LIMIT ?', (limit,)).fetchall() 
    # limit() supplys value for ? and fetchall retrives all the matching rows
    # orders them by when they were created and returns only till the requested limit 
    def mark_sent(self, det_id: str):
        '''Marks which detections have alr been sent'''
        self.db.execute("UPDATE detections SET status='sent' WHERE id=?",
        (det_id,)) # det_id sets ? 
    def mark_failed(self, det_id: str, error: str):
        '''Marks which detections failed'''
        self.db.execute(
            'UPDATE detections SET attempts= attempts+1, last_error=? WHERE id= ?', 
            # updates failed detection & latest error 
            (error[:500], det_id)) # takes first 500 characters of the error 

    def stats(self) -> dict: 
        rows = self.db.execute( # counts rows by status asking how many detections are in each one 
            'SELECT status, COUNT(*) n FROM detections GROUP BY status').fetchall()
        return {r['status']: r['n'] for r in rows}
        # groups status's into either pending or sent and counts each group 
        # turns it into a dictonary so we can index pending or sent to find out the values of each 

    def _trim(self):
        '''Bounds the table so a long outage won't fill up the SD card
        Drops oldest SENT rows first; pending never dsicarded''' # 'n' = current rows
        n = self.db.execute('SELECT COUNT(*) c FROM detections').fetchone()['c']
        # counts how many rows are in current detections table using 'c' as count 
        if n <= self.max_rows: # checks if trimming is needed
            return 
        self.db.execute( # deletes old SENT rows 
            "DELETE FROM detections WHERE id IN ("
            "    SELECT id FROM detections WHERE status='sent' "
            '    ORDER BY created_at LIMIT ?)', (n-self.max_rows,))
        # returns to us how many rows need to be deleted not how many rows of space are available 
    def close(self):
        self.db.close()
        
