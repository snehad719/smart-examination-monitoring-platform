import sqlite3

connection = sqlite3.connect("data/examguard.db")

cursor = connection.cursor()

cursor.execute(
    """
    INSERT INTO exam_sessions (
        candidate_id,
        status,
        start_time
    )
    VALUES (?, ?, datetime('now'))
    """,
    (1, "STARTED")
)

connection.commit()

print("New Session ID:", cursor.lastrowid)

connection.close()