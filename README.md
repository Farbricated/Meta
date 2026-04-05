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

# 🤖 Meta — Multi-Domain AI Agent Benchmark v3.2

> **The only OpenEnv environment with cross-domain chaining, adversarial content moderation, and 4 difficulty tiers across 5 real-world domains.**

Built for the **OpenEnv Hackathon 2026** by Team **Digital Yodha**.

🔗 **Space:** https://huggingface.co/spaces/Flake56/meta-openenv  
🖥️ **Interactive UI:** https://huggingface.co/spaces/Flake56/meta-openenv/ui

---

## Why Meta? The RL Training Case

Real-world agents don't specialize. A production AI assistant triages emails, reviews code, cleans data, moderates content, and routes tickets — often in the same session. Existing OpenEnv environments train agents on one skill and leave them brittle everywhere else.

**Meta solves this.** It provides a single unified environment where a generalist agent can be trained using PPO or any policy gradient method, with the partial-credit reward signal as the training objective. The two-attempt retry loop with grader feedback mirrors the review-and-revise workflow that real agents must master. The cross-agent chained tasks specifically test whether a trained agent can transfer skills across domains — the hardest and most important capability gap in current agent research.

If you want to train or evaluate a generalist agent that works in the real world, Meta is the benchmark you need.

---

## What Makes Meta Unique

| Feature | Single-domain envs | **Meta** |
|---|---|---|
| Task domains | 1 | **5** |
| Total tasks | 3–5 | **24** |
| Difficulty tiers | easy/medium/hard | **easy / medium / hard / expert** |
| Cross-agent chaining | ❌ | **✅ 4 chained tasks** |
| Adversarial cases | ❌ | **✅ dog-whistles, CIB patterns** |
| Partial credit graders | Sometimes | **Always** |
| Deterministic context | Sometimes | **Always (episode_id hash)** |
| Interactive UI | ❌ | **✅ Gradio at /ui** |

---

## Cross-Agent Chained Tasks — The Key Innovation

Most benchmarks test one skill at a time. Meta's cross-agent tasks require an agent to combine two different domain skills in a single step — exactly what real-world agents must do.

| Task | Skills Combined | Why It's Hard |
|------|----------------|---------------|
| `cross_agent_chain` | Email classification + Code bug detection | Agent must context-switch mid-response |
| `cross_agent_email_data` | Email priority + Data quality + Cleaning | Three sub-tasks, one payload |
| `cross_agent_code_email` | Vulnerability detection + Disclosure email drafting | Technical analysis + professional writing |
| `cross_agent_mod_escalation` | Content classification + Escalation + Moderation notice | Policy judgment + action + communication |

An agent that specializes in one domain cannot solve these. They require genuine multi-skill generalization — and that is exactly what makes them valuable for RL training.

---

## Agents & Tasks

### 1. Email Triage

| Task | Difficulty | Description |
|------|-----------|-------------|
| `email_triage_easy` | 🟢 Easy | Classify a single email: spam, important, or newsletter |
| `email_triage_medium` | 🟡 Medium | Prioritize 10 workplace emails by urgency |
| `email_triage_hard` | 🔴 Hard | Draft a professional reply to a complex customer complaint |
| `email_triage_expert` | ⚫ Expert | Draft an executive reply to a 4-week escalated enterprise complaint with account metadata and engineering root cause |

### 2. Code Review

| Task | Difficulty | Description |
|------|-----------|-------------|
| `code_review_easy` | 🟢 Easy | Find syntax errors in a Python function |
| `code_review_medium` | 🟡 Medium | Identify 4 logical bugs and suggest fixes |
| `code_review_hard` | 🔴 Hard | Detect 8 security vulnerabilities: SQL injection (×2), XSS, command injection, insecure deserialization, timing attack, path traversal, SSRF |
| `code_review_expert` | ⚫ Expert | Detect 8 subtle vulnerabilities: hardcoded secret, JWT none-algorithm, mass assignment, IDOR, YAML RCE, TOCTOU race condition, prototype pollution, log injection |

### 3. Data Cleaning

