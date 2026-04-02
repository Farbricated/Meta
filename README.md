---
title: Meta OpenEnv
emoji: 🤖
colorFrom: blue
colorTo: purple
sdk: docker
pinned: false
tags:
  - openenv
  - multi-agent
  - rl
  - workplace
  - benchmark
---

# Meta — Multi-Domain AI Agent Benchmark

> **Meta is the first multi-domain OpenEnv environment** — a single unified benchmark where AI agents
> learn email triage, code review, data cleaning, and content moderation all in one interface.
> No existing single-domain environment lets researchers test generalist agents across these four
> completely different real-world task types simultaneously, making Meta uniquely positioned for
> multi-task learning, transfer learning, and generalist agent research.

Built for the **OpenEnv Hackathon 2026** by Team **Digital Yodha**.

---

## Why Meta Fills a Critical Gap

Existing RL environments specialize: text environments don't benchmark code reasoning, and code
environments don't test social judgment. Real-world agents — the kind that will actually automate
knowledge work — need to switch fluidly between these domains. Meta provides the first unified
interface to train and benchmark them, spanning four task families with a consistent action/observation
API, partial-credit graders, and three difficulty levels per agent.

---

## Environment Design

### Action Space

All 4 agents share a unified JSON-in-message format compatible with the OpenEnv spec:

```json
POST /step
{
  "action": {
    "message": "{\"agent\": \"email_triage\", \"task_id\": \"email_triage_easy\", \"payload\": {\"classification\": \"spam\"}}"
  }
}
```

### Observation Space

```json
{
  "observation": {
    "agent": "email_triage",
    "task_id": "email_triage_easy",
    "difficulty": "easy",
    "context": { "email": { "subject": "...", "body": "...", "sender": "..." } },
    "instructions": "Classify the email as spam, important, or newsletter.",
    "feedback": "[OK] Correct! 'spam' is right.",
    "score": 1.0,
    "partial_credits": { "classification": true }
  },
  "reward": 1.0,
  "done": true
}
```

### Reward Function

- Score range: **0.0 to 1.0** — always partial credit, never binary
- Partial credits per criterion (e.g. 3 of 5 bugs found = 0.60)
- Penalty of `-0.1` for empty or malformed payloads
- Episode average score tracked in `metadata` across multi-task runs
- All graders are deterministic and reproducible

---

## Agents & Tasks

### 1. Email Triage Agent

| Task | Difficulty | Description |
|------|-----------|-------------|
| `email_triage_easy` | 🟢 Easy | Classify a single email: spam, important, or newsletter |
| `email_triage_medium` | 🟡 Medium | Prioritize 10 workplace emails by urgency |
| `email_triage_hard` | 🔴 Hard | Draft a professional reply to a complex customer complaint |

**Easy payload:**
```json
{"classification": "spam"}
```

**Medium payload:**
```json
{"order": ["m1", "m5", "m3", "m10", "m6", "m8", "m2", "m9", "m4", "m7"]}
```

**Hard payload:**
```json
{"reply": "Dear Customer, I sincerely apologize for the inconvenience..."}
```

---

### 2. Code Review Agent

| Task | Difficulty | Description |
|------|-----------|-------------|
| `code_review_easy` | 🟢 Easy | Find syntax errors in a Python function |
| `code_review_medium` | 🟡 Medium | Identify 4 logical bugs and suggest fixes |
| `code_review_hard` | 🔴 Hard | Detect 5 security vulnerabilities (SQL injection, XSS, command injection, insecure deserialization) |

**Hard payload:**
```json
{
  "vulnerabilities": [
    {"type": "sql_injection", "location": "get_user_by_name", "fix": "use parameterized queries"},
    {"type": "xss", "location": "render_comment", "fix": "sanitize user input"},
    {"type": "sql_injection", "location": "login", "fix": "use parameterized queries"},
    {"type": "command_injection", "location": "run_report", "fix": "avoid shell=True"},
    {"type": "insecure_deserialization", "location": "load_user_data", "fix": "use json instead of pickle"}
  ]
}
```

---

### 3. Data Cleaning Agent

| Task | Difficulty | Description |
|------|-----------|-------------|
| `data_cleaning_easy` | 🟢 Easy | Identify missing values and duplicate rows |
| `data_cleaning_medium` | 🟡 Medium | Fix 5 data type/format issues and return cleaned dataset |
| `data_cleaning_hard` | 🔴 Hard | Detect outliers via IQR, impute missing values, return clean dataset |

**Easy payload:**
```json
{
  "missing": ["age (row 2)", "name (row 4)", "email (row 5)", "salary (row 6)"],
  "duplicates": [1, 3]
}
```

---

### 4. Content Moderation Agent

