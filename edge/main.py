'''fetch -> daylight check -> score -> alarm -> queue -> drain.

'''

import json 
import os # working w files n directories 
import sys
import time 
from datetime import datetime, timezone # creating timestamps 

import requests 

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
# gets abs path of current file then getting its dir then that dir's name then adding the project's root to Python's list of placeswhere it looks for modules 

from alarm import AlarmBank # managing alarm state 
from detect import Detector # yolo wrapper
from fetch import fetch_frame # downloading frame 
from outbox import Outbox # detection deque db 
from sun import is_daylight # daytime function 


HERE = os.path.dirname(os.path.abspath(__file__))

def load_config(path=None):
    with open(path or os.path.join(HERE, 'config.json')) as f: 
        return json.load(f) # converts json file into Python object 

def drain(outbox: Outbox, url: str, api_key: str, limit: int =20):
    '''Sends pending detections to the API. Stops on first network failure
    Sends at most 20 pending detections per drain call'''

    if not url: 
        return 0 
    headers = {'X-API-Key': api_key} if api_key else {} # HTTP headers
    sent = 0 # creates counter 
    for row in outbox.pending(limit): # gets pending detections from sqlite outbox
        payload = { # info we are sending the server 
            'id': row['id'],
            'camera': row['camera'],
            'captured_at': row['captured_at'],
            'confidence': row['confidence'],
            'bbox': json.loads(row['bbox']) if row['bbox'] else None, 
            # since db stores bounding box as json text we convert it back into a python object 
        }
        try: # now we try sending request 
        # makes HTTP POST request, send detection dict as json, includes api key if exists
            r = requests.post(url, json=payload, headers=headers, timeout=10)
        except requests.RequestException as e: 
            outbox.mark_failed(row['id'], f'{type(e).__name__}')
        # if failure we raise excpetion(get its name) with the det_id # 
            break
        if r.status_code in (200, 201, 409): # checks server response 
            # keep 409 as detection isnt missing just duplicated 
            outbox.mark_sent(row['id']) # marks as sucessfully handled aka as 'sent'
            sent += 1 
        else: 
            outbox.mark_failed(row['id'], f'HTTP{r.status_code}')
            break 
        return sent 

def run(cfg):
    '''recives config dict''' 
    os.makedirs(cfg['frame_dir'], exist_ok=True)
# makes sure directroy exists if doesnt it makes it 
    detector = Detector(cfg['weights'], imgsz=cfg.get('imgsz', 1024))
    # creates YOLO detector 
    alarms = AlarmBank(cfg['threshold'], cfg['K'], cfg['M'])
    #creates alarm system
    outbox = Outbox(cfg['outbox_db'])
    # created detection queue db
    print(f'watching {len(cfg['cameras'])} cameras, '
          f'th={cfg['threshold']} K={cfg['K']} M={cfg['M']}')
    # counts the cameras we start with along with the repsective threhold and "M-K values"
    while True: # infinite loop 
        cycle_start = time.time() # records exact time monitoring session starts
        for cam in cfg['cameras']:
            cid = cam['id'] # gets camera id for each cam 

            if not is_daylight(cam['lat'], cam['lon'], cfg.get('min_sun_elevation_deg', 5.0)):
                continue # daylight check per camera, if false contiues to next cam as its night 
            frame = fetch_frame(cid, max_age_s=cfg.get('max_frame_age_s', 180)) 
            # frame check per camera making sure its not dead & gets most recent frame 
            if not frame.ok: 
                print(f' {cid}: {frame.reason}')
                alarms.reset(cid) # resets the alarms if dead and prints reason as to why dead
                continue 

            det = detector.score(frame.data) #runs yolo returns det
            fired = alarms.update(cid, det.max_conf) # returns alarms fired per cid and the correspondind max conf  

            print(f' {cid}: {det.max_conf:.3f}{' ALARM' if fired else ""}')
            # prints cam and & conf up to 3 decimal places
             
            if fired: 
                captured = datetime.now(timezone.utc).isoformat()
                # creates time stamp 
                path = os.path.join(
                    cfg['frame_dir'],
                    f'{cid}_{captured.replace(':', '-')}.jpg'
                )    
                # filename for img evidence/where we store timestamp
                with open(path, 'wb') as f: #open the file for writing the camera img into the file 
                    f.write(frame.data) 
                best = max(det.boxes, key=lambda b: b['conf'], default=None)
                # find the best bounding box aka highest conf
                outbox.add(cid, captured, det.max_conf,
                           bbox=best['xyxy'] if best else None, 
                           image_path=path)
                # puts detection into outbox 
                # all happens before network upload so data is saved 
        sent = drain(outbox, cfg.get('api_url'), cfg.get('api_key', ''))
        # now trys sending pending detections
        stats = outbox.stats() # gets outbox stats for how many still are pending 
        if sent or stats.get('pending'):
            print(f' outbox: sent {sent}, pending {stats.get('pending', 0)}')
        elapsed = time.time() - cycle_start # calculated how long cycle took 
        time.sleep(max(0, cfg.get('poll_seconds', 60) - elapsed)) # waits until next polling cycle 
# 0 for starting next cycle immediately if processing was longer than 60s 
if __name__ == '__main__':
    try: 
        run(load_config(sys.argv[1] if len(sys.argv)>1 else None))
        # checks for another arg and gets config path 
    except KeyboardInterrupt: # crtl c 
        print('\nstopped')

