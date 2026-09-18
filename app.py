from flask import (
    Flask,
    render_template,
    request,
    redirect,
    session,
    url_for,
    jsonify
)

from database import init_db, get_db_connection

from datetime import datetime

import os
import base64

import cv2
import numpy as np


app = Flask(__name__)

app.secret_key = "examguard-secret-key"

init_db()


# ============================================================
# SETTINGS
# ============================================================

FACE_ABSENT_THRESHOLD_SECONDS = 10
FOCUS_LOSS_THRESHOLD = 5
TAB_SWITCH_THRESHOLD = 3


# ============================================================
# FACE MONITORING MEMORY
# ============================================================

face_monitor_state = {}


# ============================================================
# QUESTIONS
# ============================================================

QUESTIONS = [

    {
        "id": 1,
        "question": "What does AI stand for?",
        "options": [
            "Artificial Intelligence",
            "Automated Internet",
            "Advanced Interface",
            "Automatic Information"
        ],
        "answer": "Artificial Intelligence"
    },

    {
        "id": 2,
        "question": "Which language is mainly used for web page structure?",
        "options": [
            "HTML",
            "Python",
            "SQL",
            "Java"
        ],
        "answer": "HTML"
    },

    {
        "id": 3,
        "question": "Which of the following is a database?",
        "options": [
            "SQLite",
            "HTML",
            "CSS",
            "JavaScript"
        ],
        "answer": "SQLite"
    },

    {
        "id": 4,
        "question": "What is the full form of CPU?",
        "options": [
            "Central Processing Unit",
            "Computer Personal Unit",
            "Central Program Utility",
            "Control Processing User"
        ],
        "answer": "Central Processing Unit"
    },

    {
        "id": 5,
        "question": "Which technology is used to style web pages?",
        "options": [
            "CSS",
            "SQL",
            "Python",
            "Flask"
        ],
        "answer": "CSS"
    }

]


# ============================================================
# DATABASE - ENSURE RESULT COLUMNS
# ============================================================

def ensure_result_columns():

    connection = get_db_connection()

    columns = connection.execute(
        "PRAGMA table_info(exam_sessions)"
    ).fetchall()

    existing_columns = {
        row["name"]
        for row in columns
    }

    if "exam_score" not in existing_columns:

        connection.execute(
            """
            ALTER TABLE exam_sessions
            ADD COLUMN exam_score INTEGER DEFAULT 0
            """
        )

    if "integrity_score" not in existing_columns:

        connection.execute(
            """
            ALTER TABLE exam_sessions
            ADD COLUMN integrity_score INTEGER DEFAULT 100
            """
        )

    if "risk_level" not in existing_columns:

        connection.execute(
            """
            ALTER TABLE exam_sessions
            ADD COLUMN risk_level TEXT DEFAULT 'Not Started'
            """
        )

    connection.commit()

    connection.close()


ensure_result_columns()


# ============================================================
# HELPER - CURRENT LOGIN EXAM SESSION
# ============================================================

def get_current_exam_session():

    if "candidate_id" not in session:
        return None

    session_id = session.get("exam_session_id")

    if not session_id:
        return None

    connection = get_db_connection()

    row = connection.execute(
        """
        SELECT *
        FROM exam_sessions
        WHERE id = ?
        AND candidate_id = ?
        LIMIT 1
        """,
        (
            session_id,
            session["candidate_id"]
        )
    ).fetchone()

    connection.close()

    return row


# ============================================================
# HELPER - LATEST SESSION
# ============================================================

def latest():

    if "candidate_id" not in session:
        return None

    connection = get_db_connection()

    row = connection.execute(
        """
        SELECT *
        FROM exam_sessions
        WHERE candidate_id = ?
        ORDER BY id DESC
        LIMIT 1
        """,
        (
            session["candidate_id"],
        )
    ).fetchone()

    connection.close()

    return row


# ============================================================
# HELPER - HAS COMPLETED EXAM
# ============================================================

def has_completed_exam():

    if "candidate_id" not in session:
        return False

    connection = get_db_connection()

    row = connection.execute(
        """
        SELECT 1
        FROM exam_sessions
        WHERE candidate_id = ?
        AND status = 'SUBMITTED'
        LIMIT 1
        """,
        (
            session["candidate_id"],
        )
    ).fetchone()

    connection.close()

    return row is not None


# ============================================================
# HELPER - GET COMPLETED EXAM
# ============================================================

def get_completed_exam():

    if "candidate_id" not in session:
        return None

    connection = get_db_connection()

    row = connection.execute(
        """
        SELECT *
        FROM exam_sessions
        WHERE candidate_id = ?
        AND status = 'SUBMITTED'
        ORDER BY id DESC
        LIMIT 1
        """,
        (
            session["candidate_id"],
        )
    ).fetchone()

    connection.close()

    return row


# ============================================================
# HELPER - CREATE ALERT
# ============================================================

def create_alert_db(
    connection,
    session_id,
    alert_type,
    severity,
    message
):

    connection.execute(
        """
        INSERT INTO alerts
        (
            session_id,
            alert_type,
            severity,
            message,
            resolved
        )
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            session_id,
            alert_type,
            severity,
            message,
            0
        )
    )


# ============================================================
# HELPER - SAVE TEXT EVIDENCE
# ============================================================

def save_text_evidence(
    connection,
    session_id,
    evidence_type,
    description
):

    connection.execute(
        """
        INSERT INTO evidence
        (
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
            None,
            description
        )
    )


