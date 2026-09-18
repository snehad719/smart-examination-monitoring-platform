import os
import sqlite3
from datetime import datetime

from app.integrity_scoring import calculate_integrity_score
from database import DATABASE


EVIDENCE_DIR = "data/evidence"


def get_connection():
    connection = sqlite3.connect(DATABASE)
    connection.row_factory = sqlite3.Row
    return connection


def create_alert(session_id, alert_type, severity, message):
    """
    Create an alert for a specific exam session.
    """

    connection = get_connection()

    connection.execute(
        """
        INSERT INTO alerts (
            session_id,
            alert_type,
            severity,
            message
        )
        VALUES (?, ?, ?, ?)
        """,
        (
            session_id,
            alert_type,
            severity,
            message
        )
    )

    connection.commit()
    connection.close()


def add_evidence(
    session_id,
    evidence_type,
    file_path=None,
    description=None
):
    """
    Store evidence information in the database.
    """

    os.makedirs(EVIDENCE_DIR, exist_ok=True)

    connection = get_connection()

    connection.execute(
        """
        INSERT INTO evidence (
            session_id,
            evidence_type,
            file_path,
            description
        )
        VALUES (?, ?, ?, ?)
        """,
        (
            session_id,
            evidence_type,
            file_path,
            description
        )
    )

    connection.commit()
    connection.close()


def generate_session_alerts(session_id):
    """
    Generate alerts based on integrity score
    and monitoring events.
    """

    result = calculate_integrity_score(session_id)

    score = result["integrity_score"]
    risk_label = result["risk_label"]

    # --------------------------------
    # Risk-based alert
    # --------------------------------

    if risk_label == "High":

        create_alert(
            session_id,
            "INTEGRITY_RISK",
            "HIGH",
            f"High integrity risk detected. Score: {score:.2f}"
        )

    elif risk_label == "Medium":

        create_alert(
            session_id,
            "INTEGRITY_RISK",
            "MEDIUM",
            f"Medium integrity risk detected. Score: {score:.2f}"
        )

    else:

        create_alert(
            session_id,
            "INTEGRITY_STATUS",
            "LOW",
            f"Low integrity risk. Score: {score:.2f}"
        )

    # --------------------------------
    # Check FACE_ABSENT events
    # --------------------------------

    connection = get_connection()

    face_events = connection.execute(
        """
        SELECT *
        FROM face_events
        WHERE session_id = ?
        AND event_type = 'FACE_ABSENT'
        ORDER BY start_time
        """,
        (session_id,)
    ).fetchall()

    connection.close()

    # --------------------------------
    # Create face absence alerts
    # --------------------------------

    for event in face_events:

        duration = event["duration_seconds"] or 0

        if duration >= 5:

            severity = "HIGH"

        elif duration >= 2:

            severity = "MEDIUM"

        else:

            severity = "LOW"

        create_alert(
            session_id,
            "FACE_ABSENT",
            severity,
            f"Candidate face was absent for {duration:.2f} seconds."
        )


def get_session_alerts(session_id):
    """
    Retrieve all alerts for a session.
    """

    connection = get_connection()

    alerts = connection.execute(
        """
        SELECT *
        FROM alerts
        WHERE session_id = ?
        ORDER BY created_at DESC
        """,
        (session_id,)
    ).fetchall()

    connection.close()

    return alerts


def get_session_evidence(session_id):
    """
    Retrieve all evidence for a session.
    """

    connection = get_connection()

    evidence = connection.execute(
        """
        SELECT *
        FROM evidence
        WHERE session_id = ?
        ORDER BY captured_at DESC
        """,
        (session_id,)
    ).fetchall()

    connection.close()

    return evidence


def demo_evidence(session_id):
    """
    Create a demo incident-log evidence entry.

    This does not create a fake screenshot.
    It records the monitoring incident as evidence.
    """

    description = (
        "Monitoring incident log generated from "
        "session events and integrity analysis."
    )

    add_evidence(
        session_id=session_id,
        evidence_type="INCIDENT_LOG",
        file_path=None,
        description=description
    )


def print_session_report(session_id):
    """
    Display alerts and evidence for a session.
    """

    print("\n===================================")
    print("EXAMGUARD ALERT & EVIDENCE REPORT")
    print("===================================")

    print(f"Session ID: {session_id}")

    alerts = get_session_alerts(session_id)

    print("\nALERTS")
    print("-----------------------------------")

    if not alerts:
        print("No alerts found.")
    else:
        for alert in alerts:
            print(
                f"[{alert['severity']}] "
                f"{alert['alert_type']} - "
                f"{alert['message']}"
            )

    evidence = get_session_evidence(session_id)

    print("\nEVIDENCE")
    print("-----------------------------------")

    if not evidence:
        print("No evidence found.")
    else:
        for item in evidence:
            print(
                f"{item['evidence_type']} - "
                f"{item['description']}"
            )


if __name__ == "__main__":

    # Test with session 9
    session_id = 9

    print(f"\nGenerating alerts for session {session_id}...")

    generate_session_alerts(session_id)

    demo_evidence(session_id)

    print_session_report(session_id)