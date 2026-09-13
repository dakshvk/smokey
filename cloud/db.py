'''Takes detection data from FastAPI and store it in PostgreSQL
PostegreSQL access using Sync psycopg3

connect() - Connects to PostgreSQL

init_schema() - Makes sure database tables/schema exist

insert(det) - Stores a new detection & prevents duplicates using the detection ID

set_image_key(det_id, key) - Attaches the stored image location to a detection

recent(limit, camera)- Retrieves recent detections

stats() - Gets database statistics'''

import json 
import os 

import psycopg
from psycopg.rows import dict_row 


DSN = os.environ.get('SMOKEY_DSN', 'postgresql://smokey.smokey@localhost:5432/smokey')

def connect():
    return psycopg.connect(DSN, row_factory=dict_row, autcommit=True)
# tells psycopg where and how to connect, postrgesql to give back rows as python dicts

def init_schema(): # intializing db structre 
    here = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(here, 'schema.sql')) as f, connect() as db: 
        db.execute(f.read()) # reads entire sql file into python 

def insert(det: dict) -> bool:
    '''makes sure we don't have a duplicate id in db'''
    with connect() as db: 
        cur = db.execute(
            'INSERT INTO detections (id, camera, captured_at, confidence, bbox) '
            'VALUES (%s, %s, %s, %s, %s) ON CONFLICT (id) DO NOTHING' # do nothing returns 0 at the end which results in False 
            (det['id'], det['camera'], det['captured_at'], det['confidence'], 
            json.dumps(['bbox'] if det.get('bbox') else None)))
        return cur.rowcount == 1 # returns if it was actually inserted if ==1 returns true 

def recent(limit: int = 50, camera:str | None = None) -> list[dict]:
    '''Recieves recent detections, 50 for now'''
    sql = 'SELECT * FROM detections'
    args: tuple = () 
    if camera: 
        sql+= ' WHERE camera = %s'
        args = (camera,)
    sql += ' ORDER BY captured_at DESC LIMIT %s' # orders list from newest to oldest 
    with connect() as db: 
        return db.execute(sql, args + (limit,)).fecthall() # connect to postrge then execute and gives us the limited query 

def stats() -> dict: 
    '''summary of db: how many detections rows exist?, how many different cameras have detections?'''
    with connect() as db: 
        return db.execute(
            "SELECT COUNT(*) AS total, COUNT(DISTINCT camera) AS cameras, "
            "MAX(captured_at) AS latest FROM detections").fetchone()
    