# ============================================================
# HELPER - SAVE FRAME EVIDENCE
# ============================================================

def save_frame_evidence(
    connection,
    session_id,
    frame,
    evidence_type,
    description
):

    evidence_dir = os.path.join(
        "data",
        "evidence"
    )

    os.makedirs(
        evidence_dir,
        exist_ok=True
    )

    filename = (
        f"session_{session_id}_"
        f"{evidence_type.lower()}_"
        f"{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}.jpg"
    )

    file_path = os.path.join(
        evidence_dir,
        filename
    )

    cv2.imwrite(
        file_path,
        frame
    )

    connection.execute(
        """
        INSERT INTO evidence
        (
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

    return file_path


# ============================================================
# HELPER - DEFAULT EVENT COUNTS
# ============================================================

def empty_event_counts():

    return {

        "TAB_SWITCH": 0,

        "FOCUS_LOST": 0,

        "SUSPICIOUS_EVENT": 0,

        "FACE_ABSENT_START": 0,

        "FACE_ABSENT_INTERVAL": 0,

        "EXAM_INTERACTION": 0

    }


# ============================================================
# HELPER - GET EVENT COUNTS
# ============================================================

def get_event_counts(session_id):

    counts = empty_event_counts()

    if not session_id:
        return counts

    connection = get_db_connection()

    rows = connection.execute(
        """
        SELECT
            event_type,
            COUNT(*) AS count
        FROM browser_events
        WHERE session_id = ?
        GROUP BY event_type
        """,
        (
            session_id,
        )
    ).fetchall()

    connection.close()

    for row in rows:

        event_type = row["event_type"]

        if event_type in counts:

            counts[event_type] = row["count"]

    return counts


# ============================================================
# HELPER - FACE ABSENT DATA
# ============================================================

def get_face_absent_data(session_id):

    result = {

        "count": 0,

        "duration": 0

    }

    if not session_id:
        return result

    connection = get_db_connection()

    rows = connection.execute(
        """
        SELECT details
        FROM browser_events
        WHERE session_id = ?
        AND event_type = 'FACE_ABSENT_INTERVAL'
        ORDER BY id
        """,
        (
            session_id,
        )
    ).fetchall()

    connection.close()

    for row in rows:

        result["count"] += 1

        details = row["details"] or ""

        try:

            if ":" in details:

                value = details.rsplit(
                    ":",
                    1
                )[1].strip()

                value = value.replace(
                    "seconds",
                    ""
                ).strip()

                result["duration"] += int(
                    float(value)
                )

        except Exception:

            pass

    return result


# ============================================================
# HELPER - INSERT BROWSER EVENT
# ============================================================

def insert_browser_event(
    connection,
    session_id,
    event_type,
    details=""
):

    connection.execute(
        """
        INSERT INTO browser_events
        (
            session_id,
            event_type,
            event_time,
            details
        )
        VALUES (?, ?, ?, ?)
        """,
        (
            session_id,
            event_type,
            datetime.now(),
            details
        )
    )


# ============================================================
# HELPER - CHECK SUSPICIOUS EVENT
# ============================================================

def suspicious_event_exists(
    connection,
    session_id,
    detail_prefix
):

    row = connection.execute(
        """
        SELECT 1
        FROM browser_events
        WHERE session_id = ?
        AND event_type = 'SUSPICIOUS_EVENT'
        AND details LIKE ?
        LIMIT 1
        """,
        (
            session_id,
            detail_prefix + "%"
        )
    ).fetchone()

    return row is not None


# ============================================================
# HELPER - CALCULATE INTEGRITY RESULT
# ============================================================

def calculate_session_integrity(session_id):

    if not session_id:

        return 100, "Low"

    connection = get_db_connection()

    tab_row = connection.execute(
        """
        SELECT COUNT(*) AS n
        FROM browser_events
        WHERE session_id = ?
        AND event_type = 'TAB_SWITCH'
        """,
        (session_id,)
    ).fetchone()

    focus_row = connection.execute(
        """
        SELECT COUNT(*) AS n
        FROM browser_events
        WHERE session_id = ?
        AND event_type = 'FOCUS_LOST'
        """,
        (session_id,)
    ).fetchone()

    suspicious_row = connection.execute(
        """
        SELECT COUNT(*) AS n
        FROM browser_events
        WHERE session_id = ?
        AND event_type = 'SUSPICIOUS_EVENT'
        """,
        (session_id,)
    ).fetchone()

    face_row = connection.execute(
        """
        SELECT COUNT(*) AS n
        FROM browser_events
        WHERE session_id = ?
        AND event_type = 'FACE_ABSENT_INTERVAL'
        """,
        (session_id,)
    ).fetchone()

    connection.close()

    tab_count = tab_row["n"]
    focus_count = focus_row["n"]
    suspicious_count = suspicious_row["n"]
    face_count = face_row["n"]

    score = 100

    score -= tab_count * 2
    score -= focus_count * 1
    score -= suspicious_count * 10
    score -= face_count * 5

    score = max(
        0,
        min(
            100,
            score
        )
    )

    if score >= 70:

        risk = "Low"

    elif score >= 40:

        risk = "Medium"

    else:

        risk = "High"

    return score, risk


# ============================================================
# HELPER - SUSPICION EVALUATION
# ============================================================

def evaluate_browser_suspicion(
    connection,
    session_id
):

    tab_row = connection.execute(
        """
        SELECT COUNT(*) AS n
        FROM browser_events
        WHERE session_id = ?
        AND event_type = 'TAB_SWITCH'
        """,
        (session_id,)
    ).fetchone()

    tab_count = tab_row["n"]

    focus_row = connection.execute(
        """
        SELECT COUNT(*) AS n
        FROM browser_events
        WHERE session_id = ?
        AND event_type = 'FOCUS_LOST'
        """,
        (session_id,)
    ).fetchone()

    focus_count = focus_row["n"]

    if tab_count > TAB_SWITCH_THRESHOLD:

        prefix = (
            f"More than {TAB_SWITCH_THRESHOLD} "
            f"tab switches"
        )

        if not suspicious_event_exists(
            connection,
            session_id,
            prefix
        ):

            message = (
                f"More than {TAB_SWITCH_THRESHOLD} "
                f"tab switches detected "
                f"(count={tab_count})."
            )

            insert_browser_event(
                connection,
                session_id,
                "SUSPICIOUS_EVENT",
                message
            )

            create_alert_db(
                connection,
                session_id,
                "TAB_SWITCH",
                "HIGH",
                f"Suspicious tab switching detected. "
                f"Count: {tab_count}"
            )

            save_text_evidence(
                connection,
                session_id,
                "TAB_SWITCH",
                message
            )

            print(
                f"SUSPICIOUS EVENT | "
                f"TAB_SWITCH | count={tab_count}"
            )

    if focus_count > FOCUS_LOSS_THRESHOLD:

        prefix = "Excessive focus loss"

        if not suspicious_event_exists(
            connection,
            session_id,
            prefix
        ):

            message = (
                f"Excessive focus loss detected "
                f"(count={focus_count})."
            )

            insert_browser_event(
                connection,
                session_id,
                "SUSPICIOUS_EVENT",
                message
            )

            create_alert_db(
                connection,
                session_id,
                "FOCUS_LOST",
                "HIGH",
                f"Excessive focus loss detected. "
                f"Count: {focus_count}"
            )

            save_text_evidence(
                connection,
                session_id,
                "FOCUS_LOST",
                message
            )

            print(
                f"SUSPICIOUS EVENT | "
                f"FOCUS_LOST | count={focus_count}"
            )


# ============================================================
# HOME
# ============================================================

@app.route("/")
def home():

    return """
    <h1>ExamGuard</h1>

    <br>

    <a href="/login">
        Candidate Login
    </a>

    <br><br>

    <a href="/register">
        Candidate Registration
    </a>
    """


# ============================================================
# REGISTER
# ============================================================

@app.route(
    "/register",
    methods=["GET", "POST"]
)
def register():

    if request.method == "POST":

        connection = get_db_connection()

        try:

            connection.execute(
                """
                INSERT INTO candidates
                (
                    name,
                    email,
                    password
                )
                VALUES (?, ?, ?)
                """,
                (
                    request.form["name"],
                    request.form["email"],
                    request.form["password"]
                )
            )

            connection.commit()

            return "Registration successful!"

        except Exception as error:

            return f"Registration failed: {error}"

        finally:

            connection.close()

    return render_template("register.html")


# ============================================================
# LOGIN
# ============================================================

@app.route(
    "/login",
    methods=["GET", "POST"]
)
def login():

    if request.method == "POST":

        connection = get_db_connection()

        candidate = connection.execute(
            """
            SELECT *
            FROM candidates
            WHERE email = ?
            AND password = ?
            """,
            (
                request.form["email"],
                request.form["password"]
            )
        ).fetchone()

        if not candidate:

            connection.close()

            return "Invalid email or password!"

        old_sessions = connection.execute(
            """
            SELECT id
            FROM exam_sessions
            WHERE candidate_id = ?
            AND status IN ('STARTED', 'PAUSED')
            """,
            (
                candidate["id"],
            )
        ).fetchall()

        connection.execute(
            """
            UPDATE exam_sessions
            SET
                status = 'ABANDONED',
                end_time = ?
            WHERE candidate_id = ?
            AND status IN ('STARTED', 'PAUSED')
            """,
            (
                datetime.now(),
                candidate["id"]
            )
        )

        connection.commit()

        connection.close()

        session.clear()

        session["candidate_id"] = candidate["id"]

        session["candidate_name"] = candidate["name"]

        session["candidate_email"] = candidate["email"]

        # ----------------------------------------------------
        # IMPORTANT:
        # If candidate already completed the exam,
        # keep the submitted session as the current result.
        # Otherwise there is no exam session yet.
        # ----------------------------------------------------

        completed_exam = get_completed_exam()

        if completed_exam:

            session["exam_session_id"] = completed_exam["id"]

            session["score"] = (
                completed_exam["exam_score"] or 0
            )

        else:

            session.pop(
                "exam_session_id",
                None
            )

            session.pop(
                "current_question",
                None
            )

            session.pop(
                "answers",
                None
            )

            session.pop(
                "score",
                None
            )

        for old_session in old_sessions:

            face_monitor_state.pop(
                old_session["id"],
                None
            )

        print(
            f"CANDIDATE LOGIN | "
            f"Candidate={candidate['id']} | "
            f"Fresh login session created"
        )

        return redirect(
            url_for("dashboard")
        )

    return render_template(
        "login.html"
    )


# ============================================================
# DASHBOARD
# ============================================================

@app.route("/dashboard")
def dashboard():

    if "candidate_id" not in session:

        return redirect(
            url_for("login")
        )

    connection = get_db_connection()

    completed_row = connection.execute(
        """
        SELECT COUNT(*) AS count
        FROM exam_sessions
        WHERE candidate_id = ?
        AND status = 'SUBMITTED'
        """,
        (
            session["candidate_id"],
        )
    ).fetchone()

    assigned_row = connection.execute(
        """
        SELECT COUNT(*) AS count
        FROM exam_sessions
        WHERE candidate_id = ?
        """,
        (
            session["candidate_id"],
        )
    ).fetchone()

    connection.close()

    completed_tests = completed_row["count"]

    assigned_tests = max(
        3,
        assigned_row["count"]
    )

    upcoming_tests = max(
        0,
        assigned_tests
        - completed_tests
        - 1
    )

    event_counts = empty_event_counts()

    face_absent_data = {
        "count": 0,
        "duration": 0
    }

    total_monitoring_events = 0

    integrity_score = 100

    risk_level = "Not Started"

    exam_status = "NOT STARTED"

    score = 0

    exam_session = None

    # ========================================================
    # CURRENT SESSION
    # ========================================================

    current_session_id = session.get(
        "exam_session_id"
    )

    if current_session_id:

        connection = get_db_connection()

        exam_session = connection.execute(
            """
            SELECT *
            FROM exam_sessions
            WHERE id = ?
            AND candidate_id = ?
            LIMIT 1
            """,
            (
                current_session_id,
                session["candidate_id"]
            )
        ).fetchone()

        connection.close()

    # ========================================================
    # IF NO CURRENT SESSION, CHECK SUBMITTED EXAM
    # ========================================================

    if not exam_session:

        exam_session = get_completed_exam()

        if exam_session:

            session["exam_session_id"] = (
                exam_session["id"]
            )

    # ========================================================
    # SHOW EXAM RESULT / MONITORING
    # ========================================================

    if exam_session:

        session_id = exam_session["id"]

        exam_status = exam_session["status"]

        event_counts = get_event_counts(
            session_id
        )

        face_absent_data = get_face_absent_data(
            session_id
        )

        total_monitoring_events = (

            event_counts["TAB_SWITCH"]

            + event_counts["FOCUS_LOST"]

            + event_counts["SUSPICIOUS_EVENT"]

            + event_counts["FACE_ABSENT_START"]

        )

        if exam_status == "SUBMITTED":

            score = (
                exam_session["exam_score"]
                or 0
            )

            integrity_score = (
                exam_session["integrity_score"]
                if exam_session["integrity_score"] is not None
                else 100
            )

            risk_level = (
                exam_session["risk_level"]
                or "Not Started"
            )

        elif exam_status in (
            "STARTED",
            "PAUSED"
        ):

            integrity_score, risk_level = (
                calculate_session_integrity(
                    session_id
                )
            )

            score = session.get(
                "score",
                0
            )

    return render_template(

        "dashboard.html",

        name=session["candidate_name"],

        assigned_tests=assigned_tests,

        completed_tests=completed_tests,

        upcoming_tests=upcoming_tests,

        integrity_score=integrity_score,

        risk_level=risk_level,

        exam_status=exam_status,

        score=score,

        event_counts=event_counts,

        face_absent_data=face_absent_data,

        total_monitoring_events=total_monitoring_events,

        recent_events=[],

        exam_session=exam_session,

        latest_session=exam_session

    )


# ============================================================
# EXAM DETAILS
# ============================================================

@app.route("/exam-details")
def exam_details():

    if "candidate_id" not in session:

        return redirect(
            url_for("login")
        )

    completed_exam = get_completed_exam()

    already_completed = (
        completed_exam is not None
    )

    return render_template(

        "exam_details.html",

        exam_title="Online Examination",

        total_questions=len(QUESTIONS),

        already_completed=already_completed,

        completed_exam=completed_exam,

        instructions=[

            "Read each question carefully.",

            "Select the correct answer before moving to the next question.",

            "Browser activity will be monitored during the examination.",

            "Camera-based face presence monitoring will be active.",

            "Avoid unnecessary tab switching or window focus changes.",

            "Review your answers before submitting the examination."

        ]

    )


# ============================================================
# EXAM PAGE
# ============================================================

@app.route("/exam")
def exam():

    if "candidate_id" not in session:

        return redirect(
            url_for("login")
        )

    cs = get_current_exam_session()

    if not cs:

        return redirect(
            url_for("exam-details")
        )

    status = cs["status"]

    if status == "SUBMITTED":

        return redirect(
            url_for("dashboard")
        )

    if status == "PAUSED":

        return render_template(

            "exam.html",

            name=session["candidate_name"],

            status=status,

            question=None,

            question_number=0,

            total_questions=len(QUESTIONS),

            answers=session.get(
                "answers",
                {}
            ),

            submitted=False,

            score=session.get(
                "score",
                0
            ),

            QUESTIONS=QUESTIONS

        )

    i = max(

        0,

        min(

            session.get(
                "current_question",
                0
            ),

            len(QUESTIONS) - 1

        )

    )

    session["current_question"] = i

    question = QUESTIONS[i]

    return render_template(

        "exam.html",

        name=session["candidate_name"],

        status=status,

        question=question,

        question_number=i + 1,

        total_questions=len(QUESTIONS),

        answers=session.get(
            "answers",
            {}
        ),

        submitted=False,

        score=session.get(
            "score",
            0
        ),

        QUESTIONS=QUESTIONS

    )


# ============================================================
# START EXAM
# ============================================================

@app.route(
    "/start-exam",
    methods=["POST"]
)
def start_exam():

    if "candidate_id" not in session:

        return redirect(
            url_for("login")
        )

    # ========================================================
    # IMPORTANT:
    # ONE CANDIDATE = ONE EXAM ATTEMPT
    # ========================================================

    if has_completed_exam():

        completed = get_completed_exam()

        if completed:

            session["exam_session_id"] = (
                completed["id"]
            )

            session["score"] = (
                completed["exam_score"] or 0
            )

        return redirect(
            url_for("exam-details")
        )

    current = get_current_exam_session()

    if current:

        if current["status"] == "STARTED":

            return redirect(
                url_for("exam")
            )

        if current["status"] == "PAUSED":

            return redirect(
                url_for("exam")
            )

    connection = get_db_connection()

    connection.execute(
        """
        UPDATE exam_sessions
        SET
            status = 'ABANDONED',
            end_time = ?
        WHERE candidate_id = ?
        AND status IN ('STARTED', 'PAUSED')
        """,
        (
            datetime.now(),
            session["candidate_id"]
        )
    )

    connection.execute(
        """
        INSERT INTO exam_sessions
        (
            candidate_id,
            status,
            start_time,
            exam_score,
            integrity_score,
            risk_level
        )
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            session["candidate_id"],
            "STARTED",
            datetime.now(),
            0,
            100,
            "Not Started"
        )
    )

    connection.commit()

    row = connection.execute(
        """
        SELECT id
        FROM exam_sessions
        WHERE candidate_id = ?
        AND status = 'STARTED'
        ORDER BY id DESC
        LIMIT 1
        """,
        (
            session["candidate_id"],
        )
    ).fetchone()

    connection.close()

    if not row:

        return "Unable to create exam session."

    session["exam_session_id"] = row["id"]

    session["current_question"] = 0

    session["answers"] = {}

    session["score"] = 0

    face_monitor_state[row["id"]] = {

        "absent_since": None,

        "alerted": False

    }

    print(
        f"EXAM STARTED | "
        f"Session={row['id']} | "
        f"Candidate={session['candidate_id']}"
    )

    return redirect(
        url_for("exam")
    )


