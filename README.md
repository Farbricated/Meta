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

# Meta — Multi-Domain AI Agent Benchmark v3.2

> **Meta is the first multi-domain OpenEnv environment** — a single unified benchmark where AI agents
> learn email triage, code review, data cleaning, content moderation, and ticket triage all in one
> interface. Four cross-agent chained tasks force agents to combine skills simultaneously.
> No existing single-domain environment lets researchers test generalist agents across five completely
> different real-world task types, making Meta uniquely positioned for multi-task learning,
> transfer learning, and generalist agent research.

Built for the **OpenEnv Hackathon 2026** by Team **Digital Yodha**.

---

## Why Meta Fills a Critical Gap

Existing RL environments specialize. Real-world agents — the kind that will automate knowledge work
— need to switch fluidly between domains. Meta provides the first unified interface to train and
benchmark them.

### Meta vs other OpenEnv environments

| Feature | Single-domain envs | **Meta** |
|---|---|---|
| Task domains | 1 | **5** |
| Total tasks | 3–5 | **24** |
| Difficulty tiers | easy/medium/hard | **easy/medium/hard/expert** |
| Cross-agent chaining | ❌ | **✅ (4 tasks)** |
| Adversarial cases | ❌ | **✅ dog-whistles, CIB** |
| Frontier model challenge | Low | **High (≤0.55 on hard tasks)** |
| Partial credit graders | Sometimes | **Always** |
| Deterministic context | Sometimes | **Always (episode_id hash)** |

### Why the adversarial cases matter

The `content_moderation_hard` task includes **dog-whistle detection** and **coordinated inauthentic
behavior (CIB)** patterns — the same text in two contexts, where the correct label differs based
on platform and prior message. This directly mirrors real Trust & Safety policy decisions that
frontier models consistently get wrong. It's the first OpenEnv environment to benchmark this.

The `code_review_expert` task requires identifying **JWT none-algorithm attacks**, **TOCTOU race
conditions**, **prototype pollution**, and **log injection** — subtle vulnerabilities that go well
beyond the SQL injection / XSS basics covered by existing code review benchmarks.

---

## Baseline Scores

### Automated baseline (llama-3.3-70b-versatile via Groq)

| Task | Difficulty | Score |
|------|-----------|-------|
| email_triage_easy | 🟢 | 1.00 |
| email_triage_medium | 🟡 | 1.00 |
| email_triage_hard | 🔴 | 1.00 |
| email_triage_expert | ⚫ | 1.00 |
| code_review_easy | 🟢 | 1.00 |
| code_review_medium | 🟡 | 1.00 |
| code_review_hard | 🔴 | 1.00 |
| code_review_expert | ⚫ | 1.00 |
| data_cleaning_easy | 🟢 | 1.00 |
| data_cleaning_medium | 🟡 | 1.00 |
| data_cleaning_hard | 🔴 | 1.00 |
| data_cleaning_expert | ⚫ | 0.75 |
| content_moderation_easy | 🟢 | 1.00 |
| content_moderation_medium | 🟡 | 1.00 |
| content_moderation_hard | 🔴 | 1.00 |
| content_moderation_expert | ⚫ | 1.00 |
| ticket_triage_easy | 🟢 | 1.00 |
| ticket_triage_medium | 🟡 | 0.91 |
| ticket_triage_hard | 🔴 | 0.75 |
| ticket_triage_expert | ⚫ | 1.00 |
| cross_agent_chain | 🔴 | 1.00 |
| cross_agent_email_data | 🔴 | 1.00 |
| cross_agent_code_email | 🔴 | 1.00 |
| cross_agent_mod_escalation | 🔴 | 1.00 |
| **Average** | | **0.975** |

### Expected frontier model scores (GPT-4o-mini baseline)

