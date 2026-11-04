let stream = null;
const video = document.getElementById('video');
const canvas = document.getElementById('canvas');
const placeholder = document.getElementById('camPlaceholder');
const statusEl = document.getElementById('status');
const btnStart = document.getElementById('btnStartCam');
const btnCapture = document.getElementById('btnCapture');
const btnStop = document.getElementById('btnStopCam');

function showStatus(msg, type = 'info') {
    statusEl.innerHTML = `<div class="alert alert-${type} mb-0">${msg}</div>`;
}

btnStart.addEventListener('click', async () => {
    try {
        stream = await navigator.mediaDevices.getUserMedia({
            video: { facingMode: 'user', width: { ideal: 640 }, height: { ideal: 480 } },
            audio: false
        });
        video.srcObject = stream;
        placeholder.classList.add('d-none');
        btnStart.disabled = true;
        btnCapture.disabled = false;
        btnStop.disabled = false;
        showStatus('Camera ready. Position your face and click Capture & Register.', 'success');
    } catch (err) {
        showStatus('Could not access camera: ' + err.message, 'danger');
    }
});

btnStop.addEventListener('click', () => {
    if (stream) {
        stream.getTracks().forEach(t => t.stop());
        stream = null;
    }
    video.srcObject = null;
    placeholder.classList.remove('d-none');
    btnStart.disabled = false;
    btnCapture.disabled = true;
    btnStop.disabled = true;
    showStatus('Camera stopped.', 'secondary');
});

btnCapture.addEventListener('click', async () => {
    const name = document.getElementById('name').value.trim();
    const staffId = document.getElementById('staff_id').value.trim();

    if (!name || !staffId) {
        showStatus('Please enter both Name and Staff/Student ID.', 'warning');
        return;
    }

    // Capture frame
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    const ctx = canvas.getContext('2d');
    ctx.drawImage(video, 0, 0);
    const imageData = canvas.toDataURL('image/jpeg', 0.92);

    btnCapture.disabled = true;
    showStatus('<div class="spinner-border spinner-border-sm me-2"></div> Processing face…', 'info');

    try {
        const res = await fetch('/api/register', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name, staff_id: staffId, image: imageData })
        });
        const data = await res.json();

        if (data.success) {
            showStatus(`<strong>✓ ${data.message}</strong>`, 'success');
            document.getElementById('name').value = '';
            document.getElementById('staff_id').value = '';
        } else {
            showStatus(data.message || 'Registration failed', 'danger');
        }
    } catch (err) {
        showStatus('Network error: ' + err.message, 'danger');
    } finally {
        btnCapture.disabled = false;
    }
});