# ============================================================
# ACTIVE EXAM CHECK
# ============================================================

def active_or_redirect():

    cs = get_current_exam_session()

    ajax = (
        request.headers.get(
            "X-ExamGuard-AJAX"
        ) == "1"
    )

    if not cs:

        if ajax:

            return jsonify({

                "success": False,

                "message":
                "Exam session not found."

            }), 404

        return redirect(
            url_for("exam-details")
        )

    if cs["status"] != "STARTED":

        if ajax:

            return jsonify({

                "success": False,

                "message":
                "Exam is not active."

            }), 400

        return redirect(
            url_for("exam")
        )

    return None


# ============================================================
# AJAX QUESTION RESPONSE
# ============================================================

def ajax_question_response():

    i = max(

        0,

        min(

            session.get(
                "current_question",
                0
            ),

            len(QUESTIONS) - 1

        )

    )

    session["current_question"] = i

    question = QUESTIONS[i]

    return jsonify({

        "success": True,

        "question_number": i + 1,

        "total_questions": len(QUESTIONS),

        "question": question["question"],

        "options": question["options"],

        "answers": session.get(
            "answers",
            {}
        ),

        "status": "STARTED"

    })


# ============================================================
# NEXT QUESTION
# ============================================================

@app.route(
    "/next-question",
    methods=["POST"]
)
def next_question():

    if "candidate_id" not in session:

        return redirect(
            url_for("login")
        )

    bad = active_or_redirect()

    if bad:

        return bad

    i = session.get(
        "current_question",
        0
    )

    answers = session.get(
        "answers",
        {}
    )

    selected = request.form.get(
        "answer"
    )

    if selected:

        answers[str(i)] = selected

    session["answers"] = answers

    if i < len(QUESTIONS) - 1:

        session["current_question"] = i + 1

    if request.headers.get(
        "X-ExamGuard-AJAX"
    ) == "1":

        return ajax_question_response()

    return redirect(
        url_for("exam")
    )


