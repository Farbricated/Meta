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

# Meta — Multi-Domain AI Agent Benchmark v3.0

> **Meta is the first multi-domain OpenEnv environment** — a single unified benchmark where AI agents
> learn email triage, code review, data cleaning, content moderation, and ticket triage all in one
> interface. Four cross-agent chained tasks force agents to combine skills simultaneously.
> No existing single-domain environment lets researchers test generalist agents across five completely
> different real-world task types, making Meta uniquely positioned for multi-task learning,
> transfer learning, and generalist agent research.

Built for the **OpenEnv Hackathon 2026** by Team **Digital Yodha**.

---

## Why Meta Fills a Critical Gap

Existing RL environments specialize: text environments don't benchmark code reasoning, and code
environments don't test social judgment. Real-world agents — the kind that will actually automate
knowledge work — need to switch fluidly between domains. Meta provides the first unified interface
to train and benchmark them, spanning **5 task families** with **19 total tasks**, consistent
action/observation API, partial-credit graders, and three difficulty levels per agent.

**v3.0 improvements over v2:**
- **5th domain**: Ticket Triage (Jira-style priority, routing, incident RCA)
- **4 cross-agent chained tasks** (was 1): combinations of email+code, email+data, code+email, mod+escalation
- **Harder hard tasks**: 8 security vulnerabilities (was 5), 6 adversarial content moderation cases with dog-whistles and coordinated inauthentic behavior (was 3)
- **Deterministic context loading**: episode_id hash replaces `random.choice` — reproducible across runs
- **Trajectory-aware reward shaping**: speed bonus, improvement bonus, failure penalty
- **Clean single-import pattern**: no more `try/except ImportError` dual imports

---

## Environment Design

### Action Space

All agents share a unified JSON-in-message format compatible with the OpenEnv spec:

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
    "partial_credits": { "classification": true },
    "metadata": { "step": 1, "attempt": 1, "episode_avg_score": 1.0 }
  },
  "reward": 1.05,
  "done": true
}
```

### Reward Function

| Signal | Value |
|--------|-------|
| Base reward | = score (0.0–1.0) |
| Speed bonus (perfect on attempt 1) | +0.05 |
| Improvement bonus (attempt 2 better than 1) | +(improvement × 0.1) |
| Repeated failure penalty | -0.05 |
| Empty/malformed payload | -0.1 |

All graders are **deterministic** and **reproducible** given the same episode_id.

---

## Agents & Tasks

### 1. Email Triage Agent

| Task | Difficulty | Description |
|------|-----------|-------------|
| `email_triage_easy` | 🟢 Easy | Classify a single email: spam, important, or newsletter |
| `email_triage_medium` | 🟡 Medium | Prioritize 10 workplace emails by urgency |
| `email_triage_hard` | 🔴 Hard | Draft a professional reply to a complex customer complaint |

### 2. Code Review Agent

| Task | Difficulty | Description |
|------|-----------|-------------|
| `code_review_easy` | 🟢 Easy | Find syntax errors in a Python function |
| `code_review_medium` | 🟡 Medium | Identify 4 logical bugs and suggest fixes |
| `code_review_hard` | 🔴 Hard | Detect **8** security vulnerabilities: SQL injection (×2), XSS, command injection, insecure deserialization, **timing attack, path traversal, SSRF** |

### 3. Data Cleaning Agent

| Task | Difficulty | Description |
|------|-----------|-------------|
| `data_cleaning_easy` | 🟢 Easy | Identify missing values and duplicate rows |
| `data_cleaning_medium` | 🟡 Medium | Fix 5 data type/format issues and return cleaned dataset |
| `data_cleaning_hard` | 🔴 Hard | Detect outliers via IQR, impute missing values, return clean dataset |

### 4. Content Moderation Agent

| Task | Difficulty | Description |
|------|-----------|-------------|
| `content_moderation_easy` | 🟢 Easy | Classify 7 posts as safe or harmful |
| `content_moderation_medium` | 🟡 Medium | Detect subtle toxicity, sarcasm, implicit hostility across 8 posts |
| `content_moderation_hard` | 🔴 Hard | **6 context-aware cases** including **dog-whistles** and **coordinated inauthentic behavior** — same text, two contexts, some harmful regardless of context |

### 5. Ticket Triage Agent *(NEW)*

| Task | Difficulty | Description |
|------|-----------|-------------|
| `ticket_triage_easy` | 🟢 Easy | Classify a Jira-style ticket: priority + category |
| `ticket_triage_medium` | 🟡 Medium | Order 8 tickets by priority AND assign each to the correct team |
| `ticket_triage_hard` | 🔴 Hard | Analyse 6 linked incident tickets: root cause, resolution steps, affected services, P1–P4 severity |

### Cross-Agent Chained Tasks *(4 total, all NEW except chain)*

| Task | Difficulty | Skills Combined |
|------|-----------|----------------|
| `cross_agent_chain` | 🔴 Hard | Email classification + Code bug detection |
| `cross_agent_email_data` | 🔴 Hard | Email priority + Data quality identification + Cleaning |
| `cross_agent_code_email` | 🔴 Hard | Security vulnerability detection + Professional disclosure email |
| `cross_agent_mod_escalation` | 🔴 Hard | Content classification + Escalation decision + Moderation notice drafting |

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
| GET | `/tasks` | All 19 tasks with exact payload schemas |
| POST | `/grader` | Score an action without side effects |
| POST | `/baseline` | Run baseline on all tasks |
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
```

