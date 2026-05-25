# GradeOps

> Human-in-the-loop grading pipeline for handwritten exams.

GradeOps lets an instructor upload scanned answer sheets and grading rubrics, automatically transcribes each handwritten answer, runs it through a multi-step LLM grader that awards partial credit with citations, and surfaces every AI-proposed grade on a high-throughput review dashboard where teaching assistants approve, override, or flag with keyboard shortcuts.

---

## Stack

| Layer | Tech |
|---|---|
| Frontend | React 18, Vite, Tailwind, Inter typography |
| Backend | FastAPI, SQLAlchemy |
| Database | SQLite (default) or Postgres |
| Agentic grader | Langchain + Langgraph (Extractor → Scorer → Justifier → Critic) |
| OCR / Vision | Gemini (free tier) or Claude vision via a swappable adapter; Qwen-VL adapter stub for HuggingFace use |
| Plagiarism | sentence-transformers cosine similarity |
| Storage | Local `storage/` folder behind a path abstraction (drop-in for S3) |

---

## Quick start

### 1. Clone, create a venv, install dependencies

```bash
cd gradeops
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS / Linux:
source .venv/bin/activate

pip install -r requirements.txt
```

### 2. Configure environment

```bash
cp .env.example .env
```

Open `.env` and set at minimum:

```
GOOGLE_API_KEY=AIzaSy...
```

Get a free Gemini API key at <https://aistudio.google.com/app/apikey> — no billing required.

### 3. Initialize the database

```bash
python scripts/init_db.py
python scripts/seed_demo.py   # optional: pre-load a sample exam + rubric
```

### 4. Run the backend

```bash
uvicorn backend.main:app --reload --port 8000
```

API docs at <http://localhost:8000/docs>.

### 5. Run the frontend (new terminal)

```bash
cd frontend
npm install
npm run dev
```

Open <http://localhost:5173>.

### 6. Optional CLI demo

For a no-UI walkthrough on one image:

```bash
python scripts/run_demo.py path/to/handwritten_answer.jpg
```

---

## How the grader works

The grader is a 4-node agentic state machine compiled with Langgraph:

```
                ┌────────────────────────────────────────────┐
                │                                            │
   image ─► Extractor ─► Scorer ─► Justifier ─► Critic ─┐    │
                            ▲                           │    │
                            │                           │    │
                            └─── retry with feedback ───┘    │
                                                             │
                                  END ◄─── pass ─────────────┘
```

- **Extractor** sees the image. Transcribes the handwriting literally and breaks it into atomic claim-steps. Never scores.
- **Scorer** sees only the extracted claims (not the image). Maps them to rubric criteria and awards points. The image-blindness is deliberate — it is the structural defense against the grader awarding credit for things it imagines rather than what is on the page.
- **Justifier** writes a 2–3 sentence rationale citing specific claim numbers.
- **Critic** audits whether every awarded point is supported by a claim. If not, it sends the Scorer back with concrete feedback. Configurable retry limit; disabled by default to keep the call budget tight.

For higher-confidence grading, set `GRADER_NUM_PASSES=5` in `.env`. The system will run the full graph 5 times per answer and aggregate median, max, and standard deviation. The review queue then sorts by std-dev DESC, surfacing the AI's most uncertain grades to TAs first.

---

## Review dashboard shortcuts

| Key | Action |
|---|---|
| `Enter` | Approve the AI's median score |
| `O` | Open the override input |
| `F` | Flag for further review |
| `J` / `→` | Next item |
| `K` / `←` | Previous item |
| `Esc` (in override) | Cancel |
| `Ctrl/⌘ + Enter` (in override) | Save override |

---

## Configuration reference

All settings live in `.env`. Key knobs:

