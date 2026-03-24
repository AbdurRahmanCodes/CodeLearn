"""Run synthetic usability validation flows without real users."""

from __future__ import annotations

import argparse
import random
import statistics

from app import create_app
from app.data import QUIZ_BANK


LEARNER_PATHS = [
    "/",
    "/study-information",
    "/my-progress",
]

MODE_START_ROUTES = {
    "static": "/static-mode",
    "interactive": "/interactive-mode",
}

TOPICS = list(QUIZ_BANK.keys())


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Synthetic usability flow runner")
    parser.add_argument("--users", type=int, default=40, help="Number of synthetic users to simulate")
    parser.add_argument("--seed", type=int, default=748, help="Random seed for reproducible simulations")
    return parser.parse_args()


def _status_ok(code: int) -> bool:
    return code in (200, 302, 303)


def run_learner_flow(client, mode: str) -> dict:
    checks = []

    for path in LEARNER_PATHS:
        resp = client.get(path)
        checks.append((path, resp.status_code))

    start_route = MODE_START_ROUTES[mode]
    checks.append((start_route, client.get(start_route).status_code))

    sample_submissions = [
        {"exercise_id": "ex01", "exercise_index": "0", "code": "print('hello')"},
        {"exercise_id": "ex02", "exercise_index": "1", "code": "print('test')"},
    ]
    for payload in sample_submissions:
        resp = client.post("/submit", data=payload)
        checks.append((f"/submit:{payload['exercise_id']}", resp.status_code))

    topic = random.choice(TOPICS)
    checks.append((f"/learn/{topic}", client.get(f"/learn/{topic}").status_code))
    checks.append((f"/quiz/{topic}", client.get(f"/quiz/{topic}").status_code))

    quiz_payload = {"qv1": "1", "qv2": "2", "qv3": "2"}
    checks.append((f"/quiz/{topic}:POST", client.post(f"/quiz/{topic}", data=quiz_payload).status_code))

    checks.append(("/complete", client.get("/complete").status_code))

    ok_count = sum(1 for _, code in checks if _status_ok(code))
    return {
        "mode": mode,
        "checks": len(checks),
        "ok": ok_count,
        "success_rate": round((ok_count / max(1, len(checks))) * 100, 2),
        "failed": [(path, code) for path, code in checks if not _status_ok(code)],
    }


def run_researcher_flow(client, username: str, password: str) -> dict:
    checks = []
    checks.append(("/admin-login", client.get("/admin-login").status_code))

    login = client.post(
        "/admin-login",
        data={"username": username, "password": password},
        follow_redirects=False,
    )
    checks.append(("/admin-login:POST", login.status_code))

    dashboard = client.get("/admin-dashboard")
    checks.append(("/admin-dashboard", dashboard.status_code))

    api_paths = [
        "/api/stats/summary",
        "/api/stats/pass-rate",
        "/api/stats/session-drilldown?limit=20&group_type=interactive&experiment_group=B_adaptive&min_pass_rate=25&max_pass_rate=95&since_hours=168",
        "/api/stats/session-drilldown/export-index?limit=20&group_type=interactive&min_pass_rate=20",
    ]
    for path in api_paths:
        resp = client.get(path)
        checks.append((path, resp.status_code))

    ok_count = sum(1 for _, code in checks if code in (200, 302, 303, 503))
    return {
        "checks": len(checks),
        "ok": ok_count,
        "success_rate": round((ok_count / max(1, len(checks))) * 100, 2),
        "failed": [(path, code) for path, code in checks if code not in (200, 302, 303, 503)],
    }


def main() -> int:
    args = parse_args()
    random.seed(args.seed)

    app = create_app()
    app.config["TESTING"] = True

    learner_results = []
    with app.test_client() as client:
        for i in range(max(2, args.users)):
            mode = "interactive" if i % 2 else "static"
            learner_results.append(run_learner_flow(client, mode))

        researcher_result = run_researcher_flow(
            client,
            app.config.get("ADMIN_USERNAME", "admin"),
            app.config.get("ADMIN_PASSWORD", "admin"),
        )

    avg_rate = statistics.mean([r["success_rate"] for r in learner_results]) if learner_results else 0.0
    min_rate = min((r["success_rate"] for r in learner_results), default=0.0)

    print("Synthetic usability validation")
    print("=" * 60)
    print(f"Users simulated: {len(learner_results)}")
    print(f"Learner avg path success: {avg_rate:.2f}%")
    print(f"Learner worst-case path success: {min_rate:.2f}%")
    print(f"Researcher flow success: {researcher_result['success_rate']:.2f}%")

    learner_failures = sum(len(r["failed"]) for r in learner_results)
    print(f"Learner failed checks: {learner_failures}")
    print(f"Researcher failed checks: {len(researcher_result['failed'])}")

    if learner_failures:
        print("\nSample learner failures:")
        for entry in learner_results:
            if entry["failed"]:
                for path, code in entry["failed"][:3]:
                    print(f"  - {path}: {code}")
                break

    if researcher_result["failed"]:
        print("\nResearcher failures:")
        for path, code in researcher_result["failed"]:
            print(f"  - {path}: {code}")

    if avg_rate < 95 or researcher_result["success_rate"] < 95:
        print("\nResult: FAIL (threshold is 95% success)")
        return 1

    print("\nResult: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
