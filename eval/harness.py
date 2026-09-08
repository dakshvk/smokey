'''
At a confidence threshold where the false-alarm rate is acceptable 
what fraction of real fires does this catch? 
Detecting False Positives 
Produces a Threshold Sweep for each confiedence cutoff 0-1 
Produces the operating point then report recall there 
Buckets by box size as 38% of boxes are under 0.1% of the whole frame
'''
from ultralytics import YOLO

if __name__ == '__main__':
    model = YOLO('models/best.pt') # Getting predictions out of model 
    results = model.predict(
        source='/path/to/images/val', # holds trained weights 
        conf=0.001, # reports all detections
        iou=0.7, # how much iou boxes need to overlap to be counted as seperate  
        verbose=False
    )# returns list of results objects one per image 
    # flattening predcitions into plain rows 
    preds = []

    for r in results: 
        for box in r.boxes: # attribute holding all detections in an image
            preds.append({
                'image': r.path,
                'conf': float(box.conf[0]), # one elemtn Tensor shape 
                'xyxy': box.xyxy[0].tolist() # x1, y1, x2, y2 in pixels 
            }) # Tensor in shape (1, 4) converts to plain python list 

    '''Comparing every prediction bounding box with every ground truth box'''

    '''Scalar Version'''

    def compute_iou(box_a, box_b):
        """IoU of two boxes in [x1, y1, x2, y2] pixel format. Returns 0.0-1.0."""
        ax1, ay1, ax2, ay2 = box_a
        bx1, by1, bx2, by2 = box_b

        # whose left edge is further right and whose top edge is lower 
        ix1, iy1 = max(ax1, bx1), max(ay1, by1) # intersection rectangle 
        ix2, iy2 = min(ax2, bx2), min(ay2, by2)
        # doesnt go into negatives so min max sets is 0 
        inter = max(ix2 - ix1, 0) * max(iy2 - iy1, 0)
        area_a = (ax2 - ax1) * (ay2 - ay1)
        area_b = (bx2 - bx1) * (by2 - by1)

        return inter / (area_a + area_b - inter + 1e-6)

    def yolo_to_xyxy(line, img_w, img_h):
        '''One yolo annotation into [x1, y1, x2, y2,] pixels so every other fucntion downstream can work off the pixels no need for extra threading
        '''
        _, xc, yc, w, h = [float(p) for p in line.split()]
        # class_id
        bw, bh = w * img_w, h * img_h # conversion to pixels
        return [xc*img_w -bw/2, yc*img_h -bh/2, # centre plus and minus a half to get min/mac corners
                xc*img_w + bw/2, yc*img_h + bh/2]

    def match(preds, truths, iou_thresh=0.5):
        '''labels each prediction true_positives or false_positives; unclaimed become false_negatives'''
        claimed, tp, fp = set(), [], []
        for p in sorted(preds, key=lambda x: -x['conf']): # sorts by highest confidence first 
        # counts as false postiive bc is a duplicate detection
            best_iou, best_j = 0.0, None
            for j, t in enumerate(truths): # pairs each item w its position 
            # returns tuples (0,'a')... so tracks which truths are alr clamied 
            # finds the best iou out of the incoming truth boxes 
                if j in claimed: 
                    continue # skips rest of pass if j is alr in claimed 
                v = compute_iou(p['xyxy'], t)
                if v > best_iou: 
                    best_iou, best_j = v, j # so it tracks the best match claiming the turth that always fits better

            if best_iou >= iou_thresh:
                claimed.add(best_j)
                # adds index j into the set 
                tp.append(p)
            else: 
                fp.append(p)
        fn = [t for j, t in enumerate(truths) if j not in claimed]
        return tp, fp, fn 

    def sweep(per_image, thresholds=None, iou_thresh=0.5):
        # At this confidencce threshold how many fires do i correclty detetc and how many false alarms so i get and how many fires do i miss 
        '''Precision and recall at each confidence cutoff, 
    per_image: list of (predictions, truths) tuples one per imag 
    returns a list of dicts, one per thrshold'''
    # takes in predicions and truths for each image
        if thresholds is None: # confidence levels we want to test at
            thresholds = [i/100 for i in range(1,100)]
    # mutable so can end up using the same list across mutltiple calls
        rows =[]
        n_images = len(per_image) # count how many images 
        for th in thresholds: # picks a threshold value 
            TP = FP = FN = 0 
            # immutable
            for preds, truths in per_image: # counts the results across all images for that threshold 
                kept = [p for p in preds if p['conf'] >= th] 
                # filters out predictions below conf threshold
                tp, fp, fn = match(kept, truths, iou_thresh) # compares predictions against real boxes 
                TP += len(tp)
                FP += len(fp)
                FN += len(fn) # adds reuslts to the total for that threshold

            rows.append({
                'thresh': th, 
                'tp': TP, 
                'fp': FP, 
                'fn': FN,
                'precision': TP/(TP + FP) if (TP + FP) > 0 else 1.0,
                'recall': TP/max(TP + FN, 1),
                'fp_per_image': FP / max(n_images, 1), # calculates precision and saves those reuslts 
            })
        return rows

    def operating_point(rows, max_fp_per_image): 
        '''lowest threshold where false alarm rate stays inside the budget
        returns one row dict or none if no threshold meets the budget'''
        ok = [r for r in rows if r['fp_per_image'] <= max_fp_per_image]
        return min(ok, key=lambda r: r['thresh']) if ok else None # if 'ok' contains something else return none  
    # takes result from sweep where each r is one table then with max_fp_per_image which is 
    # our max accepetable flase alaram rate it just finds and gives us the acceptable rows 
    # then finds the row with the lowest threshold that meets our false alaram requirement 

    def size_bucket(box, img_w=1280, img_h=720):
        '''2px error destroys a tiny boxes IoU so this checks how much of the image the box occupys 
        '''
        x1, y1, x2, y2 = box 
        frac = ((x2-x1)*(y2-y1)) / (img_w*img_h) # box's area/image area
        return 'small' if frac < 0.001 else 'medium' if frac < 0.01 else 'large'




