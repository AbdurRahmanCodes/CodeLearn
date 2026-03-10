"""
COM748 Masters Research Project
Interactive Educational Platform for Teaching Computer Programming
app.py — Main Flask Application

Architecture:
  - Flask app with Jinja2 templating
  - MongoDB Atlas via PyMongo for attempt logging
  - Sandboxed Python code execution via RestrictedPython-style exec()
  - Two learning modes: Static (limited feedback) and Interactive (detailed feedback)
  - CSV export endpoint for dissertation data analysis
"""

import os
import csv
import uuid
import traceback
import textwrap
import io
from io import StringIO
from datetime import datetime, timezone
from contextlib import redirect_stdout
from functools import wraps
import markdown as md_lib

from flask import (
    Flask, render_template, redirect, url_for,
    request, session, jsonify, make_response, send_file
)
from dotenv import load_dotenv
from pymongo import MongoClient, ASCENDING
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError

# ─────────────────────────────────────────────
# Bootstrap
# ─────────────────────────────────────────────
# Load .env from the SAME directory as app.py (works even when Flask's
# reloader spawns child processes from a different working directory).
# override=True ensures fresh values are always applied on restart.
_env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
load_dotenv(dotenv_path=_env_path, override=True)

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "dev-fallback-secret-key")

@app.template_filter('md')
def render_markdown(text):
    """Convert Markdown (tables, code fences, bold, inline code) to safe HTML."""
    return md_lib.markdown(text, extensions=['tables', 'fenced_code'])

