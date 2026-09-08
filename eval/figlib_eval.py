'''Scores Model on FIigLib/HPWREN dataset'''

import os 
import statistics 
import csv 
from collections import defaultdict 

def parse_offset(filename):
    ''' turns 1465063200_-02400.jpg' -> -2400 seconds relative to ignition'''
    stem = filename.rsplit('.',1)[0] # filename contains timestamp followed by offset so this line removes the .jpg
    return int(stem.split('_')[1]) # splits at _ and gives us the 2nd index which is the timestamp 

def load_sequence(seq_dir): 
    '''input is FigLib sequence/folder and through the offset path gives us the order of the frames earliest to latest'''
    frames = [] # takes in frames in a list 
    for name in os.listdir(seq_dir): # grabs everything in folder going through them one at a time 
        if not name.endswith('.jpg'):
            continue # skips .mp4 files and any other non jpg files
        frames.append((parse_offset(name), 
os.path.join(seq_dir, name)))
    frames.sort() # sorts by offset and final output is a tuple (offset, seq_dir/num_in_seq)
    return frames 


def build_conf_table(model, seq_dirs, out_path):
    '''YOLO MODEL, sequence of directories and out_path = resulting csv
    for every image frame we are going to recod the highest conf score that the model 
    assgined to any detected object in that frame'''

    with open (out_path, 'w', newline = '') as f: # opens output csv 
        w = csv.writer(f) # write mode and writer 
        w.writerow(['sequence', 'offset', 'max_conf']) # header of row 
        for seq_dir in seq_dirs: # loops through seqeunce directory 
            seq = os.path.basename(seq_dir.rstrip('/')) # gets name and final part of path removing the 2nd /
            frames = load_sequence(seq_dir) # loads frames 
            results = model.predict(source=[p for _, p in frames], # runs the model 
                                    conf = 0.001, verbose=False, stream=True)
            for (offset, _), r in zip(frames, results): # loops through frames and results together where zip() pairs em together 
                confs = [float(b.conf[0]) for b in r.boxes]
                w.writerow([seq, offset, max(confs) if confs else 0.0])

def load_conf_table(path): 
    seqs= defaultdict(list)

    with open(path) as f: 
        for row in csv.DictReader(f): 
            seqs[row['sequence']].append(
                (int(row['offset']), float(row['max_conf'])))
    return [sorted(v) for v in seqs.values()]



def fires(confs, i, threshold, K, M):
    '''True when at least K of the last M frames are greater than or equal to threshold'''
    window = confs[max(0, i - M +1): i + 1] # takes in conf, the current frame, threshold of a positive detection, how many frames to meet threshold(K), and M how many recent frames we are going to look at  
# looks at last M frames ending at frame i but never goes before the beggining of the list
    return sum(1 for c in window if c >= threshold) >= K # indexes the confidence and last few frames and selects max conf from those last few frames
# counts how many values are above threshold as 1 then adds them up then if greater than or equal to K 'fires'returns TRUE  


def score_sequence(frames, threshold, K, M): 
    '''main scoring function answering 'is there an alarm right now?
    Looks across every frame in the sequence and figures out 'How many false alarams happened before the fire started and when the fire was first detected after ignition?'''
# takes in tuple of offsets and confidence from sequene of frames
    offsets = [o for o, _ in frames] # offset relative to ignition & calls it o ignores other value 
    confs = [c for _, c in frames] # model confidence for that frame & pulls out 2nd value instead

    false_alarms = 0 # starts counter 
    armed = True # ready to count an alarm 

    detect_offset = None # stores when fire was first detected 

    for i, off in enumerate(offsets): # loops through each fram while giving its index 
        hot = fires(confs, i, threshold, K, M) # stores functions boolean value 
        if off < 0: # checks if we're before ignition 
            if hot and armed: # before ignition and model thinks thres a fire it raises false alarm value 
                false_alarms += 1 # counts false alarms before ignition 
                armed = False # already in alarm don't count again 
            elif not hot: 
                armed = True # arms model again if no sense of fire before ignition 
        else: # after ignition 
            if hot and detect_offset is None: # model is detecting fire and this is the first time its detecting it 
                detect_offset = off # records when detection happened 
    return {'false_alarms': false_alarms, 'detect_offset': detect_offset}
# returns dict with # of false alarms and when the real fire was detected after ignition as detection time 

def sweep(sequences, thresholds=None, Ks=(1, 2, 3, 4, 5), M_extra=(0, 1, 2, 3)): 
    if thresholds is None: # want to test confidence thresholds so we create them 
        thresholds = [i/100 for i in range(1,100)] 

    rows = []
    for th in thresholds: # trys every threshold 
        for K in Ks: # trys every K 
            for extra in M_extra: # trys every M value 
                M = K + extra 
                alarms = 0 
                pre_minutes = 0
                detects = [] # resets measurements
                for frames in sequences: # loops through every sequence after picking a particular configuration 
                    s = score_sequence(frames, th, K, M) 
                    alarms += s['false_alarms']  # adds its false alarms to the total 
                    pre_minutes += sum(1 for o, _ in frames if o < 0) # counts fire-free minutes
                    if s['detect_offset'] is not None: # checks if this sequence detected the fire 
                        detects.append(s['detect_offset']) # adds detection time to list if it was detected
                        # using this to calc the median val 
                rows.append({
                    'thresh': th,
                    'K': K, # how many + frames required
                    'M': M, # how many recent frames to look at
                    'alarms_per_day': alarms / (pre_minutes /1440) if pre_minutes else 0.0, # counts # of false alarms per day 
                    'detect_rate': len(detects) / len(sequences) if sequences else 0.0, # what fraction of sequences sucssesfullt detected by fire 
                    'median_ttd_min': statistics.median(detects)/ 60 if detects else None, # typical time till detection as mean can be distorted 
                })
    return rows

def operating_point(rows, max_alarms_per_day, min_detect_rate=0.9):
    '''from all configs tested in sweep() throw away anything with too many false alarms,
     anything that doesn't detect fires enough, then choose remaining configs w fastest median detection time'''

    ok = [r for r in rows # Creates new list called ok going through each row at a time 
          if r['alarms_per_day']<= max_alarms_per_day # keeps row if false alarms are at or below mad allowed amount
          and r['detect_rate'] >= min_detect_rate 
          and r['median_ttd_min'] is not None] # making sure we have a detection time 
    return min(ok, key=lambda r: r['median_ttd_min']) if ok else None 
# gives the minimum median ttd value from ok 
