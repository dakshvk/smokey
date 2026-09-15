from ultralytics import YOLO 
'''To avoid running PyTorch on Raspberry pi 5'''
m = YOLO('models/best.pt') # contains neural network params 
# converting into ONNX model 
m.export(
    format = 'onnx',
    imgsz = 1024,
    opset = 12, # Operator Set version 12 
    simplify = True, 
    dynamic = False
)

