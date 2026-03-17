"""
LearningJourney Service
Central orchestrator for user's learning journey
"""

import random
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional
from app import mongo
from app.models import Session, Attempt, QuizAttempt


class LearningJourney:
    """
    Central orchestrator that manages a user's entire learning path
    
    Coordinates:
    - Session state management
    - Attempt submission and logging
    - Quiz submission and scoring
    - Recommendation generation
    - Dashboard data aggregation
    """
    
    def __init__(self, session_id: str):
        """
        Initialize journey with session ID
        
        Args:
            session_id: Unique identifier for this user session
        """
        self.session_id = session_id
        self.context = self._get_or_create_session_context()
    
    def _get_or_create_session_context(self) -> Dict:
        """
        Retrieve existing session context from DB or create new one
        
        Returns:
            Dictionary containing session context
        """
        # Try to find existing session
        context = mongo.db.session_context.find_one({'session_id': self.session_id})
        
        if context:
            return context
        
        # Create new session context
        new_context = {
            'session_id': self.session_id,
            'user_mode': None,  # Will be set by user selection
            'experiment_arm': random.choice(['A_control', 'B_adaptive']),  # RANDOMIZED
            'current_exercise_id': None,
            'quiz_scores_by_topic': {},
            'recommendations_seen': [],
            'created_at': datetime.now(timezone.utc),
            'updated_at': datetime.now(timezone.utc),
        }
        
        # Insert into database
        mongo.db.session_context.insert_one(new_context)
        return new_context
    
    def set_user_mode(self, mode: str) -> bool:
        """
        User selects learning mode (Static or Interactive)
        
        Args:
            mode: "static" or "interactive"
            
        Returns:
            True if successful, False if invalid mode
        """
        if mode not in ['static', 'interactive']:
            return False
        
        self.context['user_mode'] = mode
        self.context['updated_at'] = datetime.now(timezone.utc)
        
        # Persist to database
        mongo.db.session_context.update_one(
            {'session_id': self.session_id},
            {
                '$set': {
                    'user_mode': mode,
                    'updated_at': datetime.now(timezone.utc)
                }
            }
        )
        
        return True
    
    def submit_attempt(self, exercise_id: int, code: str, language: str) -> Dict:
        """
        User submits code for an exercise
        
        Args:
            exercise_id: Which exercise (1-7)
            code: The submitted code
            language: "python" or "javascript"
            
        Returns:
            Dictionary with keys:
            - result: {tests_passed, total_tests, error_type, output}
            - pass_fail: "pass" or "fail"
            - recommendations: [] (if B_adaptive)
            - next_exercise: exercise_id + 1 if passed, else None
        """
        # Import here to avoid circular imports
        from app.services.exercise_service import ExerciseService
        from app.services.recommendation_service import RecommendationService
        
        # Get attempt number for this exercise
        attempt_num = self._get_attempt_count(exercise_id) + 1
        
        # Execute code with real ExerciseService
        result = self._execute_code(code, language, exercise_id)
        
        # Determine pass/fail
        pass_fail = "pass" if result.get('pass_fail') == 'pass' else "fail"
        
        # Log attempt to MongoDB
        attempt_doc = {
            'session_id': self.session_id,
            'exercise_id': exercise_id,
            'code': code,
            'language': language,
            'attempt_number': attempt_num,
            'result': pass_fail,
            'error_type': result.get('error_type'),
            'timestamp': datetime.now(timezone.utc),
            'experiment_arm': self.context['experiment_arm'],
            'user_mode': self.context['user_mode'],
        }
        mongo.db.attempts.insert_one(attempt_doc)
        
        # Generate recommendations if B_adaptive arm
        recommendations = []
        if self.context['experiment_arm'] == 'B_adaptive':
            recs = RecommendationService.generate_recommendation(
                session_id=self.session_id,
                exercise_id=exercise_id,
                language=language,
                result=pass_fail,
                error_type=result.get('error_type'),
                attempt_number=attempt_num,
            )
            # Log recommendations
            for rec in recs:
                RecommendationService.log_recommendation(mongo, self.session_id, rec, clicked=False)
            recommendations = recs
        
        return {
            'result': result,
            'pass_fail': pass_fail,
            'attempt_number': attempt_num,
            'recommendations': recommendations,
            'next_exercise': exercise_id + 1 if pass_fail == "pass" else None,
        }
    
    def submit_quiz(self, topic: str, score: int, total: int) -> Dict:
        """
        User completes a quiz
        
        Args:
            topic: Which topic ("variables", "loops", etc.)
            score: Points earned
            total: Total points possible
            
        Returns:
            Dictionary with quiz results
        """
        # Log quiz to MongoDB
        quiz_doc = {
            'session_id': self.session_id,
            'topic': topic,
            'score': score,
            'total': total,
            'score_percentage': (score / total * 100) if total > 0 else 0,
            'timestamp': datetime.now(timezone.utc),
            'experiment_arm': self.context['experiment_arm'],
            'user_mode': self.context['user_mode'],
        }
        mongo.db.quiz_attempts.insert_one(quiz_doc)
        
        # Update session context
        mongo.db.session_context.update_one(
            {'session_id': self.session_id},
            {
                '$set': {
                    f'quiz_scores_by_topic.{topic}': score,
                    'updated_at': datetime.now(timezone.utc)
                }
            }
        )
        
        self.context['quiz_scores_by_topic'][topic] = score
        
        return {
            'topic': topic,
            'score': score,
            'total': total,
            'percentage': quiz_doc['score_percentage'],
        }
    
    def get_user_dashboard_data(self) -> Dict:
        """
        Get learner's personal dashboard data
        (What THEY see about their own progress)
        
        Returns:
            Dictionary with personalized insights
        """
        # Query attempts for this session
        attempts = list(mongo.db.attempts.find({'session_id': self.session_id}))
        quizzes = list(mongo.db.quiz_attempts.find({'session_id': self.session_id}))
        recommendations = list(mongo.db.recommendations_log.find({'session_id': self.session_id})) if mongo.db.recommendations_log.find_one({'session_id': self.session_id}) else []
        
        # Compute metrics
        total_attempts = len(attempts)
        pass_attempts = sum(1 for a in attempts if a['result'] == 'pass')
        pass_rate = (pass_attempts / total_attempts * 100) if total_attempts > 0 else 0
        
        # Unique exercises completed (passed)
        exercises_completed = len(set(a['exercise_id'] for a in attempts if a['result'] == 'pass'))
        
        # Quiz stats
        avg_quiz_score = (sum(q['score_percentage'] for q in quizzes) / len(quizzes)) if quizzes else 0
        
        return {
            'total_attempts': total_attempts,
            'pass_rate': round(pass_rate, 1),
            'exercises_completed': exercises_completed,
            'quizzes_taken': len(quizzes),
            'average_quiz_score': round(avg_quiz_score, 1),
            'recommendations_seen': len(recommendations),
            'experiment_arm': self.context['experiment_arm'],
            'user_mode': self.context['user_mode'],
            'current_exercise': self.context.get('current_exercise_id'),
        }
    
    # ============ PRIVATE HELPERS ============
    
    def _get_attempt_count(self, exercise_id: int) -> int:
        """Count how many times user has attempted this exercise"""
        return mongo.db.attempts.count_documents({
            'session_id': self.session_id,
            'exercise_id': exercise_id,
        })
    
    def _execute_code(self, code: str, language: str, exercise_id: int) -> Dict:
        """
        Execute code and validate against test cases
        Uses ExerciseService (moved from old app.py)
        """
        from app.services.exercise_service import ExerciseService
        
        try:
            # Get exercise from MongoDB
            exercise = mongo.db.exercises.find_one({'exercise_id': exercise_id})
            
            if not exercise:
                return {
                    'tests_passed': 0,
                    'total_tests': 0,
                    'error_type': 'not_found',
                    'output': f'Exercise {exercise_id} not found',
                    'pass_fail': 'fail',
                }
            
            # Execute code against test cases
            result = ExerciseService.execute_and_evaluate(
                code=code,
                language=language,
                exercise=exercise,
                timeout=5
            )
            
            return result
            
        except Exception as e:
            return {
                'tests_passed': 0,
                'total_tests': 1,
                'error_type': 'runtime',
                'output': f'Error during execution: {str(e)}',
                'pass_fail': 'fail',
            }
