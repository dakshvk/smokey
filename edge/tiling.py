'''Overlaping tile geometry for high res frames
ive HPWREN frames are 3072x2048. The model runs at 1024. Downscaling the
whole frame shrinks a 30px plume to ~10px so titling keeps the native size'''

from ultralytics.utils.files import increment_path 

def _starts(length, tile, stride): # takes in length of the image, size of each tile, and how far we move the next tile each time
    '''given an imange dimension, tile size, and stride. Returns where each tile should start relative to that dimension'''
    if length <= tile: # if image length is smaller than or equal to tile size 
        return [0] # if so we start at 0 aka the beggining of the image
    starts = list(range(0, length - tile + 1, stride)) # stops at 0 ends at the difference between the length and the tile plus 1 then continues 
    if starts[-1] != length - tile: # is the last start different from the max valid start 
        starts.append(length - tile) # adds where the final tile starts to the end of the list 
    return starts 


def tile_grid(width, height, tile=1024, overlap=128):
    '''covers width x height of image w/ overlapping tiles
returns a list of (x0, y0, x1, y1) in pixels'''
# takes image dimensions and finds out where every tile should go 
    if tile <= 0: #validates tile size 
        raise ValueError(f'tile must be positive got {tile}')
    if not 0 <= overlap < tile: # validates overlap 
        raise ValueError(f'overlap must be in [0, {tile}), got {overlap}')

    stride = tile - overlap # next tile starts 896 pixels later 

    xs = _starts(width, tile, stride) # horizontal starts (x positions where tiles begin)
    ys = _starts(height, tile, stride) # vertical starts (y poisiotns where tiles begin)

    return [(x, y, min(x + tile, width), min(y + tile, height))
            for y in ys for x in xs] # gives the coordinates for each tile as a list (left, top, right, bottom)

def to_full_frame(box, x0, y0):
    ''' takes coordinates inside a tile and converts them to coordinates in the original image '''
    bx1, by1, bx2, by2 = box # bounding box from YOLO
    return [bx1 + x0, by1 +y0, bx2 + x0, by2 + y0]

def _iou(a, b): # duplicated so dont have to deal with unwanted dependencies 
    ax1, ay1, ax2, ay2 = a
    bx1, by1, bx2, by2, = b

    ix1, iy1 = max(ax1, bx1), max(ay1, by1)
    ix2, iy2 = min(ax2, bx2), min(ay2, by2)

    inter = max(ix2 - ix1, 0) * max(iy2 - iy1, 0)
    area_a = (ax2-ax1) * (ay2 - ay1)
    area_b = (bx2 - bx1) * (by2 - by1) 

    return inter / (area_a +area_b - inter + 1e-6)

def merge(detections , iou_thresh=0.4): 
    '''removes duplicate detections from all overlaps in the tiles'''
    kept = []
    for d in sorted(detections, key = lambda d: -d['conf']): 
        if not any(_iou(d['xyxy'], k['xyxy']) >= iou_thresh for k in kept):
            kept.append(d)
    return kept 