# ============================================================
# PREVIOUS QUESTION
# ============================================================

@app.route(
    "/previous-question",
    methods=["POST"]
)
def previous_question():

    if "candidate_id" not in session:

        return redirect(
            url_for("login")
        )

    bad = active_or_redirect()

    if bad:

        return bad

    i = session.get(
        "current_question",
        0
    )

    answers = session.get(
        "answers",
        {}
    )

    selected = request.form.get(
        "answer"
    )

    if selected:

        answers[str(i)] = selected

    session["answers"] = answers

    if i > 0:

        session["current_question"] = i - 1

    if request.headers.get(
        "X-ExamGuard-AJAX"
    ) == "1":

        return ajax_question_response()

    return redirect(
        url_for("exam")
    )


# ============================================================
# QUESTION PALETTE
# ============================================================

@app.route(
    "/question/<int:number>",
    methods=["POST"]
)
def go_to_question(number):

    if "candidate_id" not in session:

        return redirect(
            url_for("login")
        )

    bad = active_or_redirect()

    if bad:

        return bad

    i = session.get(
        "current_question",
        0
    )

    answers = session.get(
        "answers",
        {}
    )

    selected = request.form.get(
        "answer"
    )

    if selected:

        answers[str(i)] = selected

    session["answers"] = answers

    if 0 <= number - 1 < len(QUESTIONS):

        session["current_question"] = (
            number - 1
        )

    if request.headers.get(
        "X-ExamGuard-AJAX"
    ) == "1":

        return ajax_question_response()

    return redirect(
        url_for("exam")
    )


