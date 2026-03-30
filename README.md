---
title: Meta OpenEnv
emoji: 🤖
colorFrom: blue
colorTo: purple
sdk: docker
pinned: false
tags:
  - openenv
---

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

## Environment Design

### Action Space

All actions use a unified JSON-in-message format compatible with the OpenEnv spec:

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

- Score range: **0.0 to 1.0** (never binary — always partial credit)
- **Partial credits** per criterion (e.g. 3/5 bugs found = 0.6)
- **Penalty** of -0.1 for empty/malformed payloads
- **Episode average** tracked in metadata across multi-task runs
- Graders are deterministic and reproducible

---

## Task Descriptions

### Email Triage Agent

| Task | Difficulty | Description |
|------|-----------|-------------|
| `email_triage_easy` | Easy | Classify a single email: spam, important, or newsletter |
| `email_triage_medium` | Medium | Prioritize 10 workplace emails by urgency |
| `email_triage_hard` | Hard | Draft a professional reply to a complex customer complaint |

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

### Code Review Agent

| Task | Difficulty | Description |
|------|-----------|-------------|
| `code_review_easy` | Easy | Find syntax errors in a Python function |
| `code_review_medium` | Medium | Identify 4 logical bugs and suggest fixes |
| `code_review_hard` | Hard | Detect 5 security vulnerabilities (SQL injection, XSS, command injection, insecure deserialization) |

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

### Data Cleaning Agent

| Task | Difficulty | Description |
|------|-----------|-------------|
| `data_cleaning_easy` | Easy | Identify missing values and duplicate rows |
| `data_cleaning_medium` | Medium | Fix 5 data type/format issues and return cleaned dataset |
| `data_cleaning_hard` | Hard | Detect outliers via IQR, impute missing values, return clean dataset |

**Easy payload:**
```json
{
  "missing": ["age (row 2)", "name (row 4)", "email (row 5)", "salary (row 6)"],
  "duplicates": [1, 3]
}
```

---

### Content Moderation Agent

| Task | Difficulty | Description |
|------|-----------|-------------|
| `content_moderation_easy` | Easy | Classify 7 posts as safe or harmful (explicit content) |
| `content_moderation_medium` | Medium | Detect subtle toxicity, sarcasm, implicit hostility across 8 posts |
| `content_moderation_hard` | Hard | Context-aware moderation: same text, 2 different contexts, 3 cases |

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

---

## Setup & Usage

### Local Development

```bash
git clone https://huggingface.co/spaces/Flake56/meta-openenv
cd meta-openenv
pip install openenv-core openai fastapi uvicorn pydantic
uvicorn server.app:app --host 0.0.0.0 --port 7860
```

### Docker

```bash
# Build from repo root
docker build -t meta-env:latest .

# Run
docker run -p 7860:7860 meta-env:latest

# With OpenAI key for baseline
docker run -p 7860:7860 -e OPENAI_API_KEY=sk-... meta-env:latest
```

### Test All Endpoints

```bash
# Health
curl https://Flake56-meta-openenv.hf.space/health

# List all tasks
curl https://Flake56-meta-openenv.hf.space/tasks

# Reset
curl -X POST https://Flake56-meta-openenv.hf.space/reset -H "Content-Type: application/json" -d '{}'

# Step - Email triage easy
curl -X POST https://Flake56-meta-openenv.hf.space/step \
  -H "Content-Type: application/json" \
  -d '{"action": {"message": "{\"agent\": \"email_triage\", \"task_id\": \"email_triage_easy\", \"payload\": {\"classification\": \"spam\"}}"}}'
```

### Run Baseline

```bash
export OPENAI_API_KEY=sk-...
python baseline.py
```

---

## Baseline Scores (GPT-4o-mini)

| Task | Difficulty | Score |
|------|-----------|-------|
| email_triage_easy | Easy | 1.00 |
| email_triage_medium | Medium | 0.80 |
| email_triage_hard | Hard | 0.67 |
| code_review_easy | Easy | 1.00 |
| code_review_medium | Medium | 0.75 |
| code_review_hard | Hard | 0.80 |
| data_cleaning_easy | Easy | 1.00 |
| data_cleaning_medium | Medium | 0.67 |
| data_cleaning_hard | Hard | 0.67 |
| content_moderation_easy | Easy | 1.00 |
| content_moderation_medium | Medium | 0.75 |
| content_moderation_hard | Hard | 0.50 |
| **Average** | | **0.80** |

---

## Project Structure

```
meta-openenv/
├── Dockerfile                   # Container for HF Spaces
├── README.md                    # This file
├── baseline.py                  # OpenAI baseline inference script
├── models.py                    # Pydantic models: MetaAction, MetaObservation
├── openenv.yaml                 # OpenEnv spec metadata
├── pyproject.toml               # Project dependencies
├── __init__.py
└── server/
    ├── app.py                   # FastAPI app with all endpoints
    ├── Meta_environment.py      # All 4 agents + 12 tasks + graders
    ├── requirements.txt
    └── __init__.py
```

---

## Why Meta?

Most OpenEnv environments cover a single domain. **Meta is the first multi-domain
environment** that lets a single agent learn to handle completely different real-world
tasks in one unified interface. This makes it ideal for:

- Training **generalist agents** that can switch between task types
- Benchmarking **multi-task learning** capabilities of LLMs
- Evaluating **transfer learning** between related domains (e.g. email triage → content moderation)
- Testing **robustness** of agents across varying difficulty levels

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