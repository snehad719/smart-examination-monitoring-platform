import sqlite3
import pandas as pd

DATABASE = "data/examguard.db"

EVENT_WEIGHTS = {
    "FACE_ABSENT": 10,
    "TAB_SWITCH": 20,
    "FOCUS_LOST": 10,
    "MULTIPLE_FACES": 30,
    "LOOKING_AWAY": 15,
    "KEYBOARD_ACTIVITY": 10,
}


def calculate_face_presence_ratio(session_id):
    connection = sqlite3.connect(DATABASE)

    session = pd.read_sql_query(
        """
        SELECT start_time, end_time
        FROM exam_sessions
        WHERE id = ?
        """,
        connection,
        params=(session_id,)
    )

    face_events = pd.read_sql_query(
        """
        SELECT event_type, duration_seconds
        FROM face_events
        WHERE session_id = ?
        """,
        connection,
        params=(session_id,)
    )

    connection.close()

    if session.empty:
        raise ValueError(f"Session {session_id} not found.")

    start = pd.to_datetime(session.iloc[0]["start_time"])
    end = pd.to_datetime(session.iloc[0]["end_time"])

    if pd.isna(end):
        raise ValueError(f"Session {session_id} has no end time.")

    duration = (end - start).total_seconds()

    if duration <= 0:
        raise ValueError("Session duration must be greater than zero.")

    absent = face_events.loc[
        face_events["event_type"] == "FACE_ABSENT",
        "duration_seconds"
    ].fillna(0).sum()

    absent = min(float(absent), duration)

    return round((duration - absent) / duration, 4)


def calculate_event_penalty(session_id):
    connection = sqlite3.connect(DATABASE)

    face_events = pd.read_sql_query(
        """
        SELECT event_type
        FROM face_events
        WHERE session_id = ?
        """,
        connection,
        params=(session_id,)
    )

    browser_events = pd.read_sql_query(
        """
        SELECT event_type
        FROM browser_events
        WHERE session_id = ?
        """,
        connection,
        params=(session_id,)
    )

    connection.close()

    penalty = 0

    for event in face_events["event_type"]:
        penalty += EVENT_WEIGHTS.get(event, 0)

    for event in browser_events["event_type"]:
        penalty += EVENT_WEIGHTS.get(event, 0)

    return penalty


def calculate_integrity_score(session_id):

    face_ratio = calculate_face_presence_ratio(session_id)
    penalty = calculate_event_penalty(session_id)

    score = max(0, face_ratio * 100 - penalty)

    if score >= 70:
        risk = "Low"
    elif score >= 40:
        risk = "Medium"
    else:
        risk = "High"

    return {
        "session_id": session_id,
        "face_presence_ratio": face_ratio,
        "event_penalty": penalty,
        "integrity_score": round(score, 2),
        "risk_label": risk
    }


if __name__ == "__main__":

    session_id = int(input("Enter Exam Session ID: "))

    result = calculate_integrity_score(session_id)

    print("\nIntegrity Analysis")
    print("------------------")
    print("Session ID          :", result["session_id"])
    print("Face Presence Ratio :", result["face_presence_ratio"])
    print("Event Penalty       :", result["event_penalty"])
    print("Integrity Score     :", result["integrity_score"])
    print("Risk Label          :", result["risk_label"])