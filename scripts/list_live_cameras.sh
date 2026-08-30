#!/usr/bin/env bash
# List HPWREN live cameras. Live frame URL:
#   https://cdn.hpwren.ucsd.edu/RT/<camera-id>.jpg
# Cameras listed but currently offline return 403 - handle it, do not crash.
set -u
curl -s --max-time 30 https://www.hpwren.ucsd.edu/cameras/sites.js \
  | grep -o '"[a-z0-9]*-[a-z]*-mobo-[cm]"' | tr -d '"' | sort -u