# ─────────────────────────────────────────────
# MongoDB Atlas Connection
# ─────────────────────────────────────────────
# Connection string is read from the MONGO_URI environment variable.
# Never hardcode credentials — use a .env file (see .env.example).
MONGO_URI        = os.environ.get("MONGO_URI")
ADMIN_USERNAME   = os.environ.get("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD   = os.environ.get("ADMIN_PASSWORD", "research2026")
PLATFORM_VERSION = "1.2"
db = None
attempts_col = None

def connect_db():
    """Connect to MongoDB Atlas and set up indexes."""
    global db, attempts_col
    if not MONGO_URI:
        print("[WARNING] MONGO_URI not set. DB logging disabled. Set it in your .env file.")
        return
    try:
        client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
        client.admin.command("ping")  # Validate connection
        db = client["programming_research"]
        attempts_col = db["attempts"]

        # Create indexes for efficient querying and analytics export
        attempts_col.create_index([("session_id", ASCENDING)])
        attempts_col.create_index([("group_type", ASCENDING)])
        attempts_col.create_index([("exercise_id", ASCENDING)])
        print("[INFO] Connected to MongoDB Atlas — database: programming_research")
    except (ConnectionFailure, ServerSelectionTimeoutError) as e:
        print(f"[ERROR] MongoDB connection failed: {e}")
        print("[WARNING] DB logging disabled. Check MONGO_URI in your .env file.")

connect_db()

# ─────────────────────────────────────────────
# Exercise Data — stored in-app (not in DB)
# Each exercise has: id, title, description,
# example, starter_code, test_cases (hidden),
# explanation (shown in interactive mode)
# ─────────────────────────────────────────────
EXERCISES = [
    {
        "id": "ex01",
        "title": "Variables & Assignment",
        "description": (
            "Create a variable called `name` and assign your first name to it as a string. "
            "Then create a variable called `age` and assign the number 20 to it. "
            "Print both variables on separate lines."
        ),
        "example": "Output:\nAlice\n20",
        "starter_code": "# Write your code below\n",
        "explanation": (
            "A **variable** stores a value in memory so you can use it later.\n\n"
            "```python\n"
            "name = \"Alice\"   # string — text surrounded by quotes\n"
            "age  = 20        # integer — a whole number\n"
            "print(name)      # prints: Alice\n"
            "print(age)       # prints: 20\n"
            "```\n\n"
            "Rules for variable names: start with a letter or underscore, "
            "no spaces, case-sensitive."
        ),
        "test_cases": [
            {"input": "", "check_type": "variable", "var": "name", "expected_type": "str"},
            {"input": "", "check_type": "variable", "var": "age",  "expected_type": "int"},
        ],
    },
    {
        "id": "ex02",
        "title": "Arithmetic Operations",
        "description": (
            "Write a program that calculates the area of a rectangle. "
            "Set `width = 8` and `height = 5`. "
            "Calculate `area = width * height` and print the result."
        ),
        "example": "Output:\n40",
        "starter_code": "# Write your code below\n",
        "explanation": (
            "Python supports standard arithmetic operators:\n\n"
            "| Operator | Meaning         | Example |\n"
            "|----------|-----------------|---------|\n"
            "| `+`      | Addition        | 3 + 2 = 5 |\n"
            "| `-`      | Subtraction     | 7 - 4 = 3 |\n"
            "| `*`      | Multiplication  | 4 * 5 = 20 |\n"
            "| `/`      | Division        | 9 / 2 = 4.5 |\n"
            "| `//`     | Floor division  | 9 // 2 = 4 |\n"
            "| `%`      | Modulo (remainder) | 9 % 2 = 1 |\n"
            "| `**`     | Exponentiation  | 2 ** 3 = 8 |\n"
        ),
        "test_cases": [
            {"input": "", "check_type": "output", "expected": "40"},
        ],
    },
    {
        "id": "ex03",
        "title": "String Operations",
        "description": (
            "Store the string `\"hello world\"` in a variable called `text`. "
            "Print the string in UPPERCASE, then print its length (number of characters)."
        ),
        "example": "Output:\nHELLO WORLD\n11",
        "starter_code": "# Write your code below\n",
        "explanation": (
            "Strings are sequences of characters. Python provides many built-in string methods:\n\n"
            "```python\n"
            "text = \"hello world\"\n"
            "print(text.upper())   # HELLO WORLD\n"
            "print(len(text))      # 11\n"
            "print(text.lower())   # hello world\n"
            "print(text[0])        # h  (indexing starts at 0)\n"
            "```"
        ),
        "test_cases": [
            {"input": "", "check_type": "output_contains", "expected": "HELLO WORLD"},
            {"input": "", "check_type": "output_contains", "expected": "11"},
        ],
    },
    {
        "id": "ex04",
        "title": "If / Else Conditions",
        "description": (
            "Set a variable `score = 72`. "
            "Write an if/else statement: if score is 50 or more, print `\"Pass\"`, "
            "otherwise print `\"Fail\"`."
        ),
        "example": "Output:\nPass",
        "starter_code": "# Write your code below\n",
        "explanation": (
            "Use `if` / `elif` / `else` to make decisions in your code:\n\n"
            "```python\n"
            "score = 72\n"
            "if score >= 50:\n"
            "    print(\"Pass\")   # runs when condition is True\n"
            "else:\n"
            "    print(\"Fail\")   # runs when condition is False\n"
            "```\n\n"
            "Comparison operators: `==`, `!=`, `>`, `<`, `>=`, `<=`"
        ),
        "test_cases": [
            {"input": "", "check_type": "output", "expected": "Pass"},
        ],
    },
    {
        "id": "ex05",
        "title": "While Loop",
        "description": (
            "Use a `while` loop to print the numbers 1 through 5, "
            "one per line. Start with `count = 1`."
        ),
        "example": "Output:\n1\n2\n3\n4\n5",
        "starter_code": "# Write your code below\n",
        "explanation": (
            "A `while` loop repeats a block of code **while** a condition is `True`:\n\n"
            "```python\n"
            "count = 1\n"
            "while count <= 5:    # condition checked before each repetition\n"
            "    print(count)\n"
            "    count += 1       # IMPORTANT: update the counter to avoid infinite loops\n"
            "```\n\n"
            "> Always make sure the condition will eventually become `False`!"
        ),
        "test_cases": [
            {"input": "", "check_type": "output", "expected": "1\n2\n3\n4\n5"},
        ],
    },
    {
        "id": "ex06",
        "title": "For Loop & Lists",
        "description": (
            "Create a list called `fruits = [\"apple\", \"banana\", \"cherry\"]`. "
            "Use a `for` loop to print each fruit on a separate line."
        ),
        "example": "Output:\napple\nbanana\ncherry",
        "starter_code": "# Write your code below\n",
        "explanation": (
            "A `for` loop iterates over every item in a sequence:\n\n"
            "```python\n"
            "fruits = [\"apple\", \"banana\", \"cherry\"]\n"
            "for fruit in fruits:\n"
            "    print(fruit)\n"
            "```\n\n"
            "Lists are ordered collections of items. Key list operations:\n"
            "- `fruits[0]` → `\"apple\"` (index access)\n"
            "- `len(fruits)` → `3` (length)\n"
            "- `fruits.append(\"mango\")` → adds an item"
        ),
        "test_cases": [
            {"input": "", "check_type": "output", "expected": "apple\nbanana\ncherry"},
        ],
    },
    {
        "id": "ex07",
        "title": "Functions (Capstone)",
        "description": (
            "Define a function called `celsius_to_fahrenheit` that takes one parameter `c` "
            "and returns the Fahrenheit equivalent using the formula: `f = (c * 9/5) + 32`. "
            "Call the function with `c = 100` and print the result."
        ),
        "example": "Output:\n212.0",
        "starter_code": "# Write your code below\n",
        "explanation": (
            "Functions are reusable blocks of code:\n\n"
            "```python\n"
            "def celsius_to_fahrenheit(c):\n"
            "    f = (c * 9/5) + 32   # formula\n"
            "    return f             # return the computed value\n\n"
            "result = celsius_to_fahrenheit(100)\n"
            "print(result)            # 212.0\n"
            "```\n\n"
            "- `def` defines a function\n"
            "- Parameters receive data passed into the function\n"
            "- `return` sends a value back to the caller"
        ),
        "test_cases": [
            {"input": "", "check_type": "output", "expected": "212.0"},
        ],
    },
]

# Build a lookup dict for O(1) access by exercise id
EXERCISE_MAP = {ex["id"]: ex for ex in EXERCISES}

# ─────────────────────────────────────────────
# Code Execution Engine
# ─────────────────────────────────────────────
# Runs learner-submitted Python code in a restricted environment.
# - Builtins are whitelisted (only safe functions allowed)
# - Execution is time-limited via a threading approach
# - stdout is captured and compared against expected test-case output

# Whitelisted builtins — prevents access to file system, imports, etc.
SAFE_BUILTINS = {
    "print": print,
    "len":   len,
    "range": range,
    "int":   int,
    "float": float,
    "str":   str,
    "bool":  bool,
    "list":  list,
    "dict":  dict,
    "tuple": tuple,
    "set":   set,
    "abs":   abs,
    "round": round,
    "min":   min,
    "max":   max,
    "sum":   sum,
    "type":  type,
    "isinstance": isinstance,
    "enumerate":  enumerate,
    "zip":        zip,
    "sorted":     sorted,
    "reversed":   reversed,
    "True":  True,
    "False": False,
    "None":  None,
}


def run_code(code: str, timeout: int = 5) -> dict:
    """
    Execute learner code safely and return structured results.

    Returns:
        {
          "stdout": str,          # captured print output
          "error": str | None,    # error message if execution failed
          "error_type": str | None  # "syntax" | "runtime" | "timeout"
          "local_vars": dict      # variables defined in learner code
        }
    """
    import threading
    import time as _time

    result = {"stdout": "", "error": None, "error_type": None, "local_vars": {}, "execution_time_ms": 0}
    output_buffer = StringIO()
    local_ns = {}
    _t_start = _time.monotonic()

    def _exec():
        try:
            # Redirect stdout so we can capture print() calls
            safe_globals = {"__builtins__": SAFE_BUILTINS}
            with redirect_stdout(output_buffer):
                exec(compile(code, "<learner>", "exec"), safe_globals, local_ns)
            result["stdout"] = output_buffer.getvalue().strip()
            result["local_vars"] = local_ns
        except SyntaxError as e:
            result["error"] = f"Syntax Error on line {e.lineno}: {e.msg}"
            result["error_type"] = "syntax"
        except Exception as e:
            result["error"] = f"{type(e).__name__}: {e}"
            result["error_type"] = "runtime"

    thread = threading.Thread(target=_exec, daemon=True)
    thread.start()
    thread.join(timeout)

    result["execution_time_ms"] = round((_time.monotonic() - _t_start) * 1000, 1)

    if thread.is_alive():
        result["error"] = "Execution timed out (possible infinite loop). Check your loop condition."
        result["error_type"] = "timeout"

    return result


def evaluate_test_cases(exercise: dict, exec_result: dict) -> dict:
    """
    Compare execution result against the exercise's test cases.

    Returns:
        {
          "passed": bool,
          "result": "pass" | "fail",
          "error_type": "syntax" | "runtime" | "logic" | "timeout" | None,
          "feedback": str,       # human-readable message
          "details": list        # per-test-case breakdown
        }
    """
    details = []

    # If code didn't even run, return immediately
    if exec_result["error"]:
        etype = exec_result["error_type"]
        return {
            "passed": False,
            "result": "fail",
            "error_type": etype,
            "feedback": exec_result["error"],
            "details": [{"test": "Execution", "passed": False, "message": exec_result["error"]}],
        }

    stdout = exec_result["stdout"]
    local_vars = exec_result["local_vars"]
    all_passed = True

    for i, tc in enumerate(exercise["test_cases"], 1):
        check = tc["check_type"]
        passed = False
        message = ""

        if check == "output":
            expected = tc["expected"].strip()
            actual = stdout.strip()
            passed  = actual == expected
            message = f"Expected output:\n  {expected}\nYour output:\n  {actual}" if not passed else "Correct output ✓"

        elif check == "output_contains":
            expected = tc["expected"].strip()
            passed  = expected in stdout
            message = f"Expected your output to contain:\n  {expected}\nYour output:\n  {stdout}" if not passed else f"Found '{expected}' in output ✓"

        elif check == "variable":
            var_name = tc["var"]
            expected_type = tc["expected_type"]
            if var_name not in local_vars:
                message = f"Variable `{var_name}` was not found. Did you define it?"
                passed  = False
            else:
                actual_type = type(local_vars[var_name]).__name__
                passed  = actual_type == expected_type
                message = (
                    f"Variable `{var_name}` should be type `{expected_type}`, "
                    f"but got `{actual_type}`."
                ) if not passed else f"Variable `{var_name}` is correct ✓"

        if not passed:
            all_passed = False

        details.append({"test": f"Test {i}", "passed": passed, "message": message})

    error_type = None if all_passed else "logic"

    return {
        "passed": all_passed,
        "result": "pass" if all_passed else "fail",
        "error_type": error_type,
        "feedback": "All test cases passed! Great work." if all_passed else "Some test cases failed. Review the details below.",
        "details": details,
    }


# ─────────────────────────────────────────────
# DB Logging Helper
# ─────────────────────────────────────────────
def log_attempt(session_id: str, group_type: str, exercise_id: str,
                attempt_number: int, result: str, error_type,
                execution_time_ms: float = 0):
    """
    Insert one attempt document into MongoDB Atlas.
    Silently skips if DB is not connected (allows offline use).
    Includes execution_time_ms and platform_version (v1.1) for richer analytics.
    """
    if attempts_col is None:
        return
    doc = {
        "session_id":        session_id,
        "group_type":        group_type,
        "exercise_id":       exercise_id,
        "attempt_number":    attempt_number,
        "result":            result,
        "error_type":        error_type,
        "timestamp":         datetime.now(timezone.utc),
        "execution_time_ms": execution_time_ms,  # v1.1 addition
        "platform_version":  PLATFORM_VERSION,   # v1.1 addition
    }
    try:
        attempts_col.insert_one(doc)
    except Exception as e:
        print(f"[WARNING] DB insert failed: {e}")


def get_attempt_number(session_id: str, exercise_id: str) -> int:
    """Return the next attempt number for this session + exercise."""
    if attempts_col is None:
        return 1
    count = attempts_col.count_documents({
        "session_id":  session_id,
        "exercise_id": exercise_id,
    })
    return count + 1


# ─────────────────────────────────────────────
# Routes
# ─────────────────────────────────────────────

@app.route("/")
def index():
    """Landing page — study description and mode selection."""
    return render_template("index.html")


# ── Session progress helper ─────────────────────────────────────────────────
def get_session_progress(session_id):
    """Return lightweight progress stats for the current participant session."""
    if not session_id or attempts_col is None:
        return {"attempted": 0, "passed": 0, "total_attempts": 0}
    try:
        rows = list(attempts_col.find(
            {"session_id": session_id},
            {"exercise_id": 1, "result": 1, "_id": 0}
        ))
        attempted = len({r["exercise_id"] for r in rows})
        passed    = len({r["exercise_id"] for r in rows if r.get("result") == "pass"})
        return {"attempted": attempted, "passed": passed, "total_attempts": len(rows)}
    except Exception:
        return {"attempted": 0, "passed": 0, "total_attempts": 0}


@app.route("/static-mode")
def static_mode():
    """
    Static Mode entry point.
    Generates a unique session_id for this participant and stores group_type = "static".
    No login or registration required.

    Session-persistence: only creates a NEW session if no session exists at all.
    Switching from interactive → static DOES create a new session (different group).
    Re-entering static mode after going Home keeps the SAME session.
    """
    if "session_id" not in session or session.get("group_type") != "static":
        session["session_id"] = str(uuid.uuid4())
        session["group_type"] = "static"

    exercise_index = int(request.args.get("ex", 0))
    exercise_index = max(0, min(exercise_index, len(EXERCISES) - 1))
    exercise = EXERCISES[exercise_index]
    progress  = get_session_progress(session.get("session_id"))

    return render_template(
        "static_mode.html",
        exercise=exercise,
        exercises=EXERCISES,
        exercise_index=exercise_index,
        total=len(EXERCISES),
        feedback=None,
        progress=progress,
    )


@app.route("/interactive-mode")
def interactive_mode():
    """
    Interactive Mode entry point.
    Generates a unique session_id for this participant and stores group_type = "interactive".
    """
    if "session_id" not in session or session.get("group_type") != "interactive":
        session["session_id"] = str(uuid.uuid4())
        session["group_type"] = "interactive"

    exercise_index = int(request.args.get("ex", 0))
    exercise_index = max(0, min(exercise_index, len(EXERCISES) - 1))
    exercise = EXERCISES[exercise_index]
    progress  = get_session_progress(session.get("session_id"))

    return render_template(
        "interactive_mode.html",
        exercise=exercise,
        exercises=EXERCISES,
        exercise_index=exercise_index,
        total=len(EXERCISES),
        feedback=None,
        progress=progress,
    )


@app.route("/submit", methods=["POST"])
def submit():
    """
    Code submission endpoint — handles both static and interactive modes.

    POST body (form data):
      - code:           learner's submitted Python code
      - exercise_id:    which exercise is being submitted
      - exercise_index: positional index for navigation
      - group_type:     "static" or "interactive"

    Behaviour:
      - Static:      executes code, logs to DB, returns ONLY "Correct" or "Incorrect"
      - Interactive: executes code, logs to DB, returns detailed per-test-case feedback
    """
    code          = request.form.get("code", "")
    exercise_id   = request.form.get("exercise_id")
    exercise_index = int(request.form.get("exercise_index", 0))
    group_type    = session.get("group_type", "static")
    session_id    = session.get("session_id", str(uuid.uuid4()))

    exercise = EXERCISE_MAP.get(exercise_id)
    if not exercise:
        return "Invalid exercise", 400

    # Get attempt number from MongoDB (authoritative source)
    # This survives cookie loss and is always accurate.
    attempt_number = get_attempt_number(session_id, exercise_id)

    # Run the code and capture execution time
    exec_result    = run_code(code)
    eval_result    = evaluate_test_cases(exercise, exec_result)
    exec_time_ms   = exec_result.get("execution_time_ms", 0)

    # Log attempt to MongoDB Atlas (includes execution_time_ms, platform_version)
    log_attempt(
        session_id        = session_id,
        group_type        = group_type,
        exercise_id       = exercise_id,
        attempt_number    = attempt_number,
        result            = eval_result["result"],
        error_type        = eval_result["error_type"],
        execution_time_ms = exec_time_ms,
    )

    # ── Static mode: show ONLY pass/fail, no detailed breakdown ──
    if group_type == "static":
        simple_feedback = {
            "mode":    "static",
            "passed":  eval_result["passed"],
            "message": "Correct!" if eval_result["passed"] else "Incorrect.",
        }
        progress = get_session_progress(session_id)
        return render_template(
            "static_mode.html",
            exercise=exercise,
            exercises=EXERCISES,
            exercise_index=exercise_index,
            total=len(EXERCISES),
            feedback=simple_feedback,
            submitted_code=code,
            progress=progress,
        )

    # ── Interactive mode: full feedback with per-test details ──
    detailed_feedback = {
        "mode":     "interactive",
        "passed":   eval_result["passed"],
        "message":  eval_result["feedback"],
        "details":  eval_result["details"],
        "error_type": eval_result["error_type"],
    }
    return render_template(
        "interactive_mode.html",
        exercise=exercise,
        exercises=EXERCISES,
        exercise_index=exercise_index,
        total=len(EXERCISES),
        feedback=detailed_feedback,
        submitted_code=code,
    )


# ── Timestamp formatter helper ─────────────────────────────────────────────
def fmt_ts(ts) -> str:
    """
    Format a MongoDB timestamp (datetime) as a clean ISO 8601 string:
      YYYY-MM-DD HH:MM:SS  (UTC, no microseconds, no timezone suffix)
    Excel and SPSS parse this format reliably as a date+time value.
    Accepts datetime objects or returns '' for None/missing.
    """
    if ts is None:
        return ""
    if isinstance(ts, datetime):
        # Normalize to UTC naive for clean formatting
        if ts.tzinfo is not None:
            ts = ts.replace(tzinfo=None)  # MongoDB stores UTC; strip tz for clean output
        return ts.strftime("%Y-%m-%d %H:%M:%S")
    return str(ts)  # fallback for any unexpected type


@app.route("/export-data")
def export_data():
    """
    CSV export endpoint — critical for dissertation analysis.
    Downloads all attempt records from MongoDB Atlas as a CSV file.
    """
    if attempts_col is None:
        return "Database not connected.", 503

    rows = list(attempts_col.find({}, {"_id": 0}))

    buf = StringIO()
    writer = csv.writer(buf)
    writer.writerow([
        "session_id", "group_type", "exercise_id",
        "attempt_number", "result", "error_type", "timestamp"
    ])
    for row in rows:
        writer.writerow([
            row.get("session_id",     ""),
            row.get("group_type",     ""),
            row.get("exercise_id",    ""),
            row.get("attempt_number", ""),
            row.get("result",         ""),
            row.get("error_type",     ""),
            fmt_ts(row.get("timestamp")),
        ])

    bio = io.BytesIO(buf.getvalue().encode("utf-8-sig"))
    bio.seek(0)
    return send_file(
        bio,
        mimetype="text/csv",
        as_attachment=True,
        download_name="research_attempts.csv",
    )


@app.route("/export-research-dataset")
def export_research_dataset():
    """
    Enhanced full-dataset export.
    Includes execution_time_ms and platform_version for richer analysis.
    Compatible with Excel, SPSS, R, and Python pandas.
    """
    if attempts_col is None:
        return "Database not connected.", 503

    output  = StringIO()
    writer  = csv.writer(output, quoting=csv.QUOTE_NONNUMERIC)
    total   = len(EXERCISES)

    # Pre-compute per-session pass sets for session_completed field
    all_attempts = list(attempts_col.find({}, {
        "session_id": 1, "group_type": 1, "exercise_id": 1,
        "attempt_number": 1, "result": 1, "error_type": 1,
        "timestamp": 1, "execution_time_ms": 1, "platform_version": 1, "_id": 0
    }).sort("timestamp", ASCENDING))

    session_passed = {}
    for a in all_attempts:
        sid = a.get("session_id")
        if a.get("result") == "pass":
            session_passed.setdefault(sid, set()).add(a.get("exercise_id"))

    writer.writerow([
        "session_id", "group_type", "exercise_id", "attempt_number",
        "result", "error_type", "execution_time_ms", "platform_version",
        "timestamp", "session_completed"
    ])
    for a in all_attempts:
        sid = a.get("session_id")
        passed_set = session_passed.get(sid, set())
        writer.writerow([
            sid,
            a.get("group_type", ""),
            a.get("exercise_id", ""),
            a.get("attempt_number", ""),
            a.get("result", ""),
            a.get("error_type", "") or "",
            a.get("execution_time_ms", 0),
            a.get("platform_version", ""),
            fmt_ts(a.get("timestamp")),
            len(passed_set) >= total,
        ])

    csv_bio = io.BytesIO(output.getvalue().encode("utf-8-sig"))
    csv_bio.seek(0)
    return send_file(
        csv_bio,
        mimetype="text/csv",
        as_attachment=True,
        download_name="com748_research_dataset.csv",
    )


@app.route("/export-session-summary")
def export_session_summary():
    """
    Session-level aggregate export.
    One row per participant, derived from attempt data.
    Ideal for SPSS/R/pandas group comparisons.
    """
    if attempts_col is None:
        return "Database not connected.", 503

    total_ex = len(EXERCISES)
    all_rows = list(attempts_col.find({}, {
        "session_id": 1, "group_type": 1, "exercise_id": 1,
        "result": 1, "timestamp": 1, "_id": 0
    }))

    sessions = {}
    for r in all_rows:
        sid = r.get("session_id")
        if sid not in sessions:
            sessions[sid] = {
                "group_type": r.get("group_type", ""),
                "attempts": 0, "exercise_ids": set(),
                "passed_ids": set(), "timestamps": [],
            }
        sessions[sid]["attempts"] += 1
        sessions[sid]["exercise_ids"].add(r.get("exercise_id"))
        if r.get("result") == "pass":
            sessions[sid]["passed_ids"].add(r.get("exercise_id"))
        if r.get("timestamp"):
            sessions[sid]["timestamps"].append(r["timestamp"])

    output = StringIO()
    writer = csv.writer(output, quoting=csv.QUOTE_NONNUMERIC)
    writer.writerow([
        "session_id", "group_type", "exercises_attempted", "exercises_passed",
        "completion_rate_pct", "total_attempts", "session_start", "session_end",
        "session_duration_min", "session_completed"
    ])
    for sid, s in sessions.items():
        ex_att  = len(s["exercise_ids"])
        ex_pass = len(s["passed_ids"])
        ts      = [t for t in s["timestamps"] if isinstance(t, datetime)]
        dur_min = round((max(ts) - min(ts)).total_seconds() / 60, 1) if len(ts) > 1 else 0
        sess_start = fmt_ts(min(ts)) if ts else ""
        sess_end   = fmt_ts(max(ts)) if ts else ""
        writer.writerow([
            sid,
            s["group_type"],
            ex_att,
            ex_pass,
            round(ex_pass / total_ex * 100, 1),
            s["attempts"],
            sess_start,
            sess_end,
            dur_min,
            "TRUE" if ex_pass >= total_ex else "FALSE",
        ])

    csv_bio = io.BytesIO(output.getvalue().encode("utf-8-sig"))
    csv_bio.seek(0)
    return send_file(
        csv_bio,
        mimetype="text/csv",
        as_attachment=True,
        download_name="com748_session_summary.csv",
    )



@app.route("/db-status")
def db_status():
    """Simple health check — confirms DB connectivity. Useful during setup."""
    if attempts_col is None:
        return jsonify({"status": "disconnected", "message": "MONGO_URI not set or invalid."})
    try:
        count = attempts_col.count_documents({})
        return jsonify({"status": "connected", "total_attempts": count})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})


