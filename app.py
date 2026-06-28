import argparse
import base64
import io
import json
import os
import threading
import urllib.request
from PIL import Image
import datetime
import warnings

import torch
from flask import Flask, render_template, request, redirect, jsonify
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import inspect, text

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///data.db'
db = SQLAlchemy(app)
model = None
warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", category=FutureWarning)

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
        model = torch.hub.load('ultralytics/yolov5', 'custom', path=MODEL_PATH)
        model.eval()
    return model

def run_detection(img):
    active_model = load_model()
    results = active_model([img])
    detections = []

    for row in results.xyxy[0].detach().cpu().tolist():
        xmin, ymin, xmax, ymax, confidence, class_id = row[:6]
        detections.append({
            "label": results.names[int(class_id)],
            "confidence": round(float(confidence), 4),
            "box": [round(float(xmin), 2), round(float(ymin), 2), round(float(xmax), 2), round(float(ymax), 2)]
        })

    results.render()
    rendered = Image.fromarray(results.ims[0])
    return rendered, detections

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

def post_dashboard_payload(payload):
    if not HEAD_DASHBOARD_URL:
        return

    body = json.dumps(payload).encode("utf-8")
    headers = {"Content-Type": "application/json"}
    if HEAD_DASHBOARD_TOKEN:
        headers["Authorization"] = f"Bearer {HEAD_DASHBOARD_TOKEN}"

    req = urllib.request.Request(
        HEAD_DASHBOARD_URL,
        data=body,
        headers=headers,
        method="POST"
    )

    try:
        urllib.request.urlopen(req, timeout=2).close()
    except Exception as error:
        app.logger.warning("Unable to post dashboard payload: %s", error)

def send_dashboard_payload(payload):
    thread = threading.Thread(target=post_dashboard_payload, args=(payload,), daemon=True)
    thread.start()


@app.route("/detect", methods=["POST"])
def detect_frame():
    if "frame" not in request.files:
        return jsonify({"error": "No frame uploaded"}), 400

    frame = request.files["frame"].read()
    source_id = sanitize_source_id(request.form.get("source_id") or request.args.get("source_id"))
    img = Image.open(io.BytesIO(frame)).convert("RGB")
    rendered, detections = run_detection(img)
    record_detection_events(detections, source_id)
    dashboard_payload = get_dashboard_payload()
    send_dashboard_payload(dashboard_payload)

    buffer = io.BytesIO()
    rendered.save(buffer, format="JPEG", quality=85)
    encoded_image = base64.b64encode(buffer.getvalue()).decode("utf-8")

    return jsonify({
        "image": f"data:image/jpeg;base64,{encoded_image}",
        "source_id": source_id,
        "detections": detections,
        "dashboard": dashboard_payload
    })

@app.route("/dashboard-data", methods=["GET"])
def dashboard_data():
    payload = get_dashboard_payload()
    wants_json = (
        request.args.get("format") == "json"
        or request.accept_mimetypes.best == "application/json"
    )
    if wants_json:
        return jsonify(payload)

    return render_template("dashboard.html", dashboard=payload)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Flask app exposing yolov5 models")
    parser.add_argument("--port", default=5000, type=int, help="port number")
    args = parser.parse_args()
    
    with app.app_context():
        ensure_schema()
    load_model()
    app.run(host="0.0.0.0", port=args.port)  # debug=True causes Restarting with stat
