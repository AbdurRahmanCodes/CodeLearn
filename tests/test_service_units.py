import types
from datetime import datetime, timedelta, timezone

from app.services.analytics_service import AnalyticsService
from app.services.execution_engine import ExecutionEngine
from app.services.export_service import ExportService
from app.services.learning_engine import LearningEngine
from app.services.stats_service import StatsService


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
    result = ExecutionEngine.run_code("print('ok')", "python")
    assert result["error"] is None
    assert result["stdout"] == "ok"


def test_exercise_service_run_code_python_syntax_error():
    result = ExecutionEngine.run_code("if True print('x')", "python")
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
    result = ExecutionEngine.evaluate_test_cases(exercise, exec_result)
    assert result["result"] == "fail"
    assert result["error_type"] == "logic"


def test_recommendation_service_generates_hint_for_repeated_failures():
    recs = LearningEngine.generate_recommendation(
        user_state={
            "topic": "loops",
            "language": "python",
            "success": False,
            "error_type": "logic",
            "attempts": 3,
            "time_taken": 10,
        },
        topic_page_url="/learn/loops?lang=python",
        topic_quiz_url="/quiz/loops?lang=python",
        easier_exercise_url="/interactive-mode?lang=python&ex=1",
        user_profile={"error_pattern": {"dominant": "logic", "counts": {"logic": 3}}},
    )
    types_seen = {r["type"] for r in recs}
    assert "quiz" in types_seen
    assert "exercise" in types_seen


def test_recommendation_service_adds_language_focus_when_language_struggling():
    recs = LearningEngine.generate_recommendation(
        user_state={
            "topic": "conditions",
            "language": "javascript",
            "success": False,
            "error_type": "runtime",
            "attempts": 1,
            "time_taken": 15,
        },
        topic_page_url="/learn/conditions?lang=javascript",
        topic_quiz_url="/quiz/conditions?lang=javascript",
        easier_exercise_url="/interactive-mode?lang=javascript&ex=0",
        user_profile={"current_language_pressure": 0.5, "error_pattern": {"counts": {}}},
    )
    assert any(r["type"] == "language_focus" for r in recs)


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


def test_export_service_build_session_summary_rows():
    rows = [
        {"session_id": "s1", "group_type": "static", "experiment_group": "A_control", "result": "pass"},
        {"session_id": "s1", "group_type": "static", "experiment_group": "A_control", "result": "fail"},
        {"session_id": "s2", "group_type": "interactive", "experiment_group": "B_adaptive", "result": "pass"},
    ]
    out = ExportService.build_session_summary_rows(rows)
    by_sid = {row["session_id"]: row for row in out}
    assert by_sid["s1"]["attempts"] == 2
    assert by_sid["s1"]["passes"] == 1
    assert by_sid["s2"]["attempts"] == 1
    assert by_sid["s2"]["passes"] == 1


def test_export_service_to_csv_bytes_contains_header_and_values():
    rows = [{"session_id": "s1", "score": 3}, {"session_id": "s2", "score": 2}]
    payload = ExportService.to_csv_bytes(rows).decode("utf-8")
    assert "session_id,score" in payload
    assert "s1,3" in payload
    assert "s2,2" in payload


class StatsFakeCursor:
    def __init__(self, rows):
        self._rows = list(rows)

    def sort(self, *_args, **_kwargs):
        return self

    def __iter__(self):
        return iter(self._rows)


class StatsFakeCollection:
    def __init__(self, distinct_values=None, count=0, aggregate_results=None, aggregate_sequence=None, find_result=None):
        self._distinct_values = distinct_values or []
        self._count = count
        self._aggregate_results = aggregate_results or []
        self._aggregate_sequence = list(aggregate_sequence or [])
        self._find_result = find_result or []

    def distinct(self, _field):
        return list(self._distinct_values)

    def count_documents(self, _query):
        return self._count

    def aggregate(self, _pipeline):
        if self._aggregate_sequence:
            return list(self._aggregate_sequence.pop(0))
        return list(self._aggregate_results)

    def find(self, _query, _projection):
        return StatsFakeCursor(self._find_result)