| Variable | Default | Purpose |
|---|---|---|
| `LLM_PROVIDER` | `google` | `google` or `anthropic` |
| `GOOGLE_API_KEY` | — | Required for the default Google provider |
| `GRADER_MODEL_GOOGLE` | `gemini-2.5-flash-lite` | Free-tier-friendly vision model |
| `ANTHROPIC_API_KEY` | — | Required if `LLM_PROVIDER=anthropic` |
| `GRADER_MODEL_ANTHROPIC` | `claude-sonnet-4-20250514` | |
| `DATABASE_URL` | `sqlite:///./gradeops.db` | Swap to a Postgres URL when needed |
| `OCR_BACKEND` | `hosted` | `hosted` (uses configured LLM) or `qwen_vl` (HuggingFace, needs GPU) |
| `GRADER_NUM_PASSES` | `1` | Passes per answer; raise to 5 for variance-based review priority |
| `GRADER_CRITIC_RETRY` | `0` | How many times the Critic may send the Scorer back |
| `LLM_MIN_GAP_SECONDS` | `4.5` | Throttle between LLM calls; keeps free-tier RPM caps safe |
| `PLAGIARISM_THRESHOLD` | `0.82` | Cosine similarity cutoff |

---

## Schema (DB tables)

```
users               role: instructor | ta
exams               
rubrics             versioned (v1, v2, ...); immutable on update
papers              one row per uploaded PDF
crops               one row per cropped answer region
gradings            one row per grading pass
grading_aggregates  median / max / min / std-dev per crop
reviews             every approve / override / flag
plagiarism_flags    pairs of crops above similarity threshold
audit_log           append-only; every row stamped with rubric_ver + prompt_ver + model_ver
```

Every grading and every review writes an audit row, stamped with the rubric, prompt, and model versions in effect at the time. The audit log is the source of truth for traceability.

---

## Project layout

```
gradeops/
├── backend/
│   ├── main.py                    FastAPI app
│   ├── config.py · db.py · schemas.py
│   ├── audit.py · plagiarism.py
│   ├── ingestion/                 PDF split · crop · anonymize
│   ├── ocr/                       Hosted + Qwen-VL adapters + router
│   └── grader/                    Langgraph state machine + rate limiter
├── frontend/
│   ├── package.json · vite.config.js · tailwind.config.js
│   └── src/
│       ├── App.jsx · main.jsx · index.css · api.js
│       ├── components/ui.jsx
│       └── pages/{Rubrics,Grading,Review,Audit}.jsx
├── scripts/
│   ├── init_db.py
│   ├── seed_demo.py
│   └── run_demo.py
├── storage/                       Local stand-in for cloud object store
├── docker-compose.yml             Optional Postgres
├── requirements.txt
└── .env.example
```

---

## API reference

Quick tour. Full schema at `/docs` when the server is running.

| Method | Path | Description |
|---|---|---|
| GET | `/health` | Liveness probe + active model |
| GET | `/debug/env` | Diagnostic — what env vars actually loaded |
| GET | `/users` | List instructor + TA accounts |
| POST | `/exams` | Create an exam |
| GET | `/exams` | List exams |
| POST | `/rubrics` | Create a rubric (immutable; auto-versioned) |
| GET | `/rubrics?exam_id={id}` | List rubrics for an exam |
| POST | `/papers/upload` | Upload a PDF or image; runs the full pipeline |
| GET | `/crops/{id}/image` | Fetch the anonymized crop image |
| GET | `/review/queue` | Crops sorted by std-dev DESC, pending only |
| POST | `/reviews` | Submit an approve / override / flag |
| GET | `/audit` | Decision log |
| GET | `/plagiarism` | Similarity pairs above threshold |
| GET | `/stats` | Dashboard metrics |

---

## Out of scope for this build

- Real authentication / SSO — there is a role toggle in the header for RBAC demonstration
- Background workers — the pipeline runs synchronously on upload
- Cloud object storage — the local `storage/` folder is behind a path abstraction; S3 swap is a small change
- Failure recovery, idempotency, retries beyond the Critic loop

These are flagged in the architecture as the next things to add when moving to production.
