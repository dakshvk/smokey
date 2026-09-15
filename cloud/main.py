'''Ingestion API for edge devices.

POST /detections need to be idempotent as the device retries anything it did not get
a confirmed response for, so the same id will arrive twice. 
Duplicate is a success, not an error 
Returning an error would make the device retry forever.
'''
import os
from datetime import datetime

from fastapi import FastAPI, Depends, Header, HTTPException, UploadFile, File
from pydantic import BaseModel, Field

from . import db, storage

API_KEY = os.environ.get('SMOKEY_API_KEY', '')

app = FastAPI(title='Smokey', description='Wildfire smoke detection ingestion')


def require_key(x_api_key: str = Header(default='')):
    if API_KEY and x_api_key != API_KEY:
        raise HTTPException(401, 'bad or missing API key')


class Detection(BaseModel):
    id: str
    camera: str
    captured_at: datetime
    confidence: float = Field(ge=0.0, le=1.0)
    bbox: list[float] | None = None


@app.on_event('startup')
def startup():
    db.init_schema()


@app.post('/detections', status_code=201, dependencies=[Depends(require_key)])
def post_detection(det: Detection):
    payload = det.model_dump()
    payload['captured_at'] = det.captured_at.isoformat()
    if db.insert(payload):
        return {'status': 'stored', 'id': det.id}
    return {'status': 'duplicate', 'id': det.id}      # 200, not an error


@app.post('/detections/{det_id}/image', dependencies=[Depends(require_key)])
async def post_image(det_id: str, file: UploadFile = File(...)):
    '''Uploaded separately so a large image can never delay or fail the
    detection record itself.'''
    det = db.get(det_id)
    if det is None:
        raise HTTPException(404, 'unknown detection id')

    key = storage.key_for(det['camera'], det['captured_at'].isoformat(), det_id)
    storage.upload(await file.read(), key)
    db.set_image_key(det_id, key)
    return {'status': 'stored', 'key': key}


@app.get('/detections', dependencies=[Depends(require_key)])
def get_detections(limit: int = 50, camera: str | None = None):
    rows = db.recent(limit=limit, camera=camera)
    for r in rows:
        r['image_url'] = storage.presigned_url(r['image_key']) if r['image_key'] else None
    return rows


@app.get('/health')
def health():
    '''No auth - this is what the Pi and any load balancer ping.'''
    try:
        return {'ok': True, **db.stats()}
    except Exception as e:
        raise HTTPException(503, f'database unreachable: {type(e).__name__}')