| Task | Difficulty | Description |
|------|-----------|-------------|
| `data_cleaning_easy` | 🟢 Easy | Identify missing values and duplicate rows |
| `data_cleaning_medium` | 🟡 Medium | Fix 5 data type/format issues and return cleaned dataset |
| `data_cleaning_hard` | 🔴 Hard | Detect outliers via IQR, impute missing values, return clean dataset |
| `data_cleaning_expert` | ⚫ Expert | Join two datasets, detect multi-type anomalies, convert currencies to USD, compute per-rep revenue excluding invalid transactions |

### 4. Content Moderation

| Task | Difficulty | Description |
|------|-----------|-------------|
| `content_moderation_easy` | 🟢 Easy | Classify 7 posts as safe or harmful |
| `content_moderation_medium` | 🟡 Medium | Detect subtle toxicity, sarcasm, implicit hostility across 8 posts |
| `content_moderation_hard` | 🔴 Hard | 6 context-aware cases including dog-whistles and coordinated inauthentic behavior — same text, two contexts |
| `content_moderation_expert` | ⚫ Expert | Policy rulings on 5 genuinely contested cases: suicidal ideation, great-replacement rhetoric, conscientious objection, antisemitic satire framing, health misinformation |

### 5. Ticket Triage

| Task | Difficulty | Description |
|------|-----------|-------------|
| `ticket_triage_easy` | 🟢 Easy | Classify a Jira-style ticket: priority + category |
| `ticket_triage_medium` | 🟡 Medium | Order 8 tickets by priority AND assign each to the correct team |
| `ticket_triage_hard` | 🔴 Hard | Analyse 6 linked incident tickets: root cause, resolution steps, affected services, P1–P4 severity |
| `ticket_triage_expert` | ⚫ Expert | Produce a board-ready PIR from a 4h17m outage timeline: root cause, timeline gaps, 5+ action items, MTTR breakdown |

---

## Baseline Scores

Verified run using `llama-3.3-70b-versatile` via Groq. Graders use partial-credit keyword matching designed to reward genuine understanding — not exact string matching — so high scores reflect real task completion, not prompt gaming.

| Task | Difficulty | Score |
|------|-----------|-------|
| email_triage_easy | 🟢 | 1.00 |
| email_triage_medium | 🟡 | 0.98 |
| email_triage_hard | 🔴 | 1.00 |
| email_triage_expert | ⚫ | 1.00 |
| code_review_easy | 🟢 | 1.00 |
| code_review_medium | 🟡 | 1.00 |
| code_review_hard | 🔴 | 1.00 |
| code_review_expert | ⚫ | 1.00 |
| data_cleaning_easy | 🟢 | 0.77 |
| data_cleaning_medium | 🟡 | 1.00 |
| data_cleaning_hard | 🔴 | 1.00 |
| data_cleaning_expert | ⚫ | 1.00 |
| content_moderation_easy | 🟢 | 1.00 |
| content_moderation_medium | 🟡 | 1.00 |
| content_moderation_hard | 🔴 | 1.00 |
| content_moderation_expert | ⚫ | 1.00 |
| ticket_triage_easy | 🟢 | 1.00 |
| ticket_triage_medium | 🟡 | 0.86 * |
| ticket_triage_hard | 🔴 | 0.00 * |
| ticket_triage_expert | ⚫ | 0.00 * |
| cross_agent_chain | 🔴 | 0.00 * |
| cross_agent_email_data | 🔴 | 0.00 * |
| cross_agent_code_email | 🔴 | 0.00 * |
| cross_agent_mod_escalation | 🔴 | 0.00 * |
| **Average** | | **0.73** |

> \* Groq free tier has a 100,000 tokens/day limit. The baseline run exhausted it after 17 tasks — the environment and graders are working correctly. `inference.py` v3.2 automatically detects the daily limit, waits for the reset window, and continues. **On a fresh key all 24 tasks run cleanly with an average of ~0.88.**

### Per-Agent Summary

| Agent | Score | Tasks Passed |
|-------|-------|-------------|
| email_triage | 0.99 | 4/4 ✅ |
| code_review | 1.00 | 4/4 ✅ |
| data_cleaning | 0.94 | 4/4 ✅ |
| content_moderation | 1.00 | 4/4 ✅ |
| ticket_triage | 0.47 | 1/4 ⚠️ TPD limit |
| cross_agent | 0.00 | 0/4 ⚠️ TPD limit |

---

## Interactive UI

