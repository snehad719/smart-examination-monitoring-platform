import sqlite3

connection = sqlite3.connect("data/examguard.db")
cursor = connection.cursor()

cursor.execute("""
UPDATE exam_sessions
SET status = 'SUBMITTED',
    end_time = datetime('now')
WHERE id = 27
""")

connection.commit()
connection.close()

print("Session 27 closed successfully")