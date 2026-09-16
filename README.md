# 🎭 Greenroom

**Your applications, prepped and ready.**

Greenroom is an AI-powered autonomous job application agent. Upload your resume, set your preferences, and Greenroom works for you — scanning job boards, scoring matches, tailoring your resume, writing personalized cover letters, researching companies, and generating interview prep. You stay in the loop: review everything before it goes out.

> **The human stays in the loop.** Greenroom prepares everything and presents it for one-click approval. It does NOT auto-submit applications — that gets accounts banned and is unethical. The value is eliminating the 30 minutes of manual work PER application.

## What It Does

| Step | What Greenroom Does | Time Saved |
|------|-------------------|------------|
| **Job Discovery** | Scans Adzuna + JSearch (Google Jobs) for matches based on your preferences | Hours of browsing |
| **Job Scoring** | Scores each match against your resume across 5 dimensions (skills, experience, location, salary, culture) | Manual filtering |
| **Resume Tailoring** | Rewrites your resume to emphasize relevant experience for each specific job | 20+ min per app |
| **Cover Letter** | Drafts a personalized letter referencing the company's actual recent news and products | 15+ min per app |
| **Company Research** | Pulls real company data — funding, products, culture, recent news | 10+ min per app |
| **Interview Prep** | Generates likely technical, behavioral, and company-specific questions with talking points | 30+ min per app |
| **Application Tracking** | Tracks status: queued → ready → applied → interviewing → offered/rejected | Spreadsheet management |

## Architecture

```
┌─────────────────────────────────────────────────┐
│              React Dashboard (Phase 5)           │
└──────────────────────┬──────────────────────────┘
                       │ REST API
┌──────────────────────▼──────────────────────────┐
│              FastAPI Backend                      │
│  Auth │ Resumes │ Preferences │ Jobs │ Tracker   │
└──────────────────────┬──────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────┐
│           LangGraph Agent Pipeline               │
│                                                  │
│  Parse Resume → Score Job → Research Company     │
│  → Tailor Resume → Cover Letter → Interview Prep │
└──────────────────────┬──────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────┐
│              SQLite (greenroom.db)                │
│  Users │ Resumes │ Preferences │ Jobs │ Apps     │
└─────────────────────────────────────────────────┘
```

## Tech Stack

- **LLM Engine:** Google Gemini (via langchain-google-genai)
- **Agent Framework:** LangGraph (state machine with conditional edges)
- **Web Search:** Tavily API (company research)
- **Job Sources:** Adzuna API, JSearch/RapidAPI (Google Jobs)
- **Backend:** FastAPI + SQLAlchemy + SQLite
- **Auth:** JWT (python-jose) + bcrypt
- **Frontend:** React (Phase 5 — coming soon)

## Quick Start

### Prerequisites

- Python 3.12+
- API keys (all free tiers):
  - [Google Gemini](https://aistudio.google.com/apikey)
  - [Tavily](https://tavily.com) (1,000 searches/month free)
  - [Adzuna](https://developer.adzuna.com) (1,000 calls/month free)
  - [JSearch via RapidAPI](https://rapidapi.com/letscrape-6bRBa3QguO5/api/jsearch) (500 calls/month free, optional)

### Setup

```bash
git clone https://github.com/harshalbalar/greenroom.git
cd greenroom

# Install dependencies
pip install -r requirements.txt

# Configure API keys
cp .env.example .env
# Edit .env with your API keys

# Pin bcrypt for passlib compatibility
pip install bcrypt==4.0.1
```

### Run the Pipeline (Phase 1)

Test the core agent pipeline with a sample resume + job:

```bash
python main.py
```

This takes one resume + one job description and produces a tailored resume, cover letter, company research brief, and interview prep.

### Scan for Jobs (Phase 2)

Discover and score real jobs from Adzuna:

```bash
python scan.py                # Scan + score matches
python scan.py --no-score     # Discovery only (saves API calls)
python scan.py --stats        # View database stats
```

### Start the API Server (Phase 3)

```bash
uvicorn server:app --reload --port 8000
```

Then open http://localhost:8000/docs for the interactive Swagger UI.

**API flow:**
1. `POST /api/auth/register` — create account
2. `POST /api/resumes` — upload resume (auto-parsed by Gemini)
3. `PUT /api/preferences` — set target roles, locations, salary
4. `POST /api/jobs/scan` — discover jobs from all sources
5. `GET /api/jobs?worth_only=true` — see top matches
6. `POST /api/applications` — triggers full pipeline for a job
7. `GET /api/applications` — review prepped applications
8. `PATCH /api/applications/{id}` — update status (applied, interviewing, etc.)

### Run the Full E2E Test

```bash
# With server running in another terminal:
python test_api.py
```

## Project Structure

```
greenroom/
├── main.py              # Phase 1 — test pipeline with sample data
├── scan.py              # Phase 2 — CLI job scanner
├── server.py            # Phase 3 — FastAPI server
├── test_api.py          # End-to-end API test
├── graph.py             # LangGraph pipeline wiring
├── state.py             # Pydantic models + pipeline state
├── prompts.py           # All LLM prompt templates
├── config.py            # Settings + env vars
├── database.py          # SQLAlchemy models
├── auth_core.py         # JWT + bcrypt auth
├── api_schemas.py       # API request/response schemas
├── store.py             # Job store (SQLite)
├── scanner.py           # Job discovery orchestrator
├── utils.py             # Shared helpers
├── nodes/
│   ├── resume_parser.py
│   ├── job_scorer.py
│   ├── company_researcher.py
│   ├── resume_tailor.py
│   ├── cover_letter.py
│   └── interview_prep.py
├── routes/
│   ├── auth.py
│   ├── resumes.py
│   ├── preferences.py
│   ├── jobs.py
│   └── applications.py
└── sources/
    ├── base.py           # Job source interface
    ├── jsearch.py        # JSearch (Google Jobs)
    └── adzuna.py         # Adzuna API
```

## Roadmap

- [x] **Phase 1** — Core LangGraph pipeline (resume tailor, cover letter, research, interview prep)
- [x] **Phase 2** — Job discovery (Adzuna + JSearch, scoring, SQLite storage)
- [x] **Phase 3** — FastAPI backend, auth, user profiles, application tracking
- [ ] **Phase 4** — Batch processing & background queues (Celery/Redis)
- [ ] **Phase 5** — React dashboard (upload, review queue, kanban tracker)
- [ ] **Phase 6** — Scheduling & automation (cron scanning, email notifications)
- [ ] **Phase 7** — Deployment & monetization (Stripe payments, landing page)

## License

MIT

---

*Built with LangGraph, Gemini, FastAPI, and too much coffee.*
