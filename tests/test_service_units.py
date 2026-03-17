import types

from app.services.analytics_service import AnalyticsService
from app.services.exercise_service import ExerciseService
from app.services.recommendation_service import RecommendationService


class FakeCollection:
    def __init__(self, items=None):
        self.items = items or []

    def find(self, query=None):
        query = query or {}
        return [item for item in self.items if all(item.get(k) == v for k, v in query.items())]

    def count_documents(self, query=None):
        query = query or {}
        return len([item for item in self.items if all(item.get(k) == v for k, v in query.items())])


class FakeMongo:
    def __init__(self, attempts=None, quizzes=None, recs=None, sessions=None):
        self.db = types.SimpleNamespace(
            attempts=FakeCollection(attempts),
            quiz_attempts=FakeCollection(quizzes),
            recommendations_log=FakeCollection(recs),
            session_context=FakeCollection(sessions),
        )


def test_exercise_service_run_code_python_success():
    result = ExerciseService.run_code("print('ok')", "python")
    assert result["error"] is None
    assert result["stdout"] == "ok"


def test_exercise_service_run_code_python_syntax_error():
    result = ExerciseService.run_code("if True print('x')", "python")
    assert result["error_type"] == "syntax"
    assert "Syntax Error" in result["error"]


def test_exercise_service_evaluate_test_cases_logic_fail():
    exercise = {
        "test_cases": [
            {"check_type": "output", "expected": "42"},
        ]
    }
    exec_result = {
        "stdout": "41",
        "error": None,
        "error_type": None,
        "local_vars": {},
        "execution_time_ms": 1.0,
    }
    result = ExerciseService.evaluate_test_cases(exercise, exec_result)
    assert result["result"] == "fail"
    assert result["error_type"] == "logic"


def test_recommendation_service_generates_hint_for_repeated_failures():
    recs = RecommendationService.generate_recommendation(
        session_id="s1",
        exercise_id=2,
        language="python",
        result="fail",
        error_type="logic_error",
        attempt_number=3,
    )
    types_seen = {r["type"] for r in recs}
    assert "logic_guide" in types_seen
    assert "hint_request" in types_seen


def test_analytics_service_get_user_attempt_stats():
    mongo = FakeMongo(
        attempts=[
            {"session_id": "s1", "exercise_id": 1, "result": "pass", "error_type": None},
            {"session_id": "s1", "exercise_id": 2, "result": "fail", "error_type": "logic"},
            {"session_id": "s1", "exercise_id": 2, "result": "pass", "error_type": None},
        ]
    )
    stats = AnalyticsService.get_user_attempt_stats(mongo, "s1")
    assert stats["total"] == 3
    assert stats["passed"] == 2
    assert stats["failed"] == 1
    assert stats["pass_rate"] == 66.7


def test_analytics_service_get_user_quiz_stats_empty():
    mongo = FakeMongo(quizzes=[])
    stats = AnalyticsService.get_user_quiz_stats(mongo, "s1")
    assert stats["total_quizzes"] == 0
    assert stats["average_score"] == 0