# ============================================================
# PAUSE EXAM
# ============================================================

@app.route(
    "/pause-exam",
    methods=["POST"]
)
def pause_exam():

    if "candidate_id" not in session:

        return redirect(
            url_for("login")
        )

    bad = active_or_redirect()

    if bad:

        return bad

    i = session.get(
        "current_question",
        0
    )

    answers = session.get(
        "answers",
        {}
    )

    selected = request.form.get(
        "answer"
    )

    if selected:

        answers[str(i)] = selected

    session["answers"] = answers

    connection = get_db_connection()

    connection.execute(
        """
        UPDATE exam_sessions
        SET status = 'PAUSED'
        WHERE id = ?
        AND candidate_id = ?
        AND status = 'STARTED'
        """,
        (
            session["exam_session_id"],
            session["candidate_id"]
        )
    )

    connection.commit()

    connection.close()

    return redirect(
        url_for("exam")
    )


# ============================================================
# RESUME EXAM
# ============================================================

@app.route(
    "/resume-exam",
    methods=["POST"]
)
def resume_exam():

    if "candidate_id" not in session:

        return redirect(
            url_for("login")
        )

    current = get_current_exam_session()

    if not current:

        return redirect(
            url_for("exam-details")
        )

    if current["status"] == "SUBMITTED":

        return redirect(
            url_for("dashboard")
        )

    connection = get_db_connection()

    connection.execute(
        """
        UPDATE exam_sessions
        SET status = 'STARTED'
        WHERE id = ?
        AND candidate_id = ?
        AND status = 'PAUSED'
        """,
        (
            current["id"],
            session["candidate_id"]
        )
    )

    connection.commit()

    connection.close()

    return redirect(
        url_for("exam")
    )


