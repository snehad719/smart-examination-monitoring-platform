import cv2
import time
import sqlite3
import sys
import os
from datetime import datetime

from app.alert_evidence import add_evidence

DATABASE = "data/examguard.db"
EVIDENCE_DIR = "data/evidence"


# =========================================================
# Save Face Event
# =========================================================

def save_face_event(
    session_id,
    event_type,
    start_time,
    end_time,
    duration_seconds
):
    connection = sqlite3.connect(DATABASE)

    connection.execute(
        """
        INSERT INTO face_events (
            session_id,
            event_type,
            start_time,
            end_time,
            duration_seconds
        )
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            session_id,
            event_type,
            start_time,
            end_time,
            duration_seconds
        )
    )

    connection.commit()
    connection.close()


# =========================================================
# Save Evidence Image
# =========================================================

def save_evidence_image(
    session_id,
    frame,
    event_number
):
    """
    Save webcam frame as evidence image.
    Returns the saved file path.
    """

    os.makedirs(EVIDENCE_DIR, exist_ok=True)

    timestamp = datetime.now().strftime(
        "%Y%m%d_%H%M%S"
    )

    filename = (
        f"session_{session_id}"
        f"_face_absent_{event_number}"
        f"_{timestamp}.jpg"
    )

    file_path = os.path.join(
        EVIDENCE_DIR,
        filename
    )

    success = cv2.imwrite(
        file_path,
        frame
    )

    if success:

        print(
            f"Evidence image saved: {file_path}"
        )

        return file_path

    print(
        "Warning: Evidence image could not be saved."
    )

    return None


# =========================================================
# Get Session ID
# =========================================================

def get_session_id():

    if len(sys.argv) < 2:

        print("Error: Exam session ID is required.")
        print()
        print("Usage:")
        print("python face_monitor.py SESSION_ID")
        print()
        print("Example:")
        print("python face_monitor.py 7")

        return None

    try:

        session_id = int(sys.argv[1])

        return session_id

    except ValueError:

        print(
            "Error: Session ID must be a number."
        )

        return None


# =========================================================
# Check Session
# =========================================================

def check_session(session_id):

    connection = sqlite3.connect(DATABASE)

    connection.row_factory = sqlite3.Row

    exam_session = connection.execute(
        """
        SELECT *
        FROM exam_sessions
        WHERE id = ?
        """,
        (session_id,)
    ).fetchone()

    connection.close()

    return exam_session


# =========================================================
# Main
# =========================================================

session_id = get_session_id()

if session_id is None:
    sys.exit(1)


exam_session = check_session(session_id)

if exam_session is None:

    print(
        f"Error: Exam session {session_id} "
        "was not found in database."
    )

    sys.exit(1)


print(
    f"Exam session found: {session_id}"
)

print(
    f"Session status: {exam_session['status']}"
)


if exam_session["status"] not in (
    "STARTED",
    "PAUSED"
):

    print(
        "Error: This exam session is not active."
    )

    sys.exit(1)


# =========================================================
# Haar Cascade
# =========================================================

face_cascade = cv2.CascadeClassifier(
    cv2.data.haarcascades +
    "haarcascade_frontalface_default.xml"
)


if face_cascade.empty():

    print(
        "Error: Haar Cascade could not be loaded."
    )

    sys.exit(1)


# =========================================================
# Webcam
# =========================================================

cap = cv2.VideoCapture(0)


if not cap.isOpened():

    print(
        "Error: Unable to open webcam."
    )

    sys.exit(1)


print()
print("======================================")
print("ExamGuard Face Monitoring")
print("======================================")
print(f"Session ID: {session_id}")
print("Webcam started successfully.")
print("Face monitoring started.")
print("Face events will be saved to SQLite.")
print("Evidence screenshots will be saved.")
print("Press 'q' to stop.")
print("======================================")


# =========================================================
# Tracking Variables
# =========================================================

face_absent_start = None

face_absent_intervals = []

event_number = 0

current_evidence_path = None


# =========================================================
# Monitoring Loop
# =========================================================

while True:

    ret, frame = cap.read()

    if not ret:

        print(
            "Error: Unable to read webcam frame."
        )

        break


    gray = cv2.cvtColor(
        frame,
        cv2.COLOR_BGR2GRAY
    )


    faces = face_cascade.detectMultiScale(
        gray,
        scaleFactor=1.1,
        minNeighbors=5,
        minSize=(30, 30)
    )


    current_time = time.time()


    # =====================================================
    # FACE PRESENT
    # =====================================================

    if len(faces) > 0:

        if face_absent_start is not None:

            absent_end = current_time

            absent_duration = (
                absent_end -
                face_absent_start
            )


            start_timestamp = datetime.fromtimestamp(
                face_absent_start
            ).strftime(
                "%Y-%m-%d %H:%M:%S"
            )


            end_timestamp = datetime.fromtimestamp(
                absent_end
            ).strftime(
                "%Y-%m-%d %H:%M:%S"
            )


            interval = {
                "start": start_timestamp,
                "end": end_timestamp,
                "duration_seconds": round(
                    absent_duration,
                    2
                ),
                "evidence_path":
                    current_evidence_path
            }


            face_absent_intervals.append(
                interval
            )


            # ---------------------------------------------
            # Save Face Event
            # ---------------------------------------------

            save_face_event(
                session_id=session_id,
                event_type="FACE_ABSENT",
                start_time=start_timestamp,
                end_time=end_timestamp,
                duration_seconds=round(
                    absent_duration,
                    2
                )
            )


            print(
                "FACE ABSENT | "
                f"Start: {start_timestamp} | "
                f"End: {end_timestamp} | "
                f"Duration: "
                f"{absent_duration:.2f} seconds"
            )


            print(
                "Face event saved to SQLite."
            )


            # ---------------------------------------------
            # Save Evidence Record
            # ---------------------------------------------

            if current_evidence_path is not None:

                add_evidence(
                    session_id=session_id,
                    evidence_type="IMAGE",
                    file_path=current_evidence_path,
                    description=(
                        "Webcam evidence captured when "
                        "candidate face was absent."
                    )
                )

                print(
                    "Evidence record saved to SQLite."
                )


            # Reset
            face_absent_start = None

            current_evidence_path = None


        status = "FACE PRESENT"


    # =====================================================
    # FACE ABSENT
    # =====================================================

    else:

        if face_absent_start is None:

            face_absent_start = current_time

            event_number += 1

            start_timestamp = datetime.fromtimestamp(
                face_absent_start
            ).strftime(
                "%Y-%m-%d %H:%M:%S"
            )


            print(
                "FACE ABSENT STARTED | "
                f"{start_timestamp}"
            )


            # ---------------------------------------------
            # Capture Evidence Screenshot
            # ---------------------------------------------

            current_evidence_path = (
                save_evidence_image(
                    session_id=session_id,
                    frame=frame,
                    event_number=event_number
                )
            )


        status = "FACE ABSENT"


    # =====================================================
    # Draw Face Detection
    # =====================================================

    for (x, y, w, h) in faces:

        cv2.rectangle(
            frame,
            (x, y),
            (x + w, y + h),
            (0, 255, 0),
            2
        )


    cv2.putText(
        frame,
        status,
        (20, 40),
        cv2.FONT_HERSHEY_SIMPLEX,
        1,
        (0, 255, 0),
        2
    )


    cv2.putText(
        frame,
        f"Faces detected: {len(faces)}",
        (20, 80),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.8,
        (0, 255, 0),
        2
    )


    cv2.putText(
        frame,
        f"Session ID: {session_id}",
        (20, 120),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.7,
        (255, 255, 255),
        2
    )


    cv2.imshow(
        "ExamGuard - Face Monitoring",
        frame
    )


    # =====================================================
    # Stop Monitoring
    # =====================================================

    if cv2.waitKey(1) & 0xFF == ord("q"):

        break


# =========================================================
# Handle Face Absence When Monitoring Stops
# =========================================================

if face_absent_start is not None:

    absent_end = time.time()

    absent_duration = (
        absent_end -
        face_absent_start
    )


    start_timestamp = datetime.fromtimestamp(
        face_absent_start
    ).strftime(
        "%Y-%m-%d %H:%M:%S"
    )


    end_timestamp = datetime.fromtimestamp(
        absent_end
    ).strftime(
        "%Y-%m-%d %H:%M:%S"
    )


    interval = {
        "start": start_timestamp,
        "end": end_timestamp,
        "duration_seconds": round(
            absent_duration,
            2
        ),
        "evidence_path":
            current_evidence_path
    }


    face_absent_intervals.append(
        interval
    )


    save_face_event(
        session_id=session_id,
        event_type="FACE_ABSENT",
        start_time=start_timestamp,
        end_time=end_timestamp,
        duration_seconds=round(
            absent_duration,
            2
        )
    )


    print(
        "FACE ABSENT | "
        f"Start: {start_timestamp} | "
        f"End: {end_timestamp} | "
        f"Duration: "
        f"{absent_duration:.2f} seconds"
    )


    print(
        "Face event saved to SQLite."
    )


    if current_evidence_path is not None:

        add_evidence(
            session_id=session_id,
            evidence_type="IMAGE",
            file_path=current_evidence_path,
            description=(
                "Webcam evidence captured when "
                "candidate face was absent."
            )
        )

        print(
            "Evidence record saved to SQLite."
        )


# =========================================================
# Cleanup
# =========================================================

cap.release()

cv2.destroyAllWindows()


print()
print("Face monitoring stopped.")

print()
print("Face absent intervals:")


if len(face_absent_intervals) == 0:

    print(
        "No face absent intervals detected."
    )

else:

    for interval in face_absent_intervals:

        print(interval)


print()
print(
    f"Monitoring completed for session "
    f"{session_id}."
)