"""
Auth Routes - User Session Management
Handles: Session creation, mode selection
"""

from flask import Blueprint, request, jsonify, session as flask_session
from app.data import normalize_language
from app.services.learning_engine import LearningEngine
from app.utils import requires_session
import uuid

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')


@auth_bp.route('/session', methods=['POST'])
def create_session():
    """
    Create a new user session and assign experiment arm
    
    POST /auth/session
    Response: {session_id, experiment_arm}
    """
    session_id = str(uuid.uuid4())
    
    try:
        # Initialize learning journey (creates session in MongoDB)
        journey = LearningEngine(session_id)
        
        # Store session ID in Flask session for cookie-based tracking
        flask_session['session_id'] = session_id
        flask_session.pop('user_mode', None)
        flask_session.pop('mode', None)
        
        return jsonify({
            'success': True,
            'session_id': session_id,
            'experiment_arm': journey.context.get('experiment_arm', 'control'),
            'message': 'Session created successfully',
        }), 201
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
        }), 500


@auth_bp.route('/select-mode', methods=['POST'])
@requires_session
def select_mode():
    """
    User selects learning mode (Static or Interactive)
    
    POST /auth/select-mode
    Body: {mode: "static" or "interactive"}
    Response: {mode, updated_at}
    """
    session_id = str(flask_session.get('session_id') or '')
    
    payload = request.get_json(silent=True) or {}
    mode = payload.get('mode')
    requested_language = payload.get('language')
    
    if not mode:
        return jsonify({
            'success': False,
            'error': 'Missing required field: mode',
        }), 400
    
    try:
        journey = LearningEngine(session_id)
        
        if not journey.set_user_mode(mode):
            return jsonify({
                'success': False,
                'error': f'Invalid mode: {mode}. Must be "static" or "interactive".',
            }), 400

        flask_session['user_mode'] = mode
        flask_session['mode'] = mode
        if requested_language:
            flask_session['selected_language'] = normalize_language(requested_language)
        
        return jsonify({
            'success': True,
            'mode': mode,
            'language': flask_session.get('selected_language', 'python'),
            'experiment_arm': journey.context.get('experiment_arm', 'control'),
            'message': f'Mode set to {mode}',
        }), 200
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
        }), 500


@auth_bp.route('/status', methods=['GET'])
@requires_session
def session_status():
    """
    Get current session status
    
    GET /auth/status
    Response: {session_id, mode, experiment_arm}
    """
    session_id = str(flask_session.get('session_id') or '')
    
    try:
        journey = LearningEngine(session_id)
        
        return jsonify({
            'success': True,
            'session_id': session_id,
            'mode': journey.context.get('mode') or journey.context.get('user_mode'),
            'user_mode': journey.context.get('mode') or journey.context.get('user_mode'),
            'experiment_arm': journey.context.get('experiment_arm', 'control'),
        }), 200
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
        }), 500