# ============================================================
# SUBMIT EXAM
# ============================================================

@app.route(
    "/submit-exam",
    methods=["POST"]
)
def submit_exam():

    if "candidate_id" not in session:

        return redirect(
            url_for("login")
        )

    exam_session = get_current_exam_session()

    if not exam_session:

        return redirect(
            url_for("dashboard")
        )

    if exam_session["status"] not in (
        "STARTED",
        "PAUSED"
    ):

        return redirect(
            url_for("dashboard")
        )

    i = session.get(
        "current_question",
        0
    )

    answers = session.get(
        "answers",
        {}
    )

    selected = request.form.get(
        "answer"
    )

    if selected:

        answers[str(i)] = selected

    session["answers"] = answers

    # ========================================================
    # EXAM SCORE
    # ========================================================

    score = sum(

        1

        for number, question
        in enumerate(QUESTIONS)

        if answers.get(str(number))
        == question["answer"]

    )

    session["score"] = score

    session_id = exam_session["id"]

    connection = get_db_connection()

    # ========================================================
    # FINALIZE FACE ABSENCE
    # ========================================================

    state = face_monitor_state.get(
        session_id
    )

    if (
        state
        and state.get("absent_since") is not None
    ):

        now = datetime.now()

        duration = int(
            (
                now
                - state["absent_since"]
            ).total_seconds()
        )

        insert_browser_event(
            connection,
            session_id,
            "FACE_ABSENT_INTERVAL",
            f"Face absent interval: {duration} seconds."
        )

        if duration >= FACE_ABSENT_THRESHOLD_SECONDS:

            message = (
                f"Face absent for more than "
                f"{FACE_ABSENT_THRESHOLD_SECONDS} seconds "
                f"({duration} seconds)."
            )

            if not suspicious_event_exists(
                connection,
                session_id,
                "Face absent for more than"
            ):

                insert_browser_event(
                    connection,
                    session_id,
                    "SUSPICIOUS_EVENT",
                    message
                )

                create_alert_db(
                    connection,
                    session_id,
                    "FACE_ABSENT",
                    "HIGH",
                    f"Candidate face was absent for "
                    f"{duration:.2f} seconds."
                )

                save_text_evidence(
                    connection,
                    session_id,
                    "FACE_ABSENT",
                    message
                )

    # ========================================================
    # FINAL SUSPICION CHECK
    # ========================================================

    evaluate_browser_suspicion(
        connection,
        session_id
    )

    connection.commit()

    connection.close()

    # ========================================================
    # FINAL INTEGRITY SCORE
    # ========================================================

    integrity_score, risk_level = (
        calculate_session_integrity(
            session_id
        )
    )

    # ========================================================
    # SAVE EVERYTHING PERMANENTLY
    # ========================================================

    end_time = datetime.now()

    connection = get_db_connection()

    connection.execute(
        """
        UPDATE exam_sessions
        SET
            status = 'SUBMITTED',
            end_time = ?,
            exam_score = ?,
            integrity_score = ?,
            risk_level = ?
        WHERE id = ?
        AND candidate_id = ?
        """,
        (
            end_time,
            score,
            integrity_score,
            risk_level,
            session_id,
            session["candidate_id"]
        )
    )

    connection.commit()

    connection.close()

    # ========================================================
    # STOP FACE MONITORING
    # ========================================================

    face_monitor_state.pop(
        session_id,
        None
    )

    # ========================================================
    # KEEP RESULT SESSION
    # ========================================================

    session["exam_session_id"] = session_id

    session["score"] = score

    print(
        f"EXAM SUBMITTED | "
        f"Session={session_id} | "
        f"Score={score}/{len(QUESTIONS)} | "
        f"Integrity={integrity_score}/100 | "
        f"Risk={risk_level}"
    )

    return redirect(
        url_for("dashboard")
    )


