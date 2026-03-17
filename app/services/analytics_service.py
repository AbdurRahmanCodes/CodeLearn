"""
Analytics Service
Aggregates and analyzes learning outcomes and A/B experiment results
"""

from typing import Dict, List
from datetime import datetime, timedelta, timezone


class AnalyticsService:
    """
    Provides research analytics and insights from learning data
    """
    
    @staticmethod
    def get_user_attempt_stats(mongo, session_id: str) -> Dict:
        """
        Get this user's attempt statistics
        
        Returns: {total, passed, failed, avg_attempts_per_exercise, error_distribution}
        """
        attempts = list(mongo.db.attempts.find({'session_id': session_id}))
        
        if not attempts:
            return {
                'total': 0,
                'passed': 0,
                'failed': 0,
                'pass_rate': 0,
                'avg_attempts': 0,
                'error_distribution': {}
            }
        
        passed = sum(1 for a in attempts if a['result'] == 'pass')
        failed = len(attempts) - passed
        
        # Error distribution
        errors = {}
        for a in attempts:
            if a.get('error_type'):
                errors[a['error_type']] = errors.get(a['error_type'], 0) + 1
        
        # Attempts per exercise
        exercises_attempted = set(a['exercise_id'] for a in attempts)
        avg_attempts = len(attempts) / len(exercises_attempted) if exercises_attempted else 0
        
        return {
            'total': len(attempts),
            'passed': passed,
            'failed': failed,
            'pass_rate': round(passed / len(attempts) * 100, 1) if attempts else 0,
            'avg_attempts_per_exercise': round(avg_attempts, 1),
            'error_distribution': errors,
        }
    
    @staticmethod
    def get_user_quiz_stats(mongo, session_id: str) -> Dict:
        """
        Get this user's quiz statistics
        
        Returns: {total_quizzes, topics_covered, avg_score, best_topic, worst_topic}
        """
        quizzes = list(mongo.db.quiz_attempts.find({'session_id': session_id}))
        
        if not quizzes:
            return {
                'total_quizzes': 0,
                'topics_covered': 0,
                'average_score': 0,
                'best_topic': None,
                'worst_topic': None,
                'topic_scores': {}
            }
        
        # Aggregate by topic (latest score only)
        topic_scores = {}
        for quiz in quizzes:
            topic = quiz['topic']
            topic_scores[topic] = quiz['score_percentage']
        
        avg_score = sum(topic_scores.values()) / len(topic_scores) if topic_scores else 0
        best_topic = max(topic_scores, key=topic_scores.get) if topic_scores else None
        worst_topic = min(topic_scores, key=topic_scores.get) if topic_scores else None
        
        return {
            'total_quizzes': len(quizzes),
            'topics_covered': len(topic_scores),
            'average_score': round(avg_score, 1),
            'best_topic': best_topic,
            'worst_topic': worst_topic,
            'topic_scores': topic_scores,
        }
    
    @staticmethod
    def cohort_comparison(mongo) -> Dict:
        """
        Compare A_control vs B_adaptive cohorts
        
        Returns: {
            'A_control': {pass_rate, avg_attempts, avg_quiz_score, ...},
            'B_adaptive': {pass_rate, avg_attempts, avg_quiz_score, ...}
        }
        """
        
        def get_arm_stats(arm):
            attempts = list(mongo.db.attempts.find({'experiment_arm': arm}))
            quizzes = list(mongo.db.quiz_attempts.find({'experiment_arm': arm}))
            
            if not attempts:
                return {
                    'sessions': 0,
                    'total_attempts': 0,
                    'pass_rate': 0,
                    'avg_attempts_per_session': 0,
                    'quiz_attempts': 0,
                    'avg_quiz_score': 0,
                    'recommendations_shown': 0,
                }
            
            passed = sum(1 for a in attempts if a['result'] == 'pass')
            pass_rate = passed / len(attempts) * 100
            
            sessions = len(set(a['session_id'] for a in attempts))
            avg_attempts = len(attempts) / sessions if sessions > 0 else 0
            
            if quizzes:
                avg_quiz_score = sum(q['score_percentage'] for q in quizzes) / len(quizzes)
            else:
                avg_quiz_score = 0
            
            # Count recommendations for B_adaptive
            recs = mongo.db.recommendations_log.count_documents({'experiment_arm': arm})
            
            return {
                'sessions': sessions,
                'total_attempts': len(attempts),
                'pass_rate': round(pass_rate, 1),
                'avg_attempts_per_session': round(avg_attempts, 1),
                'quiz_attempts': len(quizzes),
                'avg_quiz_score': round(avg_quiz_score, 1),
                'recommendations_shown': recs,
            }
        
        return {
            'A_control': get_arm_stats('A_control'),
            'B_adaptive': get_arm_stats('B_adaptive'),
        }
    
    @staticmethod
    def exercise_difficulty_ranking(mongo) -> List[Dict]:
        """
        Rank exercises by pass rate (easiest to hardest)
        
        Returns: [{exercise_id, pass_rate, attempts, passes}, ...]
        """
        result = []
        
        for ex_id in range(1, 8):
            attempts = mongo.db.attempts.count_documents({'exercise_id': ex_id})
            passes = mongo.db.attempts.count_documents({'exercise_id': ex_id, 'result': 'pass'})
            
            if attempts > 0:
                pass_rate = passes / attempts * 100
                result.append({
                    'exercise_id': ex_id,
                    'pass_rate': round(pass_rate, 1),
                    'total_attempts': attempts,
                    'pass_attempts': passes,
                    'difficulty': 'Easy' if pass_rate >= 80 else 'Medium' if pass_rate >= 50 else 'Hard',
                })
        
        # Sort by pass rate (descending)
        return sorted(result, key=lambda x: x['pass_rate'], reverse=True)
    
    @staticmethod
    def get_platform_health(mongo) -> Dict:
        """
        Get overall platform metrics (for admin dashboard)
        
        Returns: {
            'total_sessions': int,
            'total_attempts': int,
            'global_pass_rate': float,
            'avg_attempts_per_session': float,
            'mode_distribution': {static: int, interactive: int},
            'arm_distribution': {A_control: int, B_adaptive: int},
            'active_sessions_24h': int,
        }
        """
        total_sessions = mongo.db.session_context.count_documents({})
        total_attempts = mongo.db.attempts.count_documents({})
        pass_attempts = mongo.db.attempts.count_documents({'result': 'pass'})
        
        global_pass_rate = pass_attempts / total_attempts * 100 if total_attempts > 0 else 0
        avg_attempts = total_attempts / total_sessions if total_sessions > 0 else 0
        
        mode_static = mongo.db.session_context.count_documents({'user_mode': 'static'})
        mode_interactive = mongo.db.session_context.count_documents({'user_mode': 'interactive'})
        
        arm_a = mongo.db.session_context.count_documents({'experiment_arm': 'A_control'})
        arm_b = mongo.db.session_context.count_documents({'experiment_arm': 'B_adaptive'})
        
        # Active in last 24 hours
        cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
        active_24h = mongo.db.attempts.count_documents({'timestamp': {'$gte': cutoff}})
        
        return {
            'total_sessions': total_sessions,
            'total_attempts': total_attempts,
            'global_pass_rate': round(global_pass_rate, 1),
            'avg_attempts_per_session': round(avg_attempts, 1),
            'mode_distribution': {
                'static': mode_static,
                'interactive': mode_interactive,
            },
            'arm_distribution': {
                'A_control': arm_a,
                'B_adaptive': arm_b,
            },
            'active_sessions_24h': active_24h,
        }
