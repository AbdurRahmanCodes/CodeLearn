"""
COM748 — Realistic Session Seed Script
=======================================
Generates realistic fake participant sessions directly into MongoDB Atlas.

Design rationale (mirrors expected real-world findings):
  Static  group: more attempts, lower pass rate, more syntax/runtime errors
  Interactive group: fewer attempts, higher pass rate, faster error recovery

Sessions: 20 total (10 static, 10 interactive)
Spread across: 7 days leading up to today, random hours 09:00–22:00

Run once:  python seed_data.py
To reset:  python seed_data.py --clear   (deletes all existing data first)
"""

import os, sys, uuid, random
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv
from pymongo import MongoClient

# ── Load .env ──────────────────────────────────────────────────────────────
load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))
MONGO_URI = os.environ.get("MONGO_URI")

if not MONGO_URI:
    print("ERROR: MONGO_URI not found in .env. Cannot seed data.")
    sys.exit(1)

client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=8000)
client.admin.command("ping")
db   = client["programming_research"]
col  = db["attempts"]

# ── Clear existing data if --clear flag passed ──────────────────────────────
if "--clear" in sys.argv:
    deleted = col.delete_many({})
    print(f"Cleared {deleted.deleted_count} existing documents.")

# ── Exercise definitions (must match app.py EXERCISES order) ──────────────
EXERCISES = [
    "ex01",  # Variables & Assignment  (easy)
    "ex02",  # Arithmetic Operations   (easy-medium)
    "ex03",  # String Operations       (medium)
    "ex04",  # If / Else Conditions    (medium)
    "ex05",  # While Loop              (medium-hard)
    "ex06",  # For Loop & Lists        (medium-hard)
    "ex07",  # Functions (Capstone)    (hard)
]

PLATFORM_VERSION = "1.2"

# ── Error type weights ──────────────────────────────────────────────────────
# Weights for each error type when a fail attempt occurs
STATIC_ERROR_WEIGHTS      = [0.40, 0.30, 0.25, 0.05]  # syntax, runtime, logic, timeout
INTERACTIVE_ERROR_WEIGHTS = [0.25, 0.25, 0.45, 0.05]  # fewer syntax errors (feedback helps)
ERROR_TYPES = ["syntax", "runtime", "logic", "timeout"]

# ── Exercise difficulty configuration ─────────────────────────────────────
# (max_attempts, pass_probability_per_attempt)
# Static group struggles more — needs more attempts before passing
STATIC_EXERCISE_CONFIG = {
    "ex01": (5,  0.60),  # Variables — quite doable but no hints
    "ex02": (6,  0.50),  # Arithmetic — operators confuse some
    "ex03": (7,  0.45),  # Strings — methods not obvious without feedback
    "ex04": (7,  0.40),  # Conditions — logic errors common
    "ex05": (8,  0.35),  # While — infinite loop risk
    "ex06": (8,  0.35),  # For/Lists — index confusion
    "ex07": (9,  0.30),  # Functions — hardest capstone
}
# Interactive group passes faster — immediate feedback helps
INTERACTIVE_EXERCISE_CONFIG = {
    "ex01": (3,  0.80),
    "ex02": (4,  0.70),
    "ex03": (4,  0.65),
    "ex04": (5,  0.60),
    "ex05": (5,  0.55),
    "ex06": (6,  0.50),
    "ex07": (6,  0.45),
}

# ── Timestamp helper ───────────────────────────────────────────────────────
def session_start(days_ago_min=1, days_ago_max=7):
    """Random timestamp in the past 1-7 days, between 09:00 and 22:00."""
    days_back = random.randint(days_ago_min, days_ago_max)
    base = datetime.now(timezone.utc) - timedelta(days=days_back)
    base = base.replace(hour=random.randint(9, 21), minute=random.randint(0, 59),
                        second=0, microsecond=0)
    return base

