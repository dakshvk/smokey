'''Same FIgLib scoring as run_FIglib.py but each frame is tiled 
trying to test whether 1024x1024 tiling strategy is better than shrinking entire 3071x2048 image down to model input's size'''

import os, sys, csv
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
# looking into script directory and parent directory when importing files 
from PIL import Image # open images and crop them 
from ultralytics import YOLO
from edge.tiling import tile_grid 
from figlib_eval import load_sequence, load_conf_table, sweep, operating_point

SEQ_ROOT = 'data/figlib' # config settings 
WEIGHTS = 'models/best.pt'
CSV = 'results/figlib_conf_tiled.csv'
TILE, OVERLAP = 1024, 128

def build_conf_table_tiled(model, seq_dirs, out_path): # model, figlib sequences, where to save results 
    '''per frame runs every tile keeping the highest single confidence'''
    with open(out_path, 'w', newline='') as f: # opens output csv
        w = csv.writer(f) # writes into csv object f 
        w.writerow(['sequence', 'offset', 'max_conf']) # row names 
        for seq_dir in seq_dirs: # loops through sequences
            seq = os.path.basename(seq_dir.rstrip('/'))
            for offset, path in load_sequence(seq_dir): # loops through every frame 
                img = Image.open(path) # opens frame
                crops = [img.crop(b) for b in tile_grid(img.width, img.height, TILE, OVERLAP)]
                # cuts the rectangle out of original frame then becomes a list of image objects 
                results = model.predict(source=crops, conf = 0.001, verbose=False) # runs YOLO on all tiles 
                confs = [float(b.conf[0]) for r in results for b in r.boxes] # for every result: for every bounding box: get its confidence 
                w.writerow([seq, offset, max(confs) if confs else 0.0]) # keeps highest confidence & writes the frames result 
            print(f' done{seq}') # progress checker after completing a sequence 

os.makedirs('results', exist_ok=True) # results directory 
seq_dirs = sorted( # goes into figlib directory and finds all sequences 
    os.path.join(SEQ_ROOT, d) for d in os.listdir(SEQ_ROOT)
    if os.path.isdir(os.path.join(SEQ_ROOT, d))   
)

if not os.path.exists(CSV): # doesnt redo expensive inferences 
    build_conf_table_tiled(YOLO(WEIGHTS), seq_dirs, CSV)
else: 
    print(f'reusing{CSV}')
rows = sweep(load_conf_table(CSV)) # evaluation 
for budget in (0.5, 1, 2, 5): # testing diff false alarm budgets 
    op = operating_point(rows, max_alarms_per_day=budget, min_detect_rate=0.9)
    print(f'\n<={budget} flase alarms/day (TILED):')
    print(' ', op if op else 'no config meets this budget')

         
         