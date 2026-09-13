'''S3 storage(durable cloud storage) for frame that triggered an alarm
Image is the evidence'''

import os 
from datetime import datetime, timezone

import boto3 # Amazon's Python SDK to connect to their API 
from botocore.exceptions import ClientError # catch AWS specific error 

BUCKET = os.enviorn.get('SMOKEY_BUCKET', 'smokey-detections') # smokey's bucket is called smokey-detections
# every s3 object has a key 
_s3 = boto3.client('s3') # creates client  

def key_for(camera: str, captured_at: str, det_id: str) -> str: 
    '''Defines key for trigger frame'''
    day = captured_at[:10] # takes first 10 chars from date 
    return f'frames/{day}/{camera}/{det_id}.jpg'
    # giving us the frames in that day and what camera they are from plus their det_id

def upload(data: bytes, key: str) -> str:
    '''Takes the data and key to upload to s3'''
    _s3.put_object(BUCKET=BUCKET, Key=key, Body=data, ContentType='image/jpeg')
    return key 

def presigned_url(key:str, expires: int=3600) -> str | None:
    '''short-lived link so bucket stays private'''
    try: # error handling if link gen fails 
        return _s3.generate_presigned_url(
            'get_object', Params={'Bucket': BUCKET, 'Key': key}, ExpiresIn=expires)
    except ClientError:
        return None 