# ============================================================
# BROWSER EVENT LOGGING
# ============================================================

@app.route(
    "/log-browser-event",
    methods=["POST"]
)
def log_browser_event():

    if "candidate_id" not in session:

        return jsonify({

            "success": False,

            "message":
            "Candidate not logged in."

        }), 401

    data = request.get_json(
        silent=True
    )

    if not data:

        return jsonify({

            "success": False,

            "message":
            "Invalid JSON data."

        }), 400

    event_type = data.get(
        "event_type"
    )

    details = data.get(
        "details",
        ""
    )

    if not event_type:

        return jsonify({

            "success": False,

            "message":
            "Event type is required."

        }), 400

    exam_session = get_current_exam_session()

    if not exam_session:

        return jsonify({

            "success": False,

            "message":
            "No active exam session."

        }), 400

    if exam_session["status"] != "STARTED":

        return jsonify({

            "success": False,

            "message":
            "Exam is not active."

        }), 400

    connection = get_db_connection()

    insert_browser_event(
        connection,
        exam_session["id"],
        event_type,
        details
    )

    evaluate_browser_suspicion(
        connection,
        exam_session["id"]
    )

    connection.commit()

    counts = get_event_counts(
        exam_session["id"]
    )

    connection.close()

    print(
        f"BROWSER EVENT SAVED | "
        f"{event_type} | {details}"
    )

    return jsonify({

        "success": True,

        "message":
        "Browser event saved.",

        "event_type":
        event_type,

        "counts":
        counts

    })


# ============================================================
# FACE MONITOR
# ============================================================

