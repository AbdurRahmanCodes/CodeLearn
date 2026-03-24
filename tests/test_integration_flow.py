def test_full_learner_flow_and_admin_visibility(client):
    # 1) Participant starts in static mode (creates participant session)
    r_static = client.get("/static-mode")
    assert r_static.status_code == 200

    # 2) Submit invalid logic first to trigger adaptive quiz unlock
    r_submit_fail = client.post(
        "/submit",
        data={
            "exercise_id": "ex01",
            "exercise_index": "0",
            "code": "print('Bob')\nprint(10)",
        },
    )
    assert r_submit_fail.status_code == 200

    # 3) Submit valid exercise code in static flow
    r_submit = client.post(
        "/submit",
        data={
            "exercise_id": "ex01",
            "exercise_index": "0",
            "code": "name='Alice'\nage=20\nprint(name)\nprint(age)",
        },
    )
    assert r_submit.status_code == 200

    # 4) Complete a topic quiz (now unlocked due to detected struggle)
    # variables quiz keys: qv1, qv2, qv3
    r_quiz = client.post(
        "/quiz/variables",
        data={"qv1": "1", "qv2": "2", "qv3": "2"},
    )
    assert r_quiz.status_code == 200

    # 5) Completion page should render
    r_complete = client.get("/complete")
    assert r_complete.status_code == 200

    # 6) Admin login and dashboard visibility
    admin_username = client.application.config.get("ADMIN_USERNAME")
    admin_password = client.application.config.get("ADMIN_PASSWORD")
    r_login = client.post(
        "/admin-login",
        data={"username": admin_username, "password": admin_password},
        follow_redirects=False,
    )
    assert r_login.status_code in (302, 303)

    r_admin_dashboard = client.get("/admin-dashboard")
    assert r_admin_dashboard.status_code == 200

    # 7) Admin analytics endpoint should be reachable (200 with DB or 503 without DB)
    r_stats = client.get("/api/stats/summary")
    assert r_stats.status_code in (200, 503)
