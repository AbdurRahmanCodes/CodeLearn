def test_stats_endpoints_do_not_500(client):
    endpoints = [
        "/api/stats/summary",
        "/api/stats/research-snapshot",
        "/api/stats/pass-rate",
        "/api/stats/attempts",
        "/api/stats/errors",
        "/api/stats/learning-curve",
        "/api/stats/language-difficulty",
        "/api/stats/topic-success",
        "/api/stats/quiz-performance",
        "/api/stats/recommendation-effectiveness",
        "/api/stats/session-quality",
        "/api/stats/time-to-pass",
        "/api/stats/persistence",
        "/api/stats/error-transitions",
        "/api/stats/session-drilldown",
    ]

    for endpoint in endpoints:
        response = client.get(endpoint)
        assert response.status_code in (200, 503), endpoint


def test_session_drilldown_export_requires_session_id(client):
    response = client.get("/api/stats/session-drilldown/export")
    assert response.status_code in (400, 503)


def test_session_drilldown_export_json_or_csv(client):
    response = client.get("/api/stats/session-drilldown/export?session_id=fake-session&format=json")
    assert response.status_code in (200, 503)


def test_session_drilldown_index_accepts_filters(client):
    response = client.get(
        "/api/stats/session-drilldown?limit=25&page=2&group_type=interactive&experiment_group=B_adaptive&min_pass_rate=40&max_pass_rate=95&since_hours=24"
    )
    assert response.status_code in (200, 503)


def test_session_drilldown_bundle_export_requires_session_id(client):
    response = client.get("/api/stats/session-drilldown/export-bundle")
    assert response.status_code in (400, 503)


def test_session_drilldown_bundle_export(client):
    response = client.get("/api/stats/session-drilldown/export-bundle?session_id=fake-session")
    assert response.status_code in (200, 503)


def test_session_drilldown_index_export(client):
    response = client.get("/api/stats/session-drilldown/export-index")
    assert response.status_code in (200, 503)


def test_session_drilldown_index_export_accepts_filters(client):
    response = client.get(
        "/api/stats/session-drilldown/export-index?limit=25&group_type=interactive&experiment_group=B_adaptive&min_pass_rate=40&max_pass_rate=95&since_hours=24"
    )
    assert response.status_code in (200, 503)
