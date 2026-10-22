import cv2
import time
import sqlite3
from pathlib import Path
from datetime import datetime
from db import initialize, connect, now_iso

BASE = Path(__file__).parent
ABSENCE_SECONDS = 60  # For quick demonstration, you can temporarily set this to 15.
RECOGNITION_THRESHOLD = 75  # Lower is stricter for LBPH; tune with real testing.
CASCADE_PATH = Path(cv2.data.haarcascades) / "haarcascade_frontalface_default.xml"

def load_recognizer():
    recognizer = cv2.face.LBPHFaceRecognizer_create()
    labels = {}
    images, ids = [], []
    with connect() as conn:
        people = conn.execute("SELECT id, name FROM people ORDER BY id").fetchall()
        for p in people:
            labels[int(p["id"])] = p["name"]
        samples = conn.execute("SELECT person_id, image_path FROM face_samples").fetchall()
    for sample in samples:
        image_path = Path(sample["image_path"])
        if not image_path.exists():
            continue
        image = cv2.imread(str(image_path), cv2.IMREAD_GRAYSCALE)
        if image is not None:
            images.append(cv2.resize(image, (200, 200)))
            ids.append(int(sample["person_id"]))
    if not images:
        raise RuntimeError("No face samples found. Run register_person.py first.")
    recognizer.train(images, __import__("numpy").array(ids, dtype="int32"))
    return recognizer, labels

def close_visit(person_id):
    with connect() as conn:
        row = conn.execute(
            "SELECT id, arrival_at FROM visits WHERE person_id=? AND departure_at IS NULL ORDER BY id DESC LIMIT 1",
            (person_id,)).fetchone()
        if row:
            departure = now_iso()
            start = datetime.fromisoformat(row["arrival_at"])
            end = datetime.fromisoformat(departure)
            seconds = max(0, int((end - start).total_seconds()))
            conn.execute("UPDATE visits SET departure_at=?, duration_seconds=? WHERE id=?",
                         (departure, seconds, row["id"]))

def main():
    initialize()
    try:
        recognizer, labels = load_recognizer()
    except Exception as exc:
        print(f"Cannot start recognition: {exc}")
        input("Press Enter to close...")
        return

    detector = cv2.CascadeClassifier(str(CASCADE_PATH))
    cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
    if not cap.isOpened():
        cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("Cannot open webcam. Close other camera apps and check Windows camera permissions.")
        return

    last_seen = {}
    open_visits = set()
    with connect() as conn:
        rows = conn.execute("SELECT DISTINCT person_id FROM visits WHERE departure_at IS NULL").fetchall()
        open_visits = {int(r["person_id"]) for r in rows}

    print("Recognition running. Press Q in the camera window to stop.")
    try:
        while True:
            ok, frame = cap.read()
            if not ok:
                print("Webcam frame unavailable.")
                break
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            faces = detector.detectMultiScale(gray, scaleFactor=1.2, minNeighbors=5, minSize=(90, 90))
            now = time.time()
            seen_this_frame = set()

            for (x, y, w, h) in faces:
                face = cv2.resize(gray[y:y+h, x:x+w], (200, 200))
                label_id, confidence = recognizer.predict(face)
                if confidence <= RECOGNITION_THRESHOLD and label_id in labels:
                    person_id = int(label_id)
                    name = labels[person_id]
                    color = (50, 220, 50)
                    seen_this_frame.add(person_id)
                    last_seen[person_id] = now
                    if person_id not in open_visits:
                        with connect() as conn:
                            conn.execute("INSERT INTO visits(person_id, arrival_at) VALUES(?, ?)",
                                         (person_id, now_iso()))
                        open_visits.add(person_id)
                        print(f"Arrival recorded: {name}")
                    text = f"{name} ({confidence:.0f})"
                else:
                    name, color = "Unknown", (0, 165, 255)
                    text = "Unknown visitor"
                cv2.rectangle(frame, (x, y), (x+w, y+h), color, 2)
                cv2.putText(frame, text, (x, max(25, y-10)),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.65, color, 2)

            for person_id in list(open_visits):
                if person_id not in seen_this_frame and person_id in last_seen:
                    if now - last_seen[person_id] >= ABSENCE_SECONDS:
                        close_visit(person_id)
                        open_visits.remove(person_id)
                        last_seen.pop(person_id, None)
                        print(f"Visit closed for {labels.get(person_id, person_id)} after absence timeout.")

            cv2.putText(frame, "Q: quit | Attendance is saved locally",
                        (10, frame.shape[0]-15), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 2)
            cv2.imshow("Smart Office Attendance - Webcam", frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
    finally:
        cap.release()
        cv2.destroyAllWindows()
        print("Camera stopped. Any visit still open will remain open in the database until the next run/timeout.")

if __name__ == "__main__":
    main()
