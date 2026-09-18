import sqlite3
import os
from datetime import datetime

DATABASE = "data/examguard.db"
EVIDENCE_DIR = "data/evidence"


def create_alert(session_id, alert_type, severity, message):
    conn = sqlite3.connect(DATABASE)

    conn.execute("""
        INSERT INTO alerts
        (session_id, alert_type, severity, message)
        VALUES (?, ?, ?, ?)
    """, (
        session_id,
        alert_type,
        severity,
        message
    ))

    conn.commit()
    conn.close()

    print("Alert created successfully!")


def save_evidence(session_id, evidence_type, file_path, description):
    os.makedirs(EVIDENCE_DIR, exist_ok=True)

    conn = sqlite3.connect(DATABASE)

    conn.execute("""
        INSERT INTO evidence
        (session_id, evidence_type, file_path, description)
        VALUES (?, ?, ?, ?)
    """, (
        session_id,
        evidence_type,
        file_path,
        description
    ))

    conn.commit()
    conn.close()

    print("Evidence saved successfully!")


def get_alerts(session_id):
    conn = sqlite3.connect(DATABASE)

    alerts = conn.execute("""
        SELECT id, alert_type, severity, message,
               created_at, resolved
        FROM alerts
        WHERE session_id = ?
        ORDER BY created_at DESC
    """, (session_id,)).fetchall()

    conn.close()

    return alerts


def get_evidence(session_id):
    conn = sqlite3.connect(DATABASE)

    evidence = conn.execute("""
        SELECT id, evidence_type, file_path,
               description, captured_at
        FROM evidence
        WHERE session_id = ?
        ORDER BY captured_at DESC
    """, (session_id,)).fetchall()

    conn.close()

    return evidence


def resolve_alert(alert_id):
    conn = sqlite3.connect(DATABASE)

    conn.execute("""
        UPDATE alerts
        SET resolved = 1
        WHERE id = ?
    """, (alert_id,))

    conn.commit()
    conn.close()

    print("Alert resolved successfully!")


if __name__ == "__main__":

    session_id = int(input("Enter Session ID: "))

    print("\n===== ALERTS =====")

    alerts = get_alerts(session_id)

    if alerts:
        for alert in alerts:
            print(
                f"ID: {alert[0]} | "
                f"Type: {alert[1]} | "
                f"Severity: {alert[2]} | "
                f"Resolved: {alert[5]}"
            )
            print(f"Message: {alert[3]}")
    else:
        print("No alerts found.")

    print("\n===== EVIDENCE =====")

    evidence = get_evidence(session_id)

    if evidence:
        for item in evidence:
            print(
                f"ID: {item[0]} | "
                f"Type: {item[1]} | "
                f"File: {item[2]}"
            )
            print(f"Description: {item[3]}")
    else:
        print("No evidence found.")