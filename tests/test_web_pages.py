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
    response = client.get("/research-info")
    assert response.status_code == 200


def test_methodology_renders(client):
    response = client.get("/methodology")
    assert response.status_code == 200


def test_topic_page_renders(client):
    response = client.get("/learn/variables")
    assert response.status_code == 200


def test_quiz_page_renders(client):
    response = client.get("/quiz/variables")
    assert response.status_code == 200


def test_submit_invalid_exercise_returns_400(client):
    client.get("/static-mode")
    response = client.post("/submit", data={"exercise_id": "bad", "exercise_index": "0", "code": "print(1)"})
    assert response.status_code == 400
