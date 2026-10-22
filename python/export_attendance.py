import csv
from db import initialize, connect
from pathlib import Path

initialize()
out = Path(__file__).with_name("attendance_export.csv")
with connect() as conn, out.open("w", newline="", encoding="utf-8-sig") as f:
    writer = csv.writer(f)
    writer.writerow(["Visit ID", "Name", "Arrival", "Departure", "Duration (seconds)"])
    rows = conn.execute("""
        SELECT v.id, p.name, v.arrival_at, v.departure_at, v.duration_seconds
        FROM visits v JOIN people p ON p.id = v.person_id
        ORDER BY v.id DESC
    """).fetchall()
    for row in rows:
        writer.writerow([row["id"], row["name"], row["arrival_at"],
                         row["departure_at"] or "Still open", row["duration_seconds"] or ""])
print(f"Exported {len(rows)} records to {out}")
