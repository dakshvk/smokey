'''Quantizing best.onnx (INT8 quantization)
Making model faster and smaller for the realistic edge devices
(smoke detecing cameras out in the field)'''

import os, glob, random, re # find files based on patterns
#  randomly select subset of images for calibration
import numpy as np # constructing numerical arrays
import onnx # reading the graph to find the detect head's node names
from PIL import Image
from onnxruntime.quantization import quantize_static, CalibrationDataReader, QuantType, QuantFormat
# module optimizes onnx models, faster inference speed than dynamic quantization: requires sample datset for calibration
# CDR helps feed the sample input data into quantizer for static quantization - use as subclass
# QT specifies target data type for quanitzed weights, QF determines how the quantization ops are inserted into the onnx compute graph

IMGSZ = 1024

def prep(path): # path to image
    '''Takes JPG and turns it into the numerical format the ONNX model expects'''
    im = Image.open(path).convert('RGB').resize((IMGSZ, IMGSZ)) # opens img converts to RGB then resizes
    a = np.asarray(im, dtype=np.float32)/ 255.0 # converts image into NumPy array
    # stores pixel values as 32 bit floating point numbers and then divides by 255 which normalizes the the pixel values into the RBG range
    # gives onnx model normalized input
    return np.transpose(a, (2, 0, 1))[None] # rearranges the array a's dimensions adding batch to height, width, channels and making it follow N, C, H, W
# none inside indexing creates a new dimension in our case N(batch)

class Reader(CalibrationDataReader):
    '''Calibrates on HPWREN data. Quantisation picks per tensor scales from this input data'''
    def __init__(self, files, inp):
        self.data = iter([{inp: prep(f)} for f in files])
    # turns list given from prep() into an iterator

    def get_next(self):
        return next(self.data, None)
    # called whenever we need a new claibration image

random.seed(0)
pool = glob.glob('data/figlib/*/*.jpg') # searches for all JPG images under data/figlib
files = random.sample(pool, min(300, len(pool))) # selects up to 300 imgs

import onnxruntime as ort # inspect onnx model
inp = ort.InferenceSession('models/best.onnx').get_inputs()[0].name
# loads onnx model gets a list of inputs and takes the first one

# the detect head (DFL softmax/conv decode + box-coordinate arithmetic) is too
# numerically fragile for int8 - quantizing it produces zero detections on every
# frame, including obvious fires. find the last model.N block by node name and
# keep it in float32; everything before it (backbone/neck, most of the compute)
# still gets quantized.
graph = onnx.load('models/best.onnx').graph
blocks = sorted({int(m.group(1)) for n in graph.node
                  if (m := re.match(r'/model\.(\d+)/', n.name))})
head_prefix = f'/model.{blocks[-1]}/'
exclude = [n.name for n in graph.node if n.name.startswith(head_prefix)]
print(f'excluding {len(exclude)} detect-head nodes ({head_prefix}) from quantization')

# now static quantization starts after making sure the input data is converted to onnx specifcations
quantize_static(
    'models/best.onnx', 'models/best_int8.onnx',  # starting model & output model
    # creating 2nd model for comparison
    Reader(files, inp), # gives ONNX runtime calibration data (300 imgs)
    quant_format=QuantFormat.QDQ, # preresents quantization using quantize and dequantize nodes
    # true because different convolution filters can have very different weight ranges
    per_channel=True, # lets each channel get a more appropriate qunatization scale to their own having better accuracy
    weight_type=QuantType.QInt8, # original models weights are FloatingPoint32 onnx runtime is quantizing them to Int8
    # looking at weights datatype
    # using default activation type don't want to use slower kernels for no accuary benefits
    nodes_to_exclude=exclude, # keep the fragile detect head in float32
)

print('wrote models/best_int8.onnx')
