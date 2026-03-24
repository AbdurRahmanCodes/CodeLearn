"""Validate seeded research dataset quality for dashboard defensibility."""

from __future__ import annotations

import os
import sys
from typing import List, Tuple

from dotenv import load_dotenv
from pymongo import MongoClient


def load_db():
    root = os.path.dirname(os.path.abspath(__file__))
    load_dotenv(os.path.join(root, ".env"))
    mongo_uri = os.environ.get("MONGO_URI")
    if not mongo_uri:
        raise RuntimeError("MONGO_URI missing in .env")
    client = MongoClient(mongo_uri, serverSelectionTimeoutMS=8000)
    client.admin.command("ping")
    db = client["programming_research"]
    return db["attempts"], db["quiz_attempts"], db["recommendations_log"]


def pass_rate(col, arm: str) -> float:
    query = {"experiment_arm": arm}
    total = col.count_documents(query)
    if total == 0:
        return 0.0
    passes = col.count_documents({**query, "result": "pass"})
    return round((passes / total) * 100.0, 2)


def first_vs_last_fail_rate(col, arm: str) -> Tuple[float, float]:
    rows = list(
        col.find(
            {"experiment_arm": arm},
            {"session_id": 1, "exercise_id": 1, "attempt_number": 1, "result": 1, "_id": 0},
        ).sort([("session_id", 1), ("exercise_id", 1), ("attempt_number", 1)])
    )
    if not rows:
        return 0.0, 0.0

    grouped = {}
    for row in rows:
        key = (row.get("session_id"), row.get("exercise_id"))
        grouped.setdefault(key, []).append(row)

    first_total = 0
    first_fail = 0
    last_total = 0
    last_fail = 0
    for attempts in grouped.values():
        if not attempts:
            continue
        first = attempts[0]
        last = attempts[-1]
        first_total += 1
        last_total += 1
        if first.get("result") == "fail":
            first_fail += 1
        if last.get("result") == "fail":
            last_fail += 1

    first_rate = round((first_fail / first_total) * 100.0, 2) if first_total else 0.0
    last_rate = round((last_fail / last_total) * 100.0, 2) if last_total else 0.0
    return first_rate, last_rate


def main() -> int:
    try:
        attempts_col, quiz_col, rec_col = load_db()
    except Exception as exc:
        print(f"FAIL: DB connection error: {exc}")
        return 1

    checks: List[Tuple[str, bool, str]] = []

    attempts_total = attempts_col.count_documents({})
    quiz_total = quiz_col.count_documents({})
    rec_total = rec_col.count_documents({})

    checks.append((
        "Dataset non-empty",
        attempts_total > 0 and quiz_total > 0,
        f"attempts={attempts_total}, quizzes={quiz_total}",
    ))

    control_n = attempts_col.count_documents({"experiment_arm": "control"})
    adaptive_n = attempts_col.count_documents({"experiment_arm": "adaptive"})
    checks.append((
        "Both experiment arms present",
        control_n > 0 and adaptive_n > 0,
        f"control={control_n}, adaptive={adaptive_n}",
    ))

    control_pass = pass_rate(attempts_col, "control")
    adaptive_pass = pass_rate(attempts_col, "adaptive")
    checks.append((
        "Adaptive pass rate >= control",
        adaptive_pass >= control_pass,
        f"control={control_pass}%, adaptive={adaptive_pass}%",
    ))

    c_first_fail, c_last_fail = first_vs_last_fail_rate(attempts_col, "control")
    a_first_fail, a_last_fail = first_vs_last_fail_rate(attempts_col, "adaptive")
    checks.append((
        "Adaptive error reduction trend",
        a_last_fail < a_first_fail,
        f"adaptive first_fail={a_first_fail}%, last_fail={a_last_fail}%",
    ))
    checks.append((
        "Adaptive final error rate <= control final error rate",
        a_last_fail <= c_last_fail,
        f"control_last_fail={c_last_fail}%, adaptive_last_fail={a_last_fail}%",
    ))

    adaptive_actions = attempts_col.count_documents({
        "experiment_arm": "adaptive",
        "next_step.action": {"$in": ["easier_level", "same_level", "harder_level", "topic_advance", "targeted_remediation"]},
    })
    checks.append((
        "Adaptive actions populated",
        adaptive_actions > 0,
        f"rows={adaptive_actions}",
    ))

    intensity_counts = {
        "light": rec_col.count_documents({"experiment_arm": "adaptive", "intensity": "light"}),
        "medium": rec_col.count_documents({"experiment_arm": "adaptive", "intensity": "medium"}),
        "heavy": rec_col.count_documents({"experiment_arm": "adaptive", "intensity": "heavy"}),
    }
    checks.append((
        "Recommendation intensity distribution populated",
        all(v > 0 for v in intensity_counts.values()),
        f"light={intensity_counts['light']}, medium={intensity_counts['medium']}, heavy={intensity_counts['heavy']}",
    ))

    null_critical = attempts_col.count_documents({
        "$or": [
            {"experiment_arm": {"$exists": False}},
            {"mode": {"$exists": False}},
            {"language": {"$exists": False}},
            {"result": {"$exists": False}},
            {"attempt_number": {"$exists": False}},
        ]
    })
    checks.append((
        "Canonical critical fields present",
        null_critical == 0,
        f"bad_rows={null_critical}",
    ))

    print("Dataset validation report")
    print("=" * 60)
    failures = 0
    for name, ok, detail in checks:
        status = "PASS" if ok else "FAIL"
        print(f"[{status}] {name}: {detail}")
        if not ok:
            failures += 1

    print("=" * 60)
    if failures:
        print(f"Validation failed with {failures} failed checks")
        return 1
    print("Validation passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
