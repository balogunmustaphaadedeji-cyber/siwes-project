import cv2
import sqlite3
from pathlib import Path
from datetime import datetime
from db import initialize, connect, now_iso

BASE = Path(__file__).parent
SAMPLES_DIR = BASE / "face_samples"
SAMPLES_DIR.mkdir(exist_ok=True)
CASCADE_PATH = Path(cv2.data.haarcascades) / "haarcascade_frontalface_default.xml"

def main():
    initialize()
    name = input("Participant name (with their permission): ").strip()
    if not name:
        print("Name cannot be empty.")
        return

    cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
    if not cap.isOpened():
        cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("Cannot open webcam. Close other camera apps and check Windows camera permissions.")
        return

    detector = cv2.CascadeClassifier(str(CASCADE_PATH))
    captured = []
    print("SPACE = capture face sample | Q = finish. Capture 10+ varied samples.")
    while True:
        ok, frame = cap.read()
        if not ok:
            print("Unable to read from webcam.")
            break
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = detector.detectMultiScale(gray, scaleFactor=1.2, minNeighbors=5, minSize=(90, 90))
        for (x, y, w, h) in faces:
            cv2.rectangle(frame, (x, y), (x+w, y+h), (50, 220, 50), 2)
        cv2.putText(frame, f"Samples: {len(captured)} | SPACE capture | Q finish",
                    (10, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 255, 255), 2)
        cv2.imshow("Register participant", frame)
        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'):
            break
        if key == 32 and len(faces) == 1:
            x, y, w, h = faces[0]
            face = cv2.resize(gray[y:y+h, x:x+w], (200, 200))
            captured.append(face)
            print(f"Captured sample {len(captured)}")
        elif key == 32:
            print("Please ensure exactly one face is visible.")

    cap.release()
    cv2.destroyAllWindows()
    if len(captured) < 5:
        print(f"Only {len(captured)} samples captured. Need at least 5; participant not saved.")
        return

    with connect() as conn:
        existing = conn.execute("SELECT id FROM people WHERE name = ?", (name,)).fetchone()
        if existing:
            person_id = existing["id"]
            conn.execute("DELETE FROM face_samples WHERE person_id = ?", (person_id,))
            conn.execute("DELETE FROM people WHERE id = ?", (person_id,))
        cur = conn.execute("INSERT INTO people(name, created_at) VALUES(?, ?)", (name, now_iso()))
        person_id = cur.lastrowid
        person_dir = SAMPLES_DIR / f"person_{person_id}"
        person_dir.mkdir(exist_ok=True)
        for i, face in enumerate(captured, 1):
            path = person_dir / f"sample_{i}.png"
            cv2.imwrite(str(path), face)
            conn.execute("INSERT INTO face_samples(person_id, image_path) VALUES(?, ?)",
                         (person_id, str(path)))
    print(f"Registered {name} with {len(captured)} samples. You can now run attendance_camera.py.")

if __name__ == "__main__":
    main()
