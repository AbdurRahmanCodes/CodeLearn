"""
Dashboard Routes - User Progress Visualization
Handles: Personal dashboard, study design, progress metrics
"""

from flask import Blueprint, jsonify, session as flask_session
from app import mongo
from app.services import LearningJourney
from app.utils import requires_session

dashboard_bp = Blueprint('dashboard', __name__, url_prefix='/dashboard')


@dashboard_bp.route('/user', methods=['GET'])
@requires_session
def get_user_dashboard():
    """
    Get learner's personal dashboard
    Shows: total attempts, pass rate, exercises completed, quiz scores
    
    GET /dashboard/user
    Response: {total_attempts, pass_rate, exercises_completed, ...}
    """
    session_id = flask_session.get('session_id')
    
    try:
        journey = LearningJourney(session_id)
        data = journey.get_user_dashboard_data()
        
        return jsonify({
            'success': True,
            'dashboard': data,
        }), 200
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
        }), 500


@dashboard_bp.route('/progress', methods=['GET'])
@requires_session
def get_progress_by_exercise():
    """
    Get progress by exercise (which ones passed, how many attempts)
    
    GET /dashboard/progress
    Response: {exercises: {1: {attempts: 2, passed: true}, 2: {...}}}
    """
    session_id = flask_session.get('session_id')
    
    try:
        # Query all attempts for this session
        attempts = list(mongo.db.attempts.find({
            'session_id': session_id,
        }).sort('exercise_id', 1))
        
        # Aggregate by exercise
        exercises = {}
        for attempt in attempts:
            ex_id = attempt['exercise_id']
            if ex_id not in exercises:
                exercises[ex_id] = {
                    'total_attempts': 0,
                    'passed': False,
                    'attempt_numbers': [],
                    'last_result': None,
                }
            
            exercises[ex_id]['total_attempts'] += 1
            exercises[ex_id]['attempt_numbers'].append(attempt['attempt_number'])
            exercises[ex_id]['last_result'] = attempt['result']
            
            if attempt['result'] == 'pass':
                exercises[ex_id]['passed'] = True
        
        return jsonify({
            'success': True,
            'exercises': exercises,
        }), 200
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
        }), 500


@dashboard_bp.route('/quizzes', methods=['GET'])
@requires_session
def get_quiz_performance():
    """
    Get quiz performance by topic
    
    GET /dashboard/quizzes
    Response: {quizzes: {variables: {score: 80, total: 100, percentage: 80}, ...}}
    """
    session_id = flask_session.get('session_id')
    
    try:
        quizzes = list(mongo.db.quiz_attempts.find({
            'session_id': session_id,
        }).sort('topic', 1))
        
        # Aggregate by topic (latest score)
        quiz_data = {}
        for quiz in quizzes:
            topic = quiz['topic']
            if topic not in quiz_data:
                quiz_data[topic] = []
            
            quiz_data[topic].append({
                'score': quiz['score'],
                'total': quiz['total'],
                'percentage': quiz['score_percentage'],
                'timestamp': quiz['timestamp'].isoformat() if hasattr(quiz['timestamp'], 'isoformat') else str(quiz['timestamp']),
            })
        
        return jsonify({
            'success': True,
            'quizzes': quiz_data,
        }), 200
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
        }), 500


@dashboard_bp.route('/recommendations', methods=['GET'])
@requires_session
def get_recommendations_history():
    """
    Get history of recommendations shown to this user
    (B_adaptive arm only)
    
    GET /dashboard/recommendations
    Response: {recommendations: [{id, type, title, clicked, timestamp}, ...]}
    """
    session_id = flask_session.get('session_id')
    
    try:
        recs = list(mongo.db.recommendations_log.find({
            'session_id': session_id,
        }).sort('timestamp', -1))
        
        # Remove ObjectIds
        for r in recs:
            r.pop('_id', None)
        
        return jsonify({
            'success': True,
            'recommendations': recs,
        }), 200
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
        }), 500
