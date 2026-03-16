"""
Admin Routes - Research Analytics & Data Export
Handles: Admin dashboard, data export, cohort analysis
"""

from flask import Blueprint, jsonify, session as flask_session
from app import mongo
from datetime import datetime

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')


@admin_bp.route('/stats', methods=['GET'])
def get_admin_stats():
    """
    Get aggregate stats across all sessions
    
    GET /admin/stats
    Response: {total_sessions, total_attempts, pass_rate_global, ...}
    """
    try:
        total_sessions = mongo.db.session_context.count_documents({})
        total_attempts = mongo.db.attempts.count_documents({})
        total_quizzes = mongo.db.quiz_attempts.count_documents({})
        
        # Calculate global pass rate
        pass_attempts = mongo.db.attempts.count_documents({'result': 'pass'})
        global_pass_rate = (pass_attempts / total_attempts * 100) if total_attempts > 0 else 0
        
        # Count by arm
        arm_a = mongo.db.session_context.count_documents({'experiment_arm': 'A_control'})
        arm_b = mongo.db.session_context.count_documents({'experiment_arm': 'B_adaptive'})
        
        # Count by mode
        mode_static = mongo.db.session_context.count_documents({'user_mode': 'static'})
        mode_interactive = mongo.db.session_context.count_documents({'user_mode': 'interactive'})
        
        return jsonify({
            'success': True,
            'stats': {
                'total_sessions': total_sessions,
                'total_attempts': total_attempts,
                'total_quizzes': total_quizzes,
                'global_pass_rate': round(global_pass_rate, 1),
                'pass_attempts': pass_attempts,
                'experiment_distribution': {
                    'A_control': arm_a,
                    'B_adaptive': arm_b,
                },
                'mode_distribution': {
                    'static': mode_static,
                    'interactive': mode_interactive,
                },
            },
        }), 200
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
        }), 500


@admin_bp.route('/cohort-comparison', methods=['GET'])
def cohort_comparison():
    """
    Compare metrics between A_control and B_adaptive arms
    
    GET /admin/cohort-comparison
    Response: {A_control: {...stats}, B_adaptive: {...stats}}
    """
    try:
        def get_arm_stats(arm):
            sessions_in_arm = mongo.db.session_context.count_documents({'experiment_arm': arm})
            attempts_in_arm = mongo.db.attempts.count_documents({'experiment_arm': arm})
            pass_in_arm = mongo.db.attempts.count_documents({'experiment_arm': arm, 'result': 'pass'})
            pass_rate = (pass_in_arm / attempts_in_arm * 100) if attempts_in_arm > 0 else 0
            
            quizzes_in_arm = mongo.db.quiz_attempts.count_documents({'experiment_arm': arm})
            
            return {
                'sessions': sessions_in_arm,
                'total_attempts': attempts_in_arm,
                'pass_attempts': pass_in_arm,
                'pass_rate': round(pass_rate, 1),
                'total_quizzes': quizzes_in_arm,
            }
        
        return jsonify({
            'success': True,
            'cohorts': {
                'A_control': get_arm_stats('A_control'),
                'B_adaptive': get_arm_stats('B_adaptive'),
            },
        }), 200
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
        }), 500


@admin_bp.route('/exercise-difficulty', methods=['GET'])
def exercise_difficulty():
    """
    Analyze pass rates per exercise
    
    GET /admin/exercise-difficulty
    Response: {exercises: {1: {attempts: 100, passes: 80, pass_rate: 80}, ...}}
    """
    try:
        result = {}
        
        for ex_id in range(1, 8):  # Exercises 1-7
            attempts = mongo.db.attempts.count_documents({'exercise_id': ex_id})
            passes = mongo.db.attempts.count_documents({'exercise_id': ex_id, 'result': 'pass'})
            pass_rate = (passes / attempts * 100) if attempts > 0 else 0
            
            result[ex_id] = {
                'total_attempts': attempts,
                'pass_attempts': passes,
                'pass_rate': round(pass_rate, 1),
            }
        
        return jsonify({
            'success': True,
            'exercises': result,
        }), 200
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
        }), 500


@admin_bp.route('/export-attempts/<format>', methods=['GET'])
def export_attempts(format):
    """
    Export all attempts data
    
    GET /admin/export-attempts/json
    Response: [attempt documents]
    """
    if format not in ['json', 'csv']:
        return jsonify({
            'success': False,
            'error': 'Format must be "json" or "csv"',
        }), 400
    
    try:
        attempts = list(mongo.db.attempts.find())
        
        # Remove ObjectIds
        for a in attempts:
            a.pop('_id', None)
        
        if format == 'json':
            return jsonify({
                'success': True,
                'data': attempts,
                'count': len(attempts),
            }), 200
        
        elif format == 'csv':
            # Basic CSV export
            import csv
            from io import StringIO
            
            if not attempts:
                return jsonify({'success': True, 'data': ''}), 200
            
            output = StringIO()
            writer = csv.DictWriter(output, fieldnames=attempts[0].keys())
            writer.writeheader()
            writer.writerows(attempts)
            
            return output.getvalue(), 200, {'Content-Type': 'text/csv', 'Content-Disposition': 'attachment; filename=attempts.csv'}
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
        }), 500
