#!/usr/bin/env bash
# Download FIgLib fire sequences from HPWREN.
#
#   ./download_figlib.sh          # 25 sequences (~2GB) - enough to start Day 1
#   ./download_figlib.sh 100      # 100 sequences (~9GB)
#   ./download_figlib.sh all      # all 522 (~45GB, several hours)
#
# Resumable: re-run it and it skips what you already have.
# Sequential on purpose. HPWREN is research infrastructure, not a CDN to hammer.
set -u
BASE="https://cdn.hpwren.ucsd.edu/HPWREN-FIgLib-Data/Tar"
OUT="$(cd "$(dirname "$0")/.." && pwd)/data/figlib"
COUNT="${1:-25}"
mkdir -p "$OUT"

echo "Fetching sequence list..."
curl -s --max-time 60 "$BASE/index.html" \
  | grep -o 'href=[^ >]*\.tgz' | sed 's/href=//' | sort -u > "$OUT/.all_sequences.txt"
TOTAL=$(wc -l < "$OUT/.all_sequences.txt" | tr -d ' ')
echo "$TOTAL sequences available."

if [ "$COUNT" = "all" ]; then COUNT=$TOTAL; fi
head -n "$COUNT" "$OUT/.all_sequences.txt" > "$OUT/.queue.txt"

i=0
while read -r f; do
  i=$((i+1))
  name="${f%.tgz}"
  if [ -d "$OUT/$name" ]; then echo "[$i/$COUNT] $name already extracted, skipping"; continue; fi
  echo "[$i/$COUNT] $name"
  curl -# -C - -o "$OUT/$f" "$BASE/$f" || { echo "  download failed, skipping"; continue; }
  tar -xzf "$OUT/$f" -C "$OUT" && rm -f "$OUT/$f"
done < "$OUT/.queue.txt"

echo ""
echo "Done. $(find "$OUT" -maxdepth 1 -type d | tail -n +2 | wc -l | tr -d ' ') sequences in $OUT"
echo "Disk used: $(du -sh "$OUT" | cut -f1)"
