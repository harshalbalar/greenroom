# 🎭 Greenroom

**Your applications, prepped and ready.**

Greenroom is an AI-powered autonomous job application agent. Upload your resume, set your preferences, and Greenroom works for you — scanning job boards, scoring matches, tailoring your resume, writing personalized cover letters, researching companies, and generating interview prep.

> **The human stays in the loop.** Greenroom prepares everything and presents it for review. It does NOT auto-submit applications — the value is eliminating the 30+ minutes of manual work per application.

🔗 **Live:** [greenroom-8wwb.onrender.com](https://greenroom-8wwb.onrender.com)

---

## What It Does

Upload your resume (PDF, DOCX, or text), set your target roles and locations, and Greenroom's crew takes over:

| Agent | Role | What It Does |
|-------|------|-------------|
| **Scout** | Finder | Scans Adzuna + JSearch for jobs matching your preferences |
| **Analyst** | Scorer | Scores each job against your resume across 5 dimensions |
| **Remy** | Researcher | Pulls real company data — funding, products, culture, recent news |
| **Taylor** | Tailor | Rewrites your resume to emphasize relevant experience for each job |
| **Quinn** | Writer | Drafts personalized cover letters and generates interview prep |

Every application gets a tailored resume, cover letter, company research brief, and interview prep — downloadable as ATS-friendly Word documents.

---

## Screenshots

### Landing Page
![Landing](screenshots/landing.png)

### Dashboard
![Dashboard](screenshots/dashboard.png)

### Application Detail
![Detail](screenshots/detail.png)

---

## Architecture

```
┌─────────────────────────────────────────────────────┐
│           React Dashboard + Landing Page             │
│         (Vite, dark theme, kanban board)             │
└──────────────────────┬──────────────────────────────┘
                       │ REST API
┌──────────────────────▼──────────────────────────────┐
│                 FastAPI Backend                       │
│  Auth │ Resumes │ Preferences │ Jobs │ Applications  │
│  Notifications │ Downloads │ Scheduler               │
└──────────────────────┬──────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────┐
│            LangGraph Agent Pipeline                   │
│                                                      │
│  Parse Resume → Score Job → Research Company         │
│  → Tailor Resume → Cover Letter → Interview Prep     │
└──────────────────────┬──────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────┐
│         PostgreSQL (Render managed)                   │
│  Users │ Resumes │ Preferences │ Jobs │ Apps         │
│  Background Tasks │ Notifications                    │
└─────────────────────────────────────────────────────┘
```

---

## Tech Stack

**Backend:** Python, FastAPI, SQLAlchemy, PostgreSQL, Alembic, APScheduler, Gunicorn

**AI/ML:** Google Gemini (via LangChain), LangGraph (state machine pipeline), Tavily (web search)

**Frontend:** React, Vite, CSS-in-JS (dark theme)

**Job Sources:** Adzuna API, JSearch/RapidAPI (Google Jobs)

**Email:** Resend (transactional emails, morning briefs)

**Deployment:** Render (web service + managed PostgreSQL)

---

## Features

**Core Pipeline**
- AI-powered resume parsing (PDF, DOCX, TXT upload)
- 5-dimension job scoring (skills, experience, location, salary, culture)
- Company research with real-time web search via Tavily
- Resume tailoring — rewrites to match each specific job
- Personalized cover letters referencing actual company news
- Interview prep with technical, behavioral, and company-specific questions

**Job Discovery**
- Multi-source scanning (Adzuna + JSearch)
- Per-user job scoping with individual scoring
- Deduplication across sources
- Score-based filtering (worth applying / skip)

**Dashboard**
- Theater-themed dark UI with animated crew characters
- Kanban board (In the Wings → In Rehearsal → Ready for Stage → On Stage)
- Real-time crew activity feed during scanning and prep
- Job detail panel with tabbed content view
- Direct "Apply →" links to original job postings
- Copy to clipboard + Word document download

**User Management**
- JWT authentication (register, login)
- Settings panel (edit profile, re-upload resume, update preferences)
- PDF/DOCX/TXT resume upload with Gemini parsing

**Automation**
- APScheduler for auto-scan (configurable interval, default 6 hours)
- Daily morning brief (email + in-app notification)
- New job alerts via email (Resend)
- Background task processing with progress streaming

**Downloads**
- ATS-friendly Word documents (Calibri, clean formatting, proper sections)
- Markdown-to-docx conversion (parses Gemini output into real Word styles)
- Resume and cover letter downloads per application

---

## Quick Start (Local Development)

### Prerequisites

- Python 3.12+
- PostgreSQL 17+
- Node.js 18+
- API keys (all have free tiers):
  - [Google Gemini](https://aistudio.google.com/apikey) — LLM engine
  - [Tavily](https://tavily.com) — company research (1,000 searches/month free)
  - [Adzuna](https://developer.adzuna.com) — job discovery (free tier)
  - [JSearch via RapidAPI](https://rapidapi.com/letscrape-6bRBa3QguO5/api/jsearch) — optional, Google Jobs
  - [Resend](https://resend.com) — optional, email notifications (100/day free)

### Setup

```bash
# Clone
git clone https://github.com/harshalbalar/greenroom.git
cd greenroom

# Install Python dependencies
pip install -r requirements.txt

# Create PostgreSQL database
psql -U postgres -c "CREATE DATABASE greenroom_dev;"

# Configure environment
cp .env.example .env
# Edit .env with your API keys and database URL

# Run database migrations
alembic upgrade head

# Start the backend
uvicorn server:app --reload --port 8000

# In another terminal — start the frontend
cd frontend
npm install
npm run dev
```

Open http://localhost:3000 — you'll see the landing page.

### Environment Variables

```env
# Database
DATABASE_URL=postgresql://postgres:yourpassword@localhost:5432/greenroom_dev

# AI
GOOGLE_API_KEY=your_gemini_key
GEMINI_MODEL=gemini-3.6-flash
TAVILY_API_KEY=your_tavily_key

# Job Sources
ADZUNA_APP_ID=your_adzuna_id
ADZUNA_APP_KEY=your_adzuna_key
JSEARCH_API_KEY=your_jsearch_key  # optional

# Auth
JWT_SECRET=change-me-in-production

# Email (optional)
RESEND_API_KEY=your_resend_key
FROM_EMAIL=Greenroom <onboarding@resend.dev>

# Scheduler
AUTO_SCAN_HOURS=6
MORNING_BRIEF_HOUR=8

# Scan settings
JOBS_PER_SOURCE=10
```

---

## Project Structure

```
greenroom/
├── server.py              # FastAPI server (serves API + React build)
├── database.py            # SQLAlchemy models + PostgreSQL connection
├── config.py              # Settings from environment variables
├── auth_core.py           # JWT + bcrypt authentication
├── api_schemas.py         # Pydantic request/response schemas
├── graph.py               # LangGraph pipeline wiring
├── state.py               # Pipeline state + Pydantic models
├── prompts.py             # All LLM prompt templates
├── store.py               # Job store (SQLAlchemy ORM)
├── scanner.py             # Job discovery orchestrator
├── worker.py              # Background task manager (ThreadPoolExecutor)
├── tasks.py               # Task definitions (scan, prep, batch)
├── scheduler.py           # APScheduler (auto-scan, morning brief)
├── email_service.py       # Resend email templates
├── utils.py               # Shared helpers
├── render.yaml            # Render deployment config
├── alembic/               # Database migrations
├── nodes/
│   ├── resume_parser.py
│   ├── job_scorer.py
│   ├── company_researcher.py
│   ├── resume_tailor.py
│   ├── cover_letter.py
│   └── interview_prep.py
├── routes/
│   ├── auth.py            # Register, login, profile update
│   ├── resumes.py         # Upload (file + text), parse, list
│   ├── preferences.py     # Job search preferences
│   ├── jobs_v2.py         # Scan, list, get (per-user scoped)
│   ├── applications_v2.py # Create, list, update status
│   ├── downloads.py       # Word document generation
│   ├── notifications.py   # In-app notifications
│   └── events.py          # SSE + task status polling
├── sources/
│   ├── base.py            # Job source interface
│   ├── adzuna.py          # Adzuna API
│   └── jsearch.py         # JSearch (Google Jobs)
└── frontend/
    ├── src/
    │   ├── App.jsx            # Router (landing → login → dashboard)
    │   ├── api.js             # API client
    │   ├── pages/
    │   │   ├── Landing.jsx    # Public landing page
    │   │   ├── Login.jsx      # Auth form
    │   │   └── Dashboard.jsx  # Main app (kanban, detail, crew feed)
    │   └── components/
    │       ├── Backstage.jsx  # Animated crew characters
    │       ├── SetupPanel.jsx # Onboarding (resume + preferences)
    │       └── SettingsPanel.jsx # Profile, resume, preferences editing
    └── package.json
```

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/auth/register` | Create account |
| POST | `/api/auth/login` | Login, get JWT token |
| GET | `/api/auth/me` | Current user profile |
| PATCH | `/api/auth/profile` | Update name/email |
| POST | `/api/resumes` | Upload resume (text) |
| POST | `/api/resumes/upload` | Upload resume (PDF/DOCX/TXT file) |
| GET | `/api/resumes/active` | Get active resume |
| PUT | `/api/preferences` | Save job search preferences |
| GET | `/api/preferences` | Get preferences |
| POST | `/api/jobs/scan` | Trigger job scan (background) |
| GET | `/api/jobs` | List discovered jobs |
| POST | `/api/applications` | Create application (triggers pipeline) |
| GET | `/api/applications` | List applications |
| PATCH | `/api/applications/{id}` | Update status |
| GET | `/api/applications/{id}/download` | Download as Word doc |
| GET | `/api/notifications` | List notifications |
| POST | `/api/notifications/read-all` | Mark all read |
| GET | `/api/events/{task_id}/status` | Poll task progress |

---

## Deployment

Deployed on Render with a managed PostgreSQL database. Push to `main` triggers auto-deploy.

```yaml
# render.yaml handles:
# - PostgreSQL database provisioning
# - Python + Node.js build
# - Alembic migrations
# - Gunicorn with Uvicorn workers
```

The React frontend is built during deploy and served directly by FastAPI — single domain, no CORS issues.

---

## Roadmap

- [x] **Phase 1** — Core LangGraph pipeline (resume tailor, cover letter, research, interview prep)
- [x] **Phase 2** — Job discovery (Adzuna + JSearch, scoring, deduplication)
- [x] **Phase 3** — FastAPI backend, JWT auth, user profiles, application tracking
- [x] **Phase 4** — Background workers, SSE progress streaming, batch processing
- [x] **Phase 5** — React dashboard (kanban, crew characters, dark theme)
- [x] **Phase 6A** — PostgreSQL migration + Alembic
- [x] **Phase 6B** — Deployed to Render
- [x] **Phase 6C** — Scheduling (auto-scan, morning brief, email notifications)
- [x] **Phase 7A** — Landing page with pricing
- [ ] **Phase 7B** — Stripe payments (Free/Pro/Unlimited tiers)
- [ ] **Phase 7C** — Production hardening (Sentry, rate limiting, backups)

---

## License

MIT

---

*Built with LangGraph, Gemini, FastAPI, React, and too much coffee.*
