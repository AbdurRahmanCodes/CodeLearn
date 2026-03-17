"""
Auth Routes - User Session Management
Handles: Session creation, mode selection
"""

from flask import Blueprint, request, jsonify, session as flask_session
from app.services import LearningJourney
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
        journey = LearningJourney(session_id)
        
        # Store session ID in Flask session for cookie-based tracking
        flask_session['session_id'] = session_id
        flask_session.pop('user_mode', None)
        
        return jsonify({
            'success': True,
            'session_id': session_id,
            'experiment_arm': journey.context['experiment_arm'],
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
    session_id = flask_session.get('session_id')
    
    mode = (request.get_json(silent=True) or {}).get('mode')
    
    if not mode:
        return jsonify({
            'success': False,
            'error': 'Missing required field: mode',
        }), 400
    
    try:
        journey = LearningJourney(session_id)
        
        if not journey.set_user_mode(mode):
            return jsonify({
                'success': False,
                'error': f'Invalid mode: {mode}. Must be "static" or "interactive".',
            }), 400

        flask_session['user_mode'] = mode
        
        return jsonify({
            'success': True,
            'mode': mode,
            'experiment_arm': journey.context['experiment_arm'],
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
    session_id = flask_session.get('session_id')
    
    try:
        journey = LearningJourney(session_id)
        
        return jsonify({
            'success': True,
            'session_id': session_id,
            'user_mode': journey.context.get('user_mode'),
            'experiment_arm': journey.context.get('experiment_arm'),
        }), 200
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
        }), 500
