'''Fetches a single live frame from HPWREN Camera
live endpoint: https://cdn.hpwren.ucsd.edu/RT/<camera>.jpg
one camera fram published per minute. 

Dead camera keeps on serving its last frame forever so Last-Modified age is real liveness signal.
So HTTP 200 doesnt mean camera is working, so we need to check when the imahe was last published 

sites.js marks all 503 cameras. 

Returns result object rather than raising as one bad camera cannot stop the loop

Relative order Camera name -> Build HPWREN URL -> GET image 
 -> Did server respond? -> Is it actually an image? -> Is there image data?
-> When was it published? -> Is it fresh? -> Return Frame object

DOES NOT DETECT SMOKE: just answers can i get a fresh frame from this camera? 
'''

from dataclasses import dataclass # class holding data 
from email.utils import parsedate_to_datetime # converts HTTP date string into Python datetime 
from datetime import datetime, timezone # makes sure were using UTC 

import requests # library making HTTP request 

BASE = 'https://cdn.hpwren.ucsd.edu/RT'

# NSF funded research so identifying self is important as is public infrastrcuture 

HEADERS = {'User-Agent': 'project-smokey/0.1 (wildfire smoke detection research)'}

@dataclass 
class Frame: # holds data which is one camera fetch attempt 
    ''' One fetch attempt. 'ok' is the only thing caller must check
    Returns failure instead of raising an Error'''
    camera: str # cam name 
    ok: bool # did we get the fram or not 
    reason: str = '' # reason for failure 
    data: bytes = b'' # raw jpeg uncoded
    age_s: float | None = None # Seconds since published by camera, None means we couldnt determine the age

def fetch_frame(camera: str, max_age_s: float = 180, timeout: float = 10) -> Frame:
    '''GET one frame, rejecting frames older than 3 mins and timeout is 10s long'''
    url = f'{BASE}/{camera}.jpg'
    try: # prep for failure 
        r = requests.get(url, headers=HEADERS, timeout=timeout) # http get request to HPWREN server
    except requests.Timeout: 
        return Frame(camera, False, f'timeout after {timeout}s')
    except requests.RequestException as e:  # catches other request related problems 
        return Frame(camera, False, f'request failed {type(e).__name__}') # records error type 

    if r.status_code != 200: # returns specific error type 
        return Frame(camera, False, f'HTTP {r.status_code}')

# Checking thats it an actual image 
    ctype = r.headers.get('Content-Type', '') # what type of content returned 
    if not ctype.startswith('image/'): # does it look lik ean image response
        return Frame(camera, False, f'not an image: {ctype!r}') # if not returns hidden formatting isuues with '!r'
    if not r.content: # r.content contains raw response body 
        return Frame(camera, False, 'empty body')

    lm = r.headers.get('Last-Modified') # GETs the HTTP Last-Modified header 
    if lm is None: 
        return Frame(camera, True, 'no Last-Modified', r.content, None) # gets image but doesnt know how old it is
    try: 
        published = parsedate_to_datetime(lm) # parses the date of the header
    except (TypeError, ValueError): # if the date is malformed 
        return Frame(camera, True, f'unparseable Last_Modified: {lm!r}', r.content, None)
        # keeps the image but admits we don't know the age 
    #calculate age
    age = (datetime.now(timezone.utc) - published).total_seconds()
    # = currrent time in UTC - how long ago it was published.difference into a #

    if age > max_age_s: # stale cam test if age > 180 then 'ok' = False
        return Frame(camera, False, f'stale: {age:.0f}s old', age_s = age)
    return Frame(camera, True, '', r.content, age) # sucessful case

if __name__ == '__main__':
    for cam in ('bh-n-mobo-c', 'rm-w-mobo-c', 'not-a-real-camera'): # test cams 
        f = fetch_frame(cam)
        if f.ok: 
            age = f'{f.age_s:.0f}s' if f.age_s is not None else 'Unkown' # formats age of img as float w 2 decimal places
            print(f'{cam:22s}) OK {len(f.data)/1000:6.0f} KB age {age}') # success
        else: 
            print(f'{cam:22s} FAIL {f.reason}') # fail 

    

    