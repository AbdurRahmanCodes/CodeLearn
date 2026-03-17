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
    ]

    for endpoint in endpoints:
        response = client.get(endpoint)
        assert response.status_code in (200, 503), endpoint
