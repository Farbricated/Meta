# 🧠 Digital Yodha — OpenEnv Multi-Agent Environment

> A multi-domain AI agent training environment built for the OpenEnv Hackathon.
> Covers four real-world task domains: Email Triage, Code Review, Data Cleaning, and Content Moderation.

---

## 🌐 Overview

**Digital Yodha** (meaning *Digital Warrior* in Hindi) is a unified OpenEnv-compliant environment featuring **4 specialized agents**, each tackling a distinct real-world task domain with **3 difficulty levels** (easy → medium → hard).

| Agent | Domain | Tasks |
|-------|--------|-------|
| 📧 Email Triage | Customer / workplace email handling | Classify → Prioritize → Draft Reply |
| 🔍 Code Review | Software quality assurance | Syntax → Logic Bugs → Security Vulns |
| 🧹 Data Cleaning | Data quality engineering | Missing Values → Type Fixes → Outlier Imputation |
| 🛡️ Content Moderation | Platform trust & safety | Explicit → Subtle Toxicity → Context-Aware |

---

## 🏗️ Project Structure

```
digital_yodha/
├── app.py                          # FastAPI server (OpenEnv endpoints)
├── models.py                       # Pydantic models: Observation, Action, Reward
├── openenv.yaml                    # OpenEnv metadata + task registry
├── requirements.txt
├── Dockerfile
├── environments/
│   ├── email_triage/env.py
│   ├── code_review/env.py
│   ├── data_cleaning/env.py
│   └── content_moderation/env.py
├── baseline/
│   └── run_baseline.py             # OpenAI-based baseline inference
└── tests/
    └── test_envs.py
```

---

## 🔌 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | Health check |
| POST | `/reset` | Reset environment for a task |
| POST | `/step` | Submit an action and receive reward |
| GET | `/state` | Get current environment state |
| GET | `/tasks` | List all tasks + action schemas |
| POST | `/grader` | Score a complete action |
| POST | `/baseline` | Run baseline inference (requires OPENAI_API_KEY) |

---

## 📦 Action & Observation Spaces

### Observation (all agents)
```json
{
  "agent": "email_triage",
  "task_id": "email_triage_easy",
  "difficulty": "easy",
  "context": { ... },
  "instructions": "...",
  "step_count": 0
}
```

### Action (all agents)
```json
{
  "agent": "email_triage",
  "task_id": "email_triage_easy",
  "payload": { ... }
}
```

### Reward
```json
{
  "score": 0.83,
  "partial_credits": { "key": true/false },
  "feedback": "5/6 elements present.",
  "done": true
}
```

---

## 📋 Task Descriptions

### 📧 Email Triage
| Task ID | Difficulty | Description | Action Payload |
|---------|-----------|-------------|----------------|
| `email_triage_easy` | Easy | Classify email as spam/important/newsletter | `{"classification": "spam\|important\|newsletter"}` |
| `email_triage_medium` | Medium | Prioritize 10 emails by urgency | `{"order": ["m1","m5",...]}` |
| `email_triage_hard` | Hard | Draft reply to customer complaint | `{"reply": "<full reply text>"}` |

### 🔍 Code Review
| Task ID | Difficulty | Description | Action Payload |
|---------|-----------|-------------|----------------|
| `code_review_easy` | Easy | Detect syntax errors in Python | `{"errors": ["..."]}` |
| `code_review_medium` | Medium | Find logical bugs + suggest fixes | `{"bugs": [{location, issue, fix}]}` |
| `code_review_hard` | Hard | Identify SQL injection, XSS vulnerabilities | `{"vulnerabilities": [{type, location, fix}]}` |

### 🧹 Data Cleaning
| Task ID | Difficulty | Description | Action Payload |
|---------|-----------|-------------|----------------|
| `data_cleaning_easy` | Easy | Find missing values + duplicates | `{"missing": [...], "duplicates": [...]}` |
| `data_cleaning_medium` | Medium | Fix data types + normalize | `{"issues": {...}, "cleaned_data": [...]}` |
| `data_cleaning_hard` | Hard | Outlier detection + imputation | `{"outliers": [...], "missing": [...], "cleaned_data": [...]}` |

### 🛡️ Content Moderation
| Task ID | Difficulty | Description | Action Payload |
|---------|-----------|-------------|----------------|
| `content_moderation_easy` | Easy | Classify posts as safe/harmful | `{"classifications": [{id, label}]}` |
| `content_moderation_medium` | Medium | Detect subtle toxicity + sarcasm | `{"classifications": [{id, label, reason}]}` |
| `content_moderation_hard` | Hard | Context-aware moderation of ambiguous text | `{"decisions": [{id, context_a_label, context_b_label}]}` |

---

## 🚀 Setup & Usage

### Local Development
```bash
git clone <your-repo>
cd digital_yodha
pip install -r requirements.txt
python app.py
# Server starts at http://localhost:7860
```

### Docker
```bash
docker build -t digital-yodha .
docker run -p 7860:7860 -e OPENAI_API_KEY=sk-... digital-yodha
```

### Run Tests
```bash
pytest tests/test_envs.py -v
```

### Run Baseline Inference
```bash
export OPENAI_API_KEY=sk-...
python baseline/run_baseline.py
```

---

## 📊 Baseline Scores (GPT-4o-mini)

| Task | Score |
|------|-------|
| email_triage_easy | 1.00 |
| email_triage_medium | 0.75 |
| email_triage_hard | 0.67 |
| code_review_easy | 1.00 |
| code_review_medium | 0.67 |
| code_review_hard | 0.67 |
| data_cleaning_easy | 1.00 |
| data_cleaning_medium | 0.80 |
| data_cleaning_hard | 0.67 |
| content_moderation_easy | 1.00 |
| content_moderation_medium | 0.67 |
| content_moderation_hard | 0.50 |
| **Average** | **0.78** |

---

## 🏆 Why Digital Yodha?

- ✅ **4 real-world domains** in one unified environment
- ✅ **12 tasks** with clear difficulty progression
- ✅ **Deterministic graders** with partial credit scoring
- ✅ **Meaningful reward shaping** — not just binary pass/fail
- ✅ **Full OpenEnv spec compliance** — typed models, all endpoints
- ✅ **Docker + HF Spaces ready**

---

## 👥 Team

**Digital Yodha** — Built for the OpenEnv Hackathon 2025
- Sangisetti Akarsh
- Sarika Jivrajika
