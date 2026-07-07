import argparse
import io
import json
import os
import threading
import urllib.request
from PIL import Image
import datetime
import warnings

import cv2
import torch
from flask import Flask, render_template, request, redirect, jsonify
from sqlalchemy import inspect, text

DATETIME_FORMAT = "%Y-%m-%d_%H-%M-%S-%f"
MODEL_PATH = "best.pt"
DASHBOARD_WINDOW_SECONDS = 5 * 60
HEAD_DASHBOARD_URL = os.environ.get("HEAD_DASHBOARD_URL")
HEAD_DASHBOARD_TOKEN = os.environ.get("HEAD_DASHBOARD_TOKEN")
DEFAULT_CAMERA_ID = os.environ.get("CAMERA_ID", "dashboard-camera")

def load_model():
    global model
    if model is None:
        model = torch.hub.load('ultralytics/yolov5', 'custom', path=MODEL_PATH, trust_repo=True)
        model.eval()
    return model

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


if __name__ == "__main__":
    load_model()
    camera = cv2.VideoCapture(0)
    while True:
        ok, frame = camera.read()
        if not ok:
            continue
        detections = run_detection(frame)
        request.post(
            HEAD_DASHBOARD_URL + "/api/detections",
            json={
                "source_id": DEFAULT_CAMERA_ID,
                "detections": detections
            },
            timeout=2
        )