class StatsFakeDistinctCollection(StatsFakeCollection):
    def __init__(self, distinct_map=None, pass_count=None, **kwargs):
        super().__init__(**kwargs)
        self._distinct_map = distinct_map or {}
        self._pass_count = pass_count

    def distinct(self, field, filter_query=None):
        key = (field, tuple(sorted((filter_query or {}).items())))
        return list(self._distinct_map.get(key, []))

    def count_documents(self, _query):
        if _query == {"result": "pass"} and self._pass_count is not None:
            return self._pass_count
        return super().count_documents(_query)


def test_stats_service_build_research_snapshot_includes_dataset_and_hypotheses():
    attempts = StatsFakeCollection(
        distinct_values=["s1", "s2"],
        count=6,
        aggregate_results=[
            {"_id": "A_control", "attempts": 3, "passes": 1, "avg_attempt_number": 2.4},
            {"_id": "B_adaptive", "attempts": 3, "passes": 2, "avg_attempt_number": 1.8},
        ],
    )
    quizzes = StatsFakeCollection(count=2)
    recs = StatsFakeCollection(count=4)

    snapshot = StatsService.build_research_snapshot(attempts, quizzes, recs)
    assert snapshot["dataset"]["participants"] == 2
    assert snapshot["dataset"]["attempts"] == 6
    assert snapshot["dataset"]["quiz_attempts"] == 2
    assert snapshot["dataset"]["recommendation_events"] == 4
    assert len(snapshot["hypotheses"]) == 2


def test_stats_service_build_time_to_pass_rows_handles_instant_and_timed_passes():
    now = datetime.now(timezone.utc)
    attempts = StatsFakeCollection(
        aggregate_sequence=[
            [
                {"_id": {"session_id": "s1", "exercise_id": "ex1", "group_type": "interactive"}, "first_ts": now},
                {"_id": {"session_id": "s2", "exercise_id": "ex1", "group_type": "interactive"}, "first_ts": now},
            ],
            [
                {"_id": {"session_id": "s1", "exercise_id": "ex1", "group_type": "interactive"}, "pass_ts": now + timedelta(seconds=30)},
                {"_id": {"session_id": "s2", "exercise_id": "ex1", "group_type": "interactive"}, "pass_ts": now},
            ],
        ],
    )

    rows = StatsService.build_time_to_pass_rows(attempts)
    assert len(rows) == 1
    assert rows[0]["exercise_id"] == "ex1"
    assert rows[0]["group_type"] == "interactive"
    assert rows[0]["first_attempt_passes"] == 1
    assert rows[0]["count"] == 2


def test_stats_service_build_error_transition_rows_counts_changes():
    attempts = StatsFakeCollection(find_result=[
        {"session_id": "s1", "exercise_id": "ex1", "attempt_number": 1, "error_type": "syntax", "result": "fail"},
        {"session_id": "s1", "exercise_id": "ex1", "attempt_number": 2, "error_type": "logic", "result": "fail"},
        {"session_id": "s1", "exercise_id": "ex1", "attempt_number": 3, "error_type": None, "result": "pass"},
    ])

    rows = StatsService.build_error_transition_rows(attempts, ["s1"])
    by_key = {(row["from"], row["to"]): row["count"] for row in rows}
    assert by_key[("syntax", "logic")] == 1
    assert by_key[("logic", "pass")] == 1


def test_stats_service_build_summary_computes_participant_and_pass_metrics():
    distinct_map = {
        ("session_id", tuple()): ["s1", "s2", "s3"],
        ("session_id", (("group_type", "static"),)): ["s1"],
        ("session_id", (("group_type", "interactive"),)): ["s2", "s3"],
        ("session_id", (("experiment_group", "A_control"),)): ["s1", "s2"],
        ("session_id", (("experiment_group", "B_adaptive"),)): ["s3"],
    }
    coll = StatsFakeDistinctCollection(distinct_map=distinct_map, count=10, pass_count=6)

    summary = StatsService.build_summary(coll)
    assert summary["total_participants"] == 3
    assert summary["static_participants"] == 1
    assert summary["interactive_participants"] == 2
    assert summary["overall_pass_rate"] == 60.0


def test_stats_service_build_session_quality_handles_empty_result():
    coll = StatsFakeCollection(aggregate_results=[])
    result = StatsService.build_session_quality(coll)
    assert result == {"total": 0, "valid": 0, "invalid": 0, "validity_rate": 0}
