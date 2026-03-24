# CodeLearn Research Platform
### COM748 - Design and Evaluation of an Interactive Educational Platform for Teaching Computer Programming

A Flask + MongoDB research platform for studying beginner programming behavior across static and interactive feedback conditions.

---

## Project Overview

The platform compares two learning experiences:

| Mode | Feedback Type |
|---|---|
| Static | Minimal feedback (pass/fail) |
| Interactive | Rich feedback (error class, explanation, test breakdown) |

Participants are anonymous and all submissions are logged for research analytics.

---

## Key Features

- Dual learning modes with shared exercise content
- Multi-language coding tasks (Python + JavaScript)
- Topic pages and quizzes for concept reinforcement
- Rule-based adaptive recommendations (A/B experiment layer)
- Admin dashboard with research visualizations
- Session explorer with filter + drilldown + export
- CSV/JSON/ZIP exports for SPSS, R, and Excel workflows
- Sandboxed code execution

---

## Quick Start

### 1. Clone

```bash
git clone https://github.com/<your-username>/<your-repo>.git
cd <your-repo>
```

### 2. Virtual Environment

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# macOS / Linux
source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Environment

```bash
# Windows (PowerShell)
Copy-Item .env.example .env

# macOS / Linux
cp .env.example .env
```

Set real values in .env:

```env
MONGO_URI=mongodb+srv://<user>:<pass>@<cluster>.mongodb.net/programming_research
ADMIN_USERNAME=admin
ADMIN_PASSWORD=your_secure_password
SECRET_KEY=your_long_random_secret_key
```

### 5. Run App

```bash
python -m flask run
```

Open http://localhost:5000.

---

## Testing

```bash
# Full suite
pytest -q

# Focused stats API tests
pytest tests/test_stats_api.py -q
```

Current baseline: 56 passing tests.

---

## Synthetic Population and Validation (No Real Users)

Use this workflow to populate realistic data and validate end-to-end flows.

### 1. Seed Smart Synthetic Cohorts

```bash
python seed_data.py --clear --sessions 120 --days-back 21 --seed 748
```

What it does:
- Generates balanced sessions across static/interactive and A_control/B_adaptive
- Models learner profiles (novice, intermediate, advanced)
- Simulates realistic error patterns, drop-off behavior, quiz outcomes, and recommendation events

### 2. Simulate Usability Journeys

```bash
python simulate_user_journeys.py --users 40 --seed 748
```

What it validates:
- Learner journey: home -> mode -> submit -> learn page -> quiz -> completion
- Researcher journey: admin login -> dashboard -> analytics APIs -> filtered export

### 3. Run Full Pipeline (One Command)

```bash
python run_research_pipeline.py --sessions 120 --users 40 --days-back 21 --seed 748
```

This runs seed population, synthetic journey validation, and full pytest regression in sequence.

---

## Usage

### Learner Flow

1. Start on / and select learning mode
2. Complete exercises and optional topic/quiz activities
3. Track progress on /my-progress

### Researcher Flow

1. Login on /admin-login
2. Open /admin-dashboard
3. Use Session Explorer filters (mode, arm, min/max pass rate, time window)
4. Export filtered sessions CSV or per-session JSON/CSV/ZIP

---

## Architecture

```text
CodeLearn/
|- app/
|  |- routes/          # HTTP handlers
|  |- services/        # business logic
|  |- models/          # data structures
|  |- data/            # exercises + quizzes
|  |- utils/
|- templates/
|- static/
|- tests/
|- PLANNING/           # archived planning and strategy docs
|- seed_data.py
|- simulate_user_journeys.py
|- IMPLEMENTATION_REPORT.md
|- DISSERTATION_NARRATIVE.md
|- RESEARCH_ARCHITECTURE.md
```

---

## Documentation

- IMPLEMENTATION_REPORT.md: technical implementation narrative
- DISSERTATION_NARRATIVE.md: research methodology and analysis plan
- RESEARCH_ARCHITECTURE.md: data schema and architecture references
- VIVA_PREPARATION_CHECKLIST.md: viva preparation script/checklist

---

## Notes

- Keep .env private (already gitignored)
- Platform is anonymous (no user registration)
- Preserve experiment structure to maintain research validity
