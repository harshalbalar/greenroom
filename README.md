# 🎭 Greenroom

**AI-powered job application agent — scans, scores, tailors, and preps. You review and apply.**

Upload your resume, set your preferences, and 5 AI agents scan job boards, score matches, rewrite your resume for each role, draft cover letters that reference actual company news, and generate interview prep — all in under 60 seconds per application.

> **The human stays in the loop.** Greenroom prepares everything and presents it for review. It doesn't auto-submit — the value is eliminating the 30+ minutes of manual work per application.

🔗 **Live demo:** [greenroom-8wwb.onrender.com](https://greenroom-8wwb.onrender.com)  *(free tier — may take ~30s to wake up)*

---

## Screenshots

| Dashboard | Application Detail |
|:-:|:-:|
| ![Dashboard](screenshots/dashboard.png) | ![Detail](screenshots/detail.png) |

---

## How It Works

```
 Resume + Preferences
         │
         ▼
   ┌───────────┐     ┌───────────┐     ┌───────────┐
   │   Scout   │────▶│  Analyst  │────▶│   Remy    │
   │  (Scan)   │     │  (Score)  │     │(Research) │
   └───────────┘     └───────────┘     └───────────┘
                                             │
         ┌───────────────────────────────────┘
         ▼
   ┌───────────┐     ┌───────────┐
   │  Taylor   │────▶│   Quinn   │────▶  Ready to apply
   │ (Tailor)  │     │  (Write)  │
   └───────────┘     └───────────┘
```

| Agent | What it does |
|-------|-------------|
| **Scout** | Scans Adzuna for jobs matching your target roles and locations |
| **Analyst** | Scores each job across 5 dimensions — skills, experience, location, salary, culture fit |
| **Remy** | Researches the company via Tavily — funding, products, culture, recent news |
| **Taylor** | Rewrites your resume for each job — reorders bullets, mirrors job keywords, stays factual |
| **Quinn** | Drafts a cover letter referencing real company data + generates interview prep |

The pipeline is a **LangGraph state machine** with 6 nodes. Each node calls Gemini, passes structured state to the next, and the full pipeline runs as a background task with SSE progress streaming.

---

## Key Features

**AI Pipeline**
- 6-node LangGraph state machine (parse → score → research → tailor → cover letter → interview prep)
- Google Gemini 3.6 Flash for all LLM calls
- Tavily web search for live company research
- ATS-optimized resume output with anti-AI-detection rules (banned buzzwords, varied sentence structure)
- Prompt engineering for human-sounding cover letters (contractions, specific references, no "passionate self-starter")

**"Use My Template" Resume Builder**
- Upload your DOCX resume → Greenroom stores the original file
- When tailoring, it clones your document and replaces content while preserving your exact formatting
- Extracts paragraph-level formatting profiles (fonts, spacing, borders, tab stops) from the original
- Works alongside 3 built-in templates (Classic, Modern, Minimal)

**Job Discovery & Scoring**
- Adzuna API integration with Germany/EU city detection
- Per-user job scoping — each user gets individually scored copies
- 5-dimension scoring with Gemini (0-100 overall, with reasoning)
- Deduplication via URL hashing across sources

**Dashboard**
- Theater-themed dark UI with animated crew characters
- Kanban board: In the Wings → In Rehearsal → Ready for Stage → On Stage
- Real-time crew activity feed during scanning/prepping
- Template picker (Classic / Modern / Minimal / My Template)
- One-click ZIP download (Resume + Cover Letter + Interview Cheatsheet as .docx)

**Automation**
- APScheduler: auto-scan every 6 hours, auto-prep top N matches
- Morning brief at 8:00 UTC via email (Resend)
- In-app notifications for new jobs and completed preps
- Background task processing with ThreadPoolExecutor + SSE streaming

---

## Tech Stack

| Layer | Technologies |
|-------|-------------|
| **AI** | Google Gemini 3.6 Flash, LangChain, LangGraph, Tavily |
| **Backend** | Python 3.12, FastAPI, SQLAlchemy, PostgreSQL, Alembic |
| **Frontend** | React 18, Vite, CSS-in-JS |
| **Scheduling** | APScheduler (auto-scan, morning brief, auto-prep) |
| **Email** | Resend (transactional notifications) |
| **Deployment** | Render (web service + managed PostgreSQL) |
| **Resume Gen** | python-docx (4 templates including user's own DOCX) |

---

## Architecture

```
┌──────────────────────────────────────────────────┐
│          React 18 + Vite (Single-Page App)        │
│   Landing │ Login │ Dashboard (Kanban + Detail)    │
└───────────────────────┬──────────────────────────┘
                        │ REST API + SSE
┌───────────────────────▼──────────────────────────┐
│                FastAPI Backend                     │
│                                                    │
│  Auth (JWT)          Resume Upload (PDF/DOCX/TXT)  │
│  Job Scanner         Application CRUD              │
│  DOCX Generator      Background Worker             │
│  APScheduler         Email (Resend)                 │
└───────────────────────┬──────────────────────────┘
                        │
┌───────────────────────▼──────────────────────────┐
│           LangGraph Pipeline (6 nodes)             │
│                                                    │
│  parse_resume → score_job → research_company       │
│  → tailor_resume → cover_letter → interview_prep   │
│                                                    │
│  State: PipelineState (TypedDict)                  │
│  LLM: Gemini 3.6 Flash via LangChain              │
│  Search: Tavily (company research)                 │
└───────────────────────┬──────────────────────────┘
                        │
┌───────────────────────▼──────────────────────────┐
│          PostgreSQL (Render managed)               │
│  Users │ Resumes │ Preferences │ Jobs              │
│  Applications │ Background Tasks │ Notifications   │
└──────────────────────────────────────────────────┘
```

---

## Quick Start

### Prerequisites

- Python 3.12+, PostgreSQL 17+, Node.js 18+
- API keys (all have free tiers): [Google Gemini](https://aistudio.google.com/apikey), [Tavily](https://tavily.com), [Adzuna](https://developer.adzuna.com)
- Optional: [Resend](https://resend.com) (email notifications)

### Setup

```bash
git clone https://github.com/harshalbalar/greenroom.git
cd greenroom
pip install -r requirements.txt

# Create database
psql -U postgres -c "CREATE DATABASE greenroom_dev;"

# Configure
cp .env.example .env   # add your API keys

# Migrate + run
alembic upgrade head
uvicorn server:app --reload --port 8000

# Frontend (separate terminal)
cd frontend && npm install && npm run dev
```

### Environment Variables

```env
DATABASE_URL=postgresql://postgres:password@localhost:5432/greenroom_dev
GOOGLE_API_KEY=your_gemini_key
GEMINI_MODEL=gemini-3.6-flash
TAVILY_API_KEY=your_tavily_key
ADZUNA_APP_ID=your_adzuna_id
ADZUNA_APP_KEY=your_adzuna_key
JWT_SECRET=change-me-in-production
RESEND_API_KEY=your_resend_key          # optional
FROM_EMAIL=Greenroom <onboarding@resend.dev>  # optional
AUTO_SCAN_HOURS=6
JOBS_PER_SOURCE=10
```

---

## Project Structure

```
greenroom/
├── server.py              # FastAPI — serves API + React build
├── graph.py               # LangGraph pipeline (6 nodes)
├── state.py               # Pipeline state (TypedDict + Pydantic models)
├── prompts.py             # All LLM prompts (ATS rules, humanizer, cover letter)
├── scanner.py             # Job discovery orchestrator
├── resume_templates.py    # 3 built-in DOCX templates
├── user_template.py       # "My Template" — clone user's DOCX, replace content
├── scheduler.py           # APScheduler (auto-scan, auto-prep, morning brief)
├── worker.py              # Background task manager (ThreadPoolExecutor)
├── database.py            # SQLAlchemy models + PostgreSQL
├── nodes/
│   ├── resume_parser.py   # Gemini extracts skills, experience, city
│   ├── job_scorer.py      # 5-dimension scoring
│   ├── company_researcher.py  # Tavily web search
│   ├── resume_tailor.py   # Rewrite resume for specific job
│   ├── cover_letter.py    # Personalized, human-sounding
│   └── interview_prep.py  # Technical + behavioral questions
├── routes/                # FastAPI route modules
├── sources/               # Job board API integrations
└── frontend/src/
    ├── pages/Dashboard.jsx    # Kanban board, detail panel, template picker
    ├── pages/Landing.jsx      # Public landing page
    └── components/Backstage.jsx  # Animated crew characters
```

---

## What I Learned Building This

- **LangGraph** for building multi-step AI pipelines with typed state and conditional edges
- **Prompt engineering** at scale — ATS formatting rules, anti-AI-detection, and getting structured output from Gemini
- **python-docx internals** — XML-level paragraph manipulation, cloning formatting profiles, preserving tab stops and borders
- **Full-stack deployment** — FastAPI serving React, PostgreSQL on Render, APScheduler in a web process
- **Job board APIs** — rate limits, deduplication, country-specific quirks (Adzuna's DE endpoint)

---

## License

MIT

---

*Built by [Harshal Balar](https://github.com/harshalbalar) — M.Sc. Digital Technologies, Ostfalia University*