# Smart Office Face Recognition & Attendance System (SIWES Prototype)

A Windows prototype using:
- C# WinForms launcher/dashboard (.NET 8)
- Python + OpenCV-contrib for webcam face detection and LBPH recognition
- SQLite for persistent people and attendance records

## Important prototype limitations
- This is a classroom/SIWES prototype, not a production security system.
- Face recognition can make mistakes, especially with poor lighting, camera angles, masks, or similar-looking faces.
- The first version estimates a visit as follows: the first recognized appearance opens a visit; if the person is not seen for 60 seconds, the visit is closed. This is a configurable absence rule, **not reliable physical entry/exit detection**.
- Use only consenting volunteers. Keep the database local, tell participants what is being collected, and delete test records when finished.
- Recognition uses OpenCV LBPH, which requires `opencv-contrib-python`. No photos are uploaded to a cloud service.

## 1. Install prerequisites
1. Install Python 3.11 (64-bit) from https://www.python.org/downloads/windows/
   - During installation, tick **Add python.exe to PATH**.
2. Install .NET 8 SDK from https://dotnet.microsoft.com/download/dotnet/8.0
3. Extract this ZIP to a folder such as `C:\\SIWES\\SmartOfficeAttendance`.

Open Command Prompt in the extracted folder and run:

```bat
cd python
py -3.11 -m venv .venv
.venv\\Scripts\\activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

If `py -3.11` is not recognized, install Python 3.11 or use `py -m venv .venv`.

## 2. Register a consenting test participant
Run from the `python` folder, with the virtual environment activated:

```bat
python register_person.py
```

Type the participant's name in the terminal and press Enter. Face the webcam, move slightly between captures, and press **SPACE** to capture a face sample. Capture at least 10 samples from slightly different angles/expressions. Press **Q** when done. The program needs at least 5 samples to save the person. Do not register someone without their permission.

## 3. Start face recognition
```bat
python attendance_camera.py
```
A webcam window opens. Recognized registered people get a green label; unknown faces are labelled `Unknown`. Attendance is saved automatically in `smart_office.db`.
- Press **Q** in the webcam window to quit.
- Each recognized person gets one open visit at a time.
- If they remain unseen for 60 seconds, the visit is closed. Change `ABSENCE_SECONDS` near the top of `attendance_camera.py` for testing.
- A brief disappearance does not immediately end a visit, reducing duplicate records.

## 4. Run the C# launcher
Open a second Command Prompt in `csharp\\SmartOfficeLauncher` and run:

```bat
dotnet run
```

The launcher starts/stops the Python camera program and can open the attendance CSV export. Ensure Python dependencies are installed first, as above. The Python camera window is the live view in this first version.

## 5. View records / export
The database file is `python\\smart_office.db`. To export records, close the camera and run:

```bat
python export_attendance.py
```

This creates `attendance_export.csv` in the Python folder. The database is created automatically the first time either Python program runs.

## Troubleshooting
- **Camera won't open:** close Zoom/Teams/Camera app, check Windows Settings > Privacy & security > Camera, and make sure desktop apps are allowed.
- **`cv2.face` missing:** ensure you installed `opencv-contrib-python`, not plain `opencv-python`, inside the active virtual environment:
  `pip uninstall opencv-python opencv-contrib-python -y`
  `pip install -r requirements.txt`
- **No faces recognized:** register more samples with good lighting and face centered; the initial LBPH threshold may need tuning.
- **PowerShell activation blocked:** use Command Prompt, or activate via `.venv\\Scripts\\activate.bat`.