# ── Simulate one participant session ──────────────────────────────────────
def simulate_session(group_type: str, session_date: datetime):
    """
    Simulate a plausible participant session and return list of attempt documents.
    
    Participant behaviour:
      - Works through exercises sequentially
      - May skip remaining exercises if frustrated (drop-off behaviour)
      - Each exercise: tries up to max_attempts times then moves on
      - Time between attempts: 30s–3min (realistic thinking time)
    """
    session_id = str(uuid.uuid4())
    config = STATIC_EXERCISE_CONFIG if group_type == "static" else INTERACTIVE_EXERCISE_CONFIG
    error_weights = STATIC_ERROR_WEIGHTS if group_type == "static" else INTERACTIVE_ERROR_WEIGHTS
    
    docs = []
    current_time = session_date
    
    # Static participants more likely to drop off after failing (less motivation)
    dropout_probability = 0.12 if group_type == "static" else 0.06
    
    for exercise_id in EXERCISES:
        # Random drop-off: participant may stop before finishing all exercises
        if docs and random.random() < dropout_probability:
            break  # simulates participant closing tab
        
        max_attempts, pass_prob_per_attempt = config[exercise_id]
        attempt_num = 0
        passed_this_exercise = False
        
        while attempt_num < max_attempts and not passed_this_exercise:
            attempt_num += 1
            thinking_time = timedelta(seconds=random.randint(30, 180))
            current_time += thinking_time
            
            did_pass = random.random() < pass_prob_per_attempt
            
            # Error probability increases for later attempts (tried simple things first)
            if did_pass:
                error_type = None
                result = "pass"
                passed_this_exercise = True
                exec_time = random.uniform(50, 400)
            else:
                error_type = random.choices(ERROR_TYPES, weights=error_weights)[0]
                result = "fail"
                exec_time = random.uniform(100, 2000) if error_type == "timeout" else random.uniform(30, 300)
            
            docs.append({
                "session_id":        session_id,
                "group_type":        group_type,
                "exercise_id":       exercise_id,
                "attempt_number":    attempt_num,
                "result":            result,
                "error_type":        error_type,
                "timestamp":         current_time,
                "execution_time_ms": round(exec_time, 1),
                "platform_version":  PLATFORM_VERSION,
            })
    
    return docs

# ── Generate all sessions ──────────────────────────────────────────────────
print("\nCOM748 — Seeding realistic participant data...")
print("="*60)

all_docs = []
session_log = []

# 10 Static sessions
for i in range(10):
    date = session_start(days_ago_min=1, days_ago_max=7)
    docs = simulate_session("static", date)
    all_docs.extend(docs)
    exercises_attempted = len({d["exercise_id"] for d in docs})
    exercises_passed    = len({d["exercise_id"] for d in docs if d["result"] == "pass"})
    session_log.append({
        "session_id": docs[0]["session_id"][:8] + "...",
        "group": "static",
        "attempts": len(docs),
        "exercises": f"{exercises_attempted}/7",
        "passed": f"{exercises_passed}/7",
    })
    print(f"  Static  session {i+1:02d}: {len(docs):2d} attempts, "
          f"{exercises_attempted}/7 exercises, {exercises_passed} passed")

# 10 Interactive sessions
for i in range(10):
    date = session_start(days_ago_min=1, days_ago_max=7)
    docs = simulate_session("interactive", date)
    all_docs.extend(docs)
    exercises_attempted = len({d["exercise_id"] for d in docs})
    exercises_passed    = len({d["exercise_id"] for d in docs if d["result"] == "pass"})
    session_log.append({
        "session_id": docs[0]["session_id"][:8] + "...",
        "group": "interactive",
        "attempts": len(docs),
        "exercises": f"{exercises_attempted}/7",
        "passed": f"{exercises_passed}/7",
    })
    print(f"  Interactive session {i+1:02d}: {len(docs):2d} attempts, "
          f"{exercises_attempted}/7 exercises, {exercises_passed} passed")

# ── Insert into MongoDB ────────────────────────────────────────────────────
print(f"\nInserting {len(all_docs)} attempt documents into MongoDB Atlas...")
result = col.insert_many(all_docs)
print(f"Inserted {len(result.inserted_ids)} documents successfully.")

# ── Summary statistics ─────────────────────────────────────────────────────
static_docs      = [d for d in all_docs if d["group_type"] == "static"]
interactive_docs = [d for d in all_docs if d["group_type"] == "interactive"]

def pass_rate(docs):
    if not docs: return 0
    return round(len([d for d in docs if d["result"] == "pass"]) / len(docs) * 100, 1)

def avg_attempts(docs):
    if not docs: return 0
    # Average attempt number across sessions/exercises
    return round(sum(d["attempt_number"] for d in docs) / len(docs), 1)

print("\n" + "="*60)
print("SUMMARY")
print("="*60)
print(f"  Total documents:    {len(all_docs)}")
print(f"  Static  sessions:   10  ({len(static_docs)} attempts, pass rate: {pass_rate(static_docs)}%)")
print(f"  Interactive sessions: 10  ({len(interactive_docs)} attempts, pass rate: {pass_rate(interactive_docs)}%)")
print(f"  Avg attempts — Static:      {avg_attempts(static_docs)}")
print(f"  Avg attempts — Interactive: {avg_attempts(interactive_docs)}")
print("\nDone! Open http://127.0.0.1:5000/admin-login to see the dashboard.")
print("="*60)
