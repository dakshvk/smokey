# Project Smokey

Edge-to-cloud wildfire smoke detection. A YOLOv11 detector, quantized to ONNX,
running on a Raspberry Pi 5, watching live HPWREN cameras and posting alerts to
a FastAPI + Postgres + S3 backend.

Built Aug 29 - Sep 17 2026. Tracked in Alfred at /api/smokey.

## Layout
    data/figlib/     FIgLib archive - 522 labeled fire sequences (training)
    data/pyronear/   PyroNear2025 from HuggingFace (training)
    models/          checkpoints, ONNX exports, quantized variants
    edge/            the device program: fetch -> infer -> queue -> post
    cloud/           FastAPI service, Postgres schema, S3 storage
    eval/            evaluation harness - precision at fixed low FPR
    scripts/         data download and setup
    results/         benchmarks, thermal plots, run logs

## Data
Training frames are labeled by filename: `<unix_ts>_<offset>.jpg` where offset is
seconds relative to fire ignition. Negative = before ignition (no smoke),
positive = after (smoke). No manual annotation needed.

Live inference reads https://cdn.hpwren.ucsd.edu/RT/<camera-id>.jpg
Poll at 1 frame/min per camera. HPWREN is NSF-funded research infrastructure -
their terms ask for non-wasteful bandwidth use. Never poll faster.