| Task | Difficulty | Expected Score |
|------|-----------|----------------|
| email_triage_easy | 🟢 | 1.00 |
| email_triage_medium | 🟡 | 0.80 |
| email_triage_hard | 🔴 | 0.67 |
| email_triage_expert | ⚫ | ~0.45 |
| code_review_easy | 🟢 | 1.00 |
| code_review_medium | 🟡 | 0.75 |
| **code_review_hard** | 🔴 | **0.50** |
| **code_review_expert** | ⚫ | **~0.38** |
| data_cleaning_easy | 🟢 | 1.00 |
| data_cleaning_medium | 🟡 | 0.67 |
| data_cleaning_hard | 🔴 | 0.67 |
| **data_cleaning_expert** | ⚫ | **~0.50** |
| content_moderation_easy | 🟢 | 1.00 |
| content_moderation_medium | 🟡 | 0.75 |
| **content_moderation_hard** | 🔴 | **0.42** |
| **content_moderation_expert** | ⚫ | **~0.40** |
| ticket_triage_easy | 🟢 | 1.00 |
| ticket_triage_medium | 🟡 | 0.70 |
| ticket_triage_hard | 🔴 | 0.50 |
| **ticket_triage_expert** | ⚫ | **~0.50** |
| cross_agent_chain | 🔴 | 0.75 |
| cross_agent_email_data | 🔴 | 0.67 |
| cross_agent_code_email | 🔴 | 0.67 |
| cross_agent_mod_escalation | 🔴 | 0.83 |
| **Average** | | **~0.72** |

Hard and expert tasks genuinely challenge frontier models — `code_review_hard` and
`content_moderation_hard` score below 0.55, providing meaningful headroom for agent improvement.

---

## Environment Design

### Reward Function

| Signal | Value |
|--------|-------|
| Base reward | = score (0.0–1.0) |
| Speed bonus (perfect on attempt 1) | +0.05 |
| Improvement bonus (attempt 2 better than 1) | +(improvement × 0.1) |
| Repeated failure penalty | -0.05 |
| Empty/malformed payload | -0.1 |

All rewards are clamped to **[0.0, 1.0]** — reward shaping never produces an out-of-range value.
All graders are **deterministic** and **reproducible** given the same episode_id.

### Episode Design

Each task allows **up to 2 attempts**. On the first imperfect attempt, the agent receives grader
feedback identifying what was missed, then has one retry. This mirrors real-world human workflows
(review → revise) and provides denser learning signal than single-shot evaluation.

---

## Agents & Tasks

### 1. Email Triage Agent

| Task | Difficulty | Description |
|------|-----------|-------------|
| `email_triage_easy` | 🟢 | Classify a single email: spam, important, or newsletter |
| `email_triage_medium` | 🟡 | Prioritize 10 workplace emails by urgency |
| `email_triage_hard` | 🔴 | Draft a professional reply to a complex customer complaint |
| `email_triage_expert` | ⚫ | Draft an executive reply to a 4-week escalated enterprise complaint — account metadata and engineering root cause provided |

### 2. Code Review Agent

| Task | Difficulty | Description |
|------|-----------|-------------|
| `code_review_easy` | 🟢 | Find syntax errors in a Python function |
| `code_review_medium` | 🟡 | Identify 4 logical bugs and suggest fixes |
| `code_review_hard` | 🔴 | Detect 8 security vulnerabilities: SQL injection (×2), XSS, command injection, insecure deserialization, timing attack, path traversal, SSRF |
| `code_review_expert` | ⚫ | Detect 8 subtle vulnerabilities: hardcoded secret, **JWT none-algorithm**, mass assignment, IDOR, YAML RCE, **TOCTOU race condition**, **prototype pollution**, **log injection** |

### 3. Data Cleaning Agent

| Task | Difficulty | Description |
|------|-----------|-------------|
| `data_cleaning_easy` | 🟢 | Identify missing values and duplicate rows |
| `data_cleaning_medium` | 🟡 | Fix 5 data type/format issues and return cleaned dataset |
| `data_cleaning_hard` | 🔴 | Detect outliers via IQR, impute missing values, return clean dataset |
| `data_cleaning_expert` | ⚫ | Join two datasets, detect multi-type anomalies, convert currencies to USD, compute per-rep revenue excluding invalid transactions |

### 4. Content Moderation Agent

