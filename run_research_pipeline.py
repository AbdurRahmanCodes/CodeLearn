"""One-command research pipeline: seed data, simulate journeys, and run tests."""

from __future__ import annotations

import argparse
import shlex
import subprocess
import sys
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run full local research validation pipeline")
    parser.add_argument("--sessions", type=int, default=120, help="Synthetic sessions for seed_data.py")
    parser.add_argument("--users", type=int, default=40, help="Synthetic users for simulate_user_journeys.py")
    parser.add_argument("--days-back", type=int, default=21, help="Days back for generated timestamps")
    parser.add_argument("--seed", type=int, default=748, help="Random seed for deterministic runs")
    parser.add_argument("--skip-tests", action="store_true", help="Skip pytest suite")
    parser.add_argument("--no-clear", action="store_true", help="Do not clear collections before seeding")
    return parser.parse_args()


def run_step(args: list[str], cwd: Path, title: str) -> None:
    print(f"\n[STEP] {title}")
    print("[CMD ] " + " ".join(shlex.quote(a) for a in args))
    result = subprocess.run(args, cwd=str(cwd), check=False)
    if result.returncode != 0:
        raise SystemExit(result.returncode)


def main() -> int:
    args = parse_args()
    root = Path(__file__).resolve().parent
    python_exe = sys.executable

    seed_cmd = [
        python_exe,
        "seed_data.py",
        "--sessions",
        str(args.sessions),
        "--days-back",
        str(args.days_back),
        "--seed",
        str(args.seed),
    ]
    if not args.no_clear:
        seed_cmd.insert(2, "--clear")

    simulate_cmd = [
        python_exe,
        "simulate_user_journeys.py",
        "--users",
        str(args.users),
        "--seed",
        str(args.seed),
    ]

    test_cmd = [python_exe, "-m", "pytest", "-q"]

    print("Research pipeline started")
    print("=" * 64)

    run_step(seed_cmd, root, "Populate synthetic dataset")
    run_step(simulate_cmd, root, "Run synthetic usability journeys")
    if not args.skip_tests:
        run_step(test_cmd, root, "Run full pytest regression suite")

    print("\nPipeline complete: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
