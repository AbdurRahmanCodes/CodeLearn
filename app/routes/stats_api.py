"""
Research stats API routes migrated from legacy monolith.
"""

from collections import defaultdict

from flask import jsonify

from app import mongo


def _attempts_col():
    return mongo.db.attempts if mongo.db is not None else None


def _quiz_col():
    return mongo.db.quiz_attempts if mongo.db is not None else None


def _recommendations_col():
    return mongo.db.recommendations_log if mongo.db is not None else None


def _db_unavailable():
    return jsonify({"error": "DB not connected"}), 503


def api_stats_summary():
    attempts_col = _attempts_col()
    if attempts_col is None:
        return _db_unavailable()
    try:
        total_attempts = attempts_col.count_documents({})
        all_sessions = attempts_col.distinct("session_id")
        static_sess = attempts_col.distinct("session_id", {"group_type": "static"})
        interactive_sess = attempts_col.distinct("session_id", {"group_type": "interactive"})
        control_sess = attempts_col.distinct("session_id", {"experiment_group": "A_control"})
        adaptive_sess = attempts_col.distinct("session_id", {"experiment_group": "B_adaptive"})
        passes = attempts_col.count_documents({"result": "pass"})
        pass_rate = round(passes / total_attempts * 100, 1) if total_attempts > 0 else 0
        return jsonify({
            "total_participants": len(all_sessions),
            "static_participants": len(static_sess),
            "interactive_participants": len(interactive_sess),
            "control_participants": len(control_sess),
            "adaptive_participants": len(adaptive_sess),
            "total_attempts": total_attempts,
            "overall_pass_rate": pass_rate,
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


def compute_research_snapshot():
    attempts_col = _attempts_col()
    quiz_col = _quiz_col()
    recommendations_col = _recommendations_col()

    snapshot = {
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
            "_id": "$experiment_group",
            "attempts": {"$sum": 1},
            "passes": {"$sum": {"$cond": [{"$eq": ["$result", "pass"]}, 1, 0]}},
            "avg_attempt_number": {"$avg": "$attempt_number"},
        }}
    ]))
    exp_map = {r.get("_id", "unknown"): r for r in exp_rows}
    control = exp_map.get("A_control", {"attempts": 0, "passes": 0, "avg_attempt_number": 0})
    adaptive = exp_map.get("B_adaptive", {"attempts": 0, "passes": 0, "avg_attempt_number": 0})
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


def api_research_snapshot():
    try:
        return jsonify(compute_research_snapshot())
    except Exception as e:
        return jsonify({"error": str(e)}), 500


def api_stats_pass_rate():
    attempts_col = _attempts_col()
    if attempts_col is None:
        return _db_unavailable()
    try:
        rows = list(attempts_col.aggregate([
            {"$group": {
                "_id": "$group_type",
                "total": {"$sum": 1},
                "passes": {"$sum": {"$cond": [{"$eq": ["$result", "pass"]}, 1, 0]}},
            }}
        ]))
        result = []
        for r in rows:
            total = r["total"]
            passes = r["passes"]
            result.append({
                "group": r["_id"],
                "total": total,
                "passes": passes,
                "pass_rate": round(passes / total * 100, 1) if total > 0 else 0,
            })
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


def api_stats_attempts():
    attempts_col = _attempts_col()
    if attempts_col is None:
        return _db_unavailable()
    try:
        rows = list(attempts_col.aggregate([
            {"$group": {
                "_id": {
                    "exercise_id": {"$ifNull": ["$exercise_id", "unknown"]},
                    "group_type": {"$ifNull": ["$group_type", "unknown"]},
                },
                "avg_attempts": {"$avg": "$attempt_number"},
                "count": {"$sum": 1},
            }},
            {"$sort": {"_id.exercise_id": 1}},
        ]))
        result = []
        for r in rows:
            rid = r.get("_id", {})
            result.append({
                "exercise_id": rid.get("exercise_id", "unknown"),
                "group_type": rid.get("group_type", "unknown"),
                "avg_attempts": round(r.get("avg_attempts", 0) or 0, 2),
                "count": r.get("count", 0),
            })
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