| Task | Difficulty | Description |
|------|-----------|-------------|
| `content_moderation_easy` | 🟢 Easy | Classify 7 posts as safe or harmful (explicit content) |
| `content_moderation_medium` | 🟡 Medium | Detect subtle toxicity, sarcasm, implicit hostility across 8 posts |
| `content_moderation_hard` | 🔴 Hard | Context-aware moderation: same text, 2 different contexts, 3 cases |

**Hard payload:**
```json
{
  "decisions": [
    {"id": "h1", "context_a_label": "safe", "context_b_label": "harmful"},
    {"id": "h2", "context_a_label": "safe", "context_b_label": "harmful"},
    {"id": "h3", "context_a_label": "safe", "context_b_label": "harmful"}
  ]
}
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
| GET | `/ui` | Gradio interactive frontend |

---

## Setup & Usage

### Local Development

```bash
git clone https://huggingface.co/spaces/Flake56/meta-openenv
cd meta-openenv
pip install openenv-core openai fastapi uvicorn pydantic gradio
uvicorn server.app:app --host 0.0.0.0 --port 7860
# Open http://localhost:7860/ui for the Gradio interface
```

### Docker

```bash
docker build -t meta-env:latest .
docker run -p 7860:7860 meta-env:latest
```

### inference.py (Hackathon Validator)

```bash
export API_BASE_URL=https://api.openai.com/v1
export MODEL_NAME=gpt-4o-mini
export HF_TOKEN=hf_...
python inference.py
```

### Run Tests

```bash
pytest tests/ -v
```

### Test Key Endpoints

```bash
# Health
curl https://Flake56-meta-openenv.hf.space/health

# List all tasks
curl https://Flake56-meta-openenv.hf.space/tasks

# Step — Email triage easy
curl -X POST https://Flake56-meta-openenv.hf.space/step \
  -H "Content-Type: application/json" \
  -d '{"action": {"message": "{\"agent\": \"email_triage\", \"task_id\": \"email_triage_easy\", \"payload\": {\"classification\": \"spam\"}}"}}'
```

---

## Baseline Scores (GPT-4o-mini)

| Task | Difficulty | Score |
|------|-----------|-------|
| email_triage_easy | 🟢 Easy | 1.00 |
| email_triage_medium | 🟡 Medium | 0.80 |
| email_triage_hard | 🔴 Hard | 0.67 |
| code_review_easy | 🟢 Easy | 1.00 |
| code_review_medium | 🟡 Medium | 0.75 |
| code_review_hard | 🔴 Hard | 0.80 |
| data_cleaning_easy | 🟢 Easy | 1.00 |
| data_cleaning_medium | 🟡 Medium | 0.67 |
| data_cleaning_hard | 🔴 Hard | 0.67 |
| content_moderation_easy | 🟢 Easy | 1.00 |
| content_moderation_medium | 🟡 Medium | 0.75 |
| content_moderation_hard | 🔴 Hard | 0.50 |
| **Average** | | **0.80** |

---

## Project Structure

```
meta-openenv/
├── Dockerfile                   # Container for HF Spaces (port 7860)
├── README.md                    # This file
├── inference.py                 # Hackathon validator script (API_BASE_URL, MODEL_NAME, HF_TOKEN)
├── baseline.py                  # OpenAI baseline inference script
├── models.py                    # Pydantic models: MetaAction, MetaObservation
├── openenv.yaml                 # OpenEnv spec — all 12 task IDs, port 7860
├── pyproject.toml               # Project dependencies
├── .dockerignore                # Excludes .venv — keeps build under 1MB
├── __init__.py
├── tests/
│   └── test_environment.py      # pytest suite: reset, step, grader determinism
└── server/
    ├── app.py                   # FastAPI app — all endpoints + Gradio mount at /ui
    ├── gradio_ui.py             # Gradio frontend: Task Explorer, Baseline Runner, Dashboard
    ├── Meta_environment.py      # All 4 agents + 12 tasks + graders
    ├── requirements.txt
    └── __init__.py
```

---

## Novelty

**Meta is the first multi-domain OpenEnv environment.** A single agent can step through email
classification, security vulnerability detection, statistical outlier analysis, and context-aware
content moderation — all within one standardized OpenEnv interface. This enables research that
is simply not possible with single-domain environments: multi-task curricula, cross-domain transfer
experiments, and benchmarks for genuinely generalist AI agents.

---

## Team

**Digital Yodha** — OpenEnv Hackathon 2026

| Name | GitHub |
|------|--------|
| Sangisetti Akarsh | [@Farbricated](https://github.com/Farbricated) |
| Sarika Jivrajika | [@Sarika-stack23](https://github.com/Sarika-stack23) |

---

## License

MIT License — feel free to use, modify, and build on this environment.
