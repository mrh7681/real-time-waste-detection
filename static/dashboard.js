const totalCount = document.getElementById('total-count');
const labelCount = document.getElementById('label-count');
const lastRefresh = document.getElementById('last-refresh');
const windowRange = document.getElementById('window-range');
const labelBars = document.getElementById('label-bars');
const emptyDashboard = document.getElementById('empty-dashboard');
const statusText = document.getElementById('dashboard-status-text');
const cameraList = document.getElementById('camera-list');
const emptyCameras = document.getElementById('empty-cameras');
const cameraStatus = document.getElementById('camera-status');
const cameraDeviceSelect = document.getElementById('camera-device-select');
const cameraSourceId = document.getElementById('camera-source-id');
const dashboardPrediction = document.getElementById('dashboard-prediction');
const dashboardPlaceholder = document.getElementById('dashboard-camera-placeholder');
const startCameraButton = document.getElementById('dashboard-start-camera');
const previewSourceSelect = document.getElementById('preview-source-select');
const localCameraList = document.getElementById('local-camera-list');
const hiddenCameraStages = document.getElementById('hidden-camera-stages');

const activeCameras = new Map();
let latestDashboardData = window.initialDashboardData || {};
let selectedPreviewSource = '';

function formatTime(value) {
    if (!value) {
        return '--';
    }

    return new Date(value).toLocaleTimeString([], {
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit'
    });
}

function renderDashboard(data) {
    latestDashboardData = data || {};
    const counts = latestDashboardData.counts || {};
    const cameras = latestDashboardData.cameras || {};
    const entries = Object.entries(counts).sort((a, b) => b[1] - a[1]);
    const cameraEntries = Object.entries(cameras).sort((a, b) => b[1].total - a[1].total);
    const maxCount = Math.max(...entries.map((entry) => entry[1]), 1);

    totalCount.textContent = latestDashboardData.total || 0;
    labelCount.textContent = entries.length;
    lastRefresh.textContent = formatTime(latestDashboardData.generated_at);
    windowRange.textContent = `${formatTime(latestDashboardData.window_start)} to ${formatTime(latestDashboardData.generated_at)}`;

    labelBars.innerHTML = '';
    cameraList.innerHTML = '';
    emptyDashboard.hidden = entries.length > 0;
    emptyCameras.hidden = cameraEntries.length > 0;

    entries.forEach(([label, count]) => {
        const row = document.createElement('article');
        row.className = 'label-row';

        const header = document.createElement('div');
        header.className = 'label-row-header';

        const name = document.createElement('strong');
        name.textContent = label;

        const value = document.createElement('span');
        value.textContent = count;

        const track = document.createElement('div');
        track.className = 'label-track';

        const fill = document.createElement('div');
        fill.className = 'label-fill';
        fill.style.width = `${Math.max((count / maxCount) * 100, 4)}%`;

        header.append(name, value);
        track.appendChild(fill);
        row.append(header, track);
        labelBars.appendChild(row);
    });

    cameraEntries.forEach(([sourceId, camera]) => {
        const row = document.createElement('article');
        row.className = 'camera-row';

        const title = document.createElement('div');
        title.className = 'camera-row-title';

        const name = document.createElement('strong');
        name.textContent = sourceId;

        const total = document.createElement('span');
        total.textContent = `${camera.total} detections`;

        const labels = document.createElement('p');
        labels.textContent = Object.entries(camera.counts || {})
            .sort((a, b) => b[1] - a[1])
            .map(([label, count]) => `${label}: ${count}`)
            .join(' | ');

        title.append(name, total);
        row.append(title, labels);
        cameraList.appendChild(row);
    });

    renderPreviewOptions();
    statusText.textContent = 'Live';
}

async function refreshDashboard() {
    try {
        const response = await fetch('/dashboard-data?format=json', {
            headers: { Accept: 'application/json' }
        });

        if (!response.ok) {
            throw new Error('Dashboard data unavailable');
        }

        renderDashboard(await response.json());
    } catch (error) {
        statusText.textContent = 'Offline';
    }
}

