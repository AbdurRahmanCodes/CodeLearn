import types

import pytest

from app import create_app


class FakeJourney:
    def __init__(self, session_id):
        self.session_id = session_id
        self.context = {"experiment_arm": "A_control", "user_mode": "interactive"}

    def set_user_mode(self, mode):
        self.context["user_mode"] = mode
        return mode in ["static", "interactive"]

    def submit_attempt(self, exercise_id, code, language):
        return {
            "pass_fail": "pass",
            "attempt_number": 1,
            "recommendations": [],
            "next_exercise": exercise_id + 1,
        }

    def get_user_dashboard_data(self):
        return {
            "total_attempts": 1,
            "pass_rate": 100.0,
            "exercises_completed": 1,
            "quizzes_taken": 0,
            "average_quiz_score": 0,
            "recommendations_seen": 0,
            "experiment_arm": "A_control",
            "user_mode": "interactive",
            "current_exercise": 1,
        }


class FakeFindResult(list):
    def sort(self, *_args, **_kwargs):
        return self


class FakeCollection:
    def __init__(self, data=None):
        self.data = data or []

    def find_one(self, query):
        for item in self.data:
            ok = True
            for key, value in query.items():
                if item.get(key) != value:
                    ok = False
                    break
            if ok:
                return dict(item)
        return None

    def find(self, query):
        out = []
        for item in self.data:
            ok = True
            for key, value in query.items():
                if item.get(key) != value:
                    ok = False
                    break
            if ok:
                out.append(dict(item))
        return FakeFindResult(out)


class FakeMongo:
    def __init__(self):
        self.db = types.SimpleNamespace(
            exercises=FakeCollection([
                {"exercise_id": 1, "title": "E1", "description": "D1", "test_cases": []},
            ]),
            attempts=FakeCollection([
                {"session_id": "sess", "exercise_id": 1, "attempt_number": 1, "result": "pass"},
            ]),
            quiz_attempts=FakeCollection([]),
            recommendations_log=FakeCollection([]),
        )


@pytest.fixture
def app(monkeypatch):
    import app.routes.auth as auth_routes
    import app.routes.exercises as exercise_routes
    import app.routes.dashboard as dashboard_routes

    monkeypatch.setattr(auth_routes, "LearningJourney", FakeJourney)
    monkeypatch.setattr(exercise_routes, "LearningJourney", FakeJourney)
    monkeypatch.setattr(dashboard_routes, "LearningJourney", FakeJourney)

    fake_mongo = FakeMongo()
    monkeypatch.setattr(exercise_routes, "mongo", fake_mongo)
    monkeypatch.setattr(dashboard_routes, "mongo", fake_mongo)

    _app = create_app()
    _app.config["TESTING"] = True
    return _app


@pytest.fixture
def client(app):
    return app.test_client()


def test_auth_session_creation(client):
    response = client.post("/auth/session")
    assert response.status_code == 201
    body = response.get_json()
    assert body["success"] is True
    assert "session_id" in body


def test_select_mode_requires_session(client):
    response = client.post("/auth/select-mode", json={"mode": "interactive"})
    assert response.status_code == 401


def test_exercise_requires_mode_selected(client):
    client.post("/auth/session")
    response = client.post("/exercises/1/submit", json={"code": "print(1)", "language": "python"})
    assert response.status_code == 400


def test_submit_attempt_success(client):
    client.post("/auth/session")
    client.post("/auth/select-mode", json={"mode": "interactive"})
    response = client.post("/exercises/1/submit", json={"code": "print(1)", "language": "python"})
    assert response.status_code == 200
    body = response.get_json()
    assert body["success"] is True


def test_dashboard_user_success(client):
    client.post("/auth/session")
    response = client.get("/dashboard/user")
    assert response.status_code == 200
    body = response.get_json()
    assert body["success"] is True
    assert "dashboard" in body
