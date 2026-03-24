"""Unified learning engine for adaptive flow, logging, and recommendation decisions."""

from collections import defaultdict
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, MutableMapping, Optional

from app import mongo
from app.data import EXPERIMENT_GROUPS, LEARNING_TRACKS, normalize_language
from app.services.execution_engine import ExecutionEngine


class LearningEngine:
    """Single source of truth for learning flow + research logging."""

    FAST_THRESHOLD_SECONDS = 20.0
    SLOW_THRESHOLD_SECONDS = 60.0

    @staticmethod
    def _now():
        return datetime.now(timezone.utc)

    @staticmethod
    def _arm_to_standard(arm: str | None) -> str:
        value = (arm or "").strip()
        if value in ("B_adaptive", "adaptive"):
            return "adaptive"
        return "control"

    @staticmethod
    def _arm_to_legacy(arm: str | None) -> str:
        return "B_adaptive" if LearningEngine._arm_to_standard(arm) == "adaptive" else "A_control"

    @staticmethod
    def _normalize_mode(mode: str | None) -> str:
        m = (mode or "static").strip().lower()
        return m if m in ("static", "interactive") else "static"

    @staticmethod
    def _db_col(name: str):
        return getattr(mongo.db, name, None) if mongo.db is not None else None

    @staticmethod
    def log_event(event: Dict[str, Any]) -> None:
        """Research logging for adaptive decisions and interventions."""
        col = LearningEngine._db_col("learning_events")
        if col is None:
            return
        payload = dict(event)
        payload.setdefault("timestamp", LearningEngine._now())
        col.insert_one(payload)

    def __init__(self, session_id: str):
        self.session_id = session_id
        self.context = self._get_or_create_session_context()

    def _get_or_create_session_context(self) -> Dict[str, Any]:
        col = LearningEngine._db_col("session_context")
        if col is None:
            return {
                "session_id": self.session_id,
                "experiment_arm": "control",
                "mode": None,
                "created_at": LearningEngine._now(),
                "updated_at": LearningEngine._now(),
            }

        context = col.find_one({"session_id": self.session_id})
        if context:
            # Normalize old schema in memory.
            context["experiment_arm"] = LearningEngine._arm_to_standard(
                context.get("experiment_arm") or context.get("experiment_group")
            )
            context["mode"] = LearningEngine._normalize_mode(
                context.get("mode") or context.get("group_type") or context.get("user_mode")
            ) if (context.get("mode") or context.get("group_type") or context.get("user_mode")) else None
            context["experiment_group"] = LearningEngine._arm_to_legacy(context.get("experiment_arm"))
            context["user_mode"] = context.get("mode")
            context["group_type"] = context.get("mode")
            return context

        import random

        arm_legacy = random.choice(EXPERIMENT_GROUPS)
        arm = LearningEngine._arm_to_standard(arm_legacy)
        now = LearningEngine._now()
        new_context = {
            "session_id": self.session_id,
            "experiment_arm": arm,
            "mode": None,
            "created_at": now,
            "updated_at": now,
            # Backward-compat fields during migration.
            "experiment_group": arm_legacy,
            "user_mode": None,
            "group_type": None,
        }
        col.insert_one(new_context)
        return new_context

    def set_user_mode(self, mode: str) -> bool:
        raw = (mode or "").strip().lower()
        if raw not in ("static", "interactive"):
            return False
        mode = raw
        self.context["mode"] = mode
        self.context["user_mode"] = mode
        self.context["group_type"] = mode
        self.context["experiment_group"] = LearningEngine._arm_to_legacy(self.context.get("experiment_arm"))
        self.context["updated_at"] = LearningEngine._now()
        col = LearningEngine._db_col("session_context")
        if col is not None:
            col.update_one(
                {"session_id": self.session_id},
                {"$set": {
                    "mode": mode,
                    "user_mode": mode,
                    "group_type": mode,
                    "updated_at": LearningEngine._now(),
                }}
            )
        return True

    @staticmethod
    def init_participant_session(
        session_store: MutableMapping[str, object],
        mode: str,
        random_uuid: str,
        rand_choice: Callable[[tuple], str],
    ) -> None:
        mode = LearningEngine._normalize_mode(mode)
        existing_mode = str(session_store.get("mode") or session_store.get("group_type") or "")
        if "session_id" not in session_store or LearningEngine._normalize_mode(existing_mode) != mode:
            session_store["session_id"] = random_uuid
            arm_legacy = rand_choice(EXPERIMENT_GROUPS)
            arm = LearningEngine._arm_to_standard(arm_legacy)
            session_store["mode"] = mode
            session_store["experiment_arm"] = arm
            # Backward-compat aliases
            session_store["group_type"] = mode
            session_store["experiment_group"] = arm_legacy

        if "experiment_arm" not in session_store:
            arm_legacy = rand_choice(EXPERIMENT_GROUPS)
            session_store["experiment_arm"] = LearningEngine._arm_to_standard(arm_legacy)
            session_store["experiment_group"] = arm_legacy
        if "mode" not in session_store and session_store.get("group_type"):
            session_store["mode"] = LearningEngine._normalize_mode(str(session_store.get("group_type") or ""))

    @staticmethod
    def get_session_progress(attempts_col, session_id: Optional[str]) -> Dict[str, int]:
        if not session_id or attempts_col is None:
            return {"attempted": 0, "passed": 0, "total_attempts": 0}
        rows = list(attempts_col.find({"session_id": session_id}, {"exercise_id": 1, "result": 1, "_id": 0}))
        attempted = len({r.get("exercise_id") for r in rows})
        passed = len({r.get("exercise_id") for r in rows if r.get("result") == "pass"})
        return {"attempted": attempted, "passed": passed, "total_attempts": len(rows)}

    @staticmethod
    def get_session_progress_for_language(attempts_col, session_id: Optional[str], language: str) -> Dict[str, int]:
        if not session_id or attempts_col is None:
            return {"attempted": 0, "passed": 0, "total_attempts": 0}
        rows = list(
            attempts_col.find(
                {"session_id": session_id, "programming_language": normalize_language(language)},
                {"exercise_id": 1, "result": 1, "_id": 0},
            )
        )
        attempted = len({r.get("exercise_id") for r in rows})
        passed = len({r.get("exercise_id") for r in rows if r.get("result") == "pass"})
        return {"attempted": attempted, "passed": passed, "total_attempts": len(rows)}

    @staticmethod
    def next_attempt_number(attempts_col, session_id: str, exercise_id: str) -> int:
        if attempts_col is None:
            return 1
        return attempts_col.count_documents({"session_id": session_id, "exercise_id": exercise_id}) + 1

    @staticmethod
    def build_user_profile(attempts_col, session_id: str, current_language: Optional[str] = None) -> Dict[str, Any]:
        """Aggregate learner behavior into a profile for adaptive decisions."""
        if attempts_col is None:
            return {
                "avg_attempts": 0.0,
                "avg_time": 0.0,
                "weak_topics": [],
                "strong_topics": [],
                "error_pattern": {"dominant": None, "counts": {}},
                "language_difficulty": {},
                "current_language_pressure": 0.0,
                "improvement_rate": 0.0,
            }

        rows = list(
            attempts_col.find(
                {"session_id": session_id},
                {
                    "topic": 1,
                    "programming_language": 1,
                    "result": 1,
                    "error_type": 1,
                    "attempt_number": 1,
                    "execution_time_ms": 1,
                    "_id": 0,
                },
            )
        )

        if not rows:
            return {
                "avg_attempts": 0.0,
                "avg_time": 0.0,
                "weak_topics": [],
                "strong_topics": [],
                "error_pattern": {"dominant": None, "counts": {}},
                "language_difficulty": {},
                "current_language_pressure": 0.0,
                "improvement_rate": 0.0,
            }

        topic_stats: Dict[str, Dict[str, float]] = {}
        language_stats: Dict[str, Dict[str, float]] = {}
        error_counts: Dict[str, int] = {}
        attempts_sum = 0.0
        duration_sum = 0.0

        for row in rows:
            topic = str(row.get("topic") or "unknown")
            language = normalize_language(row.get("programming_language") or "python")
            result = str(row.get("result") or "fail")
            error_type = str(row.get("error_type") or "none")
            attempt_number = float(row.get("attempt_number") or 1)
            time_sec = float(row.get("execution_time_ms") or 0) / 1000

            attempts_sum += attempt_number
            duration_sum += time_sec
            error_counts[error_type] = error_counts.get(error_type, 0) + 1

            t_bucket = topic_stats.setdefault(topic, {"total": 0.0, "pass": 0.0, "fail": 0.0, "time": 0.0})
            t_bucket["total"] += 1
            t_bucket["time"] += time_sec
            if result == "pass":
                t_bucket["pass"] += 1
            else:
                t_bucket["fail"] += 1

            l_bucket = language_stats.setdefault(language, {"total": 0.0, "fail": 0.0, "syntax": 0.0, "time": 0.0})
            l_bucket["total"] += 1
            l_bucket["time"] += time_sec
            if result != "pass":
                l_bucket["fail"] += 1
            if error_type == "syntax":
                l_bucket["syntax"] += 1

        weak_topics: List[str] = []
        strong_topics: List[str] = []
        for topic, bucket in topic_stats.items():
            total = bucket["total"] or 1
            fail_rate = bucket["fail"] / total
            pass_rate = bucket["pass"] / total
            avg_time = bucket["time"] / total
            if fail_rate >= 0.5 or avg_time >= LearningEngine.SLOW_THRESHOLD_SECONDS:
                weak_topics.append(topic)
            elif pass_rate >= 0.8 and avg_time <= LearningEngine.FAST_THRESHOLD_SECONDS:
                strong_topics.append(topic)

        language_difficulty: Dict[str, Dict[str, float]] = {}
        for language, bucket in language_stats.items():
            total = bucket["total"] or 1
            language_difficulty[language] = {
                "attempts": bucket["total"],
                "error_rate": round(bucket["fail"] / total, 3),
                "syntax_rate": round(bucket["syntax"] / total, 3),
                "avg_time": round(bucket["time"] / total, 3),
            }

        dominant_error = None
        if error_counts:
            dominant_error = max(error_counts.items(), key=lambda item: item[1])[0]

        pressure = 0.0
        if current_language:
            cur_lang = normalize_language(current_language)
            cur_error_rate = language_difficulty.get(cur_lang, {}).get("error_rate", 0.0)
            other_rates = [v.get("error_rate", 0.0) for k, v in language_difficulty.items() if k != cur_lang]
            baseline = sum(other_rates) / len(other_rates) if other_rates else 0.0
            pressure = round(cur_error_rate - baseline, 3)

        # Calculate improvement rate: comparing early vs recent attempts
        improvement_rate = 0.0
        if len(rows) >= 4:
            early_attempts = rows[:len(rows)//3]
            recent_attempts = rows[-len(rows)//3:]
            early_avg = sum(a.get("attempt_number", 1) for a in early_attempts) / len(early_attempts)
            recent_avg = sum(a.get("attempt_number", 1) for a in recent_attempts) / len(recent_attempts)
            improvement_rate = round(early_avg - recent_avg, 2)

        return {
            "avg_attempts": round(attempts_sum / len(rows), 2),
            "avg_time": round(duration_sum / len(rows), 3),
            "weak_topics": sorted(weak_topics),
            "strong_topics": sorted(strong_topics),
            "error_pattern": {"dominant": dominant_error, "counts": error_counts},
            "language_difficulty": language_difficulty,
            "current_language_pressure": pressure,
            "improvement_rate": improvement_rate,
        }

    @staticmethod
    def get_next_step(user_state: Dict[str, Any], user_profile: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Adaptive decision using topic weakness/strength and recent performance."""
        success = bool(user_state.get("success"))
        attempts = int(user_state.get("attempts") or 1)
        error_type = str(user_state.get("error_type") or "")
        if error_type == "logic_error":
            error_type = "logic"
        elif error_type == "syntax_error":
            error_type = "syntax"
        elif error_type == "runtime_error":
            error_type = "runtime"
        time_taken = float(user_state.get("time_taken") or 0)
        exercise_index = int(user_state.get("exercise_index") or 0)
        total = int(user_state.get("total_exercises") or (exercise_index + 1))
        topic = str(user_state.get("topic") or "")
        weak_topics = set((user_profile or {}).get("weak_topics") or [])
        strong_topics = set((user_profile or {}).get("strong_topics") or [])
        language_pressure = float((user_profile or {}).get("current_language_pressure") or 0)

        if topic in weak_topics and not success:
            next_index = exercise_index
            action = "targeted_remediation"
        elif not success and attempts >= 3:
            next_index = max(0, exercise_index - 1)
            action = "easier_level"
        elif success and topic in strong_topics and time_taken and time_taken < LearningEngine.FAST_THRESHOLD_SECONDS:
            next_index = min(total - 1, exercise_index + 1)
            action = "topic_advance"
        elif success and time_taken and time_taken < LearningEngine.FAST_THRESHOLD_SECONDS:
            next_index = min(total - 1, exercise_index + 1)
            action = "harder_level"
        elif language_pressure > 0.25 and not success:
            next_index = exercise_index
            action = "language_support"
        else:
            next_index = exercise_index
            action = "same_level"

        support_action = "exercise"
        if error_type == "syntax":
            support_action = "lesson"
        elif error_type == "logic":
            support_action = "quiz"
        elif error_type == "timeout":
            support_action = "lesson"

        return {
            "action": action,
            "next_exercise_index": next_index,
            "support_action": support_action,
            "profile_based": bool(user_profile),
        }

    @staticmethod
    def generate_recommendation(
        user_state: Dict[str, Any],
        topic_page_url: str,
        topic_quiz_url: str,
        easier_exercise_url: str,
        user_profile: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, str]]:
        """Centralized recommendation logic with frequency-based intensity adaptation."""
        recs: List[Dict[str, str]] = []
        error_type = str(user_state.get("error_type") or "")
        success = bool(user_state.get("success"))
        attempts = int(user_state.get("attempts") or 1)
        time_taken = float(user_state.get("time_taken") or 0)
        topic = str(user_state.get("topic") or "topic")
        current_language = normalize_language(user_state.get("language") or "python")
        profile = user_profile or {}
        dominant_error = str((profile.get("error_pattern") or {}).get("dominant") or "")
        error_counts = (profile.get("error_pattern") or {}).get("counts") or {}
        syntax_count = int(error_counts.get("syntax", 0))
        language_pressure = float(profile.get("current_language_pressure") or 0)
        improvement_rate = float(profile.get("improvement_rate") or 0)

        if success:
            return recs

        # Determine recommendation intensity based on error frequency and improvement tracking
        # Intensity levels: light (occasional), medium (repetitive), heavy (persistent + no improvement)
        
        if error_type == "syntax":
            if syntax_count >= 5 or dominant_error == "syntax":
                # Persistent syntax errors + no improvement = deep intervention
                if improvement_rate <= -0.1:
                    intensity = "heavy"
                    recs.append({
                        "type": "video",
                        "reason": "persistent_syntax_errors_no_progress",
                        "target": topic_page_url,
                        "title": "PRIORITY: Comprehensive syntax guide + exercises",
                        "resource_url": topic_page_url,
                        "intensity": intensity,
                    })
                else:
                    # Repetitive but showing some improvement
                    intensity = "medium"
                    recs.append({
                        "type": "video",
                        "reason": "repeated_syntax_errors",
                        "target": topic_page_url,
                        "title": "Beginner syntax refresher",
                        "resource_url": topic_page_url,
                        "intensity": intensity,
                    })
            else:
                # Occasional syntax error
                intensity = "light"
                recs.append({
                    "type": "tips",
                    "reason": "occasional_syntax_error",
                    "target": topic_page_url,
                    "title": "Quick syntax checklist",
                    "resource_url": topic_page_url,
                    "intensity": intensity,
                })
        elif error_type == "logic":
            recs.append({
                "type": "quiz",
                "reason": "logic_mismatch_detected",
                "target": topic_quiz_url,
                "title": "Concept quiz + practice",
                "resource_url": topic_quiz_url,
                "intensity": "medium",
            })
        elif error_type == "timeout":
            recs.append({
                "type": "lesson",
                "reason": "timeout_detected",
                "target": topic_page_url,
                "title": "Optimization hints",
                "resource_url": topic_page_url,
                "intensity": "medium",
            })

        if attempts >= 5 and improvement_rate <= 0:
            # Multiple failures with no improvement = escalate
            recs.append({
                "type": "exercise",
                "reason": "repeated_failures_with_escalation",
                "target": easier_exercise_url,
                "title": f"Strongly recommended: Easier {topic} exercise",
                "resource_url": easier_exercise_url,
                "intensity": "heavy",
            })
        elif attempts >= 3:
            recs.append({
                "type": "exercise",
                "reason": "multiple_failures",
                "target": easier_exercise_url,
                "title": f"Easier {topic} exercise",
                "resource_url": easier_exercise_url,
                "intensity": "medium",
            })

        if time_taken > LearningEngine.SLOW_THRESHOLD_SECONDS:
            recs.append({
                "type": "review_concept",
                "reason": "slow_attempt",
                "target": topic_page_url,
                "title": "Review concept before retry",
                "resource_url": topic_page_url,
                "intensity": "light",
            })

        if language_pressure > 0.25:
            recs.append({
                "type": "language_focus",
                "reason": f"{current_language}_struggle_detected",
                "target": topic_page_url,
                "title": f"Extra {current_language.title()} practice recommended",
                "resource_url": topic_page_url,
                "intensity": "medium",
            })

        return recs[:3]

    @staticmethod
    def build_recommendations(
        exercise: dict,
        attempt_number: int,
        eval_result: dict,
        topic_page_url: str,
        topic_quiz_url: str,
        easier_exercise_url: str,
        execution_time_ms: float = 0,
    ) -> List[Dict[str, str]]:
        state = {
            "topic": exercise.get("topic"),
            "attempts": attempt_number,
            "success": eval_result.get("result") == "pass",
            "error_type": eval_result.get("error_type"),
            "time_taken": float(execution_time_ms or 0) / 1000,
        }
        return LearningEngine.generate_recommendation(state, topic_page_url, topic_quiz_url, easier_exercise_url)

    @staticmethod
    def log_recommendations(
        recommend_col,
        session_id: str,
        user_id: Optional[str],
        mode: str,
        experiment_arm: str,
        exercise_id: str,
        topic: str,
        recommendations: list,
    ) -> None:
        if recommend_col is None or not recommendations:
            return
        now = LearningEngine._now()
        docs = []
        for rec in recommendations:
            docs.append({
                "session_id": session_id,
                "user_id": user_id or session_id,
                "mode": LearningEngine._normalize_mode(mode),
                "experiment_arm": LearningEngine._arm_to_standard(experiment_arm),
                "exercise_id": exercise_id,
                "topic": topic,
                "recommendation_type": rec.get("type"),
                "title": rec.get("title"),
                "reason": rec.get("reason"),
                "resource_url": rec.get("resource_url") or rec.get("target"),
                "intensity": rec.get("intensity"),
                "timestamp": now,
                # Backward-compat aliases
                "group_type": LearningEngine._normalize_mode(mode),
                "experiment_group": LearningEngine._arm_to_legacy(experiment_arm),
            })
            LearningEngine.log_event({
                "event_type": "recommendation_triggered",
                "session_id": session_id,
                "exercise_id": exercise_id,
                "topic": topic,
                "reason": rec.get("reason"),
                "recommendation_type": rec.get("type"),
            })
        recommend_col.insert_many(docs)

    @staticmethod
    def log_attempt(
        attempts_col,
        session_id: str,
        user_id: Optional[str],
        mode: str,
        exercise: dict,
        attempt_number: int,
        eval_result: dict,
        execution_time_ms: float,
        experiment_arm: str,
        recommendations: list,
        next_step: Optional[Dict[str, Any]] = None,
    ) -> None:
        if attempts_col is None:
            return
        arm = LearningEngine._arm_to_standard(experiment_arm)
        m = LearningEngine._normalize_mode(mode)
        attempts_col.insert_one({
            "session_id": session_id,
            "user_id": user_id or session_id,
            "mode": m,
            "experiment_arm": arm,
            "exercise_id": exercise["id"],
            "programming_language": exercise["language"],
            "language": exercise["language"],
            "topic": exercise["topic"],
            "attempt_number": attempt_number,
            "attempts": attempt_number,
            "result": eval_result["result"],
            "success": eval_result["result"] == "pass",
            "error_type": eval_result["error_type"],
            "recommendation_types": [r.get("type") for r in recommendations],
            "recommendations_triggered": [r.get("type") for r in recommendations],
            "recommendation_count": len(recommendations),
            "recommendation_shown": bool(recommendations),
            "next_step": next_step or {},
            "topic_quiz_score": None,
            "timestamp": LearningEngine._now(),
            "execution_time_ms": execution_time_ms,
            "time_taken": round((execution_time_ms or 0) / 1000, 3),
            "platform_version": "2.0",
            # Backward-compat aliases during migration.
            "group_type": m,
            "experiment_group": LearningEngine._arm_to_legacy(arm),
        })

    @staticmethod
    def evaluate_quiz_submission(questions: List[Dict], submitted_values: MutableMapping[str, str]) -> Dict[str, object]:
        score = 0
        answers = []
        for q in questions:
            raw = submitted_values.get(q["id"], "")
            selected = int(raw) if str(raw).isdigit() else -1
            correct = selected == q["answer"]
            if correct:
                score += 1
            answers.append({
                "question_id": q["id"],
                "selected": selected,
                "correct_option": q["answer"],
                "is_correct": correct,
            })

        total_questions = len(questions)
        score_pct = round((score / total_questions) * 100, 1) if total_questions else 0
        return {
            "score": score,
            "total_questions": total_questions,
            "score_pct": score_pct,
            "answers": answers,
        }

    @staticmethod
    def log_quiz_attempt(
        quiz_col,
        session_id: Optional[str],
        user_id: Optional[str],
        mode: str,
        experiment_arm: str,
        topic_id: str,
        quiz_result: Dict[str, object],
    ) -> None:
        if quiz_col is None:
            return
        m = LearningEngine._normalize_mode(mode)
        arm = LearningEngine._arm_to_standard(experiment_arm)
        quiz_col.insert_one({
            "session_id": session_id,
            "user_id": user_id or session_id,
            "mode": m,
            "experiment_arm": arm,
            "topic": topic_id,
            "score": quiz_result["score"],
            "total_questions": quiz_result["total_questions"],
            "score_pct": quiz_result["score_pct"],
            "answers": quiz_result["answers"],
            "timestamp": LearningEngine._now(),
            # Backward compatibility aliases
            "group_type": m,
            "experiment_group": LearningEngine._arm_to_legacy(arm),
        })
        LearningEngine.log_event({
            "event_type": "quiz_completed",
            "session_id": session_id,
            "topic": topic_id,
            "score_pct": quiz_result["score_pct"],
        })

    @staticmethod
    def topic_quiz_unlock_status(
        attempts_col,
        session_id: Optional[str],
        topic_id: str,
        selected_language: str,
        experiment_arm: str = "adaptive",
    ) -> Dict[str, object]:
        arm = LearningEngine._arm_to_standard(experiment_arm)
        if arm == "control":
            return {"unlocked": True, "reason": "Control group follows static access (no adaptive quiz trigger)."}

        if not session_id:
            return {"unlocked": False, "reason": "Start an exercise session first to unlock diagnostic quizzes."}
        if attempts_col is None:
            return {"unlocked": False, "reason": "Attempt history is unavailable; quiz remains locked."}

        rows = list(
            attempts_col.find(
                {
                    "session_id": session_id,
                    "topic": topic_id,
                    "programming_language": selected_language,
                },
                {
                    "attempt_number": 1,
                    "result": 1,
                    "error_type": 1,
                    "execution_time_ms": 1,
                    "_id": 0,
                },
            )
        )
        if not rows:
            return {"unlocked": False, "reason": "Complete at least one coding attempt on this topic to unlock the quiz."}

        has_logic_error = any((r.get("error_type") or "") == "logic" for r in rows)
        has_repeated_failure = any(r.get("result") == "fail" and int(r.get("attempt_number") or 0) >= 2 for r in rows)
        has_slow_attempt = any(float(r.get("execution_time_ms") or 0) > 60000 for r in rows)

        if has_logic_error or has_repeated_failure or has_slow_attempt:
            LearningEngine.log_event({
                "event_type": "quiz_unlocked",
                "session_id": session_id,
                "topic": topic_id,
                "reason": "struggle_detected",
            })
            return {"unlocked": True, "reason": "Diagnostic quiz unlocked due to detected learning struggle."}

        return {
            "unlocked": False,
            "reason": "Quiz unlocks when struggle is detected (logic error, repeated failure, or slow attempt).",
        }

    @staticmethod
    def build_completion_stats(
        attempts_col,
        quiz_col,
        session_id: Optional[str],
        mode: str,
        experiment_arm: str,
        total_exercises: int,
    ) -> Dict[str, object]:
        if not session_id or attempts_col is None:
            return {
                "exercises_attempted": 0,
                "exercises_passed": 0,
                "total_attempts": 0,
                "duration_min": 0,
                "completion_rate": 0,
                "mode": mode,
                "experiment_arm": LearningEngine._arm_to_standard(experiment_arm),
                "recommendation_count": 0,
                "avg_quiz_score": None,
            }

        rows = list(attempts_col.find({"session_id": session_id}))
        attempted = {r.get("exercise_id") for r in rows}
        passed = {r.get("exercise_id") for r in rows if r.get("result") == "pass"}
        timestamps = [r.get("timestamp") for r in rows if r.get("timestamp")]

        duration_min = 0
        if len(timestamps) > 1:
            duration_min = round((max(timestamps) - min(timestamps)).total_seconds() / 60, 1)

        avg_quiz = None
        if quiz_col is not None:
            qrows = list(quiz_col.find({"session_id": session_id}, {"score_pct": 1, "_id": 0}))
            if qrows:
                avg_quiz = round(sum(row.get("score_pct", 0) for row in qrows) / len(qrows), 1)

        return {
            "exercises_attempted": len(attempted),
            "exercises_passed": len(passed),
            "total_attempts": len(rows),
            "duration_min": duration_min,
            "completion_rate": round(len(passed) / total_exercises * 100) if total_exercises else 0,
            "mode": LearningEngine._normalize_mode(mode),
            "experiment_arm": LearningEngine._arm_to_standard(experiment_arm),
            "recommendation_count": sum(int(r.get("recommendation_count", 0)) for r in rows),
            "avg_quiz_score": avg_quiz,
        }

    @staticmethod
    def compute_group_metrics(attempts_col, experiment_arm: Optional[str] = None) -> Dict[str, Any]:
        """
        Compute comparative research metrics for evaluation by experiment arm.
        
        Returns aggregate metrics across all sessions in the specified arm:
        {
            "arm": "control|adaptive",
            "total_sessions": int,
            "total_attempts": int,
            "avg_attempts_to_first_pass": float,
            "exercises_passed": int,
            "pass_rate": float (0-100),
            "error_reduction_rate": float (how much errors decreased across session),
            "avg_time_per_attempt": float (seconds),
            "syntax_error_rate": float (0-100),
            "logic_error_rate": float (0-100),
            "avg_attempts_per_exercise": float,
            "topic_diversity": int (unique topics attempted),
            "difficulty_progression": str (shows if learner is attempting harder topics),
            "improvement_trajectory": float (attempts on last 30% of session vs first 30%),
        }
        """
        if attempts_col is None:
            arm_str = LearningEngine._arm_to_standard(experiment_arm)
            return {
                "arm": arm_str,
                "total_sessions": 0,
                "total_attempts": 0,
                "avg_attempts_to_first_pass": 0.0,
                "exercises_passed": 0,
                "pass_rate": 0.0,
                "error_reduction_rate": 0.0,
                "avg_time_per_attempt": 0.0,
                "syntax_error_rate": 0.0,
                "logic_error_rate": 0.0,
                "avg_attempts_per_exercise": 0.0,
                "topic_diversity": 0,
                "difficulty_progression": "no_data",
                "improvement_trajectory": 0.0,
            }
        
        # Fetch all attempts for the arm
        arm_str = LearningEngine._arm_to_standard(experiment_arm or "control")
        arm_legacy = LearningEngine._arm_to_legacy(arm_str)
        
        rows = list(attempts_col.find({
            "$or": [
                {"experiment_arm": arm_str},
                {"experiment_arm": arm_legacy},
                {"experiment_group": arm_legacy},
            ]
        }))
        
        if not rows:
            return {
                "arm": arm_str,
                "total_sessions": 0,
                "total_attempts": 0,
                "avg_attempts_to_first_pass": 0.0,
                "exercises_passed": 0,
                "pass_rate": 0.0,
                "error_reduction_rate": 0.0,
                "avg_time_per_attempt": 0.0,
                "syntax_error_rate": 0.0,
                "logic_error_rate": 0.0,
                "avg_attempts_per_exercise": 0.0,
                "topic_diversity": 0,
                "difficulty_progression": "no_data",
                "improvement_trajectory": 0.0,
            }
        
        # Aggregate metrics
        unique_sessions = {r.get("session_id") for r in rows if r.get("session_id")}
        unique_exercises = {r.get("exercise_id") for r in rows if r.get("exercise_id")}
        unique_topics = {r.get("topic") for r in rows if r.get("topic")}
        
        passed_exercises = {r.get("exercise_id") for r in rows if r.get("result") == "pass"}
        
        total_attempts = len(rows)
        total_passed = len([r for r in rows if r.get("result") == "pass"])
        
        # Attempts to first pass per exercise
        attempts_to_first_pass = []
        for exercise_id in unique_exercises:
            exercise_rows = [r for r in rows if r.get("exercise_id") == exercise_id]
            for i, row in enumerate(exercise_rows, 1):
                if row.get("result") == "pass":
                    attempts_to_first_pass.append(i)
                    break
        
        avg_attempts_to_first_pass = (
            sum(attempts_to_first_pass) / len(attempts_to_first_pass)
            if attempts_to_first_pass
            else 0.0
        )
        
        # Error counts
        syntax_count = len([r for r in rows if r.get("error_type") == "syntax"])
        logic_count = len([r for r in rows if r.get("error_type") == "logic"])
        total_errors = syntax_count + logic_count + len([r for r in rows if r.get("error_type") in ("runtime", "timeout")])
        
        # Time metrics
        times_ms = [float(r.get("execution_time_ms") or 0) for r in rows]
        avg_time_seconds = (sum(times_ms) / len(times_ms) / 1000) if times_ms else 0.0
        
        # Error reduction: compare early vs late error rates per session in chronological order.
        # This avoids mixing unrelated attempts across sessions.
        rows_by_session: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        for row in rows:
            sid = str(row.get("session_id") or "")
            if sid:
                rows_by_session[sid].append(row)

        session_reductions: List[float] = []
        for session_rows in rows_by_session.values():
            ordered = sorted(
                session_rows,
                key=lambda r: (
                    r.get("timestamp") is None,
                    r.get("timestamp"),
                    int(r.get("attempt_number") or 0),
                ),
            )
            if not ordered:
                continue

            sample = max(1, len(ordered) // 3)
            early_attempts = ordered[:sample]
            late_attempts = ordered[-sample:]

            early_error_rate = (
                len([r for r in early_attempts if r.get("result") != "pass"]) / len(early_attempts) * 100
            )
            late_error_rate = (
                len([r for r in late_attempts if r.get("result") != "pass"]) / len(late_attempts) * 100
            )
            session_reductions.append(early_error_rate - late_error_rate)

        error_reduction = round(
            sum(session_reductions) / len(session_reductions),
            2,
        ) if session_reductions else 0.0
        
        # Improvement trajectory (attempts per exercise)
        attempts_per_exercise = []
        for exercise_id in unique_exercises:
            exercise_rows = [r for r in rows if r.get("exercise_id") == exercise_id]
            attempts_per_exercise.append(len(exercise_rows))
        
        improvement_traj = 0.0
        if len(attempts_per_exercise) >= 2:
            first_half_avg = sum(attempts_per_exercise[:len(attempts_per_exercise)//2]) / (len(attempts_per_exercise)//2 or 1)
            second_half_avg = sum(attempts_per_exercise[len(attempts_per_exercise)//2:]) / (len(attempts_per_exercise) - len(attempts_per_exercise)//2 or 1)
            improvement_traj = round(first_half_avg - second_half_avg, 2)
        
        return {
            "arm": arm_str,
            "total_sessions": len(unique_sessions),
            "total_attempts": total_attempts,
            "avg_attempts_to_first_pass": round(avg_attempts_to_first_pass, 2),
            "exercises_passed": len(passed_exercises),
            "pass_rate": round(total_passed / total_attempts * 100, 1) if total_attempts else 0.0,
            "error_reduction_rate": error_reduction,
            "avg_time_per_attempt": round(avg_time_seconds, 2),
            "syntax_error_rate": round(syntax_count / total_attempts * 100, 1) if total_attempts else 0.0,
            "logic_error_rate": round(logic_count / total_attempts * 100, 1) if total_attempts else 0.0,
            "avg_attempts_per_exercise": round(total_attempts / len(unique_exercises), 2) if unique_exercises else 0.0,
            "topic_diversity": len(unique_topics),
            "difficulty_progression": "advancing" if improvement_traj > 0.1 else "plateauing" if improvement_traj > -0.1 else "regressing",
            "improvement_trajectory": improvement_traj,
        }

    def submit_attempt(self, exercise_id: int, code: str, language: str) -> Dict[str, Any]:
        from app.data import get_track_exercises

        attempts_col = LearningEngine._db_col("attempts")
        recommend_col = LearningEngine._db_col("recommendations_log")

        language = normalize_language(language)
        track = get_track_exercises(language)
        idx = max(0, int(exercise_id) - 1)
        if idx >= len(track):
            return {
                "result": {
                    "pass_fail": "fail",
                    "error_type": "not_found",
                    "feedback": f"Exercise {exercise_id} not found",
                    "execution_time_ms": 0,
                },
                "pass_fail": "fail",
                "attempt_number": 1,
                "recommendations": [],
                "next_exercise": None,
            }

        exercise = track[idx]
        ex_doc_id = str(exercise.get("id") or f"ex{exercise_id:02d}")
        topic = str(exercise.get("topic") or "unknown")
        attempt_number = LearningEngine.next_attempt_number(attempts_col, self.session_id, ex_doc_id)
        exec_result = ExecutionEngine.run_code(code, language=exercise.get("language", language))
        eval_result = ExecutionEngine.evaluate_test_cases(exercise, exec_result)
        time_taken = float(exec_result.get("execution_time_ms") or 0) / 1000

        state = {
            "topic": exercise.get("topic"),
            "attempts": attempt_number,
            "success": eval_result.get("result") == "pass",
            "error_type": eval_result.get("error_type"),
            "time_taken": time_taken,
            "exercise_index": idx,
            "total_exercises": len(track),
            "language": language,
        }

        profile = LearningEngine.build_user_profile(attempts_col, self.session_id, language)
        next_step = LearningEngine.get_next_step(state, profile)
        recommendations = []
        arm = LearningEngine._arm_to_standard(self.context.get("experiment_arm"))
        if arm == "adaptive":
            recommendations = LearningEngine.generate_recommendation(
                state,
                topic_page_url=f"/learn/{exercise.get('topic')}?lang={language}",
                topic_quiz_url=f"/quiz/{exercise.get('topic')}?lang={language}",
                easier_exercise_url=f"/interactive-mode?lang={language}&ex={max(0, idx - 1)}",
                user_profile=profile,
            )
            LearningEngine.log_recommendations(
                recommend_col,
                session_id=self.session_id,
                user_id=self.session_id,
                mode=self.context.get("mode") or "interactive",
                experiment_arm=arm,
                exercise_id=ex_doc_id,
                topic=topic,
                recommendations=recommendations,
            )

        LearningEngine.log_attempt(
            attempts_col,
            session_id=self.session_id,
            user_id=self.session_id,
            mode=self.context.get("mode") or "interactive",
            exercise=exercise,
            attempt_number=attempt_number,
            eval_result=eval_result,
            execution_time_ms=exec_result.get("execution_time_ms", 0),
            experiment_arm=arm,
            recommendations=recommendations,
            next_step=next_step,
        )

        return {
            "result": {
                "tests_passed": 1 if eval_result.get("result") == "pass" else 0,
                "total_tests": len(eval_result.get("details") or []) or 1,
                "error_type": eval_result.get("error_type"),
                "output": exec_result.get("stdout", ""),
                "pass_fail": eval_result.get("result", "fail"),
                "feedback": eval_result.get("feedback", ""),
                "details": eval_result.get("details", []),
                "execution_time_ms": exec_result.get("execution_time_ms", 0),
            },
            "pass_fail": eval_result.get("result", "fail"),
            "attempt_number": attempt_number,
            "recommendations": recommendations,
            "next_exercise": int(next_step["next_exercise_index"]) + 1 if next_step else None,
            "next_step": next_step,
            "user_profile": profile,
        }

    def submit_quiz(self, topic: str, score: int, total: int) -> Dict[str, Any]:
        quiz_col = LearningEngine._db_col("quiz_attempts")
        result = {
            "score": score,
            "total_questions": total,
            "score_pct": round((score / total) * 100, 1) if total else 0,
            "answers": [],
        }
        LearningEngine.log_quiz_attempt(
            quiz_col,
            session_id=self.session_id,
            user_id=self.session_id,
            mode=self.context.get("mode") or "interactive",
            experiment_arm=self.context.get("experiment_arm") or "control",
            topic_id=topic,
            quiz_result=result,
        )
        return {
            "topic": topic,
            "score": score,
            "total": total,
            "percentage": result["score_pct"],
        }

    def get_user_dashboard_data(self) -> Dict[str, Any]:
        attempts_col = LearningEngine._db_col("attempts")
        quiz_col = LearningEngine._db_col("quiz_attempts")
        rec_col = LearningEngine._db_col("recommendations_log")

        attempts = list(attempts_col.find({"session_id": self.session_id})) if attempts_col is not None else []
        quizzes = list(quiz_col.find({"session_id": self.session_id})) if quiz_col is not None else []
        recs = list(rec_col.find({"session_id": self.session_id})) if rec_col is not None else []

        total_attempts = len(attempts)
        pass_attempts = sum(1 for a in attempts if a.get("result") == "pass")
        pass_rate = (pass_attempts / total_attempts * 100) if total_attempts else 0
        exercises_completed = len(set(a.get("exercise_id") for a in attempts if a.get("result") == "pass"))
        avg_quiz_score = (sum(q.get("score_pct", 0) for q in quizzes) / len(quizzes)) if quizzes else 0

        return {
            "total_attempts": total_attempts,
            "pass_rate": round(pass_rate, 1),
            "exercises_completed": exercises_completed,
            "quizzes_taken": len(quizzes),
            "average_quiz_score": round(avg_quiz_score, 1),
            "recommendations_seen": len(recs),
            "experiment_arm": LearningEngine._arm_to_standard(self.context.get("experiment_arm")),
            "mode": LearningEngine._normalize_mode(self.context.get("mode") or "interactive"),
            # Backward-compat keys while migrating routes/UI
            "group_type": LearningEngine._normalize_mode(self.context.get("mode") or "interactive"),
            "experiment_group": LearningEngine._arm_to_legacy(self.context.get("experiment_arm")),
            "user_mode": LearningEngine._normalize_mode(self.context.get("mode") or "interactive"),
        }
