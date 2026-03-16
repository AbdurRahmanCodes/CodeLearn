"""
Recommendation Service
Generates adaptive recommendations for B_adaptive arm only
"""

import uuid
from typing import Dict, List, Optional
from datetime import datetime


class RecommendationService:
    """
    Generates personalized recommendations based on learner performance
    (B_adaptive arm only)
    
    Rules:
    - Triggered after code submission failure
    - Based on error type (syntax, logic, runtime)
    - Logged to recommendations_log collection for research analysis
    """
    
    # Recommendation templates by error type
    RECOMMENDATIONS = {
        'syntax_error': {
            'type': 'syntax_guide',
            'title': 'Syntax Error Guide',
            'description': 'Review your code for syntax errors (quotes, parentheses, indentation)',
            'url': '/topic/syntax-guide',
            'reason': 'Your code has a syntax error. Check quotes, parentheses, colons, and indentation.',
        },
        'runtime_error': {
            'type': 'runtime_guide',
            'title': 'Runtime Error Guide',
            'description': 'Your code runs but encounters an error during execution',
            'url': '/topic/runtime-errors',
            'reason': 'Your code has a runtime error. Check variable names and operations.',
        },
        'logic_error': {
            'type': 'logic_guide',
            'title': 'Logic and Testing Guide',
            'description': 'Compare your output with the expected output to find the logic error',
            'url': '/topic/debugging',
            'reason': 'Your output doesn\'t match expected results. Try adding print() statements to debug.',
        },
        'timeout': {
            'type': 'timeout_guide',
            'title': 'Infinite Loop Check',
            'description': 'Your code may have an infinite loop. Check your loop conditions.',
            'url': '/topic/loops',
            'reason': 'Your code timed out. Check for infinite loops in for/while statements.',
        },
        'pass': {
            'type': 'next_challenge',
            'title': 'Great! Try the Next Exercise',
            'description': 'You passed this exercise. Ready for the next challenge?',
            'url': '/exercises',
            'reason': 'You solved this exercise! Move to the next one.',
        }
    }
    
    @staticmethod
    def generate_recommendation(
        session_id: str,
        exercise_id: int,
        language: str,
        result: str,  # "pass" or "fail"
        error_type: Optional[str] = None,
        attempt_number: int = 1,
    ) -> List[Dict]:
        """
        Generate recommendations for this attempt
        
        Args:
            session_id: User's session ID
            exercise_id: Which exercise (1-7)
            language: "python" or "javascript"
            result: "pass" or "fail"
            error_type: "syntax", "runtime", "logic", "timeout", or None
            attempt_number: How many times user has tried this exercise
            
        Returns:
            List of recommendation objects with id, type, title, reason, url
        """
        recommendations = []
        
        # No recommendations for passed exercises
        if result == 'pass':
            # Motiva recommendation (optional)
            rec = RecommendationService.RECOMMENDATIONS['pass'].copy()
            recommendations.append({
                'id': f'rec_{uuid.uuid4().hex[:8]}',
                'type': rec['type'],
                'title': rec['title'],
                'description': rec['description'],
                'url': rec['url'],
                'reason': rec['reason'],
                'exercise_id': exercise_id,
                'attempt_number': attempt_number,
                'language': language,
                'clicked': False,
                'timestamp': datetime.utcnow(),
            })
            return recommendations
        
        # Recommendations for failed attempts
        if error_type and error_type in RecommendationService.RECOMMENDATIONS:
            rec = RecommendationService.RECOMMENDATIONS[error_type].copy()
            recommendations.append({
                'id': f'rec_{uuid.uuid4().hex[:8]}',
                'type': rec['type'],
                'title': rec['title'],
                'description': rec['description'],
                'url': rec['url'],
                'reason': rec['reason'],
                'exercise_id': exercise_id,
                'attempt_number': attempt_number,
                'language': language,
                'clicked': False,
                'timestamp': datetime.utcnow(),
            })
        
        # Additional recommendations for repeated failures
        if attempt_number >= 3:
            # Suggest getting help after 3 failed attempts
            recommendations.append({
                'id': f'rec_{uuid.uuid4().hex[:8]}',
                'type': 'hint_request',
                'title': 'Try a Hint',
                'description': 'You\'ve attempted this several times. Would you like a hint?',
                'url': '/exercises/{}/hint'.format(exercise_id),
                'reason': f'You\'ve tried this exercise {attempt_number} times. A hint might help.',
                'exercise_id': exercise_id,
                'attempt_number': attempt_number,
                'language': language,
                'clicked': False,
                'timestamp': datetime.utcnow(),
            })
        
        return recommendations
    
    @staticmethod
    def log_recommendation(
        mongo,
        session_id: str,
        recommendation: Dict,
        clicked: bool = False,
    ) -> bool:
        """
        Log recommendation event to MongoDB for research analysis
        
        Args:
            mongo: PyMongo instance
            session_id: User's session ID
            recommendation: Recommendation dict from generate_recommendation()
            clicked: Whether user clicked/acted on recommendation
            
        Returns:
            True if logged successfully
        """
        try:
            doc = {
                'session_id': session_id,
                'recommendation_id': recommendation.get('id'),
                'type': recommendation.get('type'),
                'title': recommendation.get('title'),
                'exercise_id': recommendation.get('exercise_id'),
                'attempt_number': recommendation.get('attempt_number'),
                'reason': recommendation.get('reason'),
                'clicked': clicked,
                'timestamp': recommendation.get('timestamp', datetime.utcnow()),
            }
            
            mongo.db.recommendations_log.insert_one(doc)
            return True
            
        except Exception as e:
            print(f"Error logging recommendation: {e}")
            return False
