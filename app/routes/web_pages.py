"""
Web pages routes migrated from legacy monolith.
Preserves existing template route names and user flow.
"""

import random
import uuid
import io
from hmac import compare_digest

from flask import current_app, jsonify, redirect, render_template, request, session, url_for, send_file

from app import mongo
from app.data import (
    EXERCISES,
    EXERCISE_MAP,
    LANGUAGE_LABELS,
    get_quiz_questions,
    get_topic_content,
    get_track_exercises,
    get_track_topics,
    normalize_language,
)
from app.services.execution_engine import ExecutionEngine
from app.services.export_service import ExportService
from app.services.learning_engine import LearningEngine
from app.utils.decorators import requires_admin_login


def _attempts_col():
    return mongo.db.attempts if mongo.db is not None else None


def _quiz_col():
    return mongo.db.quiz_attempts if mongo.db is not None else None


def _recommend_col():
    return mongo.db.recommendations_log if mongo.db is not None else None


def _language_label(exercise: dict) -> str:
    language = str(exercise.get("language") or "python")
    return LANGUAGE_LABELS.get(language, language)


def _selected_language() -> str:
    """Resolve selected language from query or session with python fallback."""
    requested = request.args.get("lang")
    if requested:
        lang = normalize_language(requested)
        session["selected_language"] = lang
        return lang
    return normalize_language(session.get("selected_language"))


def _csv_download(rows: list[dict], filename: str):
    bio = io.BytesIO(ExportService.to_csv_bytes(rows))
    return send_file(bio, mimetype="text/csv", as_attachment=True, download_name=filename)


def _render_exercise_page(
    mode: str,
    exercise_index: int,
    selected_language: str,
    feedback=None,
    submitted_code: str | None = None,
):
    track_exercises = get_track_exercises(selected_language)
    if not track_exercises:
        track_exercises = EXERCISES

    exercise_index = max(0, min(exercise_index, len(track_exercises) - 1))
    exercise = track_exercises[exercise_index]
    session_id = session.get("session_id")
    is_interactive = mode == "interactive"
    mode_endpoint = "interactive_mode" if is_interactive else "static_mode"
    active_recommendations = []
    if is_interactive:
        active_recommendations = session.get("active_recommendations") or []
    return render_template(
        "exercise.html",
        mode=mode,
        is_interactive=is_interactive,
        mode_endpoint=mode_endpoint,
        exercise=exercise,
        exercises=track_exercises,
        exercise_index=exercise_index,
        total=len(track_exercises),
        feedback=feedback,
        submitted_code=submitted_code,
        selected_language=selected_language,
        progress=LearningEngine.get_session_progress_for_language(_attempts_col(), session_id, selected_language),
        experiment_group=session.get("experiment_group"),
        language_label=_language_label(exercise),
        active_recommendations=active_recommendations,
    )


def index():
    selected_language = _selected_language()
    return render_template(
        "index.html",
        topics=get_track_topics(selected_language),
        selected_language=selected_language,
    )


def static_mode():
    selected_language = _selected_language()
    session["selected_language"] = selected_language
    LearningEngine.init_participant_session(
        session_store=session,
        mode="static",
        random_uuid=str(uuid.uuid4()),
        rand_choice=random.choice,
    )
    exercise_index = int(request.args.get("ex", 0))
    return _render_exercise_page(
        mode="static",
        exercise_index=exercise_index,
        selected_language=selected_language,
    )


def interactive_mode():
    selected_language = _selected_language()
    session["selected_language"] = selected_language
    LearningEngine.init_participant_session(
        session_store=session,
        mode="interactive",
        random_uuid=str(uuid.uuid4()),
        rand_choice=random.choice,
    )
    exercise_index = int(request.args.get("ex", 0))
    return _render_exercise_page(
        mode="interactive",
        exercise_index=exercise_index,
        selected_language=selected_language,
    )


def start_session():
    """Start participant flow only after explicit onboarding confirmation."""
    mode = LearningEngine._normalize_mode(request.form.get("mode") or request.args.get("mode"))
    language = normalize_language(request.form.get("language") or request.args.get("language"))
    session["selected_language"] = language
    session["session_completed"] = False
    if not session.get("participant_ref"):
        session["participant_ref"] = str(uuid.uuid4())
    session.pop("active_recommendations", None)

    if mode == "interactive":
        return redirect(url_for("interactive_mode", lang=language))
    return redirect(url_for("static_mode", lang=language))