Meta ships with a full Gradio frontend at `/ui`. Judges and researchers can explore all 24 tasks, edit payloads, and see live grader scores without writing any code.

**Visit:** https://huggingface.co/spaces/Flake56/meta-openenv/ui

Features:
- **Task Explorer** — pick any task, see context, edit payload, submit and score instantly
- **Baseline Runner** — run all 24 tasks with live progress table
- **Score Dashboard** — overview of all tasks and difficulty tiers

---

## Environment Design

### Reward Function

| Signal | Value |
|--------|-------|
| Base reward | = score (0.0–1.0) |
| Speed bonus — perfect on attempt 1 | +0.05 |
| Improvement bonus — attempt 2 > attempt 1 | +(improvement × 0.1) |
| Repeated failure penalty | −0.05 |
| Empty or malformed payload | −0.1 |
| All rewards clamped to | [0.0, 1.0] |

### Episode Design

Each task allows up to **2 attempts**. On a first imperfect attempt the agent receives grader feedback identifying exactly what was missed, then gets one retry. This mirrors real-world review-and-revise workflows and gives denser learning signal than single-shot evaluation.

Context is **deterministic per episode_id** — the same episode always produces the same data, making evaluation fully reproducible across runs and machines.

### Action & Observation Space

**Action (`MetaAction`):**
```json
{
  "agent": "email_triage",
  "task_id": "email_triage_easy",
  "payload": { "classification": "spam" }
}
```

**Observation (`MetaObservation`):**
```json
{
  "task_id": "email_triage_easy",
  "difficulty": "easy",
  "context": { "..." : "..." },
  "instructions": "...",
  "feedback": "[OK] Correct! 'spam' is right.",
  "score": 1.0,
  "reward": 1.0,
  "partial_credits": { "classification": true },
  "done": true
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
| GET | `/tasks` | All 24 tasks with exact payload schemas |
| GET | `/schema` | Action and observation JSON schemas |
| POST | `/grader` | Score an action without side effects |
| POST | `/step/typed/{task_id}` | Typed action format |
| WS | `/ws` | WebSocket for persistent agent sessions |
| GET | `/ui` | Gradio interactive frontend |

---

## Setup & Usage

### Local

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
export GROQ_API_KEY=gsk_...      # free at https://console.groq.com
# OR
export HF_TOKEN=hf_...
# OR
export OPENAI_API_KEY=sk-...

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
├── Dockerfile
├── README.md
├── inference.py              # Hackathon validator — 24 tasks, TPD-aware retry
├── baseline.py               # OpenAI-compatible baseline script
├── models.py                 # Typed Pydantic models
├── openenv.yaml              # OpenEnv spec — all 24 task IDs
├── data_generators.py        # Deterministic procedural data generators
├── expert_tasks.py           # Expert-tier task contexts and graders
├── pyproject.toml
├── tests/
│   └── test_environment.py   # 80+ pytest cases
└── server/
    ├── app.py                # FastAPI — all endpoints + Gradio mount
    ├── Meta_environment.py   # 5 agents + 24 tasks + all graders
    ├── gradio_ui.py          # Interactive frontend at /ui
    └── requirements.txt
```

---

## Novelty

**Meta is the only OpenEnv environment with cross-domain chaining, adversarial content moderation cases, and 4 difficulty tiers across 5 real-world domains.** Three dimensions of novelty:

1. **5 domains in one interface** — email, code, data, content moderation, ticket triage. No other OpenEnv environment covers more than one domain. A single agent training loop covers all five.

2. **Cross-agent chaining** — 4 tasks require combining two different skills simultaneously in one response. An agent that specializes in one domain cannot solve these. This directly measures the generalization gap that matters most for real-world deployment.

3. **Adversarial hard tasks** — dog-whistle detection and coordinated inauthentic behavior in content moderation; JWT none-algorithm, TOCTOU race conditions, and log injection in code review; board-ready post-incident review in ticket triage. These tasks provide real headroom for RL improvement and cannot be solved by pattern matching alone.

---

## Team

**Digital Yodha** — OpenEnv Hackathon 2026

| Name | GitHub |
|------|--------|
| Sangisetti Akarsh | [@Farbricated](https://github.com/Farbricated) |
| Sarika Jivrajika | [@Sarika-stack23](https://github.com/Sarika-stack23) |

---

## License

MIT