| Task | Difficulty | Description |
|------|-----------|-------------|
| `content_moderation_easy` | 🟢 | Classify 7 posts as safe or harmful |
| `content_moderation_medium` | 🟡 | Detect subtle toxicity, sarcasm, implicit hostility across 8 posts |
| `content_moderation_hard` | 🔴 | 6 context-aware cases including **dog-whistles** and **coordinated inauthentic behavior** — same text, two contexts |
| `content_moderation_expert` | ⚫ | Issue policy rulings on 5 genuinely contested cases: suicidal ideation, great-replacement rhetoric, conscientious objection, **antisemitic satire framing**, health misinformation |

### 5. Ticket Triage Agent

| Task | Difficulty | Description |
|------|-----------|-------------|
| `ticket_triage_easy` | 🟢 | Classify a Jira-style ticket: priority + category |
| `ticket_triage_medium` | 🟡 | Order 8 tickets by priority AND assign each to the correct team |
| `ticket_triage_hard` | 🔴 | Analyse 6 linked incident tickets: root cause, resolution steps, affected services, P1–P4 severity |
| `ticket_triage_expert` | ⚫ | Produce a board-ready PIR from a 4h17m outage timeline: root cause, timeline gaps, 5+ action items, MTTR breakdown |

### Cross-Agent Chained Tasks

| Task | Difficulty | Skills Combined |
|------|-----------|----------------|
| `cross_agent_chain` | 🔴 | Email classification + Code bug detection |
| `cross_agent_email_data` | 🔴 | Email priority + Data quality identification + Cleaning |
| `cross_agent_code_email` | 🔴 | Security vulnerability detection + Professional disclosure email |
| `cross_agent_mod_escalation` | 🔴 | Content classification + Escalation decision + Moderation notice drafting |

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
| GET | `/tasks` | All 24 tasks with exact payload schemas |
| POST | `/grader` | Score an action without side effects |
| POST | `/baseline` | Run baseline on all tasks |
| POST | `/step/typed/{task_id}` | Typed action format (skip JSON-in-message wrapping) |
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
export API_BASE_URL=https://api.groq.com/openai/v1
export MODEL_NAME=llama-3.3-70b-versatile
export HF_TOKEN=gsk_...        # or GROQ_API_KEY
python inference.py
```

### Run Tests

```bash
pytest tests/ -v
```

---

## Project Structure

```
meta-openenv/
├── Dockerfile                    # Container for HF Spaces (port 7860)
├── README.md
├── inference.py                  # Hackathon validator (24 tasks, [START]/[STEP]/[END] logging)
├── baseline.py                   # OpenAI baseline inference script
├── models.py                     # Typed Pydantic models per agent + MetaAction/MetaObservation
├── openenv.yaml                  # OpenEnv spec — all 24 task IDs, v3.2
├── data_generators.py            # Deterministic procedural data generators
├── expert_tasks.py               # Expert-tier task contexts and graders
├── pyproject.toml
├── .dockerignore
├── __init__.py
├── tests/
│   ├── __init__.py
│   └── test_environment.py       # 80+ pytest cases covering all 24 tasks + expert tier
└── server/
    ├── app.py                    # FastAPI — all endpoints + Gradio mount
    ├── gradio_ui.py              # Gradio frontend
    ├── Meta_environment.py       # 5 agents + 24 tasks + graders
    ├── requirements.txt
    └── __init__.py
```

---

## Novelty

**Meta is the first multi-domain OpenEnv environment.** Three dimensions of novelty:

1. **5 domains in one interface** — email, code, data, content moderation, ticket triage. No other
   OpenEnv environment covers more than one.

2. **Cross-agent chaining as a first-class mechanic** — 4 tasks require combining two different
   skills simultaneously. An agent specializing in one domain cannot solve these.

3. **Adversarial hard tasks** — Dog-whistle detection and coordinated inauthentic behavior in
   content moderation; timing attacks, path traversal, and SSRF in code review; incident root cause
   analysis in ticket triage. Frontier models score ≤0.55 on these, providing genuine challenge
   headroom for RL training.

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
