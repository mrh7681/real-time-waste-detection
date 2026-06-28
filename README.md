## Introduction

 This project utilizes a YOLOv5 model that was trained by @sleepingcat4 to detect trash and garbage in natural enviornments. 

### Dataset
This project uses a modified TACO dataset. This is provided by @manaporkun, and was utilized by @sleepingcat4.
<a href="https://universe.roboflow.com/alpha-tauri/plastic-project">
    <img src="https://app.roboflow.com/images/download-dataset-badge.svg"></img>
</a>

##### Running Flask
* Open `terminal`
* Navigate to the repository
* Inside the repo run `python app.py`
* Open `http://localhost:5000/dashboard-data` in a browser
* Click `Start Camera` and allow webcam access for real-time detection

The webcam mode sends frames from the browser to `/detect`, runs the YOLOv5 model on each frame, and displays the annotated result back on the page.

##### Head Dashboard Metrics
Each detection is recorded as a timestamped event. The app tracks the count per label over the last 5 minutes.

You can view the live HTML dashboard locally:

http://localhost:5000/dashboard-data


##### Camera Network
The dashboard at `http://localhost:5000/dashboard-data` can start a browser camera directly. Set the `Source ID` field before starting the camera to identify that camera in the network.

Additional cameras can be added by posting frames to the same detection endpoint with a unique `source_id`:

```bash
curl -X POST http://localhost:5000/detect \
  -F "source_id=loading-dock-camera" \
  -F "frame=@frame.jpg"
```

The dashboard response includes both aggregate label counts and per-camera counts.


#### Acknowledgement
A project developed based on the work by @sleepingcat4 and their team. Licenced under Open Source **GPL 3**.
https://github.com/sleepingcat4/wasteclassification 
