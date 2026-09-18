import sqlite3
import os

DATABASE = "data/examguard.db"


def get_db_connection():
    connection = sqlite3.connect(DATABASE)
    connection.row_factory = sqlite3.Row
    return connection


def init_db():

    os.makedirs("data", exist_ok=True)
    os.makedirs("data/evidence", exist_ok=True)

    connection = get_db_connection()

    # ==============================
    # CANDIDATES TABLE
    # ==============================

    connection.execute("""
        CREATE TABLE IF NOT EXISTS candidates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            photo_path TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # ==============================
    # EXAM SESSIONS TABLE
    # ==============================

    connection.execute("""
        CREATE TABLE IF NOT EXISTS exam_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            candidate_id INTEGER NOT NULL,
            status TEXT NOT NULL,
            start_time TIMESTAMP,
            end_time TIMESTAMP,
            FOREIGN KEY (candidate_id) REFERENCES candidates(id)
        )
    """)

    # ==============================
    # FACE EVENTS TABLE
    # ==============================

    connection.execute("""
        CREATE TABLE IF NOT EXISTS face_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id INTEGER,
            event_type TEXT NOT NULL,
            start_time TIMESTAMP NOT NULL,
            end_time TIMESTAMP,
            duration_seconds REAL,
            FOREIGN KEY (session_id) REFERENCES exam_sessions(id)
        )
    """)

    # ==============================
    # BROWSER EVENTS TABLE
    # ==============================

    connection.execute("""
        CREATE TABLE IF NOT EXISTS browser_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id INTEGER,
            event_type TEXT NOT NULL,
            event_time TIMESTAMP NOT NULL,
            details TEXT,
            FOREIGN KEY (session_id) REFERENCES exam_sessions(id)
        )
    """)

    # ==============================
    # ALERTS TABLE
    # ==============================

    connection.execute("""
        CREATE TABLE IF NOT EXISTS alerts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id INTEGER NOT NULL,
            alert_type TEXT NOT NULL,
            severity TEXT NOT NULL,
            message TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            resolved INTEGER DEFAULT 0,
            FOREIGN KEY (session_id) REFERENCES exam_sessions(id)
        )
    """)

    # ==============================
    # EVIDENCE TABLE
    # ==============================

    connection.execute("""
        CREATE TABLE IF NOT EXISTS evidence (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id INTEGER NOT NULL,
            evidence_type TEXT NOT NULL,
            file_path TEXT,
            description TEXT,
            captured_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (session_id) REFERENCES exam_sessions(id)
        )
    """)

    # ==============================
    # AI REPORTS TABLE
    # ==============================

    connection.execute("""
        CREATE TABLE IF NOT EXISTS ai_reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id INTEGER NOT NULL,
            report TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (session_id) REFERENCES exam_sessions(id)
        )
    """)

    connection.commit()
    connection.close()

    print("Database initialized successfully!")


if __name__ == "__main__":
    init_db()