def api_stats_errors():
    attempts_col = _attempts_col()
    if attempts_col is None:
        return _db_unavailable()
    try:
        rows = list(attempts_col.aggregate([
            {"$match": {"error_type": {"$ne": None}}},
            {"$group": {"_id": "$error_type", "count": {"$sum": 1}}},
            {"$sort": {"count": -1}},
        ]))
        return jsonify([{"error_type": r["_id"], "count": r["count"]} for r in rows])
    except Exception as e:
        return jsonify({"error": str(e)}), 500


def api_stats_learning_curve():
    attempts_col = _attempts_col()
    if attempts_col is None:
        return _db_unavailable()
    try:
        rows = list(attempts_col.aggregate([
            {"$match": {"result": "pass"}},
            {"$group": {
                "_id": {"session_id": "$session_id", "exercise_id": "$exercise_id", "group_type": "$group_type"},
                "first_pass": {"$min": "$attempt_number"},
            }},
            {"$group": {
                "_id": {"exercise_id": "$_id.exercise_id", "group_type": "$_id.group_type"},
                "avg_first_pass": {"$avg": "$first_pass"},
                "sessions": {"$sum": 1},
            }},
            {"$sort": {"_id.exercise_id": 1}},
        ]))
        return jsonify([
            {
                "exercise_id": r["_id"]["exercise_id"],
                "group_type": r["_id"]["group_type"],
                "avg_first_pass": round(r["avg_first_pass"], 2),
                "sessions": r["sessions"],
            }
            for r in rows
        ])
    except Exception as e:
        return jsonify({"error": str(e)}), 500


def api_stats_language_difficulty():
    attempts_col = _attempts_col()
    if attempts_col is None:
        return _db_unavailable()
    try:
        rows = list(attempts_col.aggregate([
            {"$group": {
                "_id": "$programming_language",
                "total": {"$sum": 1},
                "passes": {"$sum": {"$cond": [{"$eq": ["$result", "pass"]}, 1, 0]}},
                "syntax_errors": {"$sum": {"$cond": [{"$eq": ["$error_type", "syntax"]}, 1, 0]}},
            }},
            {"$sort": {"_id": 1}},
        ]))
        result = []
        for r in rows:
            total = r.get("total", 0)
            if total == 0:
                continue
            result.append({
                "language": r.get("_id", "unknown"),
                "pass_rate": round((r.get("passes", 0) / total) * 100, 1),
                "syntax_error_rate": round((r.get("syntax_errors", 0) / total) * 100, 1),
                "attempts": total,
            })
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


def api_stats_topic_success():
    attempts_col = _attempts_col()
    if attempts_col is None:
        return _db_unavailable()
    try:
        rows = list(attempts_col.aggregate([
            {"$group": {
                "_id": "$topic",
                "total": {"$sum": 1},
                "passes": {"$sum": {"$cond": [{"$eq": ["$result", "pass"]}, 1, 0]}},
            }},
            {"$sort": {"_id": 1}},
        ]))
        return jsonify([
            {
                "topic": r.get("_id", "unknown"),
                "success_rate": round((r["passes"] / r["total"]) * 100, 1) if r["total"] else 0,
                "attempts": r["total"],
            }
            for r in rows if r.get("_id")
        ])
    except Exception as e:
        return jsonify({"error": str(e)}), 500


def api_stats_quiz_performance():
    attempts_col = _attempts_col()
    quiz_col = _quiz_col()
    if attempts_col is None or quiz_col is None:
        return _db_unavailable()
    try:
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
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


