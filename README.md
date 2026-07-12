## Introduction

 This project utilizes a YOLOv5 model that was trained by @sleepingcat4 to detect trash and garbage in natural enviornments. 

### Dataset
This project uses a modified TACO dataset. This is provided by @manaporkun, and was utilized by @sleepingcat4.
<a href="https://universe.roboflow.com/alpha-tauri/plastic-project">
    <img src="https://app.roboflow.com/images/download-dataset-badge.svg"></img>
</a>

worker.py is to be run from any machine connected to the internet with a camera that you want to post to the dashboard.
The webcam mode sends frames from the browser to `/detect`, runs the YOLOv5 model on each frame, and displays the annotated result back on the page.

##### Head Dashboard Metrics
Each detection is recorded as a timestamped event. The app tracks the count per label over the last 5 minutes.
This project's head.py is being run on the service Render, at https://real-time-waste-detection.onrender.com/

The dashboard response includes both aggregate label counts and per-camera counts.

#### Acknowledgement
A project developed based on the detection model by @sleepingcat4 and their team. Licenced under Open Source **GPL 3**.
https://github.com/sleepingcat4/wasteclassification 
