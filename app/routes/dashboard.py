"""
Dashboard Routes - User Progress Visualization
Handles: Personal dashboard, study design, progress metrics
"""

from flask import Blueprint, jsonify, session as flask_session
from app import mongo
from app.data import LEARNING_TRACKS, get_topic_content, normalize_language
from app.services.learning_engine import LearningEngine
from app.utils import requires_session

dashboard_bp = Blueprint('dashboard', __name__, url_prefix='/dashboard')


def _db_or_none():
    return mongo.db if mongo.db is not None else None


def _identity_query() -> dict:
    session_id = str(flask_session.get('session_id') or '')
    participant_ref = str(flask_session.get('participant_ref') or '')
    if participant_ref:
        return {'$or': [{'user_id': participant_ref}, {'session_id': session_id}]}
    return {'session_id': session_id}


@dashboard_bp.route('/user', methods=['GET'])
@requires_session
def get_user_dashboard():
    """
    Get learner's personal dashboard
    Shows: total attempts, pass rate, exercises completed, quiz scores
    
    GET /dashboard/user
    Response: {total_attempts, pass_rate, exercises_completed, ...}
    """
    db = _db_or_none()
    if db is None:
        return jsonify({'success': False, 'error': 'DB not connected'}), 503

    identity_query = _identity_query()

    try:
        attempts = list(db.attempts.find(identity_query))
        quizzes = list(db.quiz_attempts.find(identity_query))

        total_attempts = len(attempts)
        passed_attempts = sum(1 for row in attempts if row.get('result') == 'pass')
        pass_rate = round((passed_attempts / total_attempts) * 100, 1) if total_attempts else 0
        completed_exercises = len({row.get('exercise_id') for row in attempts if row.get('result') == 'pass'})

        avg_quiz = 0.0
        if quizzes:
            avg_quiz = round(sum(float(row.get('score_pct', 0) or 0) for row in quizzes) / len(quizzes), 1)

        data = {
            'total_attempts': total_attempts,
            'pass_rate': pass_rate,
            'exercises_completed': completed_exercises,
            'average_quiz_score': avg_quiz,
        }
        
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
    identity_query = _identity_query()
    db = _db_or_none()
    if db is None:
        return jsonify({'success': False, 'error': 'DB not connected'}), 503
    
    try:
        # Query all attempts for this session
        attempts = list(db.attempts.find(identity_query).sort('exercise_id', 1))
        
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
    identity_query = _identity_query()
    db = _db_or_none()
    if db is None:
        return jsonify({'success': False, 'error': 'DB not connected'}), 503
    
    try:
        quizzes = list(db.quiz_attempts.find(identity_query).sort('topic', 1))
        
        # Aggregate by topic (latest score)
        quiz_data = {}
        for quiz in quizzes:
            topic = quiz['topic']
            if topic not in quiz_data:
                quiz_data[topic] = []

            score = quiz.get('score', 0)
            total = quiz.get('total', quiz.get('total_questions', 0))
            percentage = quiz.get('score_percentage', quiz.get('score_pct', 0))
            timestamp = quiz.get('timestamp')
            
            quiz_data[topic].append({
                'score': score,
                'total': total,
                'percentage': percentage,
                'timestamp': timestamp.isoformat() if hasattr(timestamp, 'isoformat') else str(timestamp),
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
    identity_query = _identity_query()
    db = _db_or_none()
    if db is None:
        return jsonify({'success': False, 'error': 'DB not connected'}), 503
    
    try:
        recs = list(db.recommendations_log.find(identity_query).sort('timestamp', -1))
        
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


@dashboard_bp.route('/weak-topics', methods=['GET'])
@requires_session
def get_weak_topics():
    """Return weak topics for current session ordered by failure rate."""
    identity_query = _identity_query()
    db = _db_or_none()
    if db is None:
        return jsonify({'success': False, 'error': 'DB not connected'}), 503

    try:
        attempts = list(db.attempts.find(identity_query))
        by_topic = {}
        for row in attempts:
            topic = row.get('topic') or 'unknown'
            bucket = by_topic.setdefault(topic, {'topic': topic, 'total': 0, 'failed': 0, 'passed': 0})
            bucket['total'] += 1
            if row.get('result') == 'pass':
                bucket['passed'] += 1
            else:
                bucket['failed'] += 1

        rows = []
        for item in by_topic.values():
            total = max(item['total'], 1)
            failure_rate = round((item['failed'] / total) * 100, 1)
            rows.append({
                'topic': item['topic'],
                'total_attempts': item['total'],
                'failed_attempts': item['failed'],
                'passed_attempts': item['passed'],
                'failure_rate': failure_rate,
            })

        rows.sort(key=lambda x: (-x['failure_rate'], -x['failed_attempts'], x['topic']))
        return jsonify({'success': True, 'weak_topics': rows[:4]}), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@dashboard_bp.route('/learning-path', methods=['GET'])
@requires_session
def get_learning_path():
    """Return progression status for selected language track topics."""
    identity_query = _identity_query()
    db = _db_or_none()
    if db is None:
        return jsonify({'success': False, 'error': 'DB not connected'}), 503

    language = normalize_language(flask_session.get('selected_language'))
    topics = LEARNING_TRACKS.get(language, [])

    try:
        attempts = list(db.attempts.find({**identity_query, 'programming_language': language}))
        path = []
        for topic in topics:
            topic_attempts = [a for a in attempts if a.get('topic') == topic]
            passed = any(a.get('result') == 'pass' for a in topic_attempts)
            if passed:
                status = 'mastered'
            elif topic_attempts:
                status = 'in_progress'
            else:
                status = 'not_started'
            path.append({
                'topic': topic,
                'status': status,
                'attempts': len(topic_attempts),
                'passed': passed,
            })

        return jsonify({'success': True, 'language': language, 'path': path}), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@dashboard_bp.route('/recommended-next-step', methods=['GET'])
@requires_session
def get_recommended_next_step():
    """Recommend next action using weakness + progression signals."""
    identity_query = _identity_query()
    db = _db_or_none()
    if db is None:
        return jsonify({'success': False, 'error': 'DB not connected'}), 503

    language = normalize_language(flask_session.get('selected_language'))
    topics = LEARNING_TRACKS.get(language, [])

    try:
        attempts = list(db.attempts.find({**identity_query, 'programming_language': language}))
        if not attempts:
            first_topic = topics[0] if topics else 'variables'
            return jsonify({
                'success': True,
                'recommendation': {
                    'type': 'start_track',
                    'language': language,
                    'topic': first_topic,
                    'message': f'Start with {first_topic} in the {language} track.',
                    'video_url': (get_topic_content(language, first_topic) or {}).get('video_url', ''),
                    'quiz_url': f'/quiz/{first_topic}?lang={language}',
                    'learn_url': f'/learn/{first_topic}?lang={language}',
                }
            }), 200

        by_topic = {}
        for row in attempts:
            topic = row.get('topic') or 'unknown'
            bucket = by_topic.setdefault(topic, {'total': 0, 'failed': 0, 'last_attempt': 0})
            bucket['total'] += 1
            if row.get('result') == 'fail':
                bucket['failed'] += 1
            bucket['last_attempt'] = max(bucket['last_attempt'], int(row.get('attempt_number', 0) or 0))

        weak_topic = None
        weak_score = -1
        for topic, stats in by_topic.items():
            score = stats['failed']
            if score > weak_score:
                weak_score = score
                weak_topic = topic

        if weak_topic and by_topic.get(weak_topic, {}).get('failed', 0) >= 2:
            info = get_topic_content(language, weak_topic) or {}
            return jsonify({
                'success': True,
                'recommendation': {
                    'type': 'remedial_topic',
                    'language': language,
                    'topic': weak_topic,
                    'message': f'You are struggling with {weak_topic}. Review the short video and retake the topic quiz before retrying.',
                    'video_url': info.get('video_url', ''),
                    'quiz_url': f'/quiz/{weak_topic}?lang={language}',
                    'learn_url': f'/learn/{weak_topic}?lang={language}',
                }
            }), 200

        # Otherwise recommend next unmastered topic in learning order.
        passed_topics = {a.get('topic') for a in attempts if a.get('result') == 'pass'}
        next_topic = next((t for t in topics if t not in passed_topics), topics[-1] if topics else 'variables')
        info = get_topic_content(language, next_topic) or {}
        return jsonify({
            'success': True,
            'recommendation': {
                'type': 'progression',
                'language': language,
                'topic': next_topic,
                'message': f'Proceed to {next_topic} to continue your learning path.',
                'video_url': info.get('video_url', ''),
                'quiz_url': f'/quiz/{next_topic}?lang={language}',
                'learn_url': f'/learn/{next_topic}?lang={language}',
            }
        }), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
