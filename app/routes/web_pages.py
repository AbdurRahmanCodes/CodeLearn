"""
Web pages routes migrated from legacy monolith.
Preserves existing template route names and user flow.
"""

import csv
import io
import os
import random
import uuid
from datetime import datetime, timezone

from flask import jsonify, redirect, render_template, request, session, url_for, send_file

from app import mongo
from app.services.exercise_service import ExerciseService

EXPERIMENT_GROUPS = ("A_control", "B_adaptive")

LANGUAGE_LABELS = {
    "python": "Python",
    "javascript": "JavaScript",
}

TOPICS = {
    "variables": {
        "title": "Variables and Assignment",
        "summary": "Store and update values using variables.",
        "video_url": "https://www.youtube.com/embed/kqtD5dpn9C8",
        "syntax_guide": "Use clear variable names and check quote usage in string literals.",
    },
    "arithmetic": {
        "title": "Arithmetic Operations",
        "summary": "Apply operators such as +, -, *, / and precedence rules.",
        "video_url": "https://www.youtube.com/embed/jZ5nY2x7uZw",
        "syntax_guide": "Check parentheses and operator order when results are unexpected.",
    },
    "strings": {
        "title": "String Operations",
        "summary": "Use built-in methods and length operations on text.",
        "video_url": "https://www.youtube.com/embed/R8rmfD9Y5-c",
        "syntax_guide": "Remember quotes and method call brackets such as .upper() or .length.",
    },
    "conditions": {
        "title": "Conditional Logic",
        "summary": "Build if/else decisions for branching behavior.",
        "video_url": "https://www.youtube.com/embed/f4KOjWS_KZs",
        "syntax_guide": "Check condition operators and block formatting in if/else statements.",
    },
    "loops": {
        "title": "Loops and Iteration",
        "summary": "Repeat actions with while and for loops.",
        "video_url": "https://www.youtube.com/embed/94UHCEmprCY",
        "syntax_guide": "Ensure loop counters change so the loop terminates.",
    },
    "functions": {
        "title": "Functions",
        "summary": "Encapsulate reusable logic with function definitions.",
        "video_url": "https://www.youtube.com/embed/NSbOtYzIQI0",
        "syntax_guide": "Define parameters clearly and ensure return values are used correctly.",
    },
}

QUIZ_BANK = {
    "variables": [
        {
            "id": "qv1",
            "question": "Which statement correctly stores the text hello in a variable x in Python?",
            "options": ["x = hello", "x = \"hello\"", "string x = hello", "x := text(hello)"],
            "answer": 1,
        },
        {
            "id": "qv2",
            "question": "What is the type of value 20 in Python?",
            "options": ["str", "float", "int", "bool"],
            "answer": 2,
        },
        {
            "id": "qv3",
            "question": "In JavaScript, which keyword declares a block-scoped variable?",
            "options": ["int", "var", "let", "define"],
            "answer": 2,
        },
    ],
    "conditions": [
        {
            "id": "qc1",
            "question": "Which operator checks equality in JavaScript?",
            "options": ["=", "==", "===", "!="],
            "answer": 2,
        },
        {
            "id": "qc2",
            "question": "What does this print in Python if x=4? if x>5: print('A') else: print('B')",
            "options": ["A", "B", "A then B", "Nothing"],
            "answer": 1,
        },
        {
            "id": "qc3",
            "question": "Which branch runs when a condition is false?",
            "options": ["if", "else", "def", "return"],
            "answer": 1,
        },
    ],
    "loops": [
        {
            "id": "ql1",
            "question": "What is the main risk with a while loop?",
            "options": ["Memory leak", "Infinite loop", "Syntax cannot compile", "No output"],
            "answer": 1,
        },
        {
            "id": "ql2",
            "question": "In JavaScript, which loop iterates over each element of an array?",
            "options": ["while", "for", "for...of", "switch"],
            "answer": 2,
        },
        {
            "id": "ql3",
            "question": "In Python, range(1, 4) produces:",
            "options": ["1,2,3", "1,2,3,4", "0,1,2,3", "Only 4"],
            "answer": 0,
        },
    ],
    "functions": [
        {
            "id": "qf1",
            "question": "What does a function return if there is no return statement in Python?",
            "options": ["0", "False", "None", "Empty string"],
            "answer": 2,
        },
        {
            "id": "qf2",
            "question": "Which line defines a JavaScript function add(a, b)?",
            "options": ["function add(a, b) { }", "def add(a,b):", "func add(a,b)", "add = function:"],
            "answer": 0,
        },
        {
            "id": "qf3",
            "question": "Why are functions useful in programming?",
            "options": ["They reduce reuse", "They avoid logic", "They improve reuse and readability", "They only print text"],
            "answer": 2,
        },
    ],
}

