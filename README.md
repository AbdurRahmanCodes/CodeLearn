# CodeLearn Research Platform
### COM748 — Design and Evaluation of an Interactive Educational Platform for Teaching Computer Programming

A web-based programming research platform built with **Flask**, **MongoDB Atlas**, and **Chart.js** for studying beginner Python programming learning behaviour.

---

## Project Overview

This platform is a Masters research tool that compares two programming learning environments:

| Mode | Feedback Type |
|---|---|
| **Static Mode** | Minimal — shows only Correct / Incorrect |
| **Interactive Mode** | Rich — error classification, concept explanation, test case breakdown |

Participants are allowed to self-select their preferred mode. All code submissions are logged to MongoDB Atlas and analysed through a research analytics dashboard.

---

## Features

- 🧪 **Dual learning modes** with identical exercise content
- 📊 **Admin research dashboard** with 7 Chart.js visualisations
- 🔐 **Session-based admin authentication**
- 📝 **7 Python exercises** of graduated difficulty
- 🗄️ **MongoDB Atlas** cloud database — no local DB setup needed
- 📥 **CSV export** compatible with SPSS, R, and Excel
- 🛡️ **Sandboxed code execution** (safe Python eval via whitelisted builtins)
- 📈 **Research metrics**: Time-to-First-Pass, Persistence Index, Error Transition Analysis
- 🌐 **Anonymous participation** — no registration required

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python 3.10+ / Flask 3.x |
| Database | MongoDB Atlas (PyMongo) |
| Frontend | HTML5 / Vanilla CSS / Vanilla JS |
| Charts | Chart.js 4.4.3 |
| Code Editor | CodeMirror 5 (Interactive Mode) |
| Icons | Lucide Icons |

---

## Quick Start

### 1. Clone the repository

```bash
git clone https://github.com/<your-username>/<your-repo>.git
cd <your-repo>
```

### 2. Create a virtual environment

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# macOS / Linux
source venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure environment variables

```bash
cp .env.example .env
```

Edit `.env` with your real values:

```env
MONGO_URI=mongodb+srv://<user>:<pass>@<cluster>.mongodb.net/<db>
ADMIN_USERNAME=admin
ADMIN_PASSWORD=your_secure_password
SECRET_KEY=your_long_random_secret_key
```

> **MongoDB Atlas setup**: Create a free M0 cluster at [mongodb.com/atlas](https://www.mongodb.com/atlas), create a database named `programming_research`, and copy the connection URI.

### 5. Run the application

```bash
python app.py
```

Visit **http://127.0.0.1:5000** to see the participant interface.

---

## Admin Dashboard

Navigate to **http://127.0.0.1:5000/admin-login** and enter the credentials set in `.env`.

The dashboard provides:
- **Overview tab**: Pass rates, error distribution, average attempts, learning curve
- **Research Insights tab**: Time-to-First-Pass, Persistence Index, Error Transition Analysis

---

## Seeding Demo Data

To populate the dashboard with realistic simulated participant data (20 sessions):

```bash
python seed_data.py
```

To clear all existing data first:

```bash
python seed_data.py --clear
```

---

## Project Structure

```
.
├── app.py                  # Flask application — all routes, logic, APIs
├── seed_data.py            # Script to generate simulated research sessions
├── requirements.txt        # Python dependencies
├── .env.example            # Environment variable template (copy to .env)
├── static/
│   ├── style.css           # Global stylesheet (CSS design system)
│   ├── dashboard.js        # Admin dashboard Chart.js rendering
│   └── script.js           # Participant interface helpers
└── templates/
    ├── base.html           # Shared navbar and layout
    ├── index.html          # Landing page
    ├── static_mode.html    # Static exercise environment
    ├── interactive_mode.html  # Interactive exercise environment
    ├── completion.html     # Session completion summary
    ├── research_info.html  # Study information for participants
    ├── admin_login.html    # Admin login page
    └── admin_dashboard.html   # Research analytics dashboard
```

---

## Research Metrics Explained

| Metric | Description |
|---|---|
| **Pass Rate** | % of attempts resulting in a correct submission, by group |
| **Average Attempts** | Mean attempt number across all submissions per exercise |
| **Learning Curve** | Average attempt number at first pass per exercise |
| **Time-to-First-Pass** | Seconds from first attempt to first pass (cognitive efficiency) |
| **Persistence Index** | Avg attempts on exercises never passed (frustration tolerance) |
| **Error Transitions** | Sequential error-type progressions (syntax→runtime→pass etc.) |

---

## Data Export

From the admin dashboard footer:

- **Full Dataset CSV** — all attempt records with timestamps, error types, and session IDs
- **Session Summary CSV** — one row per participant; aggregated stats including duration and completion rate

Both files use UTF-8 BOM encoding for immediate Excel compatibility.

---

## Environment Variables Reference

| Variable | Description |
|---|---|
| `MONGO_URI` | MongoDB Atlas connection string |
| `ADMIN_USERNAME` | Username for admin dashboard login |
| `ADMIN_PASSWORD` | Password for admin dashboard login |
| `SECRET_KEY` | Flask session signing key (long random string) |

---

## Important Notes

- **Do not** commit your `.env` file — it is in `.gitignore`
- The platform is intentionally **anonymous** — no participant accounts or registration
- The **experimental design** (mode selection, exercise structure, session logic) should not be modified as it affects research validity
- All code execution is **sandboxed** — learner-submitted Python runs with a restricted built-in whitelist and a 5-second timeout

---

## Academic Context

This platform was developed as part of a Masters Research Project (COM748) investigating how automated feedback richness affects programming learning behaviour in beginner Python learners. The study compares self-selected Static vs Interactive learning modes using Educational Data Mining (EDM) techniques.

---

## License

This project is developed for academic research purposes. All rights reserved.
