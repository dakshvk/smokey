from ultralytics import YOLO 
'''To avoid running PyTorch on Raspberry pi 5'''
m = YOLO('models/best.pt') # contains neural network params 
# converting into ONNX model 
m.export(
    format = 'onnx',
    imgsz = 1024,
    opset = 13, # opset 12 doesn't support the axis attribute on QuantizeLinear/
    # DequantizeLinear, which quantize.py's per_channel=True needs - int8 export
    # loads fine at opset 12 but quantize_static() produces an invalid graph
    simplify = True, 
    dynamic = False
)

