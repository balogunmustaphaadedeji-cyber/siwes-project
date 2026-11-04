import os
import sqlite3
import pickle
import base64
import io
from datetime import datetime, date, timedelta
from functools import wraps

import cv2
import numpy as np
import face_recognition
from flask import (
    Flask, render_template, request, jsonify, 
    send_file, g, redirect, url_for, flash
)
from PIL import Image

# -------------------------------------------------
# Configuration
# -------------------------------------------------
app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "smart-office-siwes-2026-change-me")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "data", "attendance.db")
FACES_DIR = os.path.join(BASE_DIR, "static", "faces")

os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
os.makedirs(FACES_DIR, exist_ok=True)

# Face matching threshold (lower = stricter). 0.45–0.55 is typical.
MATCH_TOLERANCE = 0.48

# Prevent the same person from being marked present again within this many minutes
COOLDOWN_MINUTES = 5


# -------------------------------------------------
# Database helpers
# -------------------------------------------------
def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def close_db(exception=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    db = get_db()
    db.executescript("""
        CREATE TABLE IF NOT EXISTS people (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            staff_id TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            encoding BLOB NOT NULL,
            photo_path TEXT,
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS attendance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            person_id INTEGER NOT NULL,
            staff_id TEXT NOT NULL,
            name TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            date TEXT NOT NULL,
            FOREIGN KEY (person_id) REFERENCES people (id)
        );

        CREATE INDEX IF NOT EXISTS idx_attendance_date ON attendance(date);
        CREATE INDEX IF NOT EXISTS idx_attendance_person ON attendance(person_id);
    """)
    db.commit()


# -------------------------------------------------
# Low-light image enhancement
# -------------------------------------------------
def enhance_for_low_light(img_bgr):
    """
    Improve dark / evening images before face detection.
    Uses CLAHE on the L channel + mild brightness boost.
    """
    if img_bgr is None or img_bgr.size == 0:
        return img_bgr

    # Convert to LAB
    lab = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)

    # CLAHE (Contrast Limited Adaptive Histogram Equalization)
    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
    l = clahe.apply(l)

    # Mild brightness boost
    l = cv2.convertScaleAbs(l, alpha=1.15, beta=15)

    enhanced = cv2.merge([l, a, b])
    enhanced = cv2.cvtColor(enhanced, cv2.COLOR_LAB2BGR)
    return enhanced


def decode_base64_image(data_url):
    """Convert browser base64 image to OpenCV BGR image."""
    if "," in data_url:
        data_url = data_url.split(",")[1]
    img_bytes = base64.b64decode(data_url)
    nparr = np.frombuffer(img_bytes, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    return img


def get_face_encoding(img_bgr):
    """
    Detect face and return 128-d encoding.
    Returns (encoding, face_location) or (None, None).
    """
    if img_bgr is None:
        return None, None

    # Enhance for low light
    enhanced = enhance_for_low_light(img_bgr)

    # Convert to RGB for face_recognition
    rgb = cv2.cvtColor(enhanced, cv2.COLOR_BGR2RGB)

    # Detect faces (HOG is faster and works on CPU)
    locations = face_recognition.face_locations(rgb, model="hog")
    if not locations:
        # Try once more with a stronger enhancement if nothing found
        lab = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2LAB)
        l, a, b = cv2.split(lab)
        clahe = cv2.createCLAHE(clipLimit=4.5, tileGridSize=(8, 8))
        l = clahe.apply(l)
        l = cv2.convertScaleAbs(l, alpha=1.3, beta=25)
        stronger = cv2.cvtColor(cv2.merge([l, a, b]), cv2.COLOR_LAB2BGR)
        rgb = cv2.cvtColor(stronger, cv2.COLOR_BGR2RGB)
        locations = face_recognition.face_locations(rgb, model="hog")

    if not locations:
        return None, None

    # Use the largest face
    locations = sorted(locations, key=lambda loc: (loc[2]-loc[0])*(loc[1]-loc[3]), reverse=True)
    encoding = face_recognition.face_encodings(rgb, [locations[0]])[0]
    return encoding, locations[0]


# -------------------------------------------------
# Routes – Pages
# -------------------------------------------------
@app.route("/")
def dashboard():
    db = get_db()
    total_people = db.execute("SELECT COUNT(*) AS c FROM people").fetchone()["c"]
    today = date.today().isoformat()
    today_count = db.execute(
        "SELECT COUNT(DISTINCT person_id) AS c FROM attendance WHERE date = ?", (today,)
    ).fetchone()["c"]
    recent = db.execute("""
        SELECT name, staff_id, timestamp 
        FROM attendance 
        ORDER BY timestamp DESC 
        LIMIT 10
    """).fetchall()
    return render_template(
        "dashboard.html",
        total_people=total_people,
        today_count=today_count,
        recent=recent,
        today=today
    )


