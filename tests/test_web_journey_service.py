from datetime import datetime, timedelta, timezone

from app.services.learning_engine import LearningEngine


class FakeCollection:
    def __init__(self, rows=None):
        self.rows = rows or []
        self.inserted = []

    def find(self, query=None, projection=None):
        query = query or {}
        out = [row for row in self.rows if all(row.get(k) == v for k, v in query.items())]
        if projection is None:
            return out
        projected = []
        for row in out:
            item = {}
            for key, include in projection.items():
                if include and key in row:
                    item[key] = row[key]
            projected.append(item)
        return projected

    def insert_one(self, doc):
        self.inserted.append(doc)


def test_topic_quiz_unlock_status_locked_without_session():
    status = LearningEngine.topic_quiz_unlock_status(
        attempts_col=FakeCollection([]),
        session_id=None,
        topic_id="variables",
        selected_language="python",
    )

    assert status["unlocked"] is False


def test_topic_quiz_unlock_status_unlocked_on_logic_error():
    attempts = FakeCollection(
        [
            {
                "session_id": "s1",
                "topic": "variables",
                "programming_language": "python",
                "attempt_number": 1,
                "result": "fail",
                "error_type": "logic",
                "execution_time_ms": 1200,
            }
        ]
    )

    status = LearningEngine.topic_quiz_unlock_status(
        attempts_col=attempts,
        session_id="s1",
        topic_id="variables",
        selected_language="python",
    )

    assert status["unlocked"] is True


def test_evaluate_quiz_submission_scores_and_answers():
    questions = [
        {"id": "q1", "answer": 1},
        {"id": "q2", "answer": 0},
        {"id": "q3", "answer": 2},
    ]
    submitted = {"q1": "1", "q2": "2", "q3": "2"}

    result = LearningEngine.evaluate_quiz_submission(questions, submitted)

    assert result["score"] == 2
    assert result["total_questions"] == 3
    assert result["score_pct"] == 66.7
    assert len(result["answers"]) == 3


def test_log_quiz_attempt_inserts_document():
    col = FakeCollection()
    quiz_result = {
        "score": 2,
        "total_questions": 3,
        "score_pct": 66.7,
        "answers": [{"question_id": "q1", "selected": 1, "correct_option": 1, "is_correct": True}],
    }

    LearningEngine.log_quiz_attempt(
        quiz_col=col,
        session_id="s1",
        user_id="s1",
        mode="interactive",
        experiment_arm="A_control",
        topic_id="variables",
        quiz_result=quiz_result,
    )

    assert len(col.inserted) == 1
    assert col.inserted[0]["session_id"] == "s1"
    assert col.inserted[0]["score_pct"] == 66.7
    assert col.inserted[0]["topic"] == "variables"


def test_build_completion_stats_computes_expected_fields():
    now = datetime.now(timezone.utc)
    attempts = FakeCollection(
        [
            {"session_id": "s1", "exercise_id": "ex01", "result": "pass", "timestamp": now, "recommendation_count": 1},
            {"session_id": "s1", "exercise_id": "ex02", "result": "fail", "timestamp": now + timedelta(minutes=10), "recommendation_count": 0},
            {"session_id": "s1", "exercise_id": "ex02", "result": "pass", "timestamp": now + timedelta(minutes=20), "recommendation_count": 2},
        ]
    )
    quizzes = FakeCollection(
        [
            {"session_id": "s1", "score_pct": 80.0},
            {"session_id": "s1", "score_pct": 60.0},
        ]
    )

    stats = LearningEngine.build_completion_stats(
        attempts_col=attempts,
        quiz_col=quizzes,
        session_id="s1",
        mode="interactive",
        experiment_arm="B_adaptive",
        total_exercises=7,
    )

    assert stats["exercises_attempted"] == 2
    assert stats["exercises_passed"] == 2
    assert stats["total_attempts"] == 3
    assert stats["duration_min"] == 20.0
    assert stats["completion_rate"] == 29
    assert stats["recommendation_count"] == 3
    assert stats["avg_quiz_score"] == 70.0


def test_build_recommendations_adds_review_concept_for_slow_attempts():
    exercise = {"topic": "loops"}
    eval_result = {"result": "fail", "error_type": "runtime"}

    recs = LearningEngine.build_recommendations(
        exercise=exercise,
        attempt_number=1,
        eval_result=eval_result,
        topic_page_url="/learn/loops?lang=python",
        topic_quiz_url="/quiz/loops?lang=python",
        easier_exercise_url="/interactive-mode?ex=0&lang=python",
        execution_time_ms=61000,
    )

    types_seen = {r.get("type") for r in recs}
    assert "review_concept" in types_seen
