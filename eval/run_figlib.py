'''Runs best.pt across FIglib'''

import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ultralytics import YOLO 
from figlib_eval import build_conf_table, load_conf_table, sweep, operating_point

SEQ_ROOT = 'data/figlib' # where sequence folders are located 
WEIGHTS = 'models/best.pt' # location of trained model 
CSV = 'results/figlib_conf.csv' # csv location

os.makedirs('results', exist_ok=True) # where our results will go 

seq_dirs = sorted(
    os.path.join(SEQ_ROOT, d) for d in os.listdir(SEQ_ROOT)
    if os.path.isdir(os.path.join(SEQ_ROOT, d)) # each item in directory is 'd' 
# creates list of sequences in figlib 
)
print(f'{len(seq_dirs)} sequences')

if not os.path.exists(CSV): 
    model = YOLO(WEIGHTS)
    print('classes:', model.names)
    build_conf_table(model, seq_dirs, CSV)
else: 
    print(f'reusing {CSV}')
sequences = load_conf_table(CSV)
rows = sweep(sequences)

for budget in(0.5, 1, 2, 5): 
    op = operating_point(rows, max_alarms_per_day=budget, min_detect_rate=0.9)
    print(f'\n<={budget} false alarms/day;')
    print(' ', op if op else 'no config meets this budget')
