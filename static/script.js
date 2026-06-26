const themeToggle = document.getElementById('theme-toggle');
const body = document.body;
const video = document.getElementById('webcam');
const prediction = document.getElementById('prediction');
const placeholder = document.getElementById('camera-placeholder');
const canvas = document.getElementById('capture-canvas');
const startButton = document.getElementById('start-camera');
const stopButton = document.getElementById('stop-camera');
const statusText = document.getElementById('status');
const detectionsList = document.getElementById('detections-list');

let stream = null;
let detectionTimer = null;
let isDetecting = false;

themeToggle.addEventListener('change', () => {
    body.classList.toggle('dark');
});

function setStatus(message) {
    statusText.textContent = message;
}

function renderDetections(detections) {
    detectionsList.innerHTML = '';

    if (!detections.length) {
        const item = document.createElement('li');
        item.textContent = 'No waste detected';
        detectionsList.appendChild(item);
        return;
    }

    detections.slice(0, 8).forEach((detection) => {
        const item = document.createElement('li');
        const percent = Math.round(detection.confidence * 100);
        item.textContent = `${detection.label} ${percent}%`;
        detectionsList.appendChild(item);
    });
}

async function detectFrame() {
    if (!stream || isDetecting || video.readyState < HTMLMediaElement.HAVE_CURRENT_DATA) {
        return;
    }

    isDetecting = true;
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;

    const context = canvas.getContext('2d');
    context.drawImage(video, 0, 0, canvas.width, canvas.height);

    canvas.toBlob(async (blob) => {
        if (!blob) {
            isDetecting = false;
            return;
        }

        const formData = new FormData();
        formData.append('frame', blob, 'webcam.jpg');

        try {
            const response = await fetch('/detect', {
                method: 'POST',
                body: formData
            });

            if (!response.ok) {
                throw new Error('Detection request failed');
            }

            const data = await response.json();
            prediction.src = data.image;
            prediction.hidden = false;
            placeholder.hidden = true;
            renderDetections(data.detections || []);
            setStatus('Detecting');
        } catch (error) {
            setStatus('Detection unavailable');
        } finally {
            isDetecting = false;
        }
    }, 'image/jpeg', 0.8);
}

async function startCamera() {
    try {
        stream = await navigator.mediaDevices.getUserMedia({
            video: {
                width: { ideal: 960 },
                height: { ideal: 540 },
                facingMode: 'environment'
            },
            audio: false
        });

        video.srcObject = stream;
        await video.play();

        startButton.disabled = true;
        stopButton.disabled = false;
        placeholder.hidden = true;
        setStatus('Camera active');
        detectionTimer = window.setInterval(detectFrame, 700);
        detectFrame();
    } catch (error) {
        setStatus('Camera permission needed');
    }
}

function stopCamera() {
    if (detectionTimer) {
        window.clearInterval(detectionTimer);
        detectionTimer = null;
    }

    if (stream) {
        stream.getTracks().forEach((track) => track.stop());
        stream = null;
    }

    video.srcObject = null;
    prediction.removeAttribute('src');
    prediction.hidden = true;
    placeholder.hidden = false;
    startButton.disabled = false;
    stopButton.disabled = true;
    setStatus('Idle');
    renderDetections([]);
}

startButton.addEventListener('click', startCamera);
stopButton.addEventListener('click', stopCamera);
