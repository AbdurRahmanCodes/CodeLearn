"""
Exercises Routes - Code Submission & Exercise Display
Handles: Exercise display, code submission, attempt logging
"""

from flask import Blueprint, request, jsonify, session as flask_session
from app import mongo
from app.services import LearningJourney
from app.utils import requires_mode_selected, requires_session

exercises_bp = Blueprint('exercises', __name__, url_prefix='/exercises')


@exercises_bp.route('/<int:exercise_id>', methods=['GET'])
@requires_session
def get_exercise(exercise_id):
    """
    Get exercise details
    
    GET /exercises/1
    Response: {exercise_id, title, description, test_cases}
    """
    session_id = flask_session.get('session_id')
    
    if exercise_id < 1 or exercise_id > 7:
        return jsonify({
            'success': False,
            'error': 'Exercise ID must be between 1 and 7',
        }), 400
    
    try:
        # Query exercise from MongoDB
        exercise = mongo.db.exercises.find_one({'exercise_id': exercise_id})
        
        if not exercise:
            return jsonify({
                'success': False,
                'error': f'Exercise {exercise_id} not found',
            }), 404
        
        # Remove MongoDB ObjectId for JSON serialization
        exercise.pop('_id', None)
        
        return jsonify({
            'success': True,
            'exercise': exercise,
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
    session_id = flask_session.get('session_id')
    
    data = request.json or {}
    code = data.get('code')
    language = data.get('language')
    
    if not code or not language:
        return jsonify({
            'success': False,
            'error': 'Missing required fields: code, language',
        }), 400
    
    if exercise_id < 1 or exercise_id > 7:
        return jsonify({
            'success': False,
            'error': 'Exercise ID must be between 1 and 7',
        }), 400
    
    if language not in ['python', 'javascript']:
        return jsonify({
            'success': False,
            'error': 'Language must be "python" or "javascript"',
        }), 400
    
    try:
        journey = LearningJourney(session_id)
        
        # Submit attempt (will execute code and log)
        result = journey.submit_attempt(exercise_id, code, language)
        
        return jsonify({
            'success': True,
            'result': result,
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
