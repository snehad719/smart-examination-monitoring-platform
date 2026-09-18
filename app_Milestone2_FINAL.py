from flask import Flask, render_template, request, redirect, session, jsonify
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

FACE_ABSENT_THRESHOLD_SECONDS = 120
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
# HELPER - LATEST EXAM SESSION
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
        (session["candidate_id"],)
    ).fetchone()

    connection.close()

    return row


# ============================================================
# HELPER - GET EVENT COUNTS
# ============================================================

def get_event_counts(session_id):

    counts = {
        "TAB_SWITCH": 0,
        "FOCUS_LOST": 0,
        "SUSPICIOUS_EVENT": 0,
        "FACE_ABSENT_START": 0,
        "FACE_ABSENT_INTERVAL": 0,
        "EXAM_INTERACTION": 0
    }

    if not session_id:
        return counts

    connection = get_db_connection()

    rows = connection.execute(
        """
        SELECT event_type, COUNT(*) AS count
        FROM browser_events
        WHERE session_id = ?
        GROUP BY event_type
        """,
        (session_id,)
    ).fetchall()

    connection.close()

    for row in rows:

        event_type = row["event_type"]

        if event_type in counts:
            counts[event_type] = row["count"]

    return counts


# ============================================================
# HELPER - GET RECENT EVENTS
# ============================================================

def get_recent_events(session_id):

    if not session_id:
        return []

    connection = get_db_connection()

    events = connection.execute(
        """
        SELECT
            event_type,
            event_time,
            details
        FROM browser_events
        WHERE session_id = ?
        ORDER BY id DESC
        LIMIT 20
        """,
        (session_id,)
    ).fetchall()

    connection.close()

    return events


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
# HELPER - SUSPICION EVALUATION
# ============================================================

def evaluate_browser_suspicion(
    connection,
    session_id
):

    # TAB SWITCH COUNT

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


    # FOCUS LOSS COUNT

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


    # TAB SWITCH SUSPICION

    if (
        tab_count > TAB_SWITCH_THRESHOLD
        and not suspicious_event_exists(
            connection,
            session_id,
            "More than 3 tab switches"
        )
    ):

        insert_browser_event(
            connection,
            session_id,
            "SUSPICIOUS_EVENT",
            f"More than 3 tab switches detected (count={tab_count})."
        )

        print(
            f"SUSPICIOUS EVENT | TAB_SWITCH | count={tab_count}"
        )


    # FOCUS LOSS SUSPICION

    if (
        focus_count > FOCUS_LOSS_THRESHOLD
        and not suspicious_event_exists(
            connection,
            session_id,
            "Excessive focus loss"
        )
    ):

        insert_browser_event(
            connection,
            session_id,
            "SUSPICIOUS_EVENT",
            f"Excessive focus loss detected (count={focus_count})."
        )

        print(
            f"SUSPICIOUS EVENT | FOCUS_LOST | count={focus_count}"
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

    <br>
    <br>

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

        connection.close()


        if candidate:

            session["candidate_id"] = candidate["id"]

            session["candidate_name"] = candidate["name"]

            session["candidate_email"] = candidate["email"]

            session.pop("current_question", None)

            session.pop("answers", None)

            session.pop("score", None)

            session.pop("exam_session_id", None)

            return redirect("/dashboard")


        return "Invalid email or password!"


    return render_template("login.html")


# ============================================================
# DASHBOARD
# ============================================================

@app.route("/dashboard")
def dashboard():

    if "candidate_id" not in session:
        return redirect("/login")


    connection = get_db_connection()


    # Latest exam

    exam_session = connection.execute(
        """
        SELECT *
        FROM exam_sessions
        WHERE candidate_id = ?
        ORDER BY id DESC
        LIMIT 1
        """,
        (session["candidate_id"],)
    ).fetchone()


    # Number of completed exams

    completed_row = connection.execute(
        """
        SELECT COUNT(*) AS count
        FROM exam_sessions
        WHERE candidate_id = ?
        AND status = 'SUBMITTED'
        """,
        (session["candidate_id"],)
    ).fetchone()


    # Total exam sessions

    assigned_row = connection.execute(
        """
        SELECT COUNT(*) AS count
        FROM exam_sessions
        WHERE candidate_id = ?
        """,
        (session["candidate_id"],)
    ).fetchone()


    connection.close()


    completed_tests = completed_row["count"]

    assigned_tests = max(
        3,
        assigned_row["count"]
    )

    upcoming_tests = max(
        0,
        assigned_tests - completed_tests - 1
    )


    # ========================================================
    # EVENT DATA
    # ========================================================

    event_counts = {
        "TAB_SWITCH": 0,
        "FOCUS_LOST": 0,
        "SUSPICIOUS_EVENT": 0,
        "FACE_ABSENT_START": 0,
        "FACE_ABSENT_INTERVAL": 0,
        "EXAM_INTERACTION": 0
    }


    recent_events = []


    if exam_session:

        event_counts = get_event_counts(
            exam_session["id"]
        )

        recent_events = get_recent_events(
            exam_session["id"]
        )


    total_monitoring_events = (
        event_counts["TAB_SWITCH"]
        + event_counts["FOCUS_LOST"]
        + event_counts["SUSPICIOUS_EVENT"]
        + event_counts["FACE_ABSENT_START"]
    )


    # ========================================================
    # INTEGRITY SCORE
    # ========================================================

    integrity_score = 100


    integrity_score -= (
        event_counts["TAB_SWITCH"] * 2
    )

    integrity_score -= (
        event_counts["FOCUS_LOST"] * 1
    )

    integrity_score -= (
        event_counts["SUSPICIOUS_EVENT"] * 10
    )


    integrity_score = max(
        0,
        integrity_score
    )


    # ========================================================
    # EXAM STATUS
    # ========================================================

    exam_status = (
        exam_session["status"]
        if exam_session
        else "NOT STARTED"
    )


    # ========================================================
    # SCORE
    # ========================================================

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

        exam_status=exam_status,

        score=score,

        event_counts=event_counts,

        total_monitoring_events=total_monitoring_events,

        recent_events=recent_events,

        exam_session=exam_session
    )


