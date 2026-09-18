import sqlite3
from app.integrity_scoring import calculate_integrity_score

DATABASE = "data/examguard.db"


def get_events(session_id):
    connection = sqlite3.connect(DATABASE)

    face_events = connection.execute("""
        SELECT event_type, duration_seconds
        FROM face_events
        WHERE session_id = ?
    """, (session_id,)).fetchall()

    browser_events = connection.execute("""
        SELECT event_type, details
        FROM browser_events
        WHERE session_id = ?
    """, (session_id,)).fetchall()

    connection.close()

    return face_events, browser_events


def generate_report(session_id):

    score = calculate_integrity_score(session_id)

    face_events, browser_events = get_events(session_id)

    # Face absence duration
    face_absent_duration = sum(
        (event[1] or 0)
        for event in face_events
        if event[0] == "FACE_ABSENT"
    )

    # Browser events
    tab_switches = sum(
        1 for event in browser_events
        if event[0] == "TAB_SWITCH"
    )

    focus_losses = sum(
        1 for event in browser_events
        if event[0] == "FOCUS_LOST"
    )

    suspicious_events = sum(
        1 for event in browser_events
        if event[0] == "SUSPICIOUS_EVENT"
    )

    # Generate explanation
    reasons = []

    if tab_switches > 3:
        reasons.append(
            f"excessive tab switching ({tab_switches} times)"
        )

    if focus_losses > 5:
        reasons.append(
            f"excessive focus loss ({focus_losses} times)"
        )

    if face_absent_duration > 0:
        reasons.append(
            f"face absence for {face_absent_duration:.0f} seconds"
        )

    if reasons:
        risk_reason = "The session was flagged because of " + ", ".join(reasons) + "."
    else:
        risk_reason = "No major suspicious activity was detected."

    # Recommendation
    if score["risk_label"] == "High":
        recommendation = (
            "Manual examiner review is recommended because the session "
            "shows significant integrity concerns."
        )
    elif score["risk_label"] == "Medium":
        recommendation = (
            "The session should be reviewed for possible suspicious activity."
        )
    else:
        recommendation = (
            "The session appears normal based on the recorded monitoring events."
        )

    report = f"""
Candidate Integrity Report
==========================

Session ID: {session_id}

MONITORING SUMMARY
------------------
Face Presence Ratio : {score['face_presence_ratio'] * 100:.2f}%
Face Absent Duration: {face_absent_duration:.0f} seconds
Tab Switches        : {tab_switches}
Focus Loss Events   : {focus_losses}
Suspicious Events   : {suspicious_events}

INTEGRITY ANALYSIS
------------------
Event Penalty       : {score['event_penalty']}
Integrity Score     : {score['integrity_score']}
Overall Risk        : {score['risk_label']}

AI-GENERATED SUMMARY
--------------------
{risk_reason}

{recommendation}

FINAL ASSESSMENT
----------------
The candidate's integrity score is {score['integrity_score']} out of 100.
The overall risk level is classified as {score['risk_label']}.
"""


    return report


def save_report(session_id, report):

    connection = sqlite3.connect(DATABASE)

    connection.execute("""
        INSERT INTO ai_reports (session_id, report)
        VALUES (?, ?)
    """, (session_id, report))

    connection.commit()
    connection.close()

    print("\nReport saved successfully!")


if __name__ == "__main__":

    session_id = int(
        input("Enter Exam Session ID: ")
    )

    try:

        report = generate_report(session_id)

        print("\n========== INTEGRITY REPORT ==========\n")
        print(report)

        save_report(
            session_id,
            report
        )

    except Exception as error:

        print(f"\nError: {error}")
