"""Seed realistic COM748 synthetic research data using canonical schema fields."""

from __future__ import annotations

import argparse
import os
import random
import sys
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Tuple

from dotenv import load_dotenv
from pymongo import MongoClient

from app.data import EXERCISES, QUIZ_BANK


PLATFORM_VERSION = "2.1"
ERROR_WEIGHTS = {
    "python": [("syntax", 0.45), ("logic", 0.25), ("runtime", 0.20), ("timeout", 0.10)],
    "javascript": [("syntax", 0.50), ("logic", 0.22), ("runtime", 0.20), ("timeout", 0.08)],
}


@dataclass(frozen=True)
class LearnerProfile:
    name: str
    base_pass_boost: float
    drop_prob: float
    quiz_range: Tuple[float, float]
    speed_range_s: Tuple[int, int]


PROFILES: Dict[str, LearnerProfile] = {
    "novice": LearnerProfile("novice", -0.10, 0.17, (30.0, 74.0), (70, 240)),
    "intermediate": LearnerProfile("intermediate", 0.00, 0.08, (50.0, 88.0), (40, 170)),
    "advanced": LearnerProfile("advanced", 0.10, 0.03, (68.0, 98.0), (25, 110)),
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Seed synthetic research data into MongoDB.")
    parser.add_argument("--sessions", type=int, default=120, help="Number of synthetic participant sessions.")
    parser.add_argument("--days-back", type=int, default=21, help="Generate timestamps within the last N days.")
    parser.add_argument("--seed", type=int, default=748, help="Random seed for reproducible data.")
    parser.add_argument("--clear", action="store_true", help="Clear target collections before insert.")
    return parser.parse_args()


def _load_collections():
    root = os.path.dirname(os.path.abspath(__file__))
    load_dotenv(os.path.join(root, ".env"))
    mongo_uri = os.environ.get("MONGO_URI")
    if not mongo_uri:
        print("ERROR: MONGO_URI missing in .env")
        sys.exit(1)

    client = MongoClient(mongo_uri, serverSelectionTimeoutMS=8000)
    client.admin.command("ping")
    db = client["programming_research"]
    return db["attempts"], db["quiz_attempts"], db["recommendations_log"]


def _random_profile() -> LearnerProfile:
    key = random.choices(["novice", "intermediate", "advanced"], weights=[0.45, 0.40, 0.15])[0]
    return PROFILES[key]


def _session_start(days_back: int) -> datetime:
    now = datetime.now(timezone.utc)
    delta_days = random.randint(0, max(1, days_back))
    base = now - timedelta(days=delta_days)
    return base.replace(
        hour=random.randint(8, 22),
        minute=random.randint(0, 59),
        second=random.randint(0, 59),
        microsecond=0,
    )


def _legacy_arm(arm: str) -> str:
    return "B_adaptive" if arm == "adaptive" else "A_control"


def _pick_error(language: str) -> str:
    lang = language if language in ERROR_WEIGHTS else "python"
    values = ERROR_WEIGHTS[lang]
    labels = [v[0] for v in values]
    weights = [v[1] for v in values]
    return random.choices(labels, weights=weights)[0]


def _base_pass_probability(mode: str, arm: str, profile: LearnerProfile, language: str) -> float:
    p = 0.34 if mode == "static" else 0.52
    if arm == "adaptive":
        p += 0.08
    if language == "javascript":
        p -= 0.05
    p += profile.base_pass_boost
    return max(0.10, min(p, 0.90))


def _recommendation_bundle(error_type: Optional[str], attempt_no: int, passed: bool) -> List[Dict[str, str]]:
    if passed:
        return []

    recs: List[Dict[str, str]] = []
    if error_type == "syntax":
        syntax_intensity = "heavy" if attempt_no >= 2 else "medium"
        recs.append({"type": "video", "intensity": syntax_intensity, "reason": "repeated_syntax_errors"})
    elif error_type == "logic":
        recs.append({"type": "quiz", "intensity": "medium", "reason": "logic_mismatch_detected"})
    elif error_type == "runtime":
        recs.append({"type": "lesson", "intensity": "light", "reason": "runtime_error_detected"})
    elif error_type == "timeout":
        recs.append({"type": "lesson", "intensity": "medium", "reason": "timeout_detected"})

    if attempt_no >= 3:
        recs.append({"type": "exercise", "intensity": "heavy", "reason": "repeated_failures_with_escalation"})
    elif attempt_no >= 2:
        recs.append({"type": "exercise", "intensity": "medium", "reason": "multiple_failures"})

    return recs[:3]


def _next_step_action(passed: bool, error_type: Optional[str], attempt_no: int) -> str:
    if passed and attempt_no == 1:
        return "harder_level"
    if passed:
        return "topic_advance"
    if error_type == "syntax":
        return "targeted_remediation"
    if attempt_no >= 3:
        return "easier_level"
    return "same_level"


def generate_session(mode: str, arm: str, profile: LearnerProfile, days_back: int):
    session_id = str(uuid.uuid4())
    timeline = _session_start(days_back)

    attempts: List[dict] = []
    quizzes: List[dict] = []
    recommendations: List[dict] = []

    for ex in [{"id": e["id"], "topic": e["topic"], "language": e["language"]} for e in EXERCISES]:
        if attempts and random.random() < profile.drop_prob:
            break

        max_attempts = random.randint(2, 5) if arm == "control" else random.randint(3, 8)
        base_p = _base_pass_probability(mode, arm, profile, ex["language"])

        for attempt_no in range(1, max_attempts + 1):
            timeline += timedelta(seconds=random.randint(*profile.speed_range_s))

            # Adaptive group has stronger improvement trajectory across repeated attempts.
            learning_gain = 0.14 if arm == "adaptive" else 0.03
            pass_probability = min(base_p + (attempt_no * learning_gain), 0.96)
            passed = random.random() < pass_probability
            error_type = None if passed else _pick_error(ex["language"])

            recs = _recommendation_bundle(error_type, attempt_no, passed) if arm == "adaptive" else []
            rec_types = [r["type"] for r in recs]
            next_action = _next_step_action(passed, error_type, attempt_no) if arm == "adaptive" else "same_level"

            for rec in recs:
                recommendations.append(
                    {
                        "session_id": session_id,
                        "mode": mode,
                        "experiment_arm": arm,
                        "exercise_id": ex["id"],
                        "topic": ex["topic"],
                        "recommendation_type": rec["type"],
                        "title": rec["type"].replace("_", " ").title(),
                        "reason": rec["reason"],
                        "resource_url": "/",
                        "intensity": rec["intensity"],
                        "timestamp": timeline,
                        # Backward-compat aliases
                        "group_type": mode,
                        "experiment_group": _legacy_arm(arm),
                    }
                )

            exec_ms = round(random.uniform(90, 3200) if error_type == "timeout" else random.uniform(55, 720), 1)
            attempts.append(
                {
                    "session_id": session_id,
                    "user_id": session_id,
                    "mode": mode,
                    "experiment_arm": arm,
                    "exercise_id": ex["id"],
                    "topic": ex["topic"],
                    "language": ex["language"],
                    "programming_language": ex["language"],
                    "attempt_number": attempt_no,
                    "attempts": attempt_no,
                    "result": "pass" if passed else "fail",
                    "success": passed,
                    "error_type": error_type,
                    "recommendation_types": rec_types,
                    "recommendations_triggered": rec_types,
                    "recommendation_count": len(rec_types),
                    "recommendation_shown": bool(rec_types),
                    "next_step": {
                        "action": next_action,
                        "support_action": "lesson" if error_type in ("syntax", "timeout") else "exercise",
                        "profile_based": True,
                    },
                    "topic_quiz_score": None,
                    "timestamp": timeline,
                    "execution_time_ms": exec_ms,
                    "time_taken": round(exec_ms / 1000.0, 3),
                    "platform_version": PLATFORM_VERSION,
                    "learner_profile": profile.name,
                    # Backward-compat aliases
                    "group_type": mode,
                    "experiment_group": _legacy_arm(arm),
                }
            )

            if passed:
                break

    quiz_topics = list(QUIZ_BANK.keys())
    quiz_prob = 0.55 if profile.name == "novice" else 0.72 if profile.name == "intermediate" else 0.86
    for topic in quiz_topics:
        if random.random() > quiz_prob:
            continue
        timeline += timedelta(seconds=random.randint(40, 210))
        score_pct = round(random.uniform(*profile.quiz_range), 1)
        quizzes.append(
            {
                "session_id": session_id,
                "mode": mode,
                "experiment_arm": arm,
                "topic": topic,
                "score": int(round(score_pct / 100 * 3)),
                "total_questions": 3,
                "score_pct": score_pct,
                "answers": [],
                "timestamp": timeline,
                "learner_profile": profile.name,
                # Backward-compat aliases
                "group_type": mode,
                "experiment_group": _legacy_arm(arm),
            }
        )

    latest_quiz = {q["topic"]: q["score_pct"] for q in quizzes}
    for row in attempts:
        if row["topic"] in latest_quiz:
            row["topic_quiz_score"] = latest_quiz[row["topic"]]

    return attempts, quizzes, recommendations, profile.name


def main() -> None:
    args = parse_args()
    random.seed(args.seed)

    attempts_col, quiz_col, recommendations_col = _load_collections()
    if args.clear:
        print(f"Cleared attempts: {attempts_col.delete_many({}).deleted_count}")
        print(f"Cleared quiz_attempts: {quiz_col.delete_many({}).deleted_count}")
        print(f"Cleared recommendations_log: {recommendations_col.delete_many({}).deleted_count}")

    sessions = max(4, args.sessions)
    all_attempts: List[dict] = []
    all_quizzes: List[dict] = []
    all_recommendations: List[dict] = []
    profile_counter = {"novice": 0, "intermediate": 0, "advanced": 0}

    modes = ["static", "interactive"]
    arms = ["control", "adaptive"]
    mode_idx = 0
    arm_idx = 0

    for _ in range(sessions):
        mode = modes[mode_idx]
        arm = arms[arm_idx]
        profile = _random_profile()
        rows_a, rows_q, rows_r, p_name = generate_session(mode, arm, profile, args.days_back)
        profile_counter[p_name] += 1

        all_attempts.extend(rows_a)
        all_quizzes.extend(rows_q)
        all_recommendations.extend(rows_r)

        mode_idx = 1 - mode_idx
        arm_idx = 1 - arm_idx

    if all_attempts:
        attempts_col.insert_many(all_attempts)
    if all_quizzes:
        quiz_col.insert_many(all_quizzes)
    if all_recommendations:
        recommendations_col.insert_many(all_recommendations)

    print("\nSynthetic seeding complete")
    print("=" * 60)
    print(f"Sessions generated: {sessions}")
    print(f"Attempt docs inserted: {len(all_attempts)}")
    print(f"Quiz docs inserted: {len(all_quizzes)}")
    print(f"Recommendation docs inserted: {len(all_recommendations)}")
    print("Learner profile mix:")
    print(f"  novice: {profile_counter['novice']}")
    print(f"  intermediate: {profile_counter['intermediate']}")
    print(f"  advanced: {profile_counter['advanced']}")


if __name__ == "__main__":
    main()
