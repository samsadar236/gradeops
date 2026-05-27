---
title: gradeops
emoji: 🚀
colorFrom: blue
colorTo: indigo
sdk: docker
pinned: false
---

# GradeOps 

> **Human-in-the-Loop AI grading pipeline for handwritten exams**


[[Live Demo](https://samruddhisadar-gradeops.hf.space)]

STACK - FastAPI, React, Langraph.
DB - SQLite / PostgreSQL

---

## What is GradeOps?

Grading handwritten exams is slow, inconsistent, and prone to bias. GradeOps solves this by combining **Vision-Language Models** and **Agentic LLMs** into a pipeline that:

1. Reads scanned exam PDFs and extracts handwritten answers using AI vision
2. Grades them automatically against instructor-defined rubrics (with partial credit)
3. Pushes the AI-proposed grades to a review dashboard where TAs approve or override — keeping humans in the loop

---

## Architecture Overview

```
React 18 + Vite + Tailwind (Frontend)
        │
        ▼
FastAPI (Backend — also serves frontend in production)
        │
   ┌────┴──────────────────────────────────────┐
   ▼          ▼             ▼           ▼       ▼
Ingestion   OCR         Agentic      Plagiarism  Audit
(PyMuPDF)  (Gemini      Grader       (sentence-  (versioned
            Vision via  (Langgraph   transformers decision log)
            Langchain)  4-node)      cosine)
                │
                ▼
        SQLAlchemy → SQLite (dev) / PostgreSQL (prod)
```

### The 4-Node Langgraph Grading Pipeline

```
Extractor → Scorer → Justifier → Critic
                         ↑____________| (retry loop if points aren't traceable to claims)
```

| Node | What it does |
|------|-------------|
| **Extractor** | Reads OCR transcript, pulls out answer claims |
| **Scorer** | Awards partial credit per rubric criterion |
| **Justifier** | Writes a 2–3 sentence rationale citing specific claims |
| **Critic** | Self-audits: every point must be traceable back to a claim |

---

## Features

- **Bulk PDF Upload** : Professors upload entire exam batches at once
- **Rubric Builder** : Define criteria with conditions, alternatives, and do-not-deduct rules
- **AI Grading** : Partial credit with structured justifications per question
- **Plagiarism Detection** : Cosine similarity over OCR transcripts using sentence-transformers
- **Review Dashboard** : Side-by-side view of student answer + AI grade with keyboard shortcuts (`Enter / O / F / J / K`)
- **Sorted by Uncertainty** : High-variance AI grades surface first for TA review
- **Audit Log** : Every decision stamped with rubric version, prompt version, and model version
- **Anonymization** : Top strip of each answer crop is masked before any external API call
- **RBAC** : Instructor and TA roles tracked in DB with reviewer attribution

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | React 18, Vite, Tailwind CSS |
| Backend | FastAPI, Python |
| Agentic AI | Langgraph, Langchain |
| LLM (default) | Gemini 2.5 Flash Lite (provider-agnostic — swap to Claude with one env var) |
| OCR | Gemini Vision (hosted) / Qwen-VL (GPU, HuggingFace) |
| Plagiarism | `sentence-transformers/all-MiniLM-L6-v2` |
| PDF Ingestion | PyMuPDF |
| Database | SQLAlchemy + SQLite (dev) / PostgreSQL (prod) |
| Deployment | Hugging Face Spaces (Docker) |

---

## Quick Start

```bash
# 1. Clone and set up
git clone <your-repo-url>
cd gradeops
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# 2. Configure
cp .env.example .env
# Open .env and set GOOGLE_API_KEY at minimum

# 3. Initialize database and seed demo data
python scripts/init_db.py
python scripts/seed_demo.py

# 4. Run backend
uvicorn backend.main:app --reload --port 8000

# 5. Run frontend (separate terminal)
cd frontend && npm install && npm run dev

# CLI demo (no UI needed)
python scripts/run_demo.py path/to/answer.jpg

# Diagnose environment / LLM chain issues
python debug_llm.py
```

---

## Environment Variables

```env
LLM_PROVIDER=google
GOOGLE_API_KEY=AIzaSy...
GRADER_MODEL_GOOGLE=gemini-2.5-flash-lite
GRADER_NUM_PASSES=1          # Bump to 5 on paid tier
GRADER_CRITIC_RETRY=0        # Set to 1 to enable self-audit retry
LLM_MIN_GAP_SECONDS=4.5      # Set 0 for paid tiers
OCR_BACKEND=hosted            # 'qwen_vl' for GPU production
DATABASE_URL=sqlite:///./gradeops.db
STORAGE_ROOT=./storage
PLAGIARISM_THRESHOLD=0.82
EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
```

---

## Project Structure

```
gradeops/
├── backend/
│   ├── main.py               FastAPI app
│   ├── grader/
│   │   ├── graph.py          Langgraph state machine
│   │   ├── nodes.py          4 agent nodes
│   │   ├── llm.py            Provider-agnostic LLM factory
│   │   └── rate_limit.py     Global throttle (free-tier safe)
│   ├── ingestion/            PDF splitting, cropping, anonymization
│   └── ocr/                  Hosted vision + Qwen-VL adapters
├── frontend/
│   └── src/pages/
│       ├── Rubrics.jsx       Rubric CRUD editor
│       ├── Grading.jsx       Batch upload + progress
│       ├── Review.jsx        Side-by-side TA dashboard
│       └── Audit.jsx         Stats + decision log
└── scripts/                  DB init, demo seeder, CLI runner
```

---

## API Endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /health` | Provider + model + OCR backend status |
| `GET /debug/env` | What `.env` actually loaded |
| `GET /docs` | Full Swagger UI |
| `POST /papers/upload` | Bulk PDF upload |

---

## Deployment (Hugging Face Spaces)


**Live at:** https://samruddhisadar-gradeops.hf.space  
*(Sleeps after 48h inactivity — ~30s cold start on first request)*






---


