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
* Open `http://localhost:5000` in a browser
* Click `Start Camera` and allow webcam access for real-time detection

The webcam mode sends frames from the browser to `/detect`, runs the YOLOv5 model on each frame, and displays the annotated result back on the page.

#### Acknowledgement
A project developed based on the work by @sleepingcat4 and their team. Licenced under Open Source **GPL 3**.
https://github.com/sleepingcat4/wasteclassification 
