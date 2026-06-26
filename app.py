import argparse
import base64
import io
import os
from PIL import Image
import datetime

import torch
from flask import Flask, render_template, request, redirect, jsonify
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///data.db'
db = SQLAlchemy(app)
model = None

DATETIME_FORMAT = "%Y-%m-%d_%H-%M-%S-%f"
MODEL_PATH = "best.pt"

class UploadedImage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255))
    path = db.Column(db.String(255))
    timestamp = db.Column(db.DateTime, default=datetime.datetime.utcnow)

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

@app.route("/", methods=["GET", "POST"])
def predict():
    if request.method == "POST":
        if "file" not in request.files:
            return redirect(request.url)
        file = request.files["file"]
        if not file:
            return

        img_bytes = file.read()
        img = Image.open(io.BytesIO(img_bytes))
        rendered, _ = run_detection(img)

        now_time = datetime.datetime.now().strftime(DATETIME_FORMAT)
        img_savename = f"static/{now_time}.png"
        rendered.save(img_savename)

        return redirect(img_savename)

    return render_template("index.html")

@app.route("/detect", methods=["POST"])
def detect_frame():
    if "frame" not in request.files:
        return jsonify({"error": "No frame uploaded"}), 400

    frame = request.files["frame"].read()
    img = Image.open(io.BytesIO(frame)).convert("RGB")
    rendered, detections = run_detection(img)

    buffer = io.BytesIO()
    rendered.save(buffer, format="JPEG", quality=85)
    encoded_image = base64.b64encode(buffer.getvalue()).decode("utf-8")

    return jsonify({
        "image": f"data:image/jpeg;base64,{encoded_image}",
        "detections": detections
    })


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Flask app exposing yolov5 models")
    parser.add_argument("--port", default=5000, type=int, help="port number")
    args = parser.parse_args()
    
    with app.app_context():
        db.create_all()
    load_model()
    app.run(host="0.0.0.0", port=args.port)  # debug=True causes Restarting with stat