@app.route("/register")
def register_page():
    return render_template("register.html")


@app.route("/recognize")
def recognize_page():
    return render_template("recognize.html")


@app.route("/attendance")
def attendance_page():
    db = get_db()
    people = db.execute("SELECT id, name, staff_id FROM people ORDER BY name").fetchall()
    return render_template("attendance.html", people=people)


@app.route("/people")
def people_page():
    db = get_db()
    people = db.execute("""
        SELECT p.*, 
               (SELECT COUNT(*) FROM attendance a WHERE a.person_id = p.id) AS attendance_count
        FROM people p
        ORDER BY p.name
    """).fetchall()
    return render_template("people.html", people=people)


# -------------------------------------------------
# API – Registration
# -------------------------------------------------
@app.route("/api/register", methods=["POST"])
def api_register():
    data = request.get_json()
    if not data:
        return jsonify({"success": False, "message": "No data received"}), 400

    name = (data.get("name") or "").strip()
    staff_id = (data.get("staff_id") or "").strip()
    image_data = data.get("image")

    if not name or not staff_id or not image_data:
        return jsonify({"success": False, "message": "Name, Staff ID and face image are required"}), 400

    db = get_db()
    existing = db.execute("SELECT id FROM people WHERE staff_id = ?", (staff_id,)).fetchone()
    if existing:
        return jsonify({"success": False, "message": f"Staff ID '{staff_id}' is already registered"}), 400

    img = decode_base64_image(image_data)
    if img is None:
        return jsonify({"success": False, "message": "Could not decode image"}), 400

    encoding, location = get_face_encoding(img)
    if encoding is None:
        return jsonify({
            "success": False,
            "message": "No face detected. Please face the camera, improve lighting, and try again."
        }), 400

    # Save a small photo for display
    photo_filename = f"{staff_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}.jpg"
    photo_path = os.path.join(FACES_DIR, photo_filename)
    # Crop face roughly
    top, right, bottom, left = location
    h, w = img.shape[:2]
    pad = 40
    top = max(0, top - pad)
    left = max(0, left - pad)
    bottom = min(h, bottom + pad)
    right = min(w, right + pad)
    face_img = img[top:bottom, left:right]
    cv2.imwrite(photo_path, face_img)

    encoding_blob = pickle.dumps(encoding)
    now = datetime.now().isoformat(timespec="seconds")

    try:
        db.execute(
            "INSERT INTO people (staff_id, name, encoding, photo_path, created_at) VALUES (?, ?, ?, ?, ?)",
            (staff_id, name, encoding_blob, f"faces/{photo_filename}", now)
        )
        db.commit()
    except sqlite3.IntegrityError:
        return jsonify({"success": False, "message": "Staff ID already exists"}), 400

    return jsonify({
        "success": True,
        "message": f"{name} registered successfully!",
        "staff_id": staff_id
    })


# -------------------------------------------------
# API – Recognition + Auto Attendance
# -------------------------------------------------
@app.route("/api/recognize", methods=["POST"])
def api_recognize():
    data = request.get_json()
    if not data or not data.get("image"):
        return jsonify({"success": False, "message": "No image"}), 400

    img = decode_base64_image(data["image"])
    if img is None:
        return jsonify({"success": False, "message": "Bad image"}), 400

    encoding, location = get_face_encoding(img)
    if encoding is None:
        return jsonify({
            "success": True,
            "recognized": False,
            "name": None,
            "message": "No face detected"
        })

    db = get_db()
    people = db.execute("SELECT id, staff_id, name, encoding FROM people").fetchall()

    if not people:
        return jsonify({
            "success": True,
            "recognized": False,
            "name": "Unknown Person",
            "message": "No people registered yet"
        })

    known_encodings = []
    known_meta = []
    for p in people:
        try:
            enc = pickle.loads(p["encoding"])
            known_encodings.append(enc)
            known_meta.append({"id": p["id"], "staff_id": p["staff_id"], "name": p["name"]})
        except Exception:
            continue

    if not known_encodings:
        return jsonify({
            "success": True,
            "recognized": False,
            "name": "Unknown Person",
            "message": "No valid face data"
        })

    distances = face_recognition.face_distance(known_encodings, encoding)
    best_idx = int(np.argmin(distances))
    best_distance = float(distances[best_idx])

    if best_distance <= MATCH_TOLERANCE:
        person = known_meta[best_idx]
        # Check cooldown
        cooldown_time = (datetime.now() - timedelta(minutes=COOLDOWN_MINUTES)).isoformat(timespec="seconds")
        recent = db.execute("""
            SELECT id FROM attendance 
            WHERE person_id = ? AND timestamp > ?
            LIMIT 1
        """, (person["id"], cooldown_time)).fetchone()

        marked = False
        if not recent:
            now = datetime.now()
            db.execute(
                "INSERT INTO attendance (person_id, staff_id, name, timestamp, date) VALUES (?, ?, ?, ?, ?)",
                (person["id"], person["staff_id"], person["name"], 
                 now.isoformat(timespec="seconds"), now.date().isoformat())
            )
            db.commit()
            marked = True

        return jsonify({
            "success": True,
            "recognized": True,
            "name": person["name"],
            "staff_id": person["staff_id"],
            "distance": round(best_distance, 4),
            "attendance_marked": marked,
            "message": "Attendance recorded" if marked else f"Already marked (wait {COOLDOWN_MINUTES} min)"
        })
    else:
        return jsonify({
            "success": True,
            "recognized": False,
            "name": "Unknown Person",
            "distance": round(best_distance, 4),
            "message": "Face not recognized"
        })