def api_stats_recommendation_effectiveness():
    attempts_col = _attempts_col()
    if attempts_col is None:
        return _db_unavailable()
    try:
        rows = list(attempts_col.aggregate([
            {"$group": {
                "_id": "$experiment_group",
                "attempts": {"$sum": 1},
                "passes": {"$sum": {"$cond": [{"$eq": ["$result", "pass"]}, 1, 0]}},
                "avg_attempt_no": {"$avg": "$attempt_number"},
                "recommendation_hits": {"$sum": "$recommendation_count"},
            }},
            {"$sort": {"_id": 1}},
        ]))
        return jsonify([
            {
                "experiment_group": r.get("_id", "unknown"),
                "attempts": r.get("attempts", 0),
                "pass_rate": round((r.get("passes", 0) / max(r.get("attempts", 1), 1)) * 100, 1),
                "avg_attempt_number": round(r.get("avg_attempt_no", 0), 2),
                "recommendation_hits": r.get("recommendation_hits", 0),
            }
            for r in rows
        ])
    except Exception as e:
        return jsonify({"error": str(e)}), 500


def get_valid_session_ids():
    attempts_col = _attempts_col()
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


def api_stats_session_quality():
    attempts_col = _attempts_col()
    if attempts_col is None:
        return _db_unavailable()
    try:
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
            return jsonify({"total": 0, "valid": 0, "invalid": 0, "validity_rate": 0})
        r = rows[0]
        return jsonify({
            "total": r["total"],
            "valid": r["valid"],
            "invalid": r["invalid"],
            "validity_rate": round(r["valid"] / r["total"] * 100, 1) if r["total"] > 0 else 0,
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


def api_stats_time_to_pass():
    attempts_col = _attempts_col()
    if attempts_col is None:
        return _db_unavailable()
    try:
        first_attempt_rows = list(attempts_col.aggregate([
            {"$group": {
                "_id": {"session_id": "$session_id", "exercise_id": "$exercise_id", "group_type": "$group_type"},
                "first_ts": {"$min": "$timestamp"},
            }},
        ]))
        first_map = {f"{r['_id']['session_id']}__{r['_id']['exercise_id']}": r for r in first_attempt_rows}

        first_pass_rows = list(attempts_col.aggregate([
            {"$match": {"result": "pass"}},
            {"$group": {
                "_id": {"session_id": "$session_id", "exercise_id": "$exercise_id", "group_type": "$group_type"},
                "pass_ts": {"$min": "$timestamp"},
            }},
        ]))

        buckets = defaultdict(lambda: {"times": [], "first_pass": 0})
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
            times = data["times"]
            first_count = data["first_pass"]
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
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


def api_stats_persistence():
    attempts_col = _attempts_col()
    if attempts_col is None:
        return _db_unavailable()
    try:
        rows = list(attempts_col.aggregate([
            {"$group": {
                "_id": {
                    "session_id": {"$ifNull": ["$session_id", "unknown"]},
                    "exercise_id": {"$ifNull": ["$exercise_id", "unknown"]},
                    "group_type": {"$ifNull": ["$group_type", "unknown"]},
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
        for r in rows:
            rid = r.get("_id", {})
            result.append({
                "exercise_id": rid.get("exercise_id", "unknown"),
                "group_type": rid.get("group_type", "unknown"),
                "avg_attempts": round(r.get("avg_attempts", 0) or 0, 2),
                "engaged_sessions": r.get("engaged_sessions", 0),
            })
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


def api_stats_error_transitions():
    attempts_col = _attempts_col()
    if attempts_col is None:
        return _db_unavailable()
    try:
        valid_ids = get_valid_session_ids()
        if not valid_ids:
            return jsonify([])

        attempts_raw = list(attempts_col.find(
            {"session_id": {"$in": valid_ids}},
            {"session_id": 1, "exercise_id": 1, "attempt_number": 1, "error_type": 1, "result": 1, "_id": 0},
        ).sort([("session_id", 1), ("exercise_id", 1), ("attempt_number", 1)]))

        transitions = {}
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

        result = sorted(
            [{"from": k.split("->")[0], "to": k.split("->")[1], "count": v} for k, v in transitions.items()],
            key=lambda x: -x["count"],
        )[:20]
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