function setCameraStatus(message) {
    cameraStatus.textContent = message;
}

function getSourceIdsForPreview() {
    const ids = new Set(Object.keys(latestDashboardData.cameras || {}));
    activeCameras.forEach((camera, sourceId) => {
        ids.add(sourceId);
    });
    return Array.from(ids).sort();
}

function renderPreviewOptions() {
    const sourceIds = getSourceIdsForPreview();
    const currentValue = selectedPreviewSource || previewSourceSelect.value;

    previewSourceSelect.innerHTML = '';

    if (!sourceIds.length) {
        const option = document.createElement('option');
        option.value = '';
        option.textContent = 'No sources available';
        previewSourceSelect.appendChild(option);
        selectedPreviewSource = '';
        renderPreview();
        return;
    }

    sourceIds.forEach((sourceId) => {
        const option = document.createElement('option');
        option.value = sourceId;
        option.textContent = sourceId;
        previewSourceSelect.appendChild(option);
    });

    selectedPreviewSource = sourceIds.includes(currentValue) ? currentValue : sourceIds[0];
    previewSourceSelect.value = selectedPreviewSource;
    renderPreview();
}

function renderPreview() {
    const camera = activeCameras.get(selectedPreviewSource);

    if (camera && camera.latestImage) {
        dashboardPrediction.src = camera.latestImage;
        dashboardPrediction.hidden = false;
        dashboardPlaceholder.hidden = true;
        return;
    }

    dashboardPrediction.removeAttribute('src');
    dashboardPrediction.hidden = true;
    dashboardPlaceholder.hidden = false;

    if (!selectedPreviewSource) {
        dashboardPlaceholder.textContent = 'Select a preview source';
    } else if (activeCameras.has(selectedPreviewSource)) {
        dashboardPlaceholder.textContent = 'Waiting for detection preview';
    } else {
        dashboardPlaceholder.textContent = `${selectedPreviewSource} has no preview`;
    }
}

function renderLocalCameraList() {
    localCameraList.innerHTML = '';

    activeCameras.forEach((camera, sourceId) => {
        const row = document.createElement('article');
        row.className = 'camera-row';

        const title = document.createElement('div');
        title.className = 'camera-row-title';

        const name = document.createElement('strong');
        name.textContent = sourceId;

        const state = document.createElement('span');
        state.textContent = camera.status;

        const stopButton = document.createElement('button');
        stopButton.type = 'button';
        stopButton.className = 'camera-stop-button';
        stopButton.textContent = 'Stop';
        stopButton.addEventListener('click', () => stopLocalCamera(sourceId));

        title.append(name, state);
        row.append(title, stopButton);
        localCameraList.appendChild(row);
    });

    const count = activeCameras.size;
    setCameraStatus(count ? `${count} active` : 'No cameras');
}

async function loadCameraDevices() {
    if (!navigator.mediaDevices?.enumerateDevices) {
        cameraDeviceSelect.innerHTML = '<option value="">Camera list unavailable</option>';
        startCameraButton.disabled = true;
        return;
    }

    const devices = await navigator.mediaDevices.enumerateDevices();
    const videoDevices = devices.filter((device) => device.kind === 'videoinput');

    cameraDeviceSelect.innerHTML = '';
    if (!videoDevices.length) {
        const option = document.createElement('option');
        option.value = '';
        option.textContent = 'Default camera';
        cameraDeviceSelect.appendChild(option);
        return;
    }

    videoDevices.forEach((device, index) => {
        const option = document.createElement('option');
        option.value = device.deviceId;
        option.textContent = device.label || `Camera ${index + 1}`;
        cameraDeviceSelect.appendChild(option);
    });
}

