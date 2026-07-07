import argparse
import io
import os
import requests
from PIL import Image
import datetime
import warnings

import cv2
import torch

DATETIME_FORMAT = "%Y-%m-%d_%H-%M-%S-%f"
MODEL_PATH = "best.pt"
model = None
DASHBOARD_WINDOW_SECONDS = 5 * 60
HEAD_SERVER_URL = "https://real-time-waste-detection.onrender.com"
HEAD_SERVER_TOKEN = os.environ.get("HEAD_SERVER_TOKEN")
DEFAULT_CAMERA_ID = os.environ.get("CAMERA_ID", "dashboard-camera")

def load_model():
    global model
    if model is None:
        model = torch.hub.load('ultralytics/yolov5', 'custom', path=MODEL_PATH, trust_repo=True)
        model.eval()
    return model

def sanitize_source_id(value):
    source_id = (value or DEFAULT_CAMERA_ID).strip()
    return source_id[:255] or DEFAULT_CAMERA_ID

def run_detection(img):
    model = load_model()
    results = model([img])
    detections = []

    for row in results.xyxy[0].detach().cpu().tolist():
        xmin, ymin, xmax, ymax, confidence, class_id = row[:6]
        detections.append({
            "label": results.names[int(class_id)],
            "confidence": round(float(confidence), 4),
            "box": [round(float(xmin), 2), round(float(ymin), 2), round(float(xmax), 2), round(float(ymax), 2)]
        })

    return detections

def send_detections(detections):

    requests.post(
        f"{HEAD_SERVER_URL}/detect",
        json={
            "source_id": DEFAULT_CAMERA_ID,
            "detections": detections
        },
        timeout=2
    )

if __name__ == "__main__":
    load_model()
    camera = cv2.VideoCapture(0)
    while True:
        ok, frame = camera.read()
        if not ok:
            continue
        detections = run_detection(frame)
        img = Image.fromarray(frame)
        detections = run_detection(img)
        send_detections(detections)
        