EXERCISES = [
    {
        "id": "ex01",
        "topic": "variables",
        "language": "python",
        "title": "Variables & Assignment",
        "description": "Create variable name (string) and age (20), then print each on a new line.",
        "example": "Output:\nAlice\n20",
        "starter_code": "# Write your code below\n",
        "explanation": "Variables store values you can reuse. Use quotes for strings and print() to output values.",
        "test_cases": [
            {"input": "", "check_type": "variable", "var": "name", "expected_type": "str"},
            {"input": "", "check_type": "variable", "var": "age", "expected_type": "int"},
        ],
    },
    {
        "id": "ex02",
        "topic": "arithmetic",
        "language": "javascript",
        "title": "Arithmetic Operations",
        "description": "Set width=8, height=5, compute area and print it.",
        "example": "Output:\n40",
        "starter_code": "// Write your code below\n",
        "explanation": "Use arithmetic operators like * for multiplication and console.log for output.",
        "test_cases": [{"input": "", "check_type": "output", "expected": "40"}],
    },
    {
        "id": "ex03",
        "topic": "strings",
        "language": "python",
        "title": "String Operations",
        "description": "Store 'hello world', print uppercase and length.",
        "example": "Output:\nHELLO WORLD\n11",
        "starter_code": "# Write your code below\n",
        "explanation": "Use .upper() and len() for basic string transformations.",
        "test_cases": [
            {"input": "", "check_type": "output_contains", "expected": "HELLO WORLD"},
            {"input": "", "check_type": "output_contains", "expected": "11"},
        ],
    },
    {
        "id": "ex04",
        "topic": "conditions",
        "language": "javascript",
        "title": "If / Else Conditions",
        "description": "Set score=72 and print Pass if >= 50 else Fail.",
        "example": "Output:\nPass",
        "starter_code": "// Write your code below\n",
        "explanation": "Use if/else with comparison operators to branch logic.",
        "test_cases": [{"input": "", "check_type": "output", "expected": "Pass"}],
    },
    {
        "id": "ex05",
        "topic": "loops",
        "language": "python",
        "title": "While Loop",
        "description": "Print numbers 1 to 5 using a while loop.",
        "example": "Output:\n1\n2\n3\n4\n5",
        "starter_code": "# Write your code below\n",
        "explanation": "Update loop counters to avoid infinite loops.",
        "test_cases": [{"input": "", "check_type": "output", "expected": "1\n2\n3\n4\n5"}],
    },
    {
        "id": "ex06",
        "topic": "loops",
        "language": "javascript",
        "title": "For Loop & Lists",
        "description": "Print each fruit from an array using for...of.",
        "example": "Output:\napple\nbanana\ncherry",
        "starter_code": "// Write your code below\n",
        "explanation": "Use for...of to iterate array values.",
        "test_cases": [{"input": "", "check_type": "output", "expected": "apple\nbanana\ncherry"}],
    },
    {
        "id": "ex07",
        "topic": "functions",
        "language": "python",
        "title": "Functions (Capstone)",
        "description": "Define celsius_to_fahrenheit(c), call with 100, print result.",
        "example": "Output:\n212.0",
        "starter_code": "# Write your code below\n",
        "explanation": "Functions encapsulate reusable logic and return computed values.",
        "test_cases": [{"input": "", "check_type": "output", "expected": "212.0"}],
    },
]

EXERCISE_MAP = {ex["id"]: ex for ex in EXERCISES}
TOPIC_EXERCISES = {}
for ex in EXERCISES:
    TOPIC_EXERCISES.setdefault(ex["topic"], []).append(ex)


def _attempts_col():
    return mongo.db.attempts if mongo.db is not None else None


def _quiz_col():
    return mongo.db.quiz_attempts if mongo.db is not None else None


def _recommend_col():
    return mongo.db.recommendations_log if mongo.db is not None else None


def _init_participant_session(mode: str):
    if "session_id" not in session or session.get("group_type") != mode:
        session["session_id"] = str(uuid.uuid4())
        session["group_type"] = mode
        session["experiment_group"] = random.choice(EXPERIMENT_GROUPS)
    if "experiment_group" not in session:
        session["experiment_group"] = random.choice(EXPERIMENT_GROUPS)


