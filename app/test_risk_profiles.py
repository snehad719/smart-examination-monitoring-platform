import sqlite3
from database import DATABASE
from app.integrity_scoring import calculate_integrity_score
from app.alert_evidence import generate_session_alerts, print_session_report


def get_connection():
    connection = sqlite3.connect(DATABASE)
    connection.row_factory = sqlite3.Row
    return connection


def create_test_session(candidate_id):
    connection = get_connection()

    cursor = connection.execute(
        """
        INSERT INTO exam_sessions (
            candidate_id,
            status,
            start_time,
            end_time
        )
        VALUES (
            ?,
            ?,
            datetime('now', '-10 minutes'),
            datetime('now')
        )
        """,
        (candidate_id, "SUBMITTED")
    )

    session_id = cursor.lastrowid

    connection.commit()
    connection.close()

    return session_id


def add_face_event(session_id, duration):
    connection = get_connection()

    connection.execute(
        """
        INSERT INTO face_events (
            session_id,
            event_type,
            start_time,
            end_time,
            duration_seconds
        )
        VALUES (
            ?,
            'FACE_ABSENT',
            datetime('now'),
            datetime('now'),
            ?
        )
        """,
        (session_id, duration)
    )

    connection.commit()
    connection.close()


def test_profile(name, candidate_id, durations):
    print("\n===================================")
    print(f"{name} RISK PROFILE")
    print("===================================")

    session_id = create_test_session(candidate_id)

    for duration in durations:
        add_face_event(session_id, duration)

    result = calculate_integrity_score(session_id)

    print(f"Session ID     : {session_id}")
    print(f"Integrity Score: {result['integrity_score']}")
    print(f"Risk Label     : {result['risk_label']}")

    generate_session_alerts(session_id)

    print_session_report(session_id)

    return session_id


if __name__ == "__main__":

    candidate_id = 1

    # ===================================
    # LOW RISK
    # ===================================

    test_profile(
        "LOW",
        candidate_id,
        []
    )

    # ===================================
    # MEDIUM RISK
    # ===================================

    test_profile(
        "MEDIUM",
        candidate_id,
        [2.5, 2.5, 2.5]
    )

    # ===================================
    # HIGH RISK
    # ===================================

    test_profile(
        "HIGH",
        candidate_id,
        [
            10, 10, 10, 10, 10,
            10, 10, 10, 10, 10
        ]
    )