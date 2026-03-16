"""
Unit Tests for LearningJourney Service
Tests the central orchestrator
"""

import pytest
import uuid
from datetime import datetime
from app import create_app, mongo
from app.services import LearningJourney


@pytest.fixture
def app():
    """Create test app"""
    app = create_app()
    app.config['TESTING'] = True
    app.config['MONGO_URI'] = 'mongodb://localhost:27017/codelearn_test'
    return app


@pytest.fixture
def client(app):
    """Create test client"""
    return app.test_client()


@pytest.fixture
def test_session_id():
    """Generate unique test session ID"""
    return f'test-session-{uuid.uuid4().hex[:8]}'


class TestLearningJourneyCreation:
    """Test journey creation and initialization"""
    
    def test_journey_creation(self, app, test_session_id):
        """Test: Can create a new LearningJourney"""
        with app.app_context():
            journey = LearningJourney(test_session_id)
            assert journey.session_id == test_session_id
            assert journey.context is not None
    
    def test_random_arm_assignment(self, app, test_session_id):
        """Test: Experiment arm is randomly assigned A or B"""
        with app.app_context():
            journey = LearningJourney(test_session_id)
            assert journey.context['experiment_arm'] in ['A_control', 'B_adaptive']
    
    def test_session_persists_in_database(self, app, test_session_id):
        """Test: Session context is saved to MongoDB"""
        with app.app_context():
            journey = LearningJourney(test_session_id)
            
            # Query database directly
            doc = mongo.db.session_context.find_one({'session_id': test_session_id})
            assert doc is not None
            assert doc['session_id'] == test_session_id


class TestUserMode:
    """Test user mode selection"""
    
    def test_set_static_mode(self, app, test_session_id):
        """Test: Can set mode to 'static'"""
        with app.app_context():
            journey = LearningJourney(test_session_id)
            result = journey.set_user_mode('static')
            assert result is True
            assert journey.context['user_mode'] == 'static'
    
    def test_set_interactive_mode(self, app, test_session_id):
        """Test: Can set mode to 'interactive'"""
        with app.app_context():
            journey = LearningJourney(test_session_id)
            result = journey.set_user_mode('interactive')
            assert result is True
            assert journey.context['user_mode'] == 'interactive'
    
    def test_invalid_mode_rejected(self, app, test_session_id):
        """Test: Invalid modes are rejected"""
        with app.app_context():
            journey = LearningJourney(test_session_id)
            result = journey.set_user_mode('invalid_mode')
            assert result is False


class TestAttemptSubmission:
    """Test submitting code attempts"""
    
    def test_submit_attempt(self, app, test_session_id):
        """Test: Can submit an attempt"""
        with app.app_context():
            journey = LearningJourney(test_session_id)
            journey.set_user_mode('interactive')
            
            result = journey.submit_attempt(
                exercise_id=1,
                code='x = 5',
                language='python'
            )
            
            assert result is not None
            assert 'attempt_number' in result
            assert result['attempt_number'] == 1
    
    def test_attempt_count_increments(self, app, test_session_id):
        """Test: Attempt numbers increment correctly"""
        with app.app_context():
            journey = LearningJourney(test_session_id)
            journey.set_user_mode('interactive')
            
            # Submit attempt 1
            result1 = journey.submit_attempt(1, 'x = 5', 'python')
            assert result1['attempt_number'] == 1
            
            # Submit attempt 2
            result2 = journey.submit_attempt(1, 'x = 10', 'python')
            assert result2['attempt_number'] == 2


class TestDashboardData:
    """Test dashboard data aggregation"""
    
    def test_get_dashboard_data(self, app, test_session_id):
        """Test: Can retrieve dashboard data"""
        with app.app_context():
            journey = LearningJourney(test_session_id)
            journey.set_user_mode('interactive')
            
            data = journey.get_user_dashboard_data()
            
            assert data is not None
            assert 'total_attempts' in data
            assert 'pass_rate' in data
            assert 'exercises_completed' in data
            assert 'experiment_arm' in data
            assert 'user_mode' in data


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
