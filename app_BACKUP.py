from flask import Flask, render_template, request, redirect, session, jsonify
from database import init_db, get_db_connection
from datetime import datetime
import os

app = Flask(__name__)

app.secret_key = "examguard-secret-key"

init_db()

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


@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":

        name = request.form["name"]
        email = request.form["email"]
        password = request.form["password"]

        connection = get_db_connection()

        try:

            connection.execute(
                """
                INSERT INTO candidates
                (name, email, password)
                VALUES (?, ?, ?)
                """,
                (
                    name,
                    email,
                    password
                )
            )

            connection.commit()

            return "Registration successful!"

        except Exception as error:

            return f"Registration failed: {error}"

        finally:

            connection.close()

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        email = request.form["email"]
        password = request.form["password"]

        connection = get_db_connection()

        candidate = connection.execute(
            """
            SELECT *
            FROM candidates
            WHERE email = ? AND password = ?
            """,
            (
                email,
                password
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

            return redirect("/dashboard")

        return "Invalid email or password!"

    return render_template("login.html")


@app.route("/dashboard")
def dashboard():

    if "candidate_id" not in session:
        return redirect("/login")

    return render_template(
        "dashboard.html",
        name=session["candidate_name"]
    )


@app.route("/exam")
def exam():

    if "candidate_id" not in session:
        return redirect("/login")

    connection = get_db_connection()

    current_session = connection.execute(
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

    status = "NOT STARTED"

    if current_session:
        status = current_session["status"]

    if status == "SUBMITTED":

        return render_template(
            "exam.html",
            name=session["candidate_name"],
            status=status,
            question=None,
            question_number=0,
            total_questions=len(QUESTIONS),
            answers=session.get("answers", {}),
            submitted=True,
            score=session.get("score", 0),
            QUESTIONS=QUESTIONS
        )

    current_question = session.get(
        "current_question",
        0
    )

    if current_question < 0:
        current_question = 0

    if current_question >= len(QUESTIONS):
        current_question = len(QUESTIONS) - 1

    session["current_question"] = current_question

    question = QUESTIONS[current_question]

    return render_template(
        "exam.html",
        name=session["candidate_name"],
        status=status,
        question=question,
        question_number=current_question + 1,
        total_questions=len(QUESTIONS),
        answers=session.get("answers", {}),
        submitted=False,
        score=session.get("score", 0),
        QUESTIONS=QUESTIONS
    )


@app.route("/start-exam", methods=["POST"])
def start_exam():

    if "candidate_id" not in session:
        return redirect("/login")

    connection = get_db_connection()

    connection.execute(
        """
        INSERT INTO exam_sessions
        (candidate_id, status, start_time)
        VALUES (?, ?, ?)
        """,
        (
            session["candidate_id"],
            "STARTED",
            datetime.now()
        )
    )

    connection.commit()

    current_session = connection.execute(
        """
        SELECT id
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

    if current_session:
        session["exam_session_id"] = current_session["id"]

    session["current_question"] = 0
    session["answers"] = {}
    session["score"] = 0

    return redirect("/exam")


def ajax_question_response():
    current_index = session.get("current_question", 0)
    if current_index < 0:
        current_index = 0
    if current_index >= len(QUESTIONS):
        current_index = len(QUESTIONS) - 1
    session["current_question"] = current_index
    question = QUESTIONS[current_index]
    return jsonify({
        "success": True,
        "question_number": current_index + 1,
        "total_questions": len(QUESTIONS),
        "question": question["question"],
        "options": question["options"],
        "answers": session.get("answers", {}),
        "status": "STARTED"
    })


@app.route("/next-question", methods=["POST"])
def next_question():

    if "candidate_id" not in session:
        return redirect("/login")

    connection = get_db_connection()

    current_session = connection.execute(
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

    if not current_session:
        return redirect("/exam")

    if current_session["status"] != "STARTED":
        return redirect("/exam")

    selected_answer = request.form.get("answer")

    current_index = session.get(
        "current_question",
        0
    )

    answers = session.get(
        "answers",
        {}
    )

    if selected_answer:
        answers[str(current_index)] = selected_answer

    session["answers"] = answers

    if current_index < len(QUESTIONS) - 1:
        session["current_question"] = current_index + 1

    if request.headers.get("X-ExamGuard-AJAX") == "1":
        return ajax_question_response()

    return redirect("/exam")


@app.route("/previous-question", methods=["POST"])
def previous_question():

    if "candidate_id" not in session:
        return redirect("/login")

    selected_answer = request.form.get("answer")

    current_index = session.get(
        "current_question",
        0
    )

    answers = session.get(
        "answers",
        {}
    )

    if selected_answer:
        answers[str(current_index)] = selected_answer

    session["answers"] = answers

    if current_index > 0:
        session["current_question"] = current_index - 1

    if request.headers.get("X-ExamGuard-AJAX") == "1":
        return ajax_question_response()

    return redirect("/exam")


@app.route("/question/<int:number>", methods=["POST"])
def go_to_question(number):

    if "candidate_id" not in session:
        return redirect("/login")

    selected_answer = request.form.get("answer")

    current_index = session.get(
        "current_question",
        0
    )

    answers = session.get(
        "answers",
        {}
    )

    if selected_answer:
        answers[str(current_index)] = selected_answer

    session["answers"] = answers

    target_index = number - 1

    if 0 <= target_index < len(QUESTIONS):
        session["current_question"] = target_index

    if request.headers.get("X-ExamGuard-AJAX") == "1":
        return ajax_question_response()

    return redirect("/exam")


@app.route("/pause-exam", methods=["POST"])
def pause_exam():

    if "candidate_id" not in session:
        return redirect("/login")

    selected_answer = request.form.get("answer")

    current_index = session.get(
        "current_question",
        0
    )

    answers = session.get(
        "answers",
        {}
    )

    if selected_answer:
        answers[str(current_index)] = selected_answer

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


@app.route("/resume-exam", methods=["POST"])
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


@app.route("/submit-exam", methods=["POST"])
def submit_exam():

    if "candidate_id" not in session:
        return redirect("/login")

    selected_answer = request.form.get("answer")

    current_index = session.get(
        "current_question",
        0
    )

    answers = session.get(
        "answers",
        {}
    )

    if selected_answer:
        answers[str(current_index)] = selected_answer

    session["answers"] = answers

    score = 0

    for index, question in enumerate(QUESTIONS):

        selected = answers.get(
            str(index)
        )

        if selected == question["answer"]:
            score += 1

    session["score"] = score

    connection = get_db_connection()

    connection.execute(
        """
        UPDATE exam_sessions
        SET status = ?,
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

    return redirect("/exam")


@app.route("/log-browser-event", methods=["POST"])
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

    current_session = connection.execute(
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

    if not current_session:

        connection.close()

        return jsonify({
            "success": False,
            "message": "Exam session not found."
        }), 404

    if current_session["status"] != "STARTED":

        connection.close()

        return jsonify({
            "success": False,
            "message": "Exam is not active."
        }), 400

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
            current_session["id"],
            event_type,
            datetime.now(),
            details
        )
    )

    connection.commit()
    connection.close()

    print(
        "BROWSER EVENT SAVED | "
        f"{event_type} | "
        f"{details}"
    )

    return jsonify({
        "success": True,
        "message": "Browser event saved."
    })


@app.route("/save-photo", methods=["POST"])
def save_photo():

    if "candidate_id" not in session:
        return redirect("/login")

    photo_path = "uploads/candidate_photo.jpg"

    if not os.path.exists(photo_path):

        return """
        Photo not found.
        Please capture the candidate photo first.
        """

    connection = get_db_connection()

    connection.execute(
        """
        UPDATE candidates
        SET photo_path = ?
        WHERE id = ?
        """,
        (
            photo_path,
            session["candidate_id"]
        )
    )

    connection.commit()
    connection.close()

    return "Photo saved successfully to candidate profile!"


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

    <br><br>

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


@app.route("/logout")
def logout():

    session.clear()

    return redirect("/login")


if __name__ == "__main__":
    app.run(
        debug=True
    )