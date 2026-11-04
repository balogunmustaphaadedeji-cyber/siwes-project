# Smart Office Face Recognition & Attendance System

A complete web-based face recognition attendance system built for SIWES / industrial training projects.

## Features

- **Dashboard** – Real counts of registered people and today’s attendance
- **Register Person** – Capture face from webcam + save name & staff ID
- **Live Recognition** – Automatic face detection every ~2 seconds
- **Low-light enhancement** – CLAHE + brightness boost to help in evening / dim rooms
- **Attendance** – Auto check-in with cooldown (prevents spam), history + filters + CSV export
- **People Management** – View, edit, delete (attendance history is kept)

## Important Notes

- Normal webcams **cannot see in complete darkness**. The system tries hard to enhance dark images, but you still need some light.
- Free Render instances have limited CPU/RAM. Face recognition may be a bit slow.
- SQLite database is used. On free Render the filesystem is ephemeral (data can be lost on restart). For permanent storage consider Render PostgreSQL later.

## Local Testing (Windows / Mac / Linux)

1. Install Python 3.10 or 3.11
2. Open terminal in the project folder
3. Create virtual environment:

```bash
python -m venv venv
```

4. Activate it:

- Windows: `venv\Scripts\activate`
- Mac/Linux: `source venv/bin/activate`

5. Install dependencies (this may take several minutes because of `dlib`):

```bash
pip install -r requirements.txt
```

6. Run the app:

```bash
python app.py
```

7. Open browser: http://127.0.0.1:5000

Allow camera permission when the browser asks.

## Deploy on Render (Recommended)

1. Create a free account on [render.com](https://render.com)
2. Push this project to a **GitHub** repository
3. On Render → **New → Web Service**
4. Connect your GitHub repo
5. Settings:

   | Setting              | Value                                      |
   |----------------------|--------------------------------------------|
   | Runtime              | Python                                     |
   | Build Command        | `pip install -r requirements.txt`          |
   | Start Command        | `gunicorn app:app --bind 0.0.0.0:$PORT --workers 1 --threads 2 --timeout 120` |
   | Instance Type        | Free                                       |

6. Click **Create Web Service**
7. Wait for the build (first build can take 10–20 minutes because of `dlib` / `face_recognition`)
8. Once live, open the Render URL and test

### If build fails on Render

`face_recognition` / `dlib` sometimes fails on free builders. Solutions:

- Upgrade to a paid Render instance (more reliable builds), **or**
- Use the Docker method below.

## Docker (more reliable on Render)

You can also deploy with Docker. Create a file named `Dockerfile` in the project root with:

```dockerfile
FROM python:3.11-slim-bookworm

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential cmake libopenblas-dev liblapack-dev \
    libx11-dev libgtk-3-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
RUN mkdir -p data static/faces

EXPOSE 10000
CMD ["gunicorn", "app:app", "--bind", "0.0.0.0:10000", "--workers", "1", "--threads", "2", "--timeout", "120"]
```

Then on Render choose **Docker** as the environment instead of Python.

## How to Demonstrate to Your Supervisor

1. Open the live URL (or localhost)
2. Go to **Register** → enter name + ID → start camera → capture
3. Go to **Recognize** → start recognition → stand in front of the camera
4. Show the name appearing and attendance being recorded
5. Show **Dashboard** and **Attendance** pages
6. Export CSV

## Project Structure

```
smart-office-attendance/
├── app.py                 # Main Flask application
├── requirements.txt
├── Procfile               # For Render
├── runtime.txt
├── templates/             # HTML pages
├── static/
│   ├── css/
│   ├── js/
│   └── faces/             # Stored face photos
└── data/                  # SQLite database
```

## Responsible Use

- This system stores face encodings. Inform people before enrolling them.
- Use only for legitimate attendance purposes.
- Face recognition is not 100% accurate (lighting, angle, masks, etc.).
- Do not use for high-security or law-enforcement purposes without proper evaluation.

---

Built for SIWES / Student Industrial Work Experience Scheme projects.
