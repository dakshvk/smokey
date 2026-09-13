-- Detections reported by edge devices - Open Source HPWREN
-- id generated on the device 
-- if POST commits but reponse is lost retry carries same id 
-- id then lands on primary key conflict rather than 

CREATE TABLE IF NOT EXISTS detections (
    id          UUID PRIMARY KEY, 
    camera      TEXT    NOT NULL, 
    captured_at TIMESTAMPZ NOT NULL, 
    confidence  REAL 
    bbox        JSONB, 
    image_key   TEXT, 
    received_at TIMESTAMPZ NOT NULL DEFAULT now(),
    CONSTRAINT confidence_range CHECK (confidence >= 0 AND confidence <= 1)

);

-- Query dashboard makes: recent detections with newest det's first 
CREATE INDEX IF NOT EXISTS idx_detections_time ON detections (captured at DESC);
CREATE INDEX IF NOT EXISTS idx_detections-camera ON detections (camera, captured_at DESC);
