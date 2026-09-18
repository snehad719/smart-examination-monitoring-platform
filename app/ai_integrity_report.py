import os
import sqlite3

from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from langchain_ollama import ChatOllama

from app.integrity_scoring import calculate_integrity_score

DATABASE = "data/examguard.db"
OLLAMA_MODEL = "llama3.2"


def get_session_events(session_id):
    connection = sqlite3.connect(DATABASE)
    connection.row_factory = sqlite3.Row

    events = connection.execute(
        """
        SELECT
            event_type,
            start_time,
            end_time,
            duration_seconds
        FROM face_events
        WHERE session_id = ?
        ORDER BY start_time
        """,
        (session_id,)
    ).fetchall()

    connection.close()

    return [dict(event) for event in events]


def build_session_context(session_id):
    score_data = calculate_integrity_score(session_id)
    events = get_session_events(session_id)

    face_absent_events = [
        event
        for event in events
        if event["event_type"] == "FACE_ABSENT"
    ]

    # Application calculates the authoritative value.
    total_face_absence = sum(
        float(event["duration_seconds"] or 0)
        for event in face_absent_events
    )

    return {
        "session_id": session_id,
        "integrity_score": score_data["integrity_score"],
        "risk_label": score_data["risk_label"],
        "face_presence_ratio": score_data["face_presence_ratio"],
        "event_penalty": score_data["event_penalty"],
        "events": events,
        "face_absent_event_count": len(face_absent_events),
        "total_face_absence": round(
            total_face_absence,
            2
        )
    }


def build_prompt():
    return ChatPromptTemplate.from_messages(
        [
            (
                "system",
                """
You are ExamGuard, an examination integrity
analysis assistant.

Generate a concise, factual and professional
integrity summary for an invigilator.

IMPORTANT RULES:

- Use ONLY the supplied session data.
- Do NOT recalculate numeric values.
- Do NOT change, estimate, round differently,
  or reinterpret any supplied numeric value.
- The supplied total face absence duration is
  already calculated by the ExamGuard application.
- Report the supplied values exactly as given.
- Do not invent events or information.
- Do not accuse the candidate of cheating.
- Clearly distinguish observed monitoring events
  from interpretation.

The report must include:

1. Session ID
2. Integrity score
3. Risk level
4. Important integrity-related events
5. Face presence information
6. Total face absence duration
7. A short overall assessment

Keep the report concise, readable and suitable
for an invigilator.
"""
            ),
            (
                "human",
                """
ExamGuard session data:

Session ID:
{session_id}

Integrity Score:
{integrity_score}

Risk Label:
{risk_label}

Face Presence Ratio:
{face_presence_ratio}

Event Penalty:
{event_penalty}

Number of FACE_ABSENT events:
{face_absent_event_count}

Total FACE_ABSENT duration:
{total_face_absence} seconds

Recorded Events:
{events}

Generate the integrity summary report.

Remember:
The numeric values above are authoritative
application-calculated values. Use them exactly.
Do not recalculate them.
"""
            )
        ]
    )


def generate_openai_report(context):
    api_key = os.getenv("OPENAI_API_KEY")

    if not api_key:
        return None

    try:
        model = ChatOpenAI(
            model="gpt-4o-mini",
            temperature=0
        )

        chain = build_prompt() | model
        response = chain.invoke(context)

        return response.content

    except Exception as error:
        print()
        print(f"OpenAI unavailable: {error}")
        return None


def generate_ollama_report(context):
    try:
        model = ChatOllama(
            model=OLLAMA_MODEL,
            temperature=0
        )

        chain = build_prompt() | model
        response = chain.invoke(context)

        return response.content

    except Exception as error:
        print()
        print(f"Ollama unavailable: {error}")
        return None


