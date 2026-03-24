import pytest


def test_home_page_renders(client):
    response = client.get("/")
    assert response.status_code == 200


def test_static_mode_renders(client):
    response = client.get("/static-mode")
    assert response.status_code == 200


def test_interactive_mode_renders(client):
    response = client.get("/interactive-mode")
    assert response.status_code == 200


def test_research_info_renders(client):
    """Test that /research-info redirects to /study-information (backward compatibility)."""
    response = client.get("/research-info", follow_redirects=True)
    assert response.status_code == 200
    assert "Study Information" in response.data.decode()


def test_methodology_renders(client):
    """Test that /methodology redirects to /study-information (backward compatibility)."""
    response = client.get("/methodology", follow_redirects=True)
    assert response.status_code == 200
    assert "Study Information" in response.data.decode()


def test_my_progress_page_renders(client):
    response = client.get("/my-progress")
    assert response.status_code == 200


def test_study_design_page_renders(client):
    """Test that /study-design redirects to /study-information (backward compatibility)."""
    response = client.get("/study-design", follow_redirects=True)
    assert response.status_code == 200
    assert "Study Information" in response.data.decode()


def test_study_information_renders(client):
    """Test consolidated study information page with all tabs."""
    response = client.get("/study-information")
    assert response.status_code == 200
    assert "Study Information" in response.data.decode()
    assert "Overview" in response.data.decode()
    assert "Study Design" in response.data.decode()
    assert "Data & Methodology" in response.data.decode()
    assert "Privacy & Ethics" in response.data.decode()


def test_topic_page_renders(client):
    response = client.get("/learn/variables")
    assert response.status_code == 200


def test_quiz_page_renders(client):
    response = client.get("/quiz/variables")
    assert response.status_code == 200
    assert "Diagnostic Quiz" in response.data.decode()


def test_quiz_unlocks_after_logic_struggle(client):
    client.get("/static-mode?lang=python")
    # Submit wrong logic for variables topic to trigger struggle-based quiz unlock.
    client.post(
        "/submit",
        data={
            "exercise_id": "ex01",
            "exercise_index": "0",
            "code": "print('wrong')",
        },
    )

    response = client.get("/quiz/variables?lang=python")
    assert response.status_code == 200
    assert "Diagnostic Quiz" in response.data.decode()
    assert "This quiz becomes available after you attempt the topic." not in response.data.decode()


def test_submit_invalid_exercise_returns_400(client):
    client.get("/static-mode")
    response = client.post("/submit", data={"exercise_id": "bad", "exercise_index": "0", "code": "print(1)"})
    assert response.status_code == 400


@pytest.mark.parametrize(
    "path",
    [
        "/admin-dashboard",
        "/export-data",
        "/export-research-dataset",
        "/export-session-summary",
        "/export-quiz-data",
        "/export-recommendations",
    ],
)
def test_admin_protected_routes_redirect_to_login(client, path):
    response = client.get(path)
    assert response.status_code in (302, 303)
    assert "/admin-login" in (response.headers.get("Location") or "")
