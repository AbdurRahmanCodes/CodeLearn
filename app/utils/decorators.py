"""
Route decorators for common session and mode preconditions.
"""

from functools import wraps

from flask import jsonify, session as flask_session


def requires_session(view_func):
    """Require an active Flask session containing a session_id."""

    @wraps(view_func)
    def wrapper(*args, **kwargs):
        if not flask_session.get("session_id"):
            return jsonify({
                "success": False,
                "error": "No active session. Call /auth/session first.",
            }), 401
        return view_func(*args, **kwargs)

    return wrapper


def requires_mode_selected(view_func):
    """Require session and selected user mode before continuing."""

    @wraps(view_func)
    @requires_session
    def wrapper(*args, **kwargs):
        if not flask_session.get("user_mode"):
            return jsonify({
                "success": False,
                "error": "Learning mode not selected. Call /auth/select-mode first.",
            }), 400
        return view_func(*args, **kwargs)

    return wrapper
