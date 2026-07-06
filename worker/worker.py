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
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import inspect, text

DATETIME_FORMAT = "%Y-%m-%d_%H-%M-%S-%f"
MODEL_PATH = "best.pt"
DASHBOARD_WINDOW_SECONDS = 5 * 60
HEAD_DASHBOARD_URL = os.environ.get("HEAD_DASHBOARD_URL")
HEAD_DASHBOARD_TOKEN = os.environ.get("HEAD_DASHBOARD_TOKEN")
DEFAULT_CAMERA_ID = os.environ.get("CAMERA_ID", "dashboard-camera")


class DetectionEvent(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    source_id = db.Column(db.String(255), nullable=False, default=DEFAULT_CAMERA_ID, index=True)
    label = db.Column(db.String(255), nullable=False, index=True)
    confidence = db.Column(db.Float)
    timestamp = db.Column(db.DateTime, default=datetime.datetime.utcnow, index=True)

def sanitize_source_id(value):
    source_id = (value or DEFAULT_CAMERA_ID).strip()
    return source_id[:255] or DEFAULT_CAMERA_ID

def ensure_schema():
    db.create_all()
    inspector = inspect(db.engine)
    columns = {column["name"] for column in inspector.get_columns("detection_event")}
    if "source_id" not in columns:
        default_source_id = DEFAULT_CAMERA_ID.replace("'", "''")
        with db.engine.begin() as connection:
            connection.execute(text(
                "ALTER TABLE detection_event "
                f"ADD COLUMN source_id VARCHAR(255) NOT NULL DEFAULT '{default_source_id}'"
            ))

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

def record_detection_events(detections, source_id=DEFAULT_CAMERA_ID):
    if not detections:
        return

    now = datetime.datetime.utcnow()
    source_id = sanitize_source_id(source_id)
    for detection in detections:
        db.session.add(DetectionEvent(
            source_id=source_id,
            label=detection["label"],
            confidence=detection["confidence"],
            timestamp=now
        ))
    db.session.commit()

def get_dashboard_payload(window_seconds=DASHBOARD_WINDOW_SECONDS):
    now = datetime.datetime.utcnow()
    window_start = now - datetime.timedelta(seconds=window_seconds)
    rows = (
        db.session.query(DetectionEvent.label, db.func.count(DetectionEvent.id))
        .filter(DetectionEvent.timestamp >= window_start)
        .group_by(DetectionEvent.label)
        .all()
    )
    camera_rows = (
        db.session.query(
            DetectionEvent.source_id,
            DetectionEvent.label,
            db.func.count(DetectionEvent.id)
        )
        .filter(DetectionEvent.timestamp >= window_start)
        .group_by(DetectionEvent.source_id, DetectionEvent.label)
        .all()
    )
    counts = {label: count for label, count in rows}
    cameras = {}
    for source_id, label, count in camera_rows:
        camera = cameras.setdefault(source_id, {"counts": {}, "total": 0})
        camera["counts"][label] = count
        camera["total"] += count

    return {
        "generated_at": now.isoformat() + "Z",
        "window_seconds": window_seconds,
        "window_start": window_start.isoformat() + "Z",
        "magnitude": "count_per_label",
        "counts": counts,
        "cameras": cameras,
        "total": sum(counts.values())
    }


if __name__ == "__main__":
    load_model()
    camera = cv2.VideoCapture(0)
    while True:
        ok, frame = camera.read()
        if not ok:
            continue
        detections = run_detection(frame)
        requests.post(
            HEAD_URL + "/detect",
            json={
                "source_id": CAMERA_ID,
                "detections": detections
            },
            timeout=2
        )