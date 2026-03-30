# Meta Multi-Agent OpenEnv

> A unified OpenEnv environment featuring **4 specialized AI agents** across **12 real-world tasks**.
> Built for the OpenEnv Hackathon 2026 by Team Digital Yodha.

---

## What Is This?

**Meta** is a multi-domain reinforcement learning environment where AI agents learn to perform
real-world workplace tasks across four distinct domains:

| Agent | Domain | Real-World Use Case |
|-------|--------|-------------------|
| Email Triage | Workplace communication | Classify, prioritize, and respond to emails |
| Code Review | Software engineering | Detect syntax errors, logic bugs, security vulnerabilities |
| Data Cleaning | Data engineering | Find missing values, fix types, detect outliers |
| Content Moderation | Trust & Safety | Detect explicit, subtle, and context-dependent harmful content |

Each agent has **3 tasks** (easy, medium, hard) with deterministic graders that score
agent performance from 0.0 to 1.0 with partial credit.

---

## Project Structure

```
Meta/                            <- repo root (this folder)
├── README.md                    <- you are here
├── Dockerfile                   <- root Dockerfile for HF Spaces
├── Meta/                        <- OpenEnv environment package
│   ├── models.py                <- Pydantic models: MetaAction, MetaObservation
│   ├── baseline.py              <- OpenAI baseline inference script
│   ├── openenv.yaml             <- OpenEnv spec metadata
│   ├── pyproject.toml           <- Project dependencies
│   ├── README.md                <- Detailed environment docs
│   ├── __init__.py
│   └── server/
│       ├── app.py               <- FastAPI app + all endpoints
│       ├── Meta_environment.py  <- All 4 agents + 12 tasks + graders
│       ├── Dockerfile           <- Inner Dockerfile (local dev)
│       ├── requirements.txt
│       └── __init__.py
```

---

## Quick Start

### Local Development

```bash
cd Meta
pip install openenv-core uv
uv sync
uv run --project . server
# Server running at http://localhost:8000
# Docs at http://localhost:8000/docs
```

### Docker (from repo root)

```bash
docker build -t meta-env:latest .
docker run -p 7860:7860 meta-env:latest
# Server running at http://localhost:7860
```

### Test It Works

```bash
# Health check
curl http://localhost:7860/health

# List all 12 tasks
curl http://localhost:7860/tasks

# Reset environment
curl -X POST http://localhost:7860/reset \
  -H "Content-Type: application/json" -d '{}'

# Run a task - Email Triage Easy
curl -X POST http://localhost:7860/step \
  -H "Content-Type: application/json" \
  -d '{"action": {"message": "{\"agent\": \"email_triage\", \"task_id\": \"email_triage_easy\", \"payload\": {\"classification\": \"important\"}}"}}'

# Perfect score - Code Review Hard (all 5 vulns)
curl -X POST http://localhost:7860/grader \
  -H "Content-Type: application/json" \
  -d '{"message": "{\"agent\": \"code_review\", \"task_id\": \"code_review_hard\", \"payload\": {\"vulnerabilities\": [{\"type\": \"sql_injection\", \"location\": \"get_user_by_name\", \"fix\": \"parameterized queries\"}, {\"type\": \"xss\", \"location\": \"render_comment\", \"fix\": \"sanitize html\"}, {\"type\": \"sql_injection\", \"location\": \"login\", \"fix\": \"parameterized queries\"}, {\"type\": \"command_injection\", \"location\": \"run_report\", \"fix\": \"no shell=True\"}, {\"type\": \"insecure_deserialization\", \"location\": \"load_user_data\", \"fix\": \"use json\"}]}}"}'
```

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/reset` | Reset environment, start new episode |
| POST | `/step` | Execute action, receive scored observation |
| GET | `/state` | Get current environment state |
| GET | `/health` | Health check |
| GET | `/schema` | Action and observation JSON schemas |
| GET | `/metadata` | Environment metadata |
| GET | `/tasks` | All 12 tasks with exact payload schemas |
| POST | `/grader` | Score an action without side effects |
| POST | `/baseline` | Run GPT-4o-mini baseline on all 12 tasks |
| WS | `/ws` | WebSocket for persistent agent sessions |

---

## The 12 Tasks

### Email Triage
| Task ID | Difficulty | Description |
|---------|-----------|-------------|
| `email_triage_easy` | Easy | Classify email: spam, important, or newsletter |
| `email_triage_medium` | Medium | Prioritize 10 workplace emails by urgency |
| `email_triage_hard` | Hard | Draft reply to a complex customer complaint |

### Code Review
| Task ID | Difficulty | Description |
|---------|-----------|-------------|
| `code_review_easy` | Easy | Find syntax errors in Python code |
| `code_review_medium` | Medium | Identify 4 logical bugs + suggest fixes |
| `code_review_hard` | Hard | Detect 5 security vulnerabilities |

### Data Cleaning
| Task ID | Difficulty | Description |
|---------|-----------|-------------|
| `data_cleaning_easy` | Easy | Find missing values and duplicate rows |
| `data_cleaning_medium` | Medium | Fix 5 data type/format issues |
| `data_cleaning_hard` | Hard | Detect outliers + impute missing values |

### Content Moderation
| Task ID | Difficulty | Description |
|---------|-----------|-------------|
| `content_moderation_easy` | Easy | Classify 7 posts as safe or harmful |
| `content_moderation_medium` | Medium | Detect subtle toxicity and sarcasm |
| `content_moderation_hard` | Hard | Context-aware moderation (same text, 2 contexts) |

---

## Action Format

All actions use a unified JSON-in-message format:

```json
POST /step
{
  "action": {
    "message": "{\"agent\": \"<agent>\", \"task_id\": \"<task_id>\", \"payload\": {...}}"
  }
}
```

Use `GET /tasks` to see the exact payload schema for each task.

---

## Reward Design

- Score range: **0.0 to 1.0** (always partial credit, never binary)
- **Per-criterion breakdown** in `partial_credits` field
- **Penalty** of -0.1 for empty payloads
- **Episode average** tracked across multi-task runs
- All graders are **deterministic and reproducible**

---

## Baseline Scores (GPT-4o-mini)

| Task | Score |
|------|-------|
| email_triage_easy | 1.00 |
| email_triage_medium | 0.80 |
| email_triage_hard | 0.67 |
| code_review_easy | 1.00 |
| code_review_medium | 0.75 |
| code_review_hard | 0.80 |
| data_cleaning_easy | 1.00 |
| data_cleaning_medium | 0.67 |
| data_cleaning_hard | 0.67 |
| content_moderation_easy | 1.00 |
| content_moderation_medium | 0.75 |
| content_moderation_hard | 0.50 |
| **Average** | **0.80** |

### Run Baseline Yourself

```bash
cd Meta
export OPENAI_API_KEY=sk-...
python baseline.py
```

---

## Why Meta?

Most OpenEnv environments cover a single domain. **Meta is a multi-domain
environment** that lets a single agent learn to handle completely different real-world
tasks in one unified interface. This makes it ideal for:

- Training **generalist agents** that switch between task types
- Benchmarking **multi-task learning** capabilities of LLMs
- Evaluating **transfer learning** between related domains
- Testing **robustness** across varying difficulty levels

---

## Team

**Digital Yodha** - OpenEnv Hackathon 2026

- Sangisetti Akarsh
- Kasarika Jivrajika
