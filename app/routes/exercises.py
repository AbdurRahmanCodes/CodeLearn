"""
Exercises Routes - Code Submission & Exercise Display
Handles: Exercise display, code submission, attempt logging
"""

from flask import Blueprint, request, jsonify, session as flask_session
from app import mongo
from app.data import EXERCISE_MAP, get_track_exercises, normalize_language
from app.services.learning_engine import LearningEngine
from app.utils import requires_mode_selected, requires_session

exercises_bp = Blueprint('exercises', __name__, url_prefix='/exercises')


def _selected_language() -> str:
    requested = ((request.get_json(silent=True) or {}).get('language') if request.method != 'GET' else request.args.get('lang'))
    if requested:
        lang = normalize_language(requested)
        flask_session['selected_language'] = lang
        return lang
    return normalize_language(flask_session.get('selected_language'))


def _exercise_from_source(exercise_id: int, language: str):
    # 1) Prefer DB collection if available.
    exercise = mongo.db.exercises.find_one({'exercise_id': exercise_id, 'language': language}) if mongo.db is not None else None
    if exercise:
        exercise.pop('_id', None)
        return exercise

    # 2) Fallback to language-track curriculum data.
    track = get_track_exercises(language)
    idx = exercise_id - 1
    if 0 <= idx < len(track):
        return track[idx]
    return None


@exercises_bp.route('/<int:exercise_id>', methods=['GET'])
@requires_session
def get_exercise(exercise_id):
    """
    Get exercise details
    
    GET /exercises/1
    Response: {exercise_id, title, description, test_cases}
    """
    session_id = flask_session.get('session_id')
    
    language = _selected_language()
    track_total = len(get_track_exercises(language))
    if exercise_id < 1 or exercise_id > track_total:
        return jsonify({
            'success': False,
            'error': f'Exercise ID must be between 1 and {track_total} for {language} track',
        }), 400
    
    try:
        exercise = _exercise_from_source(exercise_id, language)
        
        if not exercise:
            return jsonify({
                'success': False,
                'error': f'Exercise {exercise_id} not found',
            }), 404
        
        return jsonify({
            'success': True,
            'exercise': exercise,
            'language': language,
        }), 200
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
        }), 500


@exercises_bp.route('/<int:exercise_id>/submit', methods=['POST'])
@requires_mode_selected
def submit_attempt(exercise_id):
    """
    Submit code attempt for an exercise
    
    POST /exercises/1/submit
    Body: {code, language}
    Response: {result, pass_fail, recommendations, next_exercise}
    """
    session_id = str(flask_session.get('session_id') or '')
    
    data = request.json or {}
    code = data.get('code')
    language = normalize_language(data.get('language'))
    
    if not code or not language:
        return jsonify({
            'success': False,
            'error': 'Missing required fields: code, language',
        }), 400
    
    track_total = len(get_track_exercises(language))
    if exercise_id < 1 or exercise_id > track_total:
        return jsonify({
            'success': False,
            'error': f'Exercise ID must be between 1 and {track_total} for {language} track',
        }), 400
    
    selected_language = normalize_language(flask_session.get('selected_language'))
    if selected_language and selected_language != language:
        return jsonify({
            'success': False,
            'error': f'Language track mismatch. Selected track is {selected_language}.',
        }), 400

    flask_session['selected_language'] = language
    
    try:
        journey = LearningEngine(session_id)
        
        # Submit attempt (will execute code and log)
        result = journey.submit_attempt(exercise_id, code, language)
        
        return jsonify({
            'success': True,
            'result': result,
            'language': language,
        }), 200
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
        }), 500


@exercises_bp.route('/<int:exercise_id>/attempts', methods=['GET'])
@requires_session
def get_exercise_attempts(exercise_id):
    """
    Get all attempts for an exercise in this session
    
    GET /exercises/1/attempts
    Response: {attempts: [{code, result, timestamp, attempt_number}, ...]}
    """
    session_id = flask_session.get('session_id')
    if mongo.db is None:
        return jsonify({
            'success': False,
            'error': 'DB not connected',
        }), 503
    
    try:
        attempts = list(mongo.db.attempts.find({
            'session_id': session_id,
            'exercise_id': exercise_id,
        }).sort('attempt_number', 1))
        
        # Remove ObjectIds
        for a in attempts:
            a.pop('_id', None)
        
        return jsonify({
            'success': True,
            'exercise_id': exercise_id,
            'attempts': attempts,
        }), 200
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
        }), 500
