import sqlite3
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from integrity_scoring import calculate_integrity_score

DATABASE = "data/examguard.db"

llm = ChatOpenAI(
    model="gpt-4o-mini",
    temperature=0
)

prompt = ChatPromptTemplate.from_template("""
You are an online examination integrity analyst.

Analyze this candidate's examination session.

Session ID: {session_id}
Face Presence Ratio: {face_presence_ratio}
Event Penalty: {event_penalty}
Integrity Score: {integrity_score}
Risk Label: {risk_label}

Events:
{events}

Generate a concise report for the invigilator.
Mention important suspicious events, face presence,
integrity score and overall risk.
Do not recommend disciplinary action.
""")

def get_events(session_id):
    con = sqlite3.connect(DATABASE)

    face = con.execute("""
        SELECT event_type, start_time, end_time, duration_seconds
        FROM face_events
        WHERE session_id = ?
    """, (session_id,)).fetchall()

    browser = con.execute("""
        SELECT event_type, event_time, details
        FROM browser_events
        WHERE session_id = ?
    """, (session_id,)).fetchall()

    con.close()

    events = []

    for e in face:
        events.append(
            f"Face: {e[0]}, start={e[1]}, end={e[2]}, duration={e[3]} sec"
        )

    for e in browser:
        events.append(
            f"Browser: {e[0]}, time={e[1]}, details={e[2]}"
        )

    return "\n".join(events) if events else "No suspicious events."


def generate_report(session_id):
    score = calculate_integrity_score(session_id)
    events = get_events(session_id)

    chain = prompt | llm

    response = chain.invoke({
        **score,
        "events": events
    })

    return response.content


if __name__ == "__main__":
    session_id = int(input("Enter Exam Session ID: "))

    try:
        print("\n========== AI INTEGRITY REPORT ==========\n")
        print(generate_report(session_id))
    except Exception as e:
        print("Error:", e)