function createCameraStage(sourceId) {
    const video = document.createElement('video');
    video.autoplay = true;
    video.playsInline = true;
    video.muted = true;

    const canvas = document.createElement('canvas');
    hiddenCameraStages.append(video, canvas);

    return { video, canvas };
}

async function detectCameraFrame(sourceId) {
    const camera = activeCameras.get(sourceId);
    if (!camera || camera.isDetecting || camera.video.readyState < HTMLMediaElement.HAVE_CURRENT_DATA) {
        return;
    }

    camera.isDetecting = true;
    camera.canvas.width = camera.video.videoWidth;
    camera.canvas.height = camera.video.videoHeight;

    const context = camera.canvas.getContext('2d');
    context.drawImage(camera.video, 0, 0, camera.canvas.width, camera.canvas.height);

    camera.canvas.toBlob(async (blob) => {
        if (!blob) {
            camera.isDetecting = false;
            return;
        }

        const formData = new FormData();
        formData.append('frame', blob, `${sourceId}.jpg`);
        formData.append('source_id', sourceId);

        try {
            const response = await fetch('/detect', {
                method: 'POST',
                body: formData
            });

            if (!response.ok) {
                throw new Error('Detection request failed');
            }

            const data = await response.json();
            camera.latestImage = data.image;
            camera.status = 'Detecting';
            renderDashboard(data.dashboard || {});
            renderLocalCameraList();
        } catch (error) {
            camera.status = 'Unavailable';
            renderLocalCameraList();
        } finally {
            camera.isDetecting = false;
            if (selectedPreviewSource === sourceId) {
                renderPreview();
            }
        }
    }, 'image/jpeg', 0.8);
}

function getUniqueSourceId(baseId) {
    const cleanId = (baseId || 'dashboard-camera').trim() || 'dashboard-camera';
    if (!activeCameras.has(cleanId)) {
        return cleanId;
    }

    let suffix = 2;
    while (activeCameras.has(`${cleanId}-${suffix}`)) {
        suffix += 1;
    }
    return `${cleanId}-${suffix}`;
}

async function startLocalCamera() {
    try {
        const deviceId = cameraDeviceSelect.value;
        const sourceId = getUniqueSourceId(cameraSourceId.value);
        const constraints = {
            video: deviceId
                ? { deviceId: { exact: deviceId } }
                : { width: { ideal: 960 }, height: { ideal: 540 }, facingMode: 'environment' },
            audio: false
        };
        const stream = await navigator.mediaDevices.getUserMedia(constraints);
        const { video, canvas } = createCameraStage(sourceId);

        video.srcObject = stream;
        await video.play();

        const camera = {
            canvas,
            isDetecting: false,
            latestImage: '',
            status: 'Camera active',
            stream,
            timer: null,
            video
        };
        activeCameras.set(sourceId, camera);
        camera.timer = window.setInterval(() => detectCameraFrame(sourceId), 700);

        cameraSourceId.value = `${sourceId}-next`;
        selectedPreviewSource = selectedPreviewSource || sourceId;
        renderLocalCameraList();
        renderPreviewOptions();
        detectCameraFrame(sourceId);
        await loadCameraDevices();
    } catch (error) {
        setCameraStatus('Permission needed');
    }
}

function stopLocalCamera(sourceId) {
    const camera = activeCameras.get(sourceId);
    if (!camera) {
        return;
    }

    window.clearInterval(camera.timer);
    camera.stream.getTracks().forEach((track) => track.stop());
    camera.video.remove();
    camera.canvas.remove();
    activeCameras.delete(sourceId);

    if (selectedPreviewSource === sourceId) {
        selectedPreviewSource = '';
    }

    renderLocalCameraList();
    renderPreviewOptions();
}

previewSourceSelect.addEventListener('change', () => {
    selectedPreviewSource = previewSourceSelect.value;
    renderPreview();
});

startCameraButton.addEventListener('click', startLocalCamera);

loadCameraDevices();
renderDashboard(latestDashboardData);
window.setInterval(refreshDashboard, 5000);