def _get_session_progress(session_id: str):
    col = _attempts_col()
    if not session_id or col is None:
        return {"attempted": 0, "passed": 0, "total_attempts": 0}
    rows = list(col.find({"session_id": session_id}, {"exercise_id": 1, "result": 1, "_id": 0}))
    attempted = len({r.get("exercise_id") for r in rows})
    passed = len({r.get("exercise_id") for r in rows if r.get("result") == "pass"})
    return {"attempted": attempted, "passed": passed, "total_attempts": len(rows)}


def _next_attempt_number(session_id: str, exercise_id: str):
    col = _attempts_col()
    if col is None:
        return 1
    return col.count_documents({"session_id": session_id, "exercise_id": exercise_id}) + 1


def _build_recommendations(exercise: dict, attempt_number: int, eval_result: dict):
    recs = []
    topic = exercise["topic"]
    if eval_result["result"] == "fail" and attempt_number >= 3:
        recs.append({
            "type": "tutorial",
            "title": f"Review tutorial: {TOPICS.get(topic, {}).get('title', topic)}",
            "reason": "Three or more failed attempts on the same exercise.",
            "resource_url": url_for("topic_page", topic_id=topic),
        })
    if eval_result.get("error_type") == "syntax":
        recs.append({
            "type": "syntax_guide",
            "title": "Syntax support recommended",
            "reason": "Syntax issues detected.",
            "resource_url": url_for("topic_page", topic_id=topic),
        })
    if eval_result.get("error_type") == "logic":
        recs.append({
            "type": "extra_practice",
            "title": "Try targeted practice",
            "reason": "Logic mismatch against expected output.",
            "resource_url": url_for("topic_quiz", topic_id=topic),
        })
    return recs[:3]


def _log_recommendations(session_id: str, group_type: str, experiment_group: str, exercise_id: str, topic: str, recommendations: list):
    col = _recommend_col()
    if col is None or not recommendations:
        return
    now = datetime.now(timezone.utc)
    docs = []
    for rec in recommendations:
        docs.append({
            "session_id": session_id,
            "group_type": group_type,
            "experiment_group": experiment_group,
            "exercise_id": exercise_id,
            "topic": topic,
            "recommendation_type": rec.get("type"),
            "title": rec.get("title"),
            "reason": rec.get("reason"),
            "resource_url": rec.get("resource_url"),
            "timestamp": now,
        })
    col.insert_many(docs)


def _log_attempt(session_id: str, group_type: str, exercise: dict, attempt_number: int, eval_result: dict, execution_time_ms: float, experiment_group: str, recommendations: list):
    col = _attempts_col()
    if col is None:
        return
    col.insert_one({
        "session_id": session_id,
        "group_type": group_type,
        "experiment_group": experiment_group,
        "exercise_id": exercise["id"],
        "programming_language": exercise["language"],
        "topic": exercise["topic"],
        "attempt_number": attempt_number,
        "result": eval_result["result"],
        "error_type": eval_result["error_type"],
        "recommendations_triggered": [r.get("type") for r in recommendations],
        "recommendation_count": len(recommendations),
        "recommendation_shown": bool(recommendations),
        "topic_quiz_score": None,
        "timestamp": datetime.now(timezone.utc),
        "execution_time_ms": execution_time_ms,
        "platform_version": "1.2",
    })


def index():
    return render_template("index.html", topics=TOPICS)


def static_mode():
    _init_participant_session("static")
    exercise_index = int(request.args.get("ex", 0))
    exercise_index = max(0, min(exercise_index, len(EXERCISES) - 1))
    exercise = EXERCISES[exercise_index]
    progress = _get_session_progress(session.get("session_id"))
    return render_template(
        "static_mode.html",
        exercise=exercise,
        exercises=EXERCISES,
        exercise_index=exercise_index,
        total=len(EXERCISES),
        feedback=None,
        progress=progress,
        experiment_group=session.get("experiment_group"),
        language_label=LANGUAGE_LABELS.get(exercise.get("language"), exercise.get("language", "Python")),
    )


def interactive_mode():
    _init_participant_session("interactive")
    exercise_index = int(request.args.get("ex", 0))
    exercise_index = max(0, min(exercise_index, len(EXERCISES) - 1))
    exercise = EXERCISES[exercise_index]
    progress = _get_session_progress(session.get("session_id"))
    return render_template(
        "interactive_mode.html",
        exercise=exercise,
        exercises=EXERCISES,
        exercise_index=exercise_index,
        total=len(EXERCISES),
        feedback=None,
        progress=progress,
        experiment_group=session.get("experiment_group"),
        language_label=LANGUAGE_LABELS.get(exercise.get("language"), exercise.get("language", "Python")),
    )