@app.route(
    "/face-monitor",
    methods=["POST"]
)
def face_monitor():

    if "candidate_id" not in session:

        return jsonify({

            "success": False,

            "message":
            "Candidate not logged in."

        }), 401

    exam_session = get_current_exam_session()

    if (
        not exam_session
        or exam_session["status"] != "STARTED"
    ):

        return jsonify({

            "success": False,

            "message":
            "Exam is not active."

        }), 400

    data = request.get_json(
        silent=True
    ) or {}

    image_data = data.get(
        "image",
        ""
    )

    if not image_data:

        return jsonify({

            "success": False,

            "message":
            "Camera frame is required."

        }), 400

    try:

        if "," in image_data:

            image_data = image_data.split(
                ",",
                1
            )[1]

        raw = base64.b64decode(
            image_data
        )

        frame = cv2.imdecode(
            np.frombuffer(
                raw,
                dtype=np.uint8
            ),
            cv2.IMREAD_COLOR
        )

        if frame is None:

            raise ValueError(
                "Invalid camera frame"
            )

        gray = cv2.cvtColor(
            frame,
            cv2.COLOR_BGR2GRAY
        )

        gray = cv2.equalizeHist(
            gray
        )

        cascade_path = os.path.join(
            cv2.data.haarcascades,
            "haarcascade_frontalface_default.xml"
        )

        detector = cv2.CascadeClassifier(
            cascade_path
        )

        faces = detector.detectMultiScale(

            gray,

            scaleFactor=1.1,

            minNeighbors=5,

            minSize=(60, 60)

        )

        face_count = len(faces)

        now = datetime.now()

        state = face_monitor_state.setdefault(

            exam_session["id"],

            {
                "absent_since": None,

                "alerted": False
            }

        )

        connection = get_db_connection()

        suspicious = False

        absent_seconds = 0

        # ====================================================
        # FACE ABSENT
        # ====================================================

        if face_count == 0:

            if state["absent_since"] is None:

                state["absent_since"] = now

                state["alerted"] = False

                insert_browser_event(
                    connection,
                    exam_session["id"],
                    "FACE_ABSENT_START",
                    "No face detected by OpenCV Haar Cascade."
                )

                print(
                    "FACE MONITOR | "
                    "Face absent started"
                )

            absent_seconds = int(

                (
                    now
                    - state["absent_since"]
                ).total_seconds()

            )

            if (
                absent_seconds
                >= FACE_ABSENT_THRESHOLD_SECONDS
                and not state["alerted"]
            ):

                message = (
                    f"Face absent for more than "
                    f"{FACE_ABSENT_THRESHOLD_SECONDS} seconds "
                    f"({absent_seconds} seconds)."
                )

                insert_browser_event(
                    connection,
                    exam_session["id"],
                    "SUSPICIOUS_EVENT",
                    message
                )

                create_alert_db(
                    connection,
                    exam_session["id"],
                    "FACE_ABSENT",
                    "HIGH",
                    f"Candidate face was absent for "
                    f"{absent_seconds:.2f} seconds."
                )

                save_frame_evidence(
                    connection,
                    exam_session["id"],
                    frame,
                    "FACE_ABSENT",
                    f"Face absent for "
                    f"{absent_seconds} seconds."
                )

                save_text_evidence(
                    connection,
                    exam_session["id"],
                    "FACE_ABSENT",
                    message
                )

                state["alerted"] = True

                suspicious = True

                print(
                    f"SUSPICIOUS EVENT | "
                    f"FACE_ABSENT | "
                    f"{absent_seconds} seconds"
                )

        # ====================================================
        # FACE PRESENT
        # ====================================================

        else:

            if state["absent_since"] is not None:

                duration = int(

                    (
                        now
                        - state["absent_since"]
                    ).total_seconds()

                )

                insert_browser_event(
                    connection,
                    exam_session["id"],
                    "FACE_ABSENT_INTERVAL",
                    f"Face absent interval: "
                    f"{duration} seconds."
                )

                if (
                    duration
                    >= FACE_ABSENT_THRESHOLD_SECONDS
                    and not state["alerted"]
                ):

                    message = (
                        f"Face absent for more than "
                        f"{FACE_ABSENT_THRESHOLD_SECONDS} seconds "
                        f"({duration} seconds)."
                    )

                    insert_browser_event(
                        connection,
                        exam_session["id"],
                        "SUSPICIOUS_EVENT",
                        message
                    )

                    create_alert_db(
                        connection,
                        exam_session["id"],
                        "FACE_ABSENT",
                        "HIGH",
                        f"Candidate face was absent for "
                        f"{duration:.2f} seconds."
                    )

                    save_frame_evidence(
                        connection,
                        exam_session["id"],
                        frame,
                        "FACE_ABSENT",
                        f"Face absence detected for "
                        f"{duration} seconds."
                    )

                    save_text_evidence(
                        connection,
                        exam_session["id"],
                        "FACE_ABSENT",
                        message
                    )

                    suspicious = True

            state["absent_since"] = None

            state["alerted"] = False

            absent_seconds = 0

        connection.commit()

        connection.close()

        return jsonify({

            "success": True,

            "face_present":
            face_count > 0,

            "face_count":
            face_count,

            "absent_seconds":
            absent_seconds,

            "suspicious":
            suspicious

        })

    except Exception as error:

        print(
            f"FACE MONITOR ERROR | {error}"
        )

        return jsonify({

            "success": False,

            "message":
            "Face monitoring failed."

        }), 500


# ============================================================
# SAVE PHOTO
# ============================================================

@app.route(
    "/save-photo",
    methods=["POST"]
)
def save_photo():

    if "candidate_id" not in session:

        return redirect(
            url_for("login")
        )

    path = "uploads/candidate_photo.jpg"

    if not os.path.exists(path):

        return (
            "Photo not found. "
            "Please capture the candidate photo first."
        )

    connection = get_db_connection()

    connection.execute(
        """
        UPDATE candidates
        SET photo_path = ?
        WHERE id = ?
        """,
        (
            path,
            session["candidate_id"]
        )
    )

    connection.commit()

    connection.close()

    return (
        "Photo saved successfully "
        "to candidate profile!"
    )


# ============================================================
# PROFILE
# ============================================================

@app.route("/profile")
def profile():

    if "candidate_id" not in session:

        return redirect(
            url_for("login")
        )

    connection = get_db_connection()

    candidate = connection.execute(
        """
        SELECT *
        FROM candidates
        WHERE id = ?
        """,
        (
            session["candidate_id"],
        )
    ).fetchone()

    connection.close()

    if not candidate:

        return "Candidate not found."

    return f"""

    <h1>Candidate Profile</h1>

    <br>

    <p>
        <strong>Name:</strong>
        {candidate["name"]}
    </p>

    <br>

    <p>
        <strong>Email:</strong>
        {candidate["email"]}
    </p>

    <br>

    <p>
        <strong>Photo Path:</strong>
        {candidate["photo_path"]}
    </p>

    <br>

    <a href="/dashboard">
        Back to Dashboard
    </a>

    <br><br>

    <a href="/exam-details">
        Examination Details
    </a>

    <br><br>

    <a href="/logout">
        Logout
    </a>

    """


# ============================================================
# LOGOUT
# ============================================================

@app.route("/logout")
def logout():

    session.clear()

    return redirect(
        url_for("login")
    )


# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":

    app.run(
        debug=True
    )