# ============================================================
# EXAM PAGE
# ============================================================

@app.route("/exam")
def exam():

    if "candidate_id" not in session:
        return redirect("/login")


    cs = latest()


    status = (
        cs["status"]
        if cs
        else "NOT STARTED"
    )


    # SUBMITTED

    if status == "SUBMITTED":

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

            submitted=True,

            score=session.get(
                "score",
                0
            ),

            QUESTIONS=QUESTIONS
        )


    # CURRENT QUESTION

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


    question = (
        QUESTIONS[i]
        if status == "STARTED"
        else None
    )


    return render_template(
        "exam.html",

        name=session["candidate_name"],

        status=status,

        question=question,

        question_number=(
            i + 1
            if question
            else 0
        ),

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
        return redirect("/login")


    connection = get_db_connection()


    connection.execute(
        """
        INSERT INTO exam_sessions
        (
            candidate_id,
            status,
            start_time
        )
        VALUES (?, ?, ?)
        """,
        (
            session["candidate_id"],
            "STARTED",
            datetime.now()
        )
    )


    connection.commit()


    row = connection.execute(
        """
        SELECT id
        FROM exam_sessions
        WHERE candidate_id = ?
        ORDER BY id DESC
        LIMIT 1
        """,
        (session["candidate_id"],)
    ).fetchone()


    connection.close()


    if row:

        session["exam_session_id"] = row["id"]


    session["current_question"] = 0

    session["answers"] = {}

    session["score"] = 0


    return redirect("/exam")


# ============================================================
# ACTIVE EXAM CHECK
# ============================================================

def active_or_redirect():

    cs = latest()

    ajax = (
        request.headers.get(
            "X-ExamGuard-AJAX"
        ) == "1"
    )


    if not cs:

        if ajax:

            return jsonify({
                "success": False,
                "message": "Exam session not found."
            }), 404

        return redirect("/exam")


    if cs["status"] != "STARTED":

        if ajax:

            return jsonify({
                "success": False,
                "message": "Exam is not active."
            }), 400

        return redirect("/exam")


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
        return redirect("/login")


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


    return redirect("/exam")


# ============================================================
# PREVIOUS QUESTION
# ============================================================

@app.route(
    "/previous-question",
    methods=["POST"]
)
def previous_question():

    if "candidate_id" not in session:
        return redirect("/login")


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


    return redirect("/exam")


# ============================================================
# QUESTION PALETTE
# ============================================================

@app.route(
    "/question/<int:number>",
    methods=["POST"]
)
def go_to_question(number):

    if "candidate_id" not in session:
        return redirect("/login")


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


    if (
        0 <= number - 1 < len(QUESTIONS)
    ):

        session["current_question"] = (
            number - 1
        )


    if request.headers.get(
        "X-ExamGuard-AJAX"
    ) == "1":

        return ajax_question_response()


    return redirect("/exam")


# ============================================================
# PAUSE EXAM
# ============================================================

@app.route(
    "/pause-exam",
    methods=["POST"]
)
def pause_exam():

    if "candidate_id" not in session:
        return redirect("/login")


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
        SET status = ?
        WHERE candidate_id = ?
        AND status = 'STARTED'
        """,
        (
            "PAUSED",
            session["candidate_id"]
        )
    )


    connection.commit()

    connection.close()


    return redirect("/exam")


# ============================================================
# RESUME EXAM
# ============================================================

@app.route(
    "/resume-exam",
    methods=["POST"]
)
def resume_exam():

    if "candidate_id" not in session:
        return redirect("/login")


    connection = get_db_connection()


    connection.execute(
        """
        UPDATE exam_sessions
        SET status = ?
        WHERE candidate_id = ?
        AND status = 'PAUSED'
        """,
        (
            "STARTED",
            session["candidate_id"]
        )
    )


    connection.commit()

    connection.close()


    return redirect("/exam")


# ============================================================
# SUBMIT EXAM
# ============================================================

@app.route(
    "/submit-exam",
    methods=["POST"]
)
def submit_exam():

    if "candidate_id" not in session:
        return redirect("/login")


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


    # Calculate score

    score = sum(
        1
        for number, question in enumerate(QUESTIONS)
        if answers.get(str(number))
        == question["answer"]
    )


    session["score"] = score


    connection = get_db_connection()


    connection.execute(
        """
        UPDATE exam_sessions
        SET
            status = ?,
            end_time = ?
        WHERE candidate_id = ?
        AND status IN ('STARTED', 'PAUSED')
        """,
        (
            "SUBMITTED",
            datetime.now(),
            session["candidate_id"]
        )
    )


    connection.commit()

    connection.close()


    # Stop face monitoring memory

    session_id = session.get(
        "exam_session_id"
    )

    if session_id:

        face_monitor_state.pop(
            session_id,
            None
        )


    return redirect("/dashboard")


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
            "message": "Candidate not logged in."
        }), 401


    data = request.get_json(
        silent=True
    )


    if not data:

        return jsonify({
            "success": False,
            "message": "Invalid JSON data."
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
            "message": "Event type is required."
        }), 400


    connection = get_db_connection()


    exam_session = connection.execute(
        """
        SELECT *
        FROM exam_sessions
        WHERE candidate_id = ?
        ORDER BY id DESC
        LIMIT 1
        """,
        (session["candidate_id"],)
    ).fetchone()


    if not exam_session:

        connection.close()

        return jsonify({
            "success": False,
            "message": "Exam session not found."
        }), 404


    if exam_session["status"] != "STARTED":

        connection.close()

        return jsonify({
            "success": False,
            "message": "Exam is not active."
        }), 400


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


    # Current counts

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

        "message": "Browser event saved.",

        "event_type": event_type,

        "counts": counts
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
            "message": "Candidate not logged in."
        }), 401


    exam_session = latest()


    if (
        not exam_session
        or exam_session["status"] != "STARTED"
    ):

        return jsonify({
            "success": False,
            "message": "Exam is not active."
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
            "message": "Camera frame is required."
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


        # FACE ABSENT

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
                    "FACE MONITOR | Face absent started"
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

                insert_browser_event(
                    connection,
                    exam_session["id"],
                    "SUSPICIOUS_EVENT",
                    f"Face absent for more than 2 minutes ({absent_seconds} seconds)."
                )


                state["alerted"] = True

                suspicious = True


        # FACE PRESENT

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
                    f"Face absent interval: {duration} seconds."
                )


                if (
                    duration
                    >= FACE_ABSENT_THRESHOLD_SECONDS
                    and not state["alerted"]
                ):

                    insert_browser_event(
                        connection,
                        exam_session["id"],
                        "SUSPICIOUS_EVENT",
                        f"Face absent for more than 2 minutes ({duration} seconds)."
                    )


                    suspicious = True


            state["absent_since"] = None

            state["alerted"] = False

            absent_seconds = 0


        connection.commit()

        connection.close()


        return jsonify({

            "success": True,

            "face_present": face_count > 0,

            "face_count": face_count,

            "absent_seconds": absent_seconds,

            "suspicious": suspicious

        })


    except Exception as error:

        print(
            f"FACE MONITOR ERROR | {error}"
        )


        return jsonify({

            "success": False,

            "message": "Face monitoring failed."

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
        return redirect("/login")


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
        return redirect("/login")


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

    <a href="/exam">
        Go to Exam
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

    return redirect("/login")


# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":

    app.run(
        debug=True
    )