def submit():
    code = request.form.get("code", "")
    exercise_id = request.form.get("exercise_id") or ""
    exercise_index = int(request.form.get("exercise_index", 0))
    mode = session.get("mode") or session.get("group_type", "static")
    experiment_arm = session.get("experiment_arm") or session.get("experiment_group", "control")
    selected_language = normalize_language(session.get("selected_language"))
    session_id = session.get("session_id", str(uuid.uuid4()))
    session["session_id"] = session_id
    participant_ref = str(session.get("participant_ref") or session_id)
    session["participant_ref"] = participant_ref
    journey = LearningEngine(session_id)

    exercise = EXERCISE_MAP.get(exercise_id)
    if not exercise:
        return "Invalid exercise", 400

    # Enforce language-track consistency.
    if exercise.get("language") != selected_language:
        return "Exercise does not belong to selected language track", 400

    attempt_number = LearningEngine.next_attempt_number(_attempts_col(), session_id, exercise_id)
    exec_result = ExecutionEngine.run_code(code, language=exercise.get("language", "python"))
    eval_result = ExecutionEngine.evaluate_test_cases(exercise, exec_result)
    exec_time_ms = exec_result.get("execution_time_ms", 0)

    language_track = get_track_exercises(selected_language)
    user_state = {
        "topic": exercise.get("topic"),
        "attempts": attempt_number,
        "success": eval_result.get("result") == "pass",
        "error_type": eval_result.get("error_type"),
        "time_taken": float(exec_time_ms or 0) / 1000,
        "exercise_index": exercise_index,
        "total_exercises": len(language_track),
        "language": selected_language,
    }
    user_profile = LearningEngine.build_user_profile(_attempts_col(), session_id, selected_language)

    recommendations = []
    next_step = {
        "action": "static_progression",
        "next_exercise_index": min(exercise_index + 1, max(0, len(language_track) - 1)) if eval_result.get("result") == "pass" else exercise_index,
        "support_action": "exercise",
        "profile_based": False,
    }
    # Scope-aligned behavior: adaptive support is shown in interactive mode only.
    if mode == "interactive":
        next_step = LearningEngine.get_next_step(user_state, user_profile)
        recommendations = LearningEngine.generate_recommendation(
            user_state,
            topic_page_url=url_for(
                "topic_page",
                topic_id=exercise.get("topic", ""),
                lang=selected_language,
                return_mode="interactive_mode",
                ex=exercise_index,
            ),
            topic_quiz_url=url_for(
                "topic_quiz",
                topic_id=exercise.get("topic", ""),
                lang=selected_language,
                return_mode="interactive_mode",
                ex=exercise_index,
            ),
            easier_exercise_url=url_for(
                "interactive_mode",
                lang=selected_language,
                ex=max(0, exercise_index - 1),
            ),
            user_profile=user_profile,
        )
        if eval_result.get("result") == "pass":
            session.pop("active_recommendations", None)
        elif recommendations:
            session["active_recommendations"] = recommendations
        LearningEngine.log_recommendations(
            recommend_col=_recommend_col(),
            session_id=session_id,
            user_id=participant_ref,
            mode=mode,
            experiment_arm=experiment_arm,
            exercise_id=exercise_id,
            topic=exercise.get("topic", ""),
            recommendations=recommendations,
        )
    else:
        session.pop("active_recommendations", None)

    LearningEngine.log_attempt(
        attempts_col=_attempts_col(),
        session_id=session_id,
        user_id=participant_ref,
        mode=mode,
        exercise=exercise,
        attempt_number=attempt_number,
        eval_result=eval_result,
        execution_time_ms=exec_time_ms,
        experiment_arm=experiment_arm,
        recommendations=recommendations,
        next_step=next_step,
    )

    journey.log_event(
        {
            "event_type": "attempt_evaluated",
            "session_id": session_id,
            "exercise_id": exercise_id,
            "language": selected_language,
            "mode": mode,
            "experiment_arm": experiment_arm,
            "next_step_action": next_step.get("action"),
        }
    )

    if mode == "static":
        failed_tests = []
        for row in eval_result.get("details") or []:
            if not row.get("passed"):
                failed_tests.append(str(row.get("test") or "Failed test"))
        feedback = {
            "mode": "static",
            "passed": eval_result["passed"],
            "message": "Correct!" if eval_result["passed"] else "Incorrect.",
            "failed_tests": failed_tests,
            "recommendations": [],
            "next_step": next_step,
        }
        return _render_exercise_page(
            mode="static",
            exercise_index=exercise_index,
            selected_language=selected_language,
            feedback=feedback,
            submitted_code=code,
        )

    feedback = {
        "mode": "interactive",
        "passed": eval_result["passed"],
        "message": eval_result["feedback"],
        "details": eval_result["details"],
        "error_type": eval_result["error_type"],
        "recommendations": recommendations,
        "next_step": next_step,
    }
    return _render_exercise_page(
        mode="interactive",
        exercise_index=exercise_index,
        selected_language=selected_language,
        feedback=feedback,
        submitted_code=code,
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
        admin_user = str(current_app.config.get("ADMIN_USERNAME") or "")
        admin_password = str(current_app.config.get("ADMIN_PASSWORD") or "")
        credentials_configured = bool(admin_user and admin_password)

        if credentials_configured and compare_digest(user, admin_user) and compare_digest(pwd, admin_password):
            session["admin_logged_in"] = True
            return redirect(url_for("admin_dashboard"))
        error = "Invalid username or password."
    return render_template("admin_login.html", error=error)


def admin_logout():
    session.pop("admin_logged_in", None)
    return redirect(url_for("admin_login"))


@requires_admin_login
def admin_dashboard():
    return render_template("admin_dashboard.html")


def session_complete():
    sid = session.get("session_id")
    mode = session.get("mode") or session.get("group_type", "unknown")
    experiment_arm = session.get("experiment_arm") or session.get("experiment_group", "control")
    selected_language = normalize_language(session.get("selected_language"))
    total_ex = len(get_track_exercises(selected_language) or EXERCISES)
    session["session_completed"] = True

    stats = LearningEngine.build_completion_stats(
        attempts_col=_attempts_col(),
        quiz_col=_quiz_col(),
        session_id=sid,
        mode=mode,
        experiment_arm=experiment_arm,
        total_exercises=total_ex,
    )

    return render_template(
        "completion.html",
        stats=stats,
        selected_language=selected_language,
    )


def study_information():
    """Consolidated study information page (formerly 3 separate pages)."""
    return render_template("study_information.html")


def research_info():
    """Redirect to consolidated study information page (backward compatibility)."""
    return redirect(url_for('study_information'))


def methodology_page():
    """Redirect to consolidated study information page (backward compatibility)."""
    return redirect(url_for('study_information'))


def study_design_page():
    """Redirect to consolidated study information page (backward compatibility)."""
    return redirect(url_for('study_information'))


def my_progress_page():
    return render_template("my_progress.html", progress_unlocked=bool(session.get("session_completed")))


def topic_page(topic_id):
    selected_language = _selected_language()
    return_mode = request.args.get("return_mode") or "interactive_mode"
    if return_mode not in ("interactive_mode", "static_mode"):
        return_mode = "interactive_mode"
    return_ex = request.args.get("ex", "0")
    topic = get_topic_content(selected_language, topic_id)
    if not topic:
        return "Topic not found", 404
    exercises = [
        ex for ex in get_track_exercises(selected_language)
        if ex.get("topic") == topic_id
    ]
    return render_template(
        "topic.html",
        topic_id=topic_id,
        topic=topic,
        exercises=exercises,
        selected_language=selected_language,
        language_labels=LANGUAGE_LABELS,
        return_mode=return_mode,
        return_ex=return_ex,
    )


def topic_quiz(topic_id):
    selected_language = _selected_language()
    return_mode = request.args.get("return_mode") or "interactive_mode"
    if return_mode not in ("interactive_mode", "static_mode"):
        return_mode = "interactive_mode"
    return_ex = request.args.get("ex", "0")
    try:
        return_ex_int = int(return_ex)
    except (TypeError, ValueError):
        return_ex_int = 0
    topic = get_topic_content(selected_language, topic_id)
    questions = get_quiz_questions(selected_language, topic_id)
    if not topic or not questions:
        return "Quiz not available for this topic", 404

    if "session_id" not in session:
        LearningEngine.init_participant_session(
            session_store=session,
            mode="interactive",
            random_uuid=str(uuid.uuid4()),
            rand_choice=random.choice,
        )

    unlock = LearningEngine.topic_quiz_unlock_status(
        attempts_col=_attempts_col(),
        session_id=session.get("session_id"),
        topic_id=topic_id,
        selected_language=selected_language,
        experiment_arm=session.get("experiment_arm") or session.get("experiment_group", "control"),
    )

    if not unlock["unlocked"]:
        return render_template(
            "quiz.html",
            topic_id=topic_id,
            topic=topic,
            questions=questions,
            selected_language=selected_language,
            submitted=False,
            locked=True,
            lock_reason=unlock["reason"],
            return_mode=return_mode,
            return_ex=return_ex,
        )

    if request.method == "POST":
        quiz_result = LearningEngine.evaluate_quiz_submission(questions, request.form)
        mode = session.get("mode") or session.get("group_type", "interactive")
        participant_ref = str(session.get("participant_ref") or session.get("session_id") or "")
        LearningEngine.log_quiz_attempt(
            quiz_col=_quiz_col(),
            session_id=session.get("session_id"),
            user_id=participant_ref,
            mode=mode,
            experiment_arm=session.get("experiment_arm") or session.get("experiment_group", "control"),
            topic_id=topic_id,
            quiz_result=quiz_result,
        )

        raw_score_pct = quiz_result.get("score_pct", 0)
        score_pct = float(raw_score_pct if isinstance(raw_score_pct, (int, float)) else 0)
        next_guidance = {
            "label": "Continue practice",
            "message": "Return to your exercise and apply what you just reviewed.",
            "primary_url": url_for(return_mode, lang=selected_language, ex=return_ex_int),
            "primary_text": "Back to Exercise",
            "secondary_url": url_for("topic_page", topic_id=topic_id, lang=selected_language, return_mode=return_mode, ex=return_ex),
            "secondary_text": "View Lesson",
        }

        if mode == "interactive":
            lesson_url = url_for(
                "topic_page",
                topic_id=topic_id,
                lang=selected_language,
                return_mode=return_mode,
                ex=return_ex,
            )
            exercise_url = url_for(return_mode, lang=selected_language, ex=return_ex_int)
            if score_pct < 40:
                session["active_recommendations"] = [
                    {
                        "type": "lesson",
                        "title": "Recommended now: Watch the lesson",
                        "reason": "Low quiz score suggests concept gaps; review before retrying code.",
                        "resource_url": lesson_url,
                        "intensity": "high",
                    },
                    {
                        "type": "exercise",
                        "title": "Then retry this exercise",
                        "reason": "Apply the corrected concept immediately after the lesson.",
                        "resource_url": exercise_url,
                        "intensity": "medium",
                    },
                ]
                next_guidance = {
                    "label": "Review then retry",
                    "message": "Your quiz result suggests a concept gap. Watch the lesson first, then retry the exercise.",
                    "primary_url": lesson_url,
                    "primary_text": "Watch Lesson First",
                    "secondary_url": exercise_url,
                    "secondary_text": "Retry Exercise",
                }
            elif score_pct < 70:
                session["active_recommendations"] = [
                    {
                        "type": "exercise",
                        "title": "Practice now: Retry this exercise",
                        "reason": "You are close; one focused retry should help you pass.",
                        "resource_url": exercise_url,
                        "intensity": "medium",
                    }
                ]
                next_guidance = {
                    "label": "Retry now",
                    "message": "You are making progress. Retry the exercise now while this concept is fresh.",
                    "primary_url": exercise_url,
                    "primary_text": "Retry Exercise",
                    "secondary_url": lesson_url,
                    "secondary_text": "Review Lesson",
                }
            else:
                session.pop("active_recommendations", None)
                next_guidance = {
                    "label": "Advance",
                    "message": "Great quiz performance. Move on to the next coding step confidently.",
                    "primary_url": exercise_url,
                    "primary_text": "Continue Exercise",
                    "secondary_url": lesson_url,
                    "secondary_text": "Optional Lesson Review",
                }

        return render_template(
            "quiz.html",
            topic_id=topic_id,
            topic=topic,
            questions=questions,
            selected_language=selected_language,
            submitted=True,
            locked=False,
            score=quiz_result["score"],
            total=quiz_result["total_questions"],
            score_pct=quiz_result["score_pct"],
            next_guidance=next_guidance,
            return_mode=return_mode,
            return_ex=return_ex,
        )

    return render_template(
        "quiz.html",
        topic_id=topic_id,
        topic=topic,
        questions=questions,
        selected_language=selected_language,
        submitted=False,
        locked=False,
        return_mode=return_mode,
        return_ex=return_ex,
    )


@requires_admin_login
def export_research_dataset():
    col = _attempts_col()
    rows = list(col.find()) if col is not None else []
    if not rows:
        return "No data available", 404

    export_rows = ExportService.build_research_dataset_rows(rows)
    return _csv_download(export_rows, "com748_research_dataset.csv")


@requires_admin_login
def export_session_summary():
    col = _attempts_col()
    if col is None:
        return "No data available", 404

    rows = list(col.find())
    export_rows = ExportService.build_session_summary_rows(rows)
    if not export_rows:
        return "No session summaries available", 404

    return _csv_download(export_rows, "com748_session_summary.csv")


@requires_admin_login
def export_quiz_data():
    col = _quiz_col()
    rows = list(col.find()) if col is not None else []
    if not rows:
        return "No quiz data available", 404

    export_rows = ExportService.build_quiz_rows(rows)
    return _csv_download(export_rows, "com748_quiz_data.csv")


@requires_admin_login
def export_recommendations():
    col = _recommend_col()
    rows = list(col.find()) if col is not None else []
    if not rows:
        return "No recommendation data available", 404

    export_rows = ExportService.build_recommendation_rows(rows)
    return _csv_download(export_rows, "com748_recommendation_log.csv")


def register_web_page_routes(app):
    """Register legacy-compatible web page endpoints on the Flask app."""
    app.add_url_rule('/', endpoint='index', view_func=index)
    app.add_url_rule('/static-mode', endpoint='static_mode', view_func=static_mode)
    app.add_url_rule('/interactive-mode', endpoint='interactive_mode', view_func=interactive_mode)
    app.add_url_rule('/start-session', endpoint='start_session', view_func=start_session, methods=['POST'])
    app.add_url_rule('/submit', endpoint='submit', view_func=submit, methods=['POST'])
    app.add_url_rule('/db-status', endpoint='db_status', view_func=db_status)
    app.add_url_rule('/admin-login', endpoint='admin_login', view_func=admin_login, methods=['GET', 'POST'])
    app.add_url_rule('/admin-logout', endpoint='admin_logout', view_func=admin_logout)
    app.add_url_rule('/admin-dashboard', endpoint='admin_dashboard', view_func=admin_dashboard)
    app.add_url_rule('/complete', endpoint='session_complete', view_func=session_complete)
    app.add_url_rule('/study-information', endpoint='study_information', view_func=study_information)
    app.add_url_rule('/research-info', endpoint='research_info', view_func=research_info)  # redirects to study_information
    app.add_url_rule('/methodology', endpoint='methodology_page', view_func=methodology_page)  # redirects to study_information
    app.add_url_rule('/study-design', endpoint='study_design_page', view_func=study_design_page)  # redirects to study_information
    app.add_url_rule('/my-progress', endpoint='my_progress_page', view_func=my_progress_page)
    app.add_url_rule('/learn/<topic_id>', endpoint='topic_page', view_func=topic_page)
    app.add_url_rule('/quiz/<topic_id>', endpoint='topic_quiz', view_func=topic_quiz, methods=['GET', 'POST'])
    app.add_url_rule('/export-data', endpoint='export_data_csv', view_func=export_research_dataset)
    app.add_url_rule('/export-research-dataset', endpoint='export_research_dataset', view_func=export_research_dataset)
    app.add_url_rule('/export-session-summary', endpoint='export_session_summary', view_func=export_session_summary)
    app.add_url_rule('/export-quiz-data', endpoint='export_quiz_data', view_func=export_quiz_data)
    app.add_url_rule('/export-recommendations', endpoint='export_recommendations', view_func=export_recommendations)
