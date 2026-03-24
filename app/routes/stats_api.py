"""Research stats API routes migrated from legacy monolith."""

import csv
import io
import json
import zipfile

from flask import jsonify, request, send_file

from app import mongo
from app.services.stats_service import StatsService


def _attempts_col():
    return mongo.db.attempts if mongo.db is not None else None


def _quiz_col():
    return mongo.db.quiz_attempts if mongo.db is not None else None


def _recommendations_col():
    return mongo.db.recommendations_log if mongo.db is not None else None


def _db_unavailable():
    return jsonify({"error": "DB not connected"}), 503


def _to_int(value, default):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _to_float(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def api_stats_summary():
    attempts_col = _attempts_col()
    if attempts_col is None:
        return _db_unavailable()
    try:
        return jsonify(StatsService.build_summary(attempts_col))
    except Exception as e:
        return jsonify({"error": str(e)}), 500


def api_dashboard_overview():
    attempts_col = _attempts_col()
    if attempts_col is None:
        return _db_unavailable()
    try:
        return jsonify(StatsService.build_dashboard_overview(attempts_col))
    except Exception as e:
        return jsonify({"error": str(e)}), 500


def api_dashboard_core_results():
    attempts_col = _attempts_col()
    if attempts_col is None:
        return _db_unavailable()
    try:
        return jsonify(StatsService.build_core_results(attempts_col))
    except Exception as e:
        return jsonify({"error": str(e)}), 500


def api_dashboard_behavior_results():
    attempts_col = _attempts_col()
    if attempts_col is None:
        return _db_unavailable()
    try:
        return jsonify(StatsService.build_behavior_results(attempts_col))
    except Exception as e:
        return jsonify({"error": str(e)}), 500


def api_dashboard_adaptivity_results():
    attempts_col = _attempts_col()
    if attempts_col is None:
        return _db_unavailable()
    try:
        return jsonify(StatsService.build_adaptivity_results(attempts_col, _recommendations_col()))
    except Exception as e:
        return jsonify({"error": str(e)}), 500


def compute_research_snapshot():
    return StatsService.build_research_snapshot(
        _attempts_col(),
        _quiz_col(),
        _recommendations_col(),
    )


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
        return jsonify(StatsService.build_pass_rate_rows(attempts_col))
    except Exception as e:
        return jsonify({"error": str(e)}), 500


def api_stats_attempts():
    attempts_col = _attempts_col()
    if attempts_col is None:
        return _db_unavailable()
    try:
        return jsonify(StatsService.build_attempt_rows(attempts_col))
    except Exception as e:
        return jsonify({"error": str(e)}), 500


def api_stats_errors():
    attempts_col = _attempts_col()
    if attempts_col is None:
        return _db_unavailable()
    try:
        return jsonify(StatsService.build_error_rows(attempts_col))
    except Exception as e:
        return jsonify({"error": str(e)}), 500


def api_stats_learning_curve():
    attempts_col = _attempts_col()
    if attempts_col is None:
        return _db_unavailable()
    try:
        return jsonify(StatsService.build_learning_curve_rows(attempts_col))
    except Exception as e:
        return jsonify({"error": str(e)}), 500


def api_stats_language_difficulty():
    attempts_col = _attempts_col()
    if attempts_col is None:
        return _db_unavailable()
    try:
        return jsonify(StatsService.build_language_difficulty_rows(attempts_col))
    except Exception as e:
        return jsonify({"error": str(e)}), 500


def api_stats_topic_success():
    attempts_col = _attempts_col()
    if attempts_col is None:
        return _db_unavailable()
    try:
        return jsonify(StatsService.build_topic_success_rows(attempts_col))
    except Exception as e:
        return jsonify({"error": str(e)}), 500


def api_stats_topic_difficulty():
    attempts_col = _attempts_col()
    if attempts_col is None:
        return _db_unavailable()
    try:
        return jsonify(StatsService.build_topic_difficulty_rows(attempts_col))
    except Exception as e:
        return jsonify({"error": str(e)}), 500


def api_stats_quiz_performance():
    attempts_col = _attempts_col()
    quiz_col = _quiz_col()
    if attempts_col is None or quiz_col is None:
        return _db_unavailable()
    try:
        return jsonify(StatsService.build_quiz_performance_rows(attempts_col, quiz_col))
    except Exception as e:
        return jsonify({"error": str(e)}), 500


def api_stats_recommendation_effectiveness():
    attempts_col = _attempts_col()
    if attempts_col is None:
        return _db_unavailable()
    try:
        return jsonify(StatsService.build_recommendation_effectiveness_rows(attempts_col))
    except Exception as e:
        return jsonify({"error": str(e)}), 500


def api_stats_recommendation_impact():
    attempts_col = _attempts_col()
    if attempts_col is None:
        return _db_unavailable()
    try:
        return jsonify(StatsService.build_recommendation_impact_rows(attempts_col))
    except Exception as e:
        return jsonify({"error": str(e)}), 500


def get_valid_session_ids():
    return StatsService.get_valid_session_ids(_attempts_col())


def api_stats_session_quality():
    attempts_col = _attempts_col()
    if attempts_col is None:
        return _db_unavailable()
    try:
        return jsonify(StatsService.build_session_quality(attempts_col))
    except Exception as e:
        return jsonify({"error": str(e)}), 500


def api_stats_time_to_pass():
    attempts_col = _attempts_col()
    if attempts_col is None:
        return _db_unavailable()
    try:
        return jsonify(StatsService.build_time_to_pass_rows(attempts_col))
    except Exception as e:
        return jsonify({"error": str(e)}), 500


def api_stats_persistence():
    attempts_col = _attempts_col()
    if attempts_col is None:
        return _db_unavailable()
    try:
        return jsonify(StatsService.build_persistence_rows(attempts_col))
    except Exception as e:
        return jsonify({"error": str(e)}), 500


def api_stats_error_transitions():
    attempts_col = _attempts_col()
    if attempts_col is None:
        return _db_unavailable()
    try:
        valid_ids = get_valid_session_ids()
        return jsonify(StatsService.build_error_transition_rows(attempts_col, valid_ids))
    except Exception as e:
        return jsonify({"error": str(e)}), 500


def api_stats_session_drilldown():
    attempts_col = _attempts_col()
    if attempts_col is None:
        return _db_unavailable()

    session_id = (request.args.get("session_id") or "").strip()
    limit = _to_int(request.args.get("limit", 40), 40)
    page = _to_int(request.args.get("page", 1), 1)

    filters = {
        "group_type": (request.args.get("group_type") or "").strip(),
        "experiment_group": (request.args.get("experiment_group") or "").strip(),
        "min_pass_rate": _to_float(request.args.get("min_pass_rate")),
        "max_pass_rate": _to_float(request.args.get("max_pass_rate")),
        "since_hours": _to_float(request.args.get("since_hours")),
    }

    try:
        if not session_id:
            return jsonify(
                StatsService.build_session_drilldown_index_page(
                    attempts_col,
                    limit=limit,
                    page=page,
                    filters=filters,
                )
            )

        return jsonify(
            StatsService.build_session_drilldown_detail(
                attempts_col=attempts_col,
                quiz_col=_quiz_col(),
                recommendations_col=_recommendations_col(),
                session_id=session_id,
            )
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 500


def api_stats_session_drilldown_bundle_export():
    attempts_col = _attempts_col()
    if attempts_col is None:
        return _db_unavailable()

    session_id = (request.args.get("session_id") or "").strip()
    if not session_id:
        return jsonify({"error": "session_id is required"}), 400

    try:
        detail = StatsService.build_session_drilldown_detail(
            attempts_col=attempts_col,
            quiz_col=_quiz_col(),
            recommendations_col=_recommendations_col(),
            session_id=session_id,
        )
        rows = StatsService.build_session_drilldown_event_rows(detail)

        csv_output = io.StringIO()
        writer = csv.DictWriter(csv_output, fieldnames=list(rows[0].keys()) if rows else [
            "session_id", "event_type", "timestamp", "exercise_id", "topic", "attempt_number",
            "result", "error_type", "score", "score_pct", "recommendation_type", "title", "reason",
        ])
        writer.writeheader()
        if rows:
            writer.writerows(rows)

        zip_stream = io.BytesIO()
        with zipfile.ZipFile(zip_stream, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
            zf.writestr(
                f"session_{session_id}_drilldown.json",
                json.dumps(detail, indent=2),
            )
            zf.writestr(
                f"session_{session_id}_drilldown.csv",
                csv_output.getvalue(),
            )

        zip_stream.seek(0)
        return send_file(
            zip_stream,
            mimetype="application/zip",
            as_attachment=True,
            download_name=f"session_{session_id}_drilldown_bundle.zip",
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 500


def api_stats_session_drilldown_index_export():
    attempts_col = _attempts_col()
    if attempts_col is None:
        return _db_unavailable()

    limit = _to_int(request.args.get("limit", 200), 200)
    filters = {
        "group_type": (request.args.get("group_type") or "").strip(),
        "experiment_group": (request.args.get("experiment_group") or "").strip(),
        "min_pass_rate": _to_float(request.args.get("min_pass_rate")),
        "max_pass_rate": _to_float(request.args.get("max_pass_rate")),
        "since_hours": _to_float(request.args.get("since_hours")),
    }

    try:
        sessions = StatsService.build_session_drilldown_index(
            attempts_col,
            limit=limit,
            filters=filters,
        )

        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=[
            "session_id", "attempts", "passes", "pass_rate", "group_type",
            "experiment_group", "duration_s", "first_ts", "last_ts",
        ])
        writer.writeheader()
        if sessions:
            writer.writerows(sessions)

        payload = io.BytesIO(output.getvalue().encode("utf-8"))
        return send_file(
            payload,
            mimetype="text/csv",
            as_attachment=True,
            download_name="session_drilldown_filtered_index.csv",
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 500


def api_stats_session_drilldown_export():
    attempts_col = _attempts_col()
    if attempts_col is None:
        return _db_unavailable()

    session_id = (request.args.get("session_id") or "").strip()
    output_format = (request.args.get("format") or "json").strip().lower()
    if not session_id:
        return jsonify({"error": "session_id is required"}), 400
    if output_format not in {"json", "csv"}:
        return jsonify({"error": "format must be json or csv"}), 400

    try:
        detail = StatsService.build_session_drilldown_detail(
            attempts_col=attempts_col,
            quiz_col=_quiz_col(),
            recommendations_col=_recommendations_col(),
            session_id=session_id,
        )
        if output_format == "json":
            return jsonify(detail)

        rows = StatsService.build_session_drilldown_event_rows(detail)
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=list(rows[0].keys()) if rows else [
            "session_id", "event_type", "timestamp", "exercise_id", "topic", "attempt_number",
            "result", "error_type", "score", "score_pct", "recommendation_type", "title", "reason",
        ])
        writer.writeheader()
        if rows:
            writer.writerows(rows)

        payload = io.BytesIO(output.getvalue().encode("utf-8"))
        return send_file(
            payload,
            mimetype="text/csv",
            as_attachment=True,
            download_name=f"session_{session_id}_drilldown.csv",
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 500


def register_stats_routes(app):
    """Register stats API endpoints used by the admin dashboard."""
    app.add_url_rule('/api/stats/summary', endpoint='api_stats_summary', view_func=api_stats_summary)
    app.add_url_rule('/api/stats/dashboard-overview', endpoint='api_dashboard_overview', view_func=api_dashboard_overview)
    app.add_url_rule('/api/stats/dashboard-core', endpoint='api_dashboard_core_results', view_func=api_dashboard_core_results)
    app.add_url_rule('/api/stats/dashboard-behavior', endpoint='api_dashboard_behavior_results', view_func=api_dashboard_behavior_results)
    app.add_url_rule('/api/stats/dashboard-adaptivity', endpoint='api_dashboard_adaptivity_results', view_func=api_dashboard_adaptivity_results)
    app.add_url_rule('/api/stats/research-snapshot', endpoint='api_research_snapshot', view_func=api_research_snapshot)
    app.add_url_rule('/api/stats/pass-rate', endpoint='api_stats_pass_rate', view_func=api_stats_pass_rate)
    app.add_url_rule('/api/stats/attempts', endpoint='api_stats_attempts', view_func=api_stats_attempts)
    app.add_url_rule('/api/stats/errors', endpoint='api_stats_errors', view_func=api_stats_errors)
    app.add_url_rule('/api/stats/learning-curve', endpoint='api_stats_learning_curve', view_func=api_stats_learning_curve)
    app.add_url_rule('/api/stats/language-difficulty', endpoint='api_stats_language_difficulty', view_func=api_stats_language_difficulty)
    app.add_url_rule('/api/stats/topic-success', endpoint='api_stats_topic_success', view_func=api_stats_topic_success)
    app.add_url_rule('/api/stats/topic-difficulty', endpoint='api_stats_topic_difficulty', view_func=api_stats_topic_difficulty)
    app.add_url_rule('/api/stats/quiz-performance', endpoint='api_stats_quiz_performance', view_func=api_stats_quiz_performance)
    app.add_url_rule('/api/stats/recommendation-effectiveness', endpoint='api_stats_recommendation_effectiveness', view_func=api_stats_recommendation_effectiveness)
    app.add_url_rule('/api/stats/recommendation-impact', endpoint='api_stats_recommendation_impact', view_func=api_stats_recommendation_impact)
    app.add_url_rule('/api/stats/session-quality', endpoint='api_stats_session_quality', view_func=api_stats_session_quality)
    app.add_url_rule('/api/stats/time-to-pass', endpoint='api_stats_time_to_pass', view_func=api_stats_time_to_pass)
    app.add_url_rule('/api/stats/persistence', endpoint='api_stats_persistence', view_func=api_stats_persistence)
    app.add_url_rule('/api/stats/error-transitions', endpoint='api_stats_error_transitions', view_func=api_stats_error_transitions)
    app.add_url_rule('/api/stats/session-drilldown', endpoint='api_stats_session_drilldown', view_func=api_stats_session_drilldown)
    app.add_url_rule('/api/stats/session-drilldown/export', endpoint='api_stats_session_drilldown_export', view_func=api_stats_session_drilldown_export)
    app.add_url_rule('/api/stats/session-drilldown/export-bundle', endpoint='api_stats_session_drilldown_bundle_export', view_func=api_stats_session_drilldown_bundle_export)
    app.add_url_rule('/api/stats/session-drilldown/export-index', endpoint='api_stats_session_drilldown_index_export', view_func=api_stats_session_drilldown_index_export)
