let stream = null;
let recognizing = false;
let intervalId = null;

const video = document.getElementById('video');
const overlay = document.getElementById('overlay');
const placeholder = document.getElementById('camPlaceholder');
const resultBox = document.getElementById('resultBox');
const statusBadge = document.getElementById('statusBadge');
const btnStart = document.getElementById('btnStart');
const btnStop = document.getElementById('btnStop');

// Capture every 1.8 seconds (avoids flooding the server)
const CAPTURE_INTERVAL = 1800;

function setBadge(text, type) {
    statusBadge.textContent = text;
    statusBadge.className = `badge bg-${type}`;
}

function showResult(html) {
    resultBox.innerHTML = html;
}

btnStart.addEventListener('click', async () => {
    try {
        stream = await navigator.mediaDevices.getUserMedia({
            video: { facingMode: 'user', width: { ideal: 640 }, height: { ideal: 480 } },
            audio: false
        });
        video.srcObject = stream;
        placeholder.classList.add('d-none');
        recognizing = true;
        btnStart.disabled = true;
        btnStop.disabled = false;
        setBadge('Recognizing…', 'success');
        showResult('<div class="text-center text-muted py-3"><div class="spinner-border text-primary mb-2"></div><div>Looking for faces…</div></div>');

        // Start automatic detection loop
        intervalId = setInterval(captureAndRecognize, CAPTURE_INTERVAL);
        // Also run once immediately
        setTimeout(captureAndRecognize, 600);
    } catch (err) {
        setBadge('Camera Error', 'danger');
        showResult(`<div class="text-danger">Could not access camera:<br>${err.message}</div>`);
    }
});

btnStop.addEventListener('click', () => {
    recognizing = false;
    if (intervalId) {
        clearInterval(intervalId);
        intervalId = null;
    }
    if (stream) {
        stream.getTracks().forEach(t => t.stop());
        stream = null;
    }
    video.srcObject = null;
    placeholder.classList.remove('d-none');
    btnStart.disabled = false;
    btnStop.disabled = true;
    setBadge('Camera Off', 'secondary');
    showResult('<div class="text-center text-muted py-3"><i class="bi bi-person-bounding-box fs-1 d-block mb-2"></i>Waiting for face…</div>');

    // Clear overlay
    const ctx = overlay.getContext('2d');
    ctx.clearRect(0, 0, overlay.width, overlay.height);
});

async function captureAndRecognize() {
    if (!recognizing || !video.srcObject) return;

    // Draw current frame to a temporary canvas
    const temp = document.createElement('canvas');
    temp.width = video.videoWidth || 640;
    temp.height = video.videoHeight || 480;
    const ctx = temp.getContext('2d');
    ctx.drawImage(video, 0, 0);
    const imageData = temp.toDataURL('image/jpeg', 0.85);

    try {
        const res = await fetch('/api/recognize', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ image: imageData })
        });
        const data = await res.json();

        if (!data.success) {
            showResult(`<div class="text-danger">${data.message || 'Error'}</div>`);
            return;
        }

        if (data.recognized) {
            let extra = '';
            if (data.attendance_marked) {
                extra = `<div class="badge bg-success mt-2">✓ Attendance Recorded</div>`;
            } else {
                extra = `<div class="badge bg-secondary mt-2">${data.message}</div>`;
            }
            showResult(`
                <div class="recognized">${data.name}</div>
                <div class="text-muted small">${data.staff_id}</div>
                ${extra}
                <div class="text-muted small mt-2">Distance: ${data.distance}</div>
            `);
            setBadge('Recognized', 'success');
        } else {
            if (data.message === 'No face detected') {
                showResult(`
                    <div class="text-center text-muted py-2">
                        <i class="bi bi-emoji-neutral fs-3 d-block mb-1"></i>
                        No face detected
                    </div>
                `);
                setBadge('Searching…', 'warning');
            } else {
                showResult(`
                    <div class="unknown">Unknown Person</div>
                    <div class="text-muted small mt-1">${data.message || ''}</div>
                `);
                setBadge('Unknown', 'danger');
            }
        }
    } catch (err) {
        showResult(`<div class="text-danger">Network error</div>`);
        setBadge('Error', 'danger');
    }
}

// Keep overlay canvas size in sync
function resizeOverlay() {
    overlay.width = video.clientWidth;
    overlay.height = video.clientHeight;
}
window.addEventListener('resize', resizeOverlay);
video.addEventListener('loadedmetadata', resizeOverlay);