def generate_offline_report(context):
    if context["risk_label"] == "High":
        assessment = (
            "The session shows high integrity risk "
            "and requires invigilator review."
        )

    elif context["risk_label"] == "Medium":
        assessment = (
            "The session shows medium integrity risk "
            "and may require invigilator review."
        )

    else:
        assessment = (
            "The session shows low integrity risk "
            "based on the recorded monitoring data."
        )

    report = (
        f"Session {context['session_id']} has an integrity "
        f"score of {context['integrity_score']}, classified as "
        f"{context['risk_label']} risk.\n"
        f"Face presence ratio was "
        f"{context['face_presence_ratio']}.\n"
        f"The recorded event penalty was "
        f"{context['event_penalty']}.\n"
        f"{context['face_absent_event_count']} FACE_ABSENT "
        f"event(s) were recorded, with a combined absence "
        f"duration of {context['total_face_absence']:.2f} seconds.\n"
        f"Overall assessment: {assessment}\n"
        f"This report is based only on recorded monitoring "
        f"events and calculated integrity metrics."
    )

    return report


def generate_integrity_report(session_id):
    context = build_session_context(session_id)

    # Priority 1: OpenAI
    report = generate_openai_report(context)

    if report:
        return report, "OPENAI"

    # Priority 2: Local Ollama
    report = generate_ollama_report(context)

    if report:
        return report, "OLLAMA LOCAL AI"

    # Priority 3: Offline fallback
    report = generate_offline_report(context)

    return report, "OFFLINE DEMO"


def ensure_ai_reports_table(connection):
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS ai_reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id INTEGER NOT NULL,
            report TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    columns = [
        row[1]
        for row in connection.execute(
            "PRAGMA table_info(ai_reports)"
        ).fetchall()
    ]

    # Migration for older ai_reports table
    if "mode" not in columns:
        connection.execute(
            """
            ALTER TABLE ai_reports
            ADD COLUMN mode TEXT DEFAULT 'AI'
            """
        )


def save_report(session_id, report, mode):
    connection = sqlite3.connect(DATABASE)

    ensure_ai_reports_table(connection)

    connection.execute(
        """
        INSERT INTO ai_reports (
            session_id,
            report,
            mode
        )
        VALUES (?, ?, ?)
        """,
        (
            session_id,
            report,
            mode
        )
    )

    connection.commit()
    connection.close()


def main():
    print()
    print("======================================")
    print("ExamGuard AI Integrity Report Agent")
    print("======================================")

    try:
        session_id = int(
            input("Enter Exam Session ID: ")
        )

    except ValueError:
        print("Error: Session ID must be a number.")
        return

    try:
        context = build_session_context(
            session_id
        )

    except Exception as error:
        print(
            f"Error reading session data: {error}"
        )
        return

    print()
    print("Session Information")
    print("-------------------")

    print(
        f"Session ID            : "
        f"{context['session_id']}"
    )

    print(
        f"Integrity Score       : "
        f"{context['integrity_score']}"
    )

    print(
        f"Risk Label            : "
        f"{context['risk_label']}"
    )

    print(
        f"Face Presence Ratio   : "
        f"{context['face_presence_ratio']}"
    )

    print(
        f"Event Penalty         : "
        f"{context['event_penalty']}"
    )

    print(
        f"FACE_ABSENT Events    : "
        f"{context['face_absent_event_count']}"
    )

    print(
        f"Total Face Absence    : "
        f"{context['total_face_absence']} seconds"
    )

    print(
        f"Recorded Events       : "
        f"{len(context['events'])}"
    )

    print()
    print("Generating integrity report...")

    report, mode = generate_integrity_report(
        session_id
    )

    print()
    print("======================================")
    print("Integrity Summary")
    print("======================================")
    print()

    print(
        f"Report Mode: {mode}"
    )

    print()
    print(report)

    try:
        save_report(
            session_id,
            report,
            mode
        )

        print()
        print(
            f"Report saved to SQLite "
            f"({mode} mode)."
        )

    except Exception as error:
        print()
        print(
            "Warning: Report generated but "
            f"could not be saved: {error}"
        )


if __name__ == "__main__":
    main()