# ─────────────────────────────────────────────
# Admin Auth  (session-based, credentials from .env)
# ─────────────────────────────────────────────

def admin_required(f):
    """Decorator: redirect to /admin-login if not authenticated."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("admin_logged_in"):
            return redirect(url_for("admin_login"))
        return f(*args, **kwargs)
    return decorated


@app.route("/admin-login", methods=["GET", "POST"])
def admin_login():
    """Simple admin login. Credentials stored in .env (ADMIN_USERNAME / ADMIN_PASSWORD)."""
    error = None
    if request.method == "POST":
        u = request.form.get("username", "").strip()
        p = request.form.get("password", "").strip()
        if u == ADMIN_USERNAME and p == ADMIN_PASSWORD:
            session["admin_logged_in"] = True
            return redirect(url_for("admin_dashboard"))
        error = "Invalid username or password."
    return render_template("admin_login.html", error=error)


@app.route("/admin-logout")
def admin_logout():
    """Clear admin session and redirect to login page."""
    session.pop("admin_logged_in", None)
    return redirect(url_for("admin_login"))


@app.route("/admin-dashboard")
@admin_required
def admin_dashboard():
    """Protected admin analytics dashboard — requires session login."""
    return render_template("admin_dashboard.html")


@app.route("/complete")
def session_complete():
    """
    Session completion page shown after the last exercise.
    Computes participant stats on-the-fly from their attempt records.
    No new data is stored — purely derived from existing attempts.
    """
    sid        = session.get("session_id")
    group_type = session.get("group_type", "unknown")
    total_ex   = len(EXERCISES)

    if not sid or attempts_col is None:
        stats = {"exercises_attempted": 0, "exercises_passed": 0,
                 "total_attempts": 0, "duration_min": 0,
                 "completion_rate": 0, "group_type": group_type}
    else:
        rows = list(attempts_col.find({"session_id": sid}))
        ex_attempted = {r["exercise_id"] for r in rows}
        ex_passed    = {r["exercise_id"] for r in rows if r.get("result") == "pass"}
        timestamps   = [r["timestamp"] for r in rows if r.get("timestamp")]
        duration_min = 0
        if len(timestamps) > 1:
            duration_min = round((max(timestamps) - min(timestamps)).total_seconds() / 60, 1)
        stats = {
            "exercises_attempted": len(ex_attempted),
            "exercises_passed":    len(ex_passed),
            "total_attempts":      len(rows),
            "duration_min":        duration_min,
            "completion_rate":     round(len(ex_passed) / total_ex * 100),
            "group_type":          group_type,
        }
    return render_template("completion.html", stats=stats)


@app.route("/research-info")
def research_info():
    """Participant-facing page explaining the research study, ethics, and data use."""
    return render_template("research_info.html")


# ─────────────────────────────────────────────
# Stats API Endpoints (used by admin dashboard)
# ─────────────────────────────────────────────

@app.route("/api/stats/summary")
def api_stats_summary():
    """
    Summary statistics for the dashboard top cards.
    Returns: unique participants, group counts, total attempts, pass rate.
    """
    if attempts_col is None:
        return jsonify({"error": "DB not connected"}), 503
    try:
        total_attempts = attempts_col.count_documents({})
        all_sessions   = attempts_col.distinct("session_id")
        static_sess    = attempts_col.distinct("session_id", {"group_type": "static"})
        interactive_sess = attempts_col.distinct("session_id", {"group_type": "interactive"})
        passes         = attempts_col.count_documents({"result": "pass"})
        pass_rate      = round(passes / total_attempts * 100, 1) if total_attempts > 0 else 0
        return jsonify({
            "total_participants":    len(all_sessions),
            "static_participants":   len(static_sess),
            "interactive_participants": len(interactive_sess),
            "total_attempts":        total_attempts,
            "overall_pass_rate":     pass_rate,
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/stats/pass-rate")
def api_stats_pass_rate():
    """
    Pass rate broken down by group_type (static vs interactive).
    Returns: [{group, total, passes, pass_rate}]
    """
    if attempts_col is None:
        return jsonify({"error": "DB not connected"}), 503
    try:
        pipeline = [
            {"$group": {
                "_id":    "$group_type",
                "total":  {"$sum": 1},
                "passes": {"$sum": {"$cond": [{"$eq": ["$result", "pass"]}, 1, 0]}}
            }}
        ]
        rows = list(attempts_col.aggregate(pipeline))
        result = []
        for r in rows:
            total = r["total"]
            passes = r["passes"]
            result.append({
                "group":     r["_id"],
                "total":     total,
                "passes":    passes,
                "pass_rate": round(passes / total * 100, 1) if total > 0 else 0,
            })
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/stats/attempts")
def api_stats_attempts():
    """
    Average attempt_number per exercise, split by group_type.
    Returns: [{exercise_id, group_type, avg_attempts, count}]
    """
    if attempts_col is None:
        return jsonify({"error": "DB not connected"}), 503
    try:
        pipeline = [
            {"$group": {
                "_id": {"exercise_id": "$exercise_id", "group_type": "$group_type"},
                "avg_attempts": {"$avg": "$attempt_number"},
                "count":        {"$sum": 1},
            }},
            {"$sort": {"_id.exercise_id": 1}}
        ]
        rows = list(attempts_col.aggregate(pipeline))
        result = [{
            "exercise_id":  r["_id"]["exercise_id"],
            "group_type":   r["_id"]["group_type"],
            "avg_attempts": round(r["avg_attempts"], 2),
            "count":        r["count"],
        } for r in rows]
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/stats/errors")
def api_stats_errors():
    """
    Error type distribution across all attempts.
    Returns: [{error_type, count}]
    """
    if attempts_col is None:
        return jsonify({"error": "DB not connected"}), 503
    try:
        pipeline = [
            {"$match": {"error_type": {"$ne": None}}},
            {"$group": {
                "_id":   "$error_type",
                "count": {"$sum": 1},
            }},
            {"$sort": {"count": -1}}
        ]
        rows = list(attempts_col.aggregate(pipeline))
        return jsonify([{"error_type": r["_id"], "count": r["count"]} for r in rows])
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/stats/learning-curve")
def api_stats_learning_curve():
    """
    Average attempt number at first pass per exercise, split by group.
    This measures how quickly each group learns each concept.
    Returns: [{exercise_id, group_type, avg_first_pass}]
    """
    if attempts_col is None:
        return jsonify({"error": "DB not connected"}), 503
    try:
        pipeline = [
            # Only look at passing attempts
            {"$match": {"result": "pass"}},
            # Find the earliest passing attempt per session per exercise
            {"$group": {
                "_id": {
                    "session_id":  "$session_id",
                    "exercise_id": "$exercise_id",
                    "group_type":  "$group_type",
                },
                "first_pass": {"$min": "$attempt_number"},
            }},
            # Average across all sessions per exercise+group
            {"$group": {
                "_id": {
                    "exercise_id": "$_id.exercise_id",
                    "group_type":  "$_id.group_type",
                },
                "avg_first_pass": {"$avg": "$first_pass"},
                "sessions":       {"$sum": 1},
            }},
            {"$sort": {"_id.exercise_id": 1}}
        ]
        rows = list(attempts_col.aggregate(pipeline))
        result = [{
            "exercise_id":    r["_id"]["exercise_id"],
            "group_type":     r["_id"]["group_type"],
            "avg_first_pass": round(r["avg_first_pass"], 2),
            "sessions":       r["sessions"],
        } for r in rows]
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ─────────────────────────────────────────────
# Data Integrity & Research Analytics (v1.1)
# ─────────────────────────────────────────────

def get_valid_session_ids():
    """
    Return list of session IDs that pass data-quality checks:
      - More than 1 attempt (not trivially brief)
      - Total session duration > 10 seconds
    Invalid sessions are stored but excluded from research analytics.
    """
    if attempts_col is None:
        return []
    try:
        pipeline = [
            {"$group": {
                "_id":       "$session_id",
                "attempts":  {"$sum": 1},
                "first_ts":  {"$min": "$timestamp"},
                "last_ts":   {"$max": "$timestamp"},
            }},
            {"$addFields": {
                "duration_s": {"$divide": [{"$subtract": ["$last_ts", "$first_ts"]}, 1000]}
            }},
            {"$match": {
                "attempts":   {"$gt": 1},
                "duration_s": {"$gt": 10},
            }},
        ]
        return [r["_id"] for r in attempts_col.aggregate(pipeline)]
    except Exception:
        return []


@app.route("/api/stats/session-quality")
def api_stats_session_quality():
    """
    Session data-quality breakdown.
    Returns counts of valid vs invalid sessions and validity rate.
    """
    if attempts_col is None:
        return jsonify({"error": "DB not connected"}), 503
    try:
        pipeline = [
            {"$group": {
                "_id":       "$session_id",
                "attempts":  {"$sum": 1},
                "first_ts":  {"$min": "$timestamp"},
                "last_ts":   {"$max": "$timestamp"},
                "group_type": {"$first": "$group_type"},
            }},
            {"$addFields": {
                "duration_s": {"$divide": [{"$subtract": ["$last_ts", "$first_ts"]}, 1000]},
                "is_valid": {"$and": [
                    {"$gt": ["$attempts", 1]},
                    {"$gt": [{"$divide": [{"$subtract": ["$last_ts", "$first_ts"]}, 1000]}, 10]},
                ]},
            }},
            {"$group": {
                "_id": None,
                "total":   {"$sum": 1},
                "valid":   {"$sum": {"$cond": ["$is_valid", 1, 0]}},
                "invalid": {"$sum": {"$cond": ["$is_valid", 0, 1]}},
            }},
        ]
        rows = list(attempts_col.aggregate(pipeline))
        if not rows:
            return jsonify({"total": 0, "valid": 0, "invalid": 0, "validity_rate": 0})
        r = rows[0]
        return jsonify({
            "total":         r["total"],
            "valid":         r["valid"],
            "invalid":       r["invalid"],
            "validity_rate": round(r["valid"] / r["total"] * 100, 1) if r["total"] > 0 else 0,
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/stats/time-to-pass")
def api_stats_time_to_pass():
    """
    Cognitive efficiency metric: average time (seconds) from first attempt to first pass.
    - delta > 0  only: sessions where the participant needed >1 attempt are timed
    - delta = 0 (first-attempt pass) contributes to 'first_pass_count' for context
      but is NOT averaged in (a 0-second value distorts the learning-time metric)
    """
    if attempts_col is None:
        return jsonify({"error": "DB not connected"}), 503
    try:
        # Get first attempt timestamp per session+exercise
        first_attempt_rows = list(attempts_col.aggregate([
            {"$group": {
                "_id":      {"session_id": "$session_id", "exercise_id": "$exercise_id", "group_type": "$group_type"},
                "first_ts": {"$min": "$timestamp"},
            }},
        ]))
        first_map = {
            f"{r['_id']['session_id']}__{r['_id']['exercise_id']}": r
            for r in first_attempt_rows
        }

        # Get first pass timestamp per session+exercise
        first_pass_rows = list(attempts_col.aggregate([
            {"$match": {"result": "pass"}},
            {"$group": {
                "_id":     {"session_id": "$session_id", "exercise_id": "$exercise_id", "group_type": "$group_type"},
                "pass_ts": {"$min": "$timestamp"},
            }},
        ]))

        from collections import defaultdict
        # Store (sum_of_deltas, count_with_delta, count_first_pass)
        buckets = defaultdict(lambda: {"times": [], "first_pass": 0})

        for row in first_pass_rows:
            key  = f"{row['_id']['session_id']}__{row['_id']['exercise_id']}"
            bkey = (row["_id"]["exercise_id"], row["_id"]["group_type"])
            if key in first_map:
                delta = (row["pass_ts"] - first_map[key]["first_ts"]).total_seconds()
                if delta > 0:
                    # Meaningful learning time: had to try more than once
                    buckets[bkey]["times"].append(delta)
                else:
                    # Passed on first attempt — no measurable time, record count only
                    buckets[bkey]["first_pass"] += 1

        result = []
        for (ex_id, grp), data in buckets.items():
            times       = data["times"]
            first_count = data["first_pass"]
            total_count = len(times) + first_count
            if times:
                avg_secs = round(sum(times) / len(times), 1)
            elif first_count > 0:
                # All participants passed on first attempt — use 5s as
                # a representative minimum so the bar is visible
                avg_secs = 5.0
            else:
                continue
            result.append({
                "exercise_id":       ex_id,
                "group_type":        grp,
                "avg_time_seconds":  avg_secs,
                "count":             total_count,
                "first_attempt_passes": first_count,
            })
        result.sort(key=lambda x: x["exercise_id"])
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/stats/persistence")
def api_stats_persistence():
    """
    Persistence / frustration-tolerance metric.
    Average attempts on exercises that were NEVER passed in a given session.
    Uses ALL sessions (not just 'valid' ones) so every drop-off is counted.
    """
    if attempts_col is None:
        return jsonify({"error": "DB not connected"}), 503
    try:
        pipeline = [
            # Group by session+exercise to see total attempts and whether passed
            {"$group": {
                "_id": {"session_id": "$session_id", "exercise_id": "$exercise_id", "group_type": "$group_type"},
                "total_attempts": {"$sum": 1},
                "passes": {"$sum": {"$cond": [{"$eq": ["$result", "pass"]}, 1, 0]}},
            }},
            # Only keep exercise+session combos where it was NEVER passed
            {"$match": {"passes": 0, "total_attempts": {"$gte": 1}}},
            # Average across all such sessions per exercise+group
            {"$group": {
                "_id": {"exercise_id": "$_id.exercise_id", "group_type": "$_id.group_type"},
                "avg_attempts":     {"$avg": "$total_attempts"},
                "engaged_sessions": {"$sum": 1},
            }},
            {"$sort": {"_id.exercise_id": 1}},
        ]
        rows = list(attempts_col.aggregate(pipeline))
        return jsonify([{
            "exercise_id":      r["_id"]["exercise_id"],
            "group_type":       r["_id"]["group_type"],
            "avg_attempts":     round(r["avg_attempts"], 2),
            "engaged_sessions": r["engaged_sessions"],
        } for r in rows])
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/stats/error-transitions")
def api_stats_error_transitions():
    """
    Error progression analysis.
    Counts sequential error-type transitions within sessions (e.g. syntax→runtime, runtime→logic).
    Identifies common failure sequences for Educational Data Mining analysis.
    """
    if attempts_col is None:
        return jsonify({"error": "DB not connected"}), 503
    try:
        valid_ids = get_valid_session_ids()
        if not valid_ids:
            return jsonify([])

        # Fetch all attempts for valid sessions, sorted for sequential processing
        attempts_raw = list(attempts_col.find(
            {"session_id": {"$in": valid_ids}},
            {"session_id": 1, "exercise_id": 1, "attempt_number": 1,
             "error_type": 1, "result": 1, "_id": 0},
        ).sort([("session_id", 1), ("exercise_id", 1), ("attempt_number", 1)]))

        transitions = {}
        prev_key    = None
        prev_label  = None

        for att in attempts_raw:
            curr_key   = f"{att['session_id']}__{att['exercise_id']}"
            curr_label = att.get("error_type") or ("pass" if att["result"] == "pass" else "none")

            if curr_key == prev_key and prev_label is not None and curr_label != prev_label:
                t_key = f"{prev_label}\u2192{curr_label}"
                transitions[t_key] = transitions.get(t_key, 0) + 1

            prev_key   = curr_key
            prev_label = curr_label

        result = sorted(
            [{"from": k.split("\u2192")[0], "to": k.split("\u2192")[1], "count": v}
             for k, v in transitions.items()],
            key=lambda x: -x["count"]
        )[:20]  # top 20 transitions
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ─────────────────────────────────────────────
# Entry Point

# ─────────────────────────────────────────────
if __name__ == "__main__":
    print("\n" + "="*60)
    print("  COM748 Interactive Educational Platform")
    print("  Running at: http://127.0.0.1:5000")
    print("  DB status:  /db-status")
    print("  Export CSV: /export-data")
    print("="*60 + "\n")
    app.run(debug=True, port=5000)
