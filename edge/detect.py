'''Load's the YOLO model oncem then uses it to score incoming images'''

from dataclasses import dataclass, field 
from io import BytesIO # create in-memory file-like object so we dont have to save the jpeg to disk 

from PIL import Image # turns image into object for YOLO processing 
from ultralytics import YOLO 

@dataclass 
class Dectection: # holds results 
    max_conf: float = 0.0
    boxes: list = field(default_factory=list) # stores bounding boxes in a list 'xyxy': [lst]
    # default_factory makes sure each new detection gets its own list 

class Detector: # runs the model 
    def __init__(self, weights: str, conf_floor: float = 0.001, imgsz: int=1024):
        self.model = YOLO(weights) # path to model & loads it 
        self.conf_floor = conf_floor # min conf YOLO will report 
        self.imgsz = imgsz
        print(f'detector ready: {weights} classes={self.model.names}')
        # prints actual weights path and class names model has 

    def score(self, data: bytes) -> Dectection: 
        '''runs model on one JPEG and scores it'''
        img = Image.open(BytesIO(data)).convert('RGB') # converts bytes into image
        # takes raw jpeg bytes and make them behave like a file then opens the file and then converts it into RGB
        r = self.model.predict(source=img, conf=self.conf_floor, 
                            imgsz=self.imgsz, verbose=False)[0] # runs object detection on image 
        # verbose = False makes sure inference info doesnt get printed into terminal 
        # stores image result into r
        boxes = [{'xyxy': [float(v) for v in b.xyxy[0]],
        # loops through detected bounding boxes getting coordinate for that detection b.xyxy
                'conf': float(b.conf[0])} for b in r.boxes]
            # converts each coordinate into python float and gets conf for that detection and stores it into a dict for every detected box 
        return Dectection(max((b['conf'] for b in boxes), default=0.0), boxes)
    # returns detection object pulling out the max confidence 

    