def submit():
    code = request.form.get("code", "")
    exercise_id = request.form.get("exercise_id")
    exercise_index = int(request.form.get("exercise_index", 0))
    group_type = session.get("group_type", "static")
    experiment_group = session.get("experiment_group", "A_control")
    session_id = session.get("session_id", str(uuid.uuid4()))
    session["session_id"] = session_id

    exercise = EXERCISE_MAP.get(exercise_id)
    if not exercise:
        return "Invalid exercise", 400

    attempt_number = _next_attempt_number(session_id, exercise_id)
    exec_result = ExerciseService.run_code(code, language=exercise.get("language", "python"))
    eval_result = ExerciseService.evaluate_test_cases(exercise, exec_result)
    exec_time_ms = exec_result.get("execution_time_ms", 0)

    recommendations = []
    if experiment_group == "B_adaptive":
        recommendations = _build_recommendations(exercise, attempt_number, eval_result)
        _log_recommendations(
            session_id=session_id,
            group_type=group_type,
            experiment_group=experiment_group,
            exercise_id=exercise_id,
            topic=exercise.get("topic", ""),
            recommendations=recommendations,
        )

    _log_attempt(
        session_id=session_id,
        group_type=group_type,
        exercise=exercise,
        attempt_number=attempt_number,
        eval_result=eval_result,
        execution_time_ms=exec_time_ms,
        experiment_group=experiment_group,
        recommendations=recommendations,
    )

    if group_type == "static":
        feedback = {
            "mode": "static",
            "passed": eval_result["passed"],
            "message": "Correct!" if eval_result["passed"] else "Incorrect.",
            "recommendations": recommendations,
        }
        return render_template(
            "static_mode.html",
            exercise=exercise,
            exercises=EXERCISES,
            exercise_index=exercise_index,
            total=len(EXERCISES),
            feedback=feedback,
            submitted_code=code,
            progress=_get_session_progress(session_id),
            experiment_group=experiment_group,
            language_label=LANGUAGE_LABELS.get(exercise.get("language"), exercise.get("language", "Python")),
        )

    feedback = {
        "mode": "interactive",
        "passed": eval_result["passed"],
        "message": eval_result["feedback"],
        "details": eval_result["details"],
        "error_type": eval_result["error_type"],
        "recommendations": recommendations,
    }
    return render_template(
        "interactive_mode.html",
        exercise=exercise,
        exercises=EXERCISES,
        exercise_index=exercise_index,
        total=len(EXERCISES),
        feedback=feedback,
        submitted_code=code,
        progress=_get_session_progress(session_id),
        experiment_group=experiment_group,
        language_label=LANGUAGE_LABELS.get(exercise.get("language"), exercise.get("language", "Python")),
    )


def db_status():
    col = _attempts_col()
    if col is None:
        return jsonify({"status": "disconnected", "message": "MongoDB is not connected."})
    return jsonify({"status": "connected", "total_attempts": col.count_documents({})})


def admin_login():
    error = None
    if request.method == "POST":
        user = request.form.get("username", "").strip()
        pwd = request.form.get("password", "").strip()
        if user == os.getenv("ADMIN_USERNAME", "admin") and pwd == os.getenv("ADMIN_PASSWORD", "research2026"):
            session["admin_logged_in"] = True
            return redirect(url_for("admin_dashboard"))
        error = "Invalid username or password."
    return render_template("admin_login.html", error=error)


def admin_logout():
    session.pop("admin_logged_in", None)
    return redirect(url_for("admin_login"))


def admin_dashboard():
    if not session.get("admin_logged_in"):
        return redirect(url_for("admin_login"))
    return render_template("admin_dashboard.html")