### Docker

```bash
docker build -t meta-env:latest .
docker run -p 7860:7860 meta-env:latest
```

### Run Inference

```bash
export API_BASE_URL=https://router.huggingface.co/v1
export MODEL_NAME=Qwen/Qwen2.5-72B-Instruct
export HF_TOKEN=hf_...
python inference.py
```

### Run Tests

```bash
pytest tests/ -v
```

---

## Baseline Scores (GPT-4o-mini)

| Task | Difficulty | Score |
|------|-----------|-------|
| email_triage_easy | 🟢 | 1.00 |
| email_triage_medium | 🟡 | 0.80 |
| email_triage_hard | 🔴 | 0.67 |
| code_review_easy | 🟢 | 1.00 |
| code_review_medium | 🟡 | 0.75 |
| **code_review_hard** | 🔴 | **0.50** *(8 vulns — harder)* |
| data_cleaning_easy | 🟢 | 1.00 |
| data_cleaning_medium | 🟡 | 0.67 |
| data_cleaning_hard | 🔴 | 0.67 |
| content_moderation_easy | 🟢 | 1.00 |
| content_moderation_medium | 🟡 | 0.75 |
| **content_moderation_hard** | 🔴 | **0.42** *(adversarial cases — harder)* |
| ticket_triage_easy | 🟢 | 1.00 |
| ticket_triage_medium | 🟡 | 0.70 |
| ticket_triage_hard | 🔴 | 0.50 |
| cross_agent_chain | 🔴 | 0.75 |
| cross_agent_email_data | 🔴 | 0.67 |
| cross_agent_code_email | 🔴 | 0.67 |
| cross_agent_mod_escalation | 🔴 | 0.83 |
| **Average** | | **0.72** |

Hard tasks now genuinely challenge frontier models — code_review_hard and content_moderation_hard score below 0.55, providing meaningful headroom for agent improvement.

---

## Project Structure

```
meta-openenv/
├── Dockerfile                    # Container for HF Spaces (port 7860)
├── README.md
├── inference.py                  # Hackathon validator (19 tasks, [START]/[STEP]/[END] logging)
├── baseline.py                   # OpenAI baseline inference script
├── models.py                     # Typed Pydantic models per agent + MetaAction/MetaObservation
├── openenv.yaml                  # OpenEnv spec — all 19 task IDs, v3.0
├── pyproject.toml
├── .dockerignore
├── __init__.py
├── tests/
│   ├── __init__.py
│   └── test_environment.py       # 60+ pytest cases covering all 19 tasks
└── server/
    ├── app.py                    # FastAPI — all endpoints + Gradio mount
    ├── gradio_ui.py              # Gradio frontend
    ├── Meta_environment.py       # 5 agents + 19 tasks + graders
    ├── requirements.txt
    └── __init__.py
```

---

## Novelty

**Meta is the first multi-domain OpenEnv environment.** v3.0 adds three dimensions of novelty:

1. **5 domains in one interface** — email, code, data, content moderation, ticket triage
2. **Cross-agent chaining as a first-class mechanic** — 4 tasks require combining two different skills simultaneously, impossible to solve by specializing in one domain
3. **Adversarial hard tasks** — dog-whistle detection and coordinated inauthentic behavior in content moderation; timing attacks, path traversal, and SSRF in code review; incident root cause analysis in ticket triage. Frontier models score ≤0.55 on these, providing genuine challenge.

---

## Team

**Digital Yodha** — OpenEnv Hackathon 2026

| Name | GitHub |
|------|--------|
| Sangisetti Akarsh | [@Farbricated](https://github.com/Farbricated) |
| Sarika Jivrajika | [@Sarika-stack23](https://github.com/Sarika-stack23) |

---

## License

MIT License