# -------------------------------------------------
# API – Attendance history & export
# -------------------------------------------------
@app.route("/api/attendance")
def api_attendance():
    db = get_db()
    person_id = request.args.get("person_id")
    date_from = request.args.get("date_from")
    date_to = request.args.get("date_to")

    query = "SELECT * FROM attendance WHERE 1=1"
    params = []

    if person_id:
        query += " AND person_id = ?"
        params.append(person_id)
    if date_from:
        query += " AND date >= ?"
        params.append(date_from)
    if date_to:
        query += " AND date <= ?"
        params.append(date_to)

    query += " ORDER BY timestamp DESC LIMIT 500"
    rows = db.execute(query, params).fetchall()
    return jsonify([dict(r) for r in rows])


@app.route("/api/attendance/export")
def api_attendance_export():
    db = get_db()
    person_id = request.args.get("person_id")
    date_from = request.args.get("date_from")
    date_to = request.args.get("date_to")

    query = "SELECT staff_id, name, timestamp, date FROM attendance WHERE 1=1"
    params = []

    if person_id:
        query += " AND person_id = ?"
        params.append(person_id)
    if date_from:
        query += " AND date >= ?"
        params.append(date_from)
    if date_to:
        query += " AND date <= ?"
        params.append(date_to)

    query += " ORDER BY timestamp DESC"
    rows = db.execute(query, params).fetchall()

    # Build CSV in memory
    import csv
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Staff ID", "Name", "Timestamp", "Date"])
    for r in rows:
        writer.writerow([r["staff_id"], r["name"], r["timestamp"], r["date"]])

    output.seek(0)
    return send_file(
        io.BytesIO(output.getvalue().encode("utf-8")),
        mimetype="text/csv",
        as_attachment=True,
        download_name=f"attendance_{date.today().isoformat()}.csv"
    )


# -------------------------------------------------
# API – People management
# -------------------------------------------------
@app.route("/api/people/<int:person_id>", methods=["DELETE"])
def api_delete_person(person_id):
    db = get_db()
    person = db.execute("SELECT * FROM people WHERE id = ?", (person_id,)).fetchone()
    if not person:
        return jsonify({"success": False, "message": "Person not found"}), 404

    # Delete photo if exists
    if person["photo_path"]:
        full_path = os.path.join(BASE_DIR, "static", person["photo_path"])
        if os.path.exists(full_path):
            try:
                os.remove(full_path)
            except OSError:
                pass

    # Keep attendance history (person_id will just become orphaned – safer)
    # Or you can choose to delete attendance too. We keep it.
    db.execute("DELETE FROM people WHERE id = ?", (person_id,))
    db.commit()
    return jsonify({"success": True, "message": f"{person['name']} removed. Attendance history kept."})


@app.route("/api/people/<int:person_id>", methods=["PUT"])
def api_update_person(person_id):
    data = request.get_json()
    name = (data.get("name") or "").strip()
    staff_id = (data.get("staff_id") or "").strip()

    if not name or not staff_id:
        return jsonify({"success": False, "message": "Name and Staff ID required"}), 400

    db = get_db()
    # Check staff_id uniqueness
    conflict = db.execute(
        "SELECT id FROM people WHERE staff_id = ? AND id != ?", (staff_id, person_id)
    ).fetchone()
    if conflict:
        return jsonify({"success": False, "message": "Staff ID already used by another person"}), 400

    db.execute(
        "UPDATE people SET name = ?, staff_id = ? WHERE id = ?",
        (name, staff_id, person_id)
    )
    # Also update name/staff_id in past attendance records for consistency
    db.execute(
        "UPDATE attendance SET name = ?, staff_id = ? WHERE person_id = ?",
        (name, staff_id, person_id)
    )
    db.commit()
    return jsonify({"success": True, "message": "Updated successfully"})


# -------------------------------------------------
# Startup
# -------------------------------------------------
with app.app_context():
    init_db()


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