def session_complete():
    sid = session.get("session_id")
    group_type = session.get("group_type", "unknown")
    experiment_group = session.get("experiment_group", "A_control")
    total_ex = len(EXERCISES)

    col = _attempts_col()
    qcol = _quiz_col()
    if not sid or col is None:
        stats = {
            "exercises_attempted": 0,
            "exercises_passed": 0,
            "total_attempts": 0,
            "duration_min": 0,
            "completion_rate": 0,
            "group_type": group_type,
            "experiment_group": experiment_group,
            "recommendation_count": 0,
            "avg_quiz_score": None,
        }
    else:
        rows = list(col.find({"session_id": sid}))
        attempted = {r.get("exercise_id") for r in rows}
        passed = {r.get("exercise_id") for r in rows if r.get("result") == "pass"}
        timestamps = [r.get("timestamp") for r in rows if r.get("timestamp")]
        duration_min = 0
        if len(timestamps) > 1:
            duration_min = round((max(timestamps) - min(timestamps)).total_seconds() / 60, 1)
        avg_quiz = None
        if qcol is not None:
            qrows = list(qcol.find({"session_id": sid}, {"score_pct": 1, "_id": 0}))
            if qrows:
                avg_quiz = round(sum(row.get("score_pct", 0) for row in qrows) / len(qrows), 1)

        stats = {
            "exercises_attempted": len(attempted),
            "exercises_passed": len(passed),
            "total_attempts": len(rows),
            "duration_min": duration_min,
            "completion_rate": round(len(passed) / total_ex * 100) if total_ex else 0,
            "group_type": group_type,
            "experiment_group": experiment_group,
            "recommendation_count": sum(int(r.get("recommendation_count", 0)) for r in rows),
            "avg_quiz_score": avg_quiz,
        }

    return render_template("completion.html", stats=stats)


def research_info():
    return render_template("research_info.html")


def methodology_page():
    return render_template("methodology.html")


def topic_page(topic_id):
    topic = TOPICS.get(topic_id)
    if not topic:
        return "Topic not found", 404
    exercises = TOPIC_EXERCISES.get(topic_id, [])
    return render_template(
        "topic.html",
        topic_id=topic_id,
        topic=topic,
        exercises=exercises,
        language_labels=LANGUAGE_LABELS,
    )


def topic_quiz(topic_id):
    topic = TOPICS.get(topic_id)
    questions = QUIZ_BANK.get(topic_id, [])
    if not topic or not questions:
        return "Quiz not available for this topic", 404

    if "session_id" not in session:
        _init_participant_session("interactive")

    if request.method == "POST":
        score = 0
        answers = []
        for q in questions:
            raw = request.form.get(q["id"], "")
            selected = int(raw) if raw.isdigit() else -1
            correct = selected == q["answer"]
            if correct:
                score += 1
            answers.append({
                "question_id": q["id"],
                "selected": selected,
                "correct_option": q["answer"],
                "is_correct": correct,
            })

        score_pct = round((score / len(questions)) * 100, 1)
        col = _quiz_col()
        if col is not None:
            col.insert_one({
                "session_id": session.get("session_id"),
                "group_type": session.get("group_type", "interactive"),
                "experiment_group": session.get("experiment_group", "A_control"),
                "topic": topic_id,
                "score": score,
                "total_questions": len(questions),
                "score_pct": score_pct,
                "answers": answers,
                "timestamp": datetime.now(timezone.utc),
            })

        return render_template(
            "quiz.html",
            topic_id=topic_id,
            topic=topic,
            questions=questions,
            submitted=True,
            score=score,
            total=len(questions),
            score_pct=score_pct,
        )

    return render_template(
        "quiz.html",
        topic_id=topic_id,
        topic=topic,
        questions=questions,
        submitted=False,
    )


def export_research_dataset():
    if not session.get("admin_logged_in"):
        return redirect(url_for("admin_login"))

    col = _attempts_col()
    rows = list(col.find()) if col is not None else []
    if not rows:
        return "No data available", 404

    for row in rows:
        row.pop("_id", None)

    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=list(rows[0].keys()))
    writer.writeheader()
    writer.writerows(rows)

    bio = io.BytesIO(output.getvalue().encode("utf-8"))
    return send_file(bio, mimetype="text/csv", as_attachment=True, download_name="com748_research_dataset.csv")


def export_session_summary():
    if not session.get("admin_logged_in"):
        return redirect(url_for("admin_login"))

    col = _attempts_col()
    if col is None:
        return "No data available", 404

    rows = list(col.find())
    per_session = {}
    for row in rows:
        sid = row.get("session_id")
        if sid not in per_session:
            per_session[sid] = {
                "session_id": sid,
                "group_type": row.get("group_type"),
                "experiment_group": row.get("experiment_group"),
                "attempts": 0,
                "passes": 0,
            }
        per_session[sid]["attempts"] += 1
        if row.get("result") == "pass":
            per_session[sid]["passes"] += 1

    export_rows = list(per_session.values())
    if not export_rows:
        return "No session summaries available", 404

    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=list(export_rows[0].keys()))
    writer.writeheader()
    writer.writerows(export_rows)

    bio = io.BytesIO(output.getvalue().encode("utf-8"))
    return send_file(bio, mimetype="text/csv", as_attachment=True, download_name="com748_session_summary.csv")
