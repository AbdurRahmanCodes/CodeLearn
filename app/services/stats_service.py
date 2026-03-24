"""Stats computation helpers used by stats API routes."""

from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Tuple

from app.services.learning_engine import LearningEngine


class StatsService:
    """Business logic for research and analytics computations."""

    @staticmethod
    def build_research_snapshot(attempts_col, quiz_col, recommendations_col) -> Dict[str, Any]:
        snapshot: Dict[str, Any] = {
            "dataset": {
                "participants": 0,
                "attempts": 0,
                "quiz_attempts": 0,
                "recommendation_events": 0,
            },
            "primary_question": "Do activity-based recommendations improve beginner programming outcomes compared with a non-adaptive condition?",
            "hypotheses": [],
            "key_findings": [],
            "notes": [],
        }

        if attempts_col is None:
            snapshot["notes"].append("Database not connected.")
            return snapshot

        snapshot["dataset"]["participants"] = len(attempts_col.distinct("session_id"))
        snapshot["dataset"]["attempts"] = attempts_col.count_documents({})
        snapshot["dataset"]["quiz_attempts"] = quiz_col.count_documents({}) if quiz_col is not None else 0
        snapshot["dataset"]["recommendation_events"] = recommendations_col.count_documents({}) if recommendations_col is not None else 0

        exp_rows = list(attempts_col.aggregate([
            {"$group": {
                "_id": {"$ifNull": ["$experiment_arm", "$experiment_group"]},
                "attempts": {"$sum": 1},
                "passes": {"$sum": {"$cond": [{"$eq": ["$result", "pass"]}, 1, 0]}},
                "avg_attempt_number": {"$avg": "$attempt_number"},
            }}
        ]))
        exp_map = {r.get("_id", "unknown"): r for r in exp_rows}
        control = exp_map.get("control", exp_map.get("A_control", {"attempts": 0, "passes": 0, "avg_attempt_number": 0}))
        adaptive = exp_map.get("adaptive", exp_map.get("B_adaptive", {"attempts": 0, "passes": 0, "avg_attempt_number": 0}))
        control_pass = round((control["passes"] / control["attempts"]) * 100, 1) if control["attempts"] else 0
        adaptive_pass = round((adaptive["passes"] / adaptive["attempts"]) * 100, 1) if adaptive["attempts"] else 0
        control_avg_attempt = round(control.get("avg_attempt_number", 0), 2)
        adaptive_avg_attempt = round(adaptive.get("avg_attempt_number", 0), 2)

        snapshot["hypotheses"].append({
            "id": "H1",
            "statement": "Adaptive recommendations improve pass rate versus the control condition.",
            "status": "supported" if adaptive_pass > control_pass else "not_supported",
            "evidence": f"Adaptive pass rate {adaptive_pass}% vs control {control_pass}%.",
        })
        snapshot["hypotheses"].append({
            "id": "H2",
            "statement": "Adaptive recommendations reduce the average attempt number needed to progress.",
            "status": "supported" if adaptive_avg_attempt and adaptive_avg_attempt < control_avg_attempt else "not_supported",
            "evidence": f"Adaptive average attempt number {adaptive_avg_attempt} vs control {control_avg_attempt}.",
        })

        snapshot["key_findings"].append(
            f"Adaptive-group pass rate is {adaptive_pass}% compared with {control_pass}% in the control group."
        )
        snapshot["notes"].append("These interpretations are descriptive and should be supported with formal statistical tests in the dissertation chapter.")
        return snapshot

    @staticmethod
    def build_summary(attempts_col) -> Dict[str, Any]:
        total_attempts = attempts_col.count_documents({})
        all_sessions = attempts_col.distinct("session_id")
        static_sess = list({
            *attempts_col.distinct("session_id", {"mode": "static"}),
            *attempts_col.distinct("session_id", {"group_type": "static"}),
        })
        interactive_sess = list({
            *attempts_col.distinct("session_id", {"mode": "interactive"}),
            *attempts_col.distinct("session_id", {"group_type": "interactive"}),
        })
        control_sess = list({
            *attempts_col.distinct("session_id", {"experiment_arm": "control"}),
            *attempts_col.distinct("session_id", {"experiment_group": "A_control"}),
        })
        adaptive_sess = list({
            *attempts_col.distinct("session_id", {"experiment_arm": "adaptive"}),
            *attempts_col.distinct("session_id", {"experiment_group": "B_adaptive"}),
        })
        passes = attempts_col.count_documents({"result": "pass"})
        pass_rate = round(passes / total_attempts * 100, 1) if total_attempts > 0 else 0
        return {
            "total_participants": len(all_sessions),
            "static_participants": len(static_sess),
            "interactive_participants": len(interactive_sess),
            "control_participants": len(control_sess),
            "adaptive_participants": len(adaptive_sess),
            "total_attempts": total_attempts,
            "overall_pass_rate": pass_rate,
        }

    @staticmethod
    def build_pass_rate_rows(attempts_col) -> List[Dict[str, Any]]:
        rows = list(attempts_col.aggregate([
            {"$group": {
                "_id": {"$ifNull": ["$mode", "$group_type"]},
                "total": {"$sum": 1},
                "passes": {"$sum": {"$cond": [{"$eq": ["$result", "pass"]}, 1, 0]}},
            }}
        ]))
        result = []
        for row in rows:
            total = row.get("total", 0)
            passes = row.get("passes", 0)
            result.append({
                "group": row.get("_id"),
                "total": total,
                "passes": passes,
                "pass_rate": round((passes / total) * 100, 1) if total > 0 else 0,
            })
        return result

    @staticmethod
    def build_attempt_rows(attempts_col) -> List[Dict[str, Any]]:
        rows = list(attempts_col.aggregate([
            {"$group": {
                "_id": {
                    "exercise_id": {"$ifNull": ["$exercise_id", "unknown"]},
                    "group_type": {"$ifNull": ["$mode", {"$ifNull": ["$group_type", "unknown"]}]},
                },
                "avg_attempts": {"$avg": "$attempt_number"},
                "count": {"$sum": 1},
            }},
            {"$sort": {"_id.exercise_id": 1}},
        ]))
        result = []
        for row in rows:
            rid = row.get("_id", {})
            result.append({
                "exercise_id": rid.get("exercise_id", "unknown"),
                "group_type": rid.get("group_type", "unknown"),
                "avg_attempts": round(row.get("avg_attempts", 0) or 0, 2),
                "count": row.get("count", 0),
            })
        return result

    @staticmethod
    def build_error_rows(attempts_col) -> List[Dict[str, Any]]:
        rows = list(attempts_col.aggregate([
            {"$match": {"error_type": {"$ne": None}}},
            {"$group": {"_id": "$error_type", "count": {"$sum": 1}}},
            {"$sort": {"count": -1}},
        ]))
        return [{"error_type": row.get("_id"), "count": row.get("count", 0)} for row in rows]

    @staticmethod
    def build_learning_curve_rows(attempts_col) -> List[Dict[str, Any]]:
        rows = list(attempts_col.aggregate([
            {"$match": {"result": "pass"}},
            {"$group": {
                "_id": {"session_id": "$session_id", "exercise_id": "$exercise_id", "group_type": {"$ifNull": ["$mode", "$group_type"]}},
                "first_pass": {"$min": "$attempt_number"},
            }},
            {"$group": {
                "_id": {"exercise_id": "$_id.exercise_id", "group_type": "$_id.group_type"},
                "avg_first_pass": {"$avg": "$first_pass"},
                "sessions": {"$sum": 1},
            }},
            {"$sort": {"_id.exercise_id": 1}},
        ]))
        return [
            {
                "exercise_id": row["_id"]["exercise_id"],
                "group_type": row["_id"]["group_type"],
                "avg_first_pass": round(row["avg_first_pass"], 2),
                "sessions": row["sessions"],
            }
            for row in rows
        ]

    @staticmethod
    def build_language_difficulty_rows(attempts_col) -> List[Dict[str, Any]]:
        rows = list(attempts_col.aggregate([
            {"$group": {
                "_id": {"$ifNull": ["$language", "$programming_language"]},
                "total": {"$sum": 1},
                "passes": {"$sum": {"$cond": [{"$eq": ["$result", "pass"]}, 1, 0]}},
                "syntax_errors": {"$sum": {"$cond": [{"$eq": ["$error_type", "syntax"]}, 1, 0]}},
                "any_errors": {"$sum": {"$cond": [{"$ne": ["$error_type", None]}, 1, 0]}},
                "avg_execution_ms": {"$avg": "$execution_time_ms"},
            }},
            {"$sort": {"_id": 1}},
        ]))
        result = []
        for row in rows:
            total = row.get("total", 0)
            if total == 0:
                continue
            result.append({
                "language": row.get("_id", "unknown"),
                "pass_rate": round((row.get("passes", 0) / total) * 100, 1),
                "syntax_error_rate": round((row.get("syntax_errors", 0) / total) * 100, 1),
                "error_rate": round((row.get("any_errors", 0) / total) * 100, 1),
                "avg_time_s": round(float(row.get("avg_execution_ms", 0) or 0) / 1000, 3),
                "attempts": total,
            })
        return result

    @staticmethod
    def build_topic_difficulty_rows(attempts_col) -> List[Dict[str, Any]]:
        """Compute topic-level failure rates for difficulty ranking."""
        rows = list(attempts_col.aggregate([
            {"$group": {
                "_id": "$topic",
                "total": {"$sum": 1},
                "failed": {"$sum": {"$cond": [{"$eq": ["$result", "fail"]}, 1, 0]}},
                "passes": {"$sum": {"$cond": [{"$eq": ["$result", "pass"]}, 1, 0]}},
            }},
            {"$sort": {"_id": 1}},
        ]))
        return [
            {
                "topic": row.get("_id", "unknown"),
                "total_attempts": row.get("total", 0),
                "failed_attempts": row.get("failed", 0),
                "passed_attempts": row.get("passes", 0),
                "failure_rate": round((row.get("failed", 0) / max(row.get("total", 1), 1)) * 100, 1),
            }
            for row in rows if row.get("_id")
        ]

    @staticmethod
    def build_recommendation_impact_rows(attempts_col) -> List[Dict[str, Any]]:
        """Compare success before and after recommendation trigger by session/topic."""
        rows = list(attempts_col.find(
            {},
            {
                "_id": 0,
                "session_id": 1,
                "topic": 1,
                "attempt_number": 1,
                "result": 1,
                "recommendation_count": 1,
            },
        ).sort([("session_id", 1), ("topic", 1), ("attempt_number", 1)]))

        if not rows:
            return []

        topic_stats: Dict[str, Dict[str, int]] = {}
        grouped: Dict[Tuple[str, str], List[Dict[str, Any]]] = {}
        for row in rows:
            key = (row.get("session_id", ""), row.get("topic", ""))
            grouped.setdefault(key, []).append(row)

        for (_session_id, topic), attempts in grouped.items():
            stats = topic_stats.setdefault(topic or "unknown", {
                "before_total": 0,
                "before_success": 0,
                "after_total": 0,
                "after_success": 0,
            })

            triggered = False
            for att in attempts:
                success = att.get("result") == "pass"
                if not triggered:
                    stats["before_total"] += 1
                    if success:
                        stats["before_success"] += 1
                else:
                    stats["after_total"] += 1
                    if success:
                        stats["after_success"] += 1

                if int(att.get("recommendation_count", 0) or 0) > 0:
                    triggered = True

        result = []
        for topic, stats in topic_stats.items():
            before_total = max(stats["before_total"], 1)
            after_total = max(stats["after_total"], 1)
            before_rate = round((stats["before_success"] / before_total) * 100, 1)
            after_rate = round((stats["after_success"] / after_total) * 100, 1)
            result.append({
                "topic": topic,
                "before_success_rate": before_rate,
                "after_success_rate": after_rate,
                "delta": round(after_rate - before_rate, 1),
                "before_samples": stats["before_total"],
                "after_samples": stats["after_total"],
            })
        result.sort(key=lambda r: r["topic"])
        return result

    @staticmethod
    def build_topic_success_rows(attempts_col) -> List[Dict[str, Any]]:
        rows = list(attempts_col.aggregate([
            {"$group": {
                "_id": "$topic",
                "total": {"$sum": 1},
                "passes": {"$sum": {"$cond": [{"$eq": ["$result", "pass"]}, 1, 0]}},
            }},
            {"$sort": {"_id": 1}},
        ]))
        return [
            {
                "topic": row.get("_id", "unknown"),
                "success_rate": round((row["passes"] / row["total"]) * 100, 1) if row.get("total") else 0,
                "attempts": row.get("total", 0),
            }
            for row in rows if row.get("_id")
        ]

    @staticmethod
    def build_quiz_performance_rows(attempts_col, quiz_col) -> List[Dict[str, Any]]:
        quiz_rows = list(quiz_col.aggregate([
            {"$group": {
                "_id": {"session_id": "$session_id", "topic": "$topic"},
                "score_pct": {"$max": "$score_pct"},
            }},
        ]))

        result = []
        for row in quiz_rows:
            sid = row["_id"]["session_id"]
            topic = row["_id"]["topic"]
            attempts = attempts_col.count_documents({"session_id": sid, "topic": topic})
            passes = attempts_col.count_documents({"session_id": sid, "topic": topic, "result": "pass"})
            if attempts == 0:
                continue
            result.append({
                "topic": topic,
                "quiz_score_pct": row.get("score_pct", 0),
                "coding_pass_rate": round((passes / attempts) * 100, 1),
            })
        return result

    @staticmethod
    def build_recommendation_effectiveness_rows(attempts_col) -> List[Dict[str, Any]]:
        rows = list(attempts_col.aggregate([
            {"$group": {
                "_id": {"$ifNull": ["$experiment_arm", "$experiment_group"]},
                "attempts": {"$sum": 1},
                "passes": {"$sum": {"$cond": [{"$eq": ["$result", "pass"]}, 1, 0]}},
                "avg_attempt_no": {"$avg": "$attempt_number"},
                "recommendation_hits": {"$sum": "$recommendation_count"},
            }},
            {"$sort": {"_id": 1}},
        ]))
        return [
            {
                "experiment_group": row.get("_id", "unknown"),
                "attempts": row.get("attempts", 0),
                "pass_rate": round((row.get("passes", 0) / max(row.get("attempts", 1), 1)) * 100, 1),
                "avg_attempt_number": round(row.get("avg_attempt_no", 0), 2),
                "recommendation_hits": row.get("recommendation_hits", 0),
            }
            for row in rows
        ]

    @staticmethod
    def build_session_quality(attempts_col) -> Dict[str, Any]:
        rows = list(attempts_col.aggregate([
            {"$group": {
                "_id": "$session_id",
                "attempts": {"$sum": 1},
                "first_ts": {"$min": "$timestamp"},
                "last_ts": {"$max": "$timestamp"},
            }},
            {"$addFields": {
                "duration_s": {"$divide": [{"$subtract": ["$last_ts", "$first_ts"]}, 1000]},
                "is_valid": {"$and": [{"$gt": ["$attempts", 1]}, {"$gt": [{"$divide": [{"$subtract": ["$last_ts", "$first_ts"]}, 1000]}, 10]}]},
            }},
            {"$group": {
                "_id": None,
                "total": {"$sum": 1},
                "valid": {"$sum": {"$cond": ["$is_valid", 1, 0]}},
                "invalid": {"$sum": {"$cond": ["$is_valid", 0, 1]}},
            }},
        ]))
        if not rows:
            return {"total": 0, "valid": 0, "invalid": 0, "validity_rate": 0}
        row = rows[0]
        return {
            "total": row["total"],
            "valid": row["valid"],
            "invalid": row["invalid"],
            "validity_rate": round(row["valid"] / row["total"] * 100, 1) if row["total"] > 0 else 0,
        }

    @staticmethod
    def build_persistence_rows(attempts_col) -> List[Dict[str, Any]]:
        rows = list(attempts_col.aggregate([
            {"$group": {
                "_id": {
                    "session_id": {"$ifNull": ["$session_id", "unknown"]},
                    "exercise_id": {"$ifNull": ["$exercise_id", "unknown"]},
                    "group_type": {"$ifNull": ["$mode", {"$ifNull": ["$group_type", "unknown"]}]},
                },
                "total_attempts": {"$sum": 1},
                "passes": {"$sum": {"$cond": [{"$eq": ["$result", "pass"]}, 1, 0]}},
            }},
            {"$match": {"passes": 0, "total_attempts": {"$gte": 1}}},
            {"$group": {
                "_id": {"exercise_id": "$_id.exercise_id", "group_type": "$_id.group_type"},
                "avg_attempts": {"$avg": "$total_attempts"},
                "engaged_sessions": {"$sum": 1},
            }},
            {"$sort": {"_id.exercise_id": 1}},
        ]))
        result = []
        for row in rows:
            rid = row.get("_id", {})
            result.append({
                "exercise_id": rid.get("exercise_id", "unknown"),
                "group_type": rid.get("group_type", "unknown"),
                "avg_attempts": round(row.get("avg_attempts", 0) or 0, 2),
                "engaged_sessions": row.get("engaged_sessions", 0),
            })
        return result

    @staticmethod
    def get_valid_session_ids(attempts_col) -> List[str]:
        if attempts_col is None:
            return []
        try:
            rows = list(attempts_col.aggregate([
                {"$group": {
                    "_id": "$session_id",
                    "attempts": {"$sum": 1},
                    "first_ts": {"$min": "$timestamp"},
                    "last_ts": {"$max": "$timestamp"},
                }},
                {"$addFields": {
                    "duration_s": {"$divide": [{"$subtract": ["$last_ts", "$first_ts"]}, 1000]}
                }},
                {"$match": {"attempts": {"$gt": 1}, "duration_s": {"$gt": 10}}},
            ]))
            return [r["_id"] for r in rows]
        except Exception:
            return []

    @staticmethod
    def build_time_to_pass_rows(attempts_col) -> List[Dict[str, Any]]:
        first_attempt_rows = list(attempts_col.aggregate([
            {"$group": {
                "_id": {"session_id": "$session_id", "exercise_id": "$exercise_id", "group_type": {"$ifNull": ["$mode", "$group_type"]}},
                "first_ts": {"$min": "$timestamp"},
            }},
        ]))
        first_map = {f"{r['_id']['session_id']}__{r['_id']['exercise_id']}": r for r in first_attempt_rows}

        first_pass_rows = list(attempts_col.aggregate([
            {"$match": {"result": "pass"}},
            {"$group": {
                "_id": {"session_id": "$session_id", "exercise_id": "$exercise_id", "group_type": {"$ifNull": ["$mode", "$group_type"]}},
                "pass_ts": {"$min": "$timestamp"},
            }},
        ]))

        buckets: Dict[Tuple[Any, Any], Dict[str, Any]] = defaultdict(lambda: {"times": [], "first_pass": 0})
        for row in first_pass_rows:
            key = f"{row['_id']['session_id']}__{row['_id']['exercise_id']}"
            bkey = (row["_id"]["exercise_id"], row["_id"]["group_type"])
            if key in first_map:
                delta = (row["pass_ts"] - first_map[key]["first_ts"]).total_seconds()
                if delta > 0:
                    buckets[bkey]["times"].append(delta)
                else:
                    buckets[bkey]["first_pass"] += 1

        result = []
        for (ex_id, grp), data in buckets.items():
            times = data.get("times", [])
            first_count = int(data.get("first_pass", 0))
            total_count = len(times) + first_count
            if times:
                avg_secs = round(sum(times) / len(times), 1)
            elif first_count > 0:
                avg_secs = 5.0
            else:
                continue
            result.append({
                "exercise_id": ex_id,
                "group_type": grp,
                "avg_time_seconds": avg_secs,
                "count": total_count,
                "first_attempt_passes": first_count,
            })
        result.sort(key=lambda x: x["exercise_id"])
        return result

    @staticmethod
    def build_error_transition_rows(attempts_col, valid_ids: List[str]) -> List[Dict[str, Any]]:
        if not valid_ids:
            return []

        attempts_raw = list(attempts_col.find(
            {"session_id": {"$in": valid_ids}},
            {"session_id": 1, "exercise_id": 1, "attempt_number": 1, "error_type": 1, "result": 1, "_id": 0},
        ).sort([("session_id", 1), ("exercise_id", 1), ("attempt_number", 1)]))

        transitions: Dict[str, int] = {}
        prev_key = None
        prev_label = None
        for att in attempts_raw:
            curr_key = f"{att['session_id']}__{att['exercise_id']}"
            curr_label = att.get("error_type") or ("pass" if att["result"] == "pass" else "none")
            if curr_key == prev_key and prev_label is not None and curr_label != prev_label:
                t_key = f"{prev_label}->{curr_label}"
                transitions[t_key] = transitions.get(t_key, 0) + 1
            prev_key = curr_key
            prev_label = curr_label

        return sorted(
            [{"from": k.split("->")[0], "to": k.split("->")[1], "count": v} for k, v in transitions.items()],
            key=lambda x: -int(x.get("count", 0)),
        )[:20]

    @staticmethod
    def _iso(value: Any) -> str:
        return value.isoformat() if hasattr(value, "isoformat") else ""

    @staticmethod
    def build_session_drilldown_index(
        attempts_col,
        limit: int = 40,
        filters: Dict[str, Any] | None = None,
    ) -> List[Dict[str, Any]]:
        rows = StatsService._build_session_drilldown_rows(attempts_col, filters=filters)
        safe_limit = max(1, min(limit, 500))
        return rows[:safe_limit]

    @staticmethod
    def _build_session_drilldown_rows(
        attempts_col,
        filters: Dict[str, Any] | None = None,
    ) -> List[Dict[str, Any]]:
        filters = filters or {}
        match_stage: Dict[str, Any] = {}

        group_type = filters.get("group_type")
        if group_type in {"static", "interactive"}:
            match_stage["group_type"] = group_type

        experiment_group = filters.get("experiment_group")
        if experiment_group in {"A_control", "B_adaptive"}:
            match_stage["experiment_group"] = experiment_group

        since_hours = filters.get("since_hours")
        if isinstance(since_hours, (int, float)) and since_hours > 0:
            cutoff = datetime.now(timezone.utc) - timedelta(hours=float(since_hours))
            match_stage["timestamp"] = {"$gte": cutoff}

        pipeline: List[Dict[str, Any]] = []
        if match_stage:
            pipeline.append({"$match": match_stage})

        pipeline.extend([
            {"$group": {
                "_id": "$session_id",
                "attempts": {"$sum": 1},
                "passes": {"$sum": {"$cond": [{"$eq": ["$result", "pass"]}, 1, 0]}},
                "first_ts": {"$min": "$timestamp"},
                "last_ts": {"$max": "$timestamp"},
                "group_type": {"$last": "$group_type"},
                "experiment_group": {"$last": "$experiment_group"},
            }},
            {"$addFields": {
                "duration_s": {"$divide": [{"$subtract": ["$last_ts", "$first_ts"]}, 1000]}
            }},
            {"$sort": {"last_ts": -1}},
        ])
        rows = list(attempts_col.aggregate(pipeline))

        min_pass_rate = filters.get("min_pass_rate")
        max_pass_rate = filters.get("max_pass_rate")

        result: List[Dict[str, Any]] = []
        for row in rows:
            if not row.get("_id"):
                continue
            pass_rate = round((row.get("passes", 0) / max(row.get("attempts", 1), 1)) * 100, 1)
            if isinstance(min_pass_rate, (int, float)) and pass_rate < float(min_pass_rate):
                continue
            if isinstance(max_pass_rate, (int, float)) and pass_rate > float(max_pass_rate):
                continue

            result.append({
                "session_id": row.get("_id"),
                "attempts": row.get("attempts", 0),
                "passes": row.get("passes", 0),
                "pass_rate": pass_rate,
                "group_type": row.get("group_type", "unknown"),
                "experiment_group": row.get("experiment_group", "unknown"),
                "duration_s": round(float(row.get("duration_s", 0) or 0), 1),
                "first_ts": StatsService._iso(row.get("first_ts")),
                "last_ts": StatsService._iso(row.get("last_ts")),
            })

        return result

    @staticmethod
    def build_session_drilldown_index_page(
        attempts_col,
        limit: int = 40,
        page: int = 1,
        filters: Dict[str, Any] | None = None,
    ) -> Dict[str, Any]:
        rows = StatsService._build_session_drilldown_rows(attempts_col, filters=filters)
        safe_limit = max(1, min(limit, 80))
        safe_page = max(1, page)
        total = len(rows)
        total_pages = max(1, (total + safe_limit - 1) // safe_limit)
        if safe_page > total_pages:
            safe_page = total_pages
        start = (safe_page - 1) * safe_limit
        end = start + safe_limit
        return {
            "sessions": rows[start:end],
            "page": safe_page,
            "limit": safe_limit,
            "total": total,
            "total_pages": total_pages,
            "has_prev": safe_page > 1,
            "has_next": safe_page < total_pages,
        }

    @staticmethod
    def build_session_drilldown_detail(attempts_col, quiz_col, recommendations_col, session_id: str) -> Dict[str, Any]:
        attempts = list(attempts_col.find(
            {"session_id": session_id},
            {
                "_id": 0,
                "session_id": 1,
                "exercise_id": 1,
                "topic": 1,
                "attempt_number": 1,
                "result": 1,
                "error_type": 1,
                "group_type": 1,
                "experiment_group": 1,
                "recommendation_count": 1,
                "timestamp": 1,
            },
        ).sort([("timestamp", 1), ("exercise_id", 1), ("attempt_number", 1)]))

        quizzes = []
        if quiz_col is not None:
            quizzes = list(quiz_col.find(
                {"session_id": session_id},
                {"_id": 0, "topic": 1, "score": 1, "score_pct": 1, "total_questions": 1, "timestamp": 1},
            ).sort([("timestamp", 1)]))

        recommendations = []
        if recommendations_col is not None:
            recommendations = list(recommendations_col.find(
                {"session_id": session_id},
                {"_id": 0, "topic": 1, "recommendation_type": 1, "title": 1, "reason": 1, "timestamp": 1},
            ).sort([("timestamp", 1)]))

        for row in attempts:
            row["timestamp"] = StatsService._iso(row.get("timestamp"))
        for row in quizzes:
            row["score_pct"] = row.get("score_pct", row.get("score_percentage", 0))
            row["total_questions"] = row.get("total_questions", row.get("total", 0))
            row["timestamp"] = StatsService._iso(row.get("timestamp"))
        for row in recommendations:
            row["timestamp"] = StatsService._iso(row.get("timestamp"))

        passes = sum(1 for row in attempts if row.get("result") == "pass")
        recommendations_shown = sum(int(row.get("recommendation_count", 0) or 0) for row in attempts)
        timestamps = [row.get("timestamp") for row in attempts if row.get("timestamp")]

        return {
            "session": {
                "session_id": session_id,
                "attempts": len(attempts),
                "passes": passes,
                "pass_rate": round((passes / max(len(attempts), 1)) * 100, 1) if attempts else 0,
                "quiz_attempts": len(quizzes),
                "recommendation_events": len(recommendations),
                "recommendations_shown": recommendations_shown,
                "first_ts": timestamps[0] if timestamps else "",
                "last_ts": timestamps[-1] if timestamps else "",
            },
            "attempts": attempts,
            "quizzes": quizzes,
            "recommendations": recommendations,
        }

    @staticmethod
    def build_session_drilldown_event_rows(detail: Dict[str, Any]) -> List[Dict[str, Any]]:
        session = detail.get("session", {})
        sid = session.get("session_id", "")
        rows: List[Dict[str, Any]] = []

        for item in detail.get("attempts", []):
            rows.append({
                "session_id": sid,
                "event_type": "attempt",
                "timestamp": item.get("timestamp", ""),
                "exercise_id": item.get("exercise_id", ""),
                "topic": item.get("topic", ""),
                "attempt_number": item.get("attempt_number", 0),
                "result": item.get("result", ""),
                "error_type": item.get("error_type", ""),
                "score": "",
                "score_pct": "",
                "recommendation_type": "",
                "title": "",
                "reason": "",
            })

        for item in detail.get("quizzes", []):
            rows.append({
                "session_id": sid,
                "event_type": "quiz",
                "timestamp": item.get("timestamp", ""),
                "exercise_id": "",
                "topic": item.get("topic", ""),
                "attempt_number": "",
                "result": "",
                "error_type": "",
                "score": item.get("score", 0),
                "score_pct": item.get("score_pct", 0),
                "recommendation_type": "",
                "title": "",
                "reason": "",
            })

        for item in detail.get("recommendations", []):
            rows.append({
                "session_id": sid,
                "event_type": "recommendation",
                "timestamp": item.get("timestamp", ""),
                "exercise_id": "",
                "topic": item.get("topic", ""),
                "attempt_number": "",
                "result": "",
                "error_type": "",
                "score": "",
                "score_pct": "",
                "recommendation_type": item.get("recommendation_type", ""),
                "title": item.get("title", ""),
                "reason": item.get("reason", ""),
            })

        rows.sort(key=lambda r: str(r.get("timestamp", "")))
        return rows

    @staticmethod
    def no_data_series() -> Dict[str, List[Any]]:
        return {"labels": ["No Data"], "values": [0]}

    @staticmethod
    def _safe_arm(value: Any) -> str:
        return LearningEngine._arm_to_standard(str(value or ""))

    @staticmethod
    def _to_seconds(value: Any) -> float:
        try:
            return float(value or 0.0)
        except (TypeError, ValueError):
            return 0.0

    @staticmethod
    def _time_to_first_pass_by_arm(attempts_col, arm: str) -> float:
        rows = list(
            attempts_col.find(
                {"experiment_arm": arm},
                {"session_id": 1, "exercise_id": 1, "timestamp": 1, "result": 1, "_id": 0},
            ).sort([("session_id", 1), ("exercise_id", 1), ("timestamp", 1)])
        )
        grouped: Dict[Tuple[str, str], List[Dict[str, Any]]] = defaultdict(list)
        for row in rows:
            sid = str(row.get("session_id") or "")
            ex = str(row.get("exercise_id") or "")
            if sid and ex:
                grouped[(sid, ex)].append(row)

        deltas: List[float] = []
        for items in grouped.values():
            start = next((r.get("timestamp") for r in items if r.get("timestamp")), None)
            first_pass = next((r.get("timestamp") for r in items if r.get("result") == "pass" and r.get("timestamp")), None)
            if start and first_pass:
                delta = (first_pass - start).total_seconds()
                deltas.append(max(0.0, float(delta)))
        if not deltas:
            return 0.0
        return round(sum(deltas) / len(deltas), 2)

    @staticmethod
    def build_dashboard_overview(attempts_col) -> Dict[str, Any]:
        if attempts_col is None:
            return {
                "total_participants": 0,
                "total_attempts": 0,
                "control_group_size": 0,
                "adaptive_group_size": 0,
                "overall_pass_rate": 0.0,
                "avg_attempts_to_first_pass_control": 0.0,
                "avg_attempts_to_first_pass_adaptive": 0.0,
            }

        summary = StatsService.build_summary(attempts_col)
        control_metrics = LearningEngine.compute_group_metrics(attempts_col, "control")
        adaptive_metrics = LearningEngine.compute_group_metrics(attempts_col, "adaptive")
        return {
            "total_participants": int(summary.get("total_participants", 0)),
            "total_attempts": int(summary.get("total_attempts", 0)),
            "control_group_size": int(summary.get("control_participants", 0)),
            "adaptive_group_size": int(summary.get("adaptive_participants", 0)),
            "overall_pass_rate": float(summary.get("overall_pass_rate", 0.0)),
            "avg_attempts_to_first_pass_control": float(control_metrics.get("avg_attempts_to_first_pass", 0.0)),
            "avg_attempts_to_first_pass_adaptive": float(adaptive_metrics.get("avg_attempts_to_first_pass", 0.0)),
        }

    @staticmethod
    def build_core_results(attempts_col) -> Dict[str, Any]:
        if attempts_col is None:
            nd = StatsService.no_data_series()
            return {
                "pass_rate": nd,
                "attempts_to_first_pass": nd,
                "time_to_first_pass": nd,
                "improvement_rate": nd,
                "error_reduction_rate": nd,
            }

        control = LearningEngine.compute_group_metrics(attempts_col, "control")
        adaptive = LearningEngine.compute_group_metrics(attempts_col, "adaptive")
        labels = ["Control", "Adaptive"]

        c_time = StatsService._time_to_first_pass_by_arm(attempts_col, "control")
        a_time = StatsService._time_to_first_pass_by_arm(attempts_col, "adaptive")

        return {
            "pass_rate": {
                "labels": labels,
                "values": [float(control.get("pass_rate", 0.0)), float(adaptive.get("pass_rate", 0.0))],
            },
            "attempts_to_first_pass": {
                "labels": labels,
                "values": [
                    float(control.get("avg_attempts_to_first_pass", 0.0)),
                    float(adaptive.get("avg_attempts_to_first_pass", 0.0)),
                ],
            },
            "time_to_first_pass": {
                "labels": labels,
                "values": [c_time, a_time],
            },
            "improvement_rate": {
                "labels": labels,
                "values": [
                    float(control.get("improvement_trajectory", 0.0)),
                    float(adaptive.get("improvement_trajectory", 0.0)),
                ],
            },
            "error_reduction_rate": {
                "labels": labels,
                "values": [
                    float(control.get("error_reduction_rate", 0.0)),
                    float(adaptive.get("error_reduction_rate", 0.0)),
                ],
            },
        }

    @staticmethod
    def build_behavior_results(attempts_col) -> Dict[str, Any]:
        if attempts_col is None:
            nd = StatsService.no_data_series()
            return {
                "error_distribution": nd,
                "topic_success": nd,
                "language_difficulty": {"labels": ["No Data"], "pass_rate": [0], "syntax_error_rate": [0]},
            }

        errors = StatsService.build_error_rows(attempts_col)
        topics = StatsService.build_topic_success_rows(attempts_col)
        langs = StatsService.build_language_difficulty_rows(attempts_col)

        error_distribution = {
            "labels": [r.get("error_type", "unknown").title() for r in errors],
            "values": [int(r.get("count", 0)) for r in errors],
        } if errors else StatsService.no_data_series()

        topic_success = {
            "labels": [str(r.get("topic", "unknown")).title() for r in topics],
            "values": [float(r.get("success_rate", 0.0)) for r in topics],
        } if topics else StatsService.no_data_series()

        if langs:
            language_difficulty = {
                "labels": [str(r.get("language", "unknown")).title() for r in langs],
                "pass_rate": [float(r.get("pass_rate", 0.0)) for r in langs],
                "syntax_error_rate": [float(r.get("syntax_error_rate", 0.0)) for r in langs],
            }
        else:
            language_difficulty = {"labels": ["No Data"], "pass_rate": [0], "syntax_error_rate": [0]}

        return {
            "error_distribution": error_distribution,
            "topic_success": topic_success,
            "language_difficulty": language_difficulty,
        }

    @staticmethod
    def build_adaptivity_results(attempts_col, recommendations_col) -> Dict[str, Any]:
        if attempts_col is None:
            nd = StatsService.no_data_series()
            return {
                "recommendation_effectiveness": nd,
                "adaptive_actions": nd,
                "recommendation_intensity": nd,
            }

        rec_effect_rows = StatsService.build_recommendation_effectiveness_rows(attempts_col)
        if rec_effect_rows:
            rec_effect = {
                "labels": ["Control", "Adaptive"],
                "values": [0.0, 0.0],
            }
            for row in rec_effect_rows:
                arm = StatsService._safe_arm(row.get("experiment_group"))
                if arm == "control":
                    rec_effect["values"][0] = float(row.get("pass_rate", 0.0))
                else:
                    rec_effect["values"][1] = float(row.get("pass_rate", 0.0))
        else:
            rec_effect = StatsService.no_data_series()

        action_rows = list(
            attempts_col.aggregate([
                {"$match": {
                    "$or": [
                        {"experiment_arm": "adaptive"},
                        {"experiment_group": "B_adaptive"},
                    ],
                    "next_step.action": {"$ne": None},
                }},
                {"$group": {"_id": "$next_step.action", "count": {"$sum": 1}}},
            ])
        )
        action_map = {str(r.get("_id") or ""): int(r.get("count", 0)) for r in action_rows}
        adaptive_actions = {
            "labels": ["Easier", "Same", "Harder"],
            "values": [
                action_map.get("easier_level", 0) + action_map.get("targeted_remediation", 0),
                action_map.get("same_level", 0),
                action_map.get("harder_level", 0) + action_map.get("topic_advance", 0),
            ],
        }
        if sum(adaptive_actions["values"]) == 0:
            adaptive_actions = StatsService.no_data_series()

        intensity_rows = []
        if recommendations_col is not None:
            intensity_rows = list(
                recommendations_col.aggregate([
                    {"$match": {
                        "$or": [
                            {"experiment_arm": "adaptive"},
                            {"experiment_group": "B_adaptive"},
                        ],
                        "intensity": {"$ne": None},
                    }},
                    {"$group": {"_id": "$intensity", "count": {"$sum": 1}}},
                ])
            )
        intensity_map = {str(r.get("_id") or ""): int(r.get("count", 0)) for r in intensity_rows}
        recommendation_intensity = {
            "labels": ["Light", "Medium", "Heavy"],
            "values": [intensity_map.get("light", 0), intensity_map.get("medium", 0), intensity_map.get("heavy", 0)],
        }
        if sum(recommendation_intensity["values"]) == 0:
            recommendation_intensity = StatsService.no_data_series()

        return {
            "recommendation_effectiveness": rec_effect,
            "adaptive_actions": adaptive_actions,
            "recommendation_intensity": recommendation_intensity,
        }
