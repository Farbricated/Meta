"""
FastAPI application for Meta Multi-Agent Environment v3.0

Standard OpenEnv endpoints (from create_app):
    POST /reset    — Reset environment
    POST /step     — Execute action
    GET  /state    — Current state
    GET  /schema   — Action/observation schemas
    GET  /health   — Health check
    GET  /metadata — Environment metadata
    WS   /ws       — WebSocket persistent session

Custom Meta endpoints:
    GET  /tasks    — All 19 tasks with payload schemas
    POST /grader   — Score an action without side effects
    POST /baseline — Run baseline across all tasks
    GET  /ui       — Gradio interactive frontend
    GET  /         — Redirects to /ui
"""

from __future__ import annotations

import json
import os
import sys

from fastapi import Request
from fastapi.responses import JSONResponse, RedirectResponse

from openenv.core.env_server.http_server import create_app

from models import MetaAction, MetaObservation
from server.Meta_environment import MetaEnvironment

# ── Create base OpenEnv app ───────────────────────────────────────────────────
app = create_app(
    MetaEnvironment,
    MetaAction,
    MetaObservation,
    env_name="Meta",
    max_concurrent_envs=20,
)

# ── Mount Gradio UI ───────────────────────────────────────────────────────────
try:
    from server.gradio_ui import mount_gradio
    mount_gradio(app)
except ImportError as e:
    print(f"[WARN] Gradio UI not mounted: {e}")


# ── Root redirect ─────────────────────────────────────────────────────────────
@app.get("/")
def root():
    return RedirectResponse(url="/ui")


# ── Task Registry ─────────────────────────────────────────────────────────────
TASK_REGISTRY = [
    # Email Triage
    {
        "id": "email_triage_easy",
        "name": "Email Classification",
        "agent": "email_triage",
        "difficulty": "easy",
        "description": "Classify a single email as spam, important, or newsletter.",
        "action_schema": {"message": json.dumps({"agent": "email_triage", "task_id": "email_triage_easy", "payload": {"classification": "spam | important | newsletter"}})},
    },
    {
        "id": "email_triage_medium",
        "name": "Email Prioritization",
        "agent": "email_triage",
        "difficulty": "medium",
        "description": "Prioritize 10 workplace emails from most to least urgent.",
        "action_schema": {"message": json.dumps({"agent": "email_triage", "task_id": "email_triage_medium", "payload": {"order": ["m1", "m5", "m3", "m10", "m6", "m8", "m2", "m9", "m4", "m7"]}})},
    },
    {
        "id": "email_triage_hard",
        "name": "Email Reply Drafting",
        "agent": "email_triage",
        "difficulty": "hard",
        "description": "Draft a professional, empathetic reply to a complex customer complaint.",
        "action_schema": {"message": json.dumps({"agent": "email_triage", "task_id": "email_triage_hard", "payload": {"reply": "<full reply text>"}})},
    },
    # Code Review
    {
        "id": "code_review_easy",
        "name": "Syntax Error Detection",
        "agent": "code_review",
        "difficulty": "easy",
        "description": "Find the syntax error(s) in a Python code snippet.",
        "action_schema": {"message": json.dumps({"agent": "code_review", "task_id": "code_review_easy", "payload": {"errors": ["description of syntax error"]}})},
    },
    {
        "id": "code_review_medium",
        "name": "Logic Bug Detection",
        "agent": "code_review",
        "difficulty": "medium",
        "description": "Find all 4 logical bugs in the code and suggest fixes.",
        "action_schema": {"message": json.dumps({"agent": "code_review", "task_id": "code_review_medium", "payload": {"bugs": [{"location": "fn_name", "issue": "...", "fix": "..."}]}})},
    },
    {
        "id": "code_review_hard",
        "name": "Security Vulnerability Detection (8 vulns)",
        "agent": "code_review",
        "difficulty": "hard",
        "description": "Identify all 8 security vulnerabilities: SQL injection (x2), XSS, command injection, insecure deserialization, timing attack, path traversal, SSRF.",
        "action_schema": {"message": json.dumps({"agent": "code_review", "task_id": "code_review_hard", "payload": {"vulnerabilities": [{"type": "sql_injection", "location": "fn_name", "severity": "critical", "fix": "..."}]}})},
    },
    # Data Cleaning
    {
        "id": "data_cleaning_easy",
        "name": "Missing Value & Duplicate Detection",
        "agent": "data_cleaning",
        "difficulty": "easy",
        "description": "Find all missing values (by field+row) and identify duplicate rows.",
        "action_schema": {"message": json.dumps({"agent": "data_cleaning", "task_id": "data_cleaning_easy", "payload": {"missing": ["age (row 2)"], "duplicates": [1, 3]}})},
    },
    {
        "id": "data_cleaning_medium",
        "name": "Data Type Normalization",
        "agent": "data_cleaning",
        "difficulty": "medium",
        "description": "Identify 5 data quality issues and return cleaned dataset.",
        "action_schema": {"message": json.dumps({"agent": "data_cleaning", "task_id": "data_cleaning_medium", "payload": {"issues": {"field_name": "description"}, "cleaned_data": []}})},
    },
    {
        "id": "data_cleaning_hard",
        "name": "Outlier Detection & Imputation",
        "agent": "data_cleaning",
        "difficulty": "hard",
        "description": "Detect outliers, find missing values, impute and return clean dataset.",
        "action_schema": {"message": json.dumps({"agent": "data_cleaning", "task_id": "data_cleaning_hard", "payload": {"outliers": [4, 8], "missing": [6, 11], "cleaned_data": []}})},
    },
    # Content Moderation
    {
        "id": "content_moderation_easy",
        "name": "Explicit Content Detection",
        "agent": "content_moderation",
        "difficulty": "easy",
        "description": "Classify 7 posts as safe or harmful.",
        "action_schema": {"message": json.dumps({"agent": "content_moderation", "task_id": "content_moderation_easy", "payload": {"classifications": [{"id": "c1", "label": "harmful"}]}})},
    },
    {
        "id": "content_moderation_medium",
        "name": "Subtle Toxicity Detection",
        "agent": "content_moderation",
        "difficulty": "medium",
        "description": "Detect subtle toxicity, sarcasm, and implicit hostility across 8 posts.",
        "action_schema": {"message": json.dumps({"agent": "content_moderation", "task_id": "content_moderation_medium", "payload": {"classifications": [{"id": "m1", "label": "harmful", "reason": "..."}]}})},
    },
    {
        "id": "content_moderation_hard",
        "name": "Context-Aware & Adversarial Moderation",
        "agent": "content_moderation",
        "difficulty": "hard",
        "description": "6 cases including dog-whistles and coordinated inauthentic behavior. Same text, two contexts.",
        "action_schema": {"message": json.dumps({"agent": "content_moderation", "task_id": "content_moderation_hard", "payload": {"decisions": [{"id": "h1", "context_a_label": "safe", "context_b_label": "harmful"}]}})},
    },
    # Ticket Triage (NEW)
    {
        "id": "ticket_triage_easy",
        "name": "Ticket Classification",
        "agent": "ticket_triage",
        "difficulty": "easy",
        "description": "Classify a support ticket by priority and category.",
        "action_schema": {"message": json.dumps({"agent": "ticket_triage", "task_id": "ticket_triage_easy", "payload": {"priority": "critical", "category": "bug"}})},
    },
    {
        "id": "ticket_triage_medium",
        "name": "Ticket Prioritization & Routing",
        "agent": "ticket_triage",
        "difficulty": "medium",
        "description": "Order 8 tickets by priority and assign each to the correct team.",
        "action_schema": {"message": json.dumps({"agent": "ticket_triage", "task_id": "ticket_triage_medium", "payload": {"order": ["tk1", "tk4", "..."], "assignments": {"tk1": "backend"}}})},
    },
    {
        "id": "ticket_triage_hard",
        "name": "Incident Root Cause Analysis",
        "agent": "ticket_triage",
        "difficulty": "hard",
        "description": "Analyse 6 linked incident tickets: root cause, resolution steps, affected services, P1-P4 severity.",
        "action_schema": {"message": json.dumps({"agent": "ticket_triage", "task_id": "ticket_triage_hard", "payload": {"root_cause": "...", "resolution_steps": ["..."], "affected_services": ["..."], "severity": "P1"}})},
    },
    # Cross-Agent Chained
    {
        "id": "cross_agent_chain",
        "name": "Email + Code Review Chain",
        "agent": "cross_agent",
        "difficulty": "hard",
        "description": "Classify the email AND identify the code bug in the attachment.",
        "action_schema": {"message": json.dumps({"agent": "cross_agent", "task_id": "cross_agent_chain", "payload": {"email_classification": "important", "bugs": [{"location": "fn", "issue": "...", "fix": "..."}]}})},
    },
    {
        "id": "cross_agent_email_data",
        "name": "Email Priority + Data Cleaning Chain",
        "agent": "cross_agent",
        "difficulty": "hard",
        "description": "Classify the email urgency AND identify+fix data quality issues in the attachment.",
        "action_schema": {"message": json.dumps({"agent": "cross_agent", "task_id": "cross_agent_email_data", "payload": {"email_priority": "critical", "data_issues": {"field": "issue"}, "cleaned_data": []}})},
    },
    {
        "id": "cross_agent_code_email",
        "name": "Vulnerability + Disclosure Email Chain",
        "agent": "cross_agent",
        "difficulty": "hard",
        "description": "Identify the security vulnerability AND draft a professional disclosure email.",
        "action_schema": {"message": json.dumps({"agent": "cross_agent", "task_id": "cross_agent_code_email", "payload": {"vulnerability_type": "sql_injection", "vulnerability_location": "fn_name", "disclosure_email": "..."}})},
    },
    {
        "id": "cross_agent_mod_escalation",
        "name": "Moderation + Escalation Chain",
        "agent": "cross_agent",
        "difficulty": "hard",
        "description": "Classify the content AND decide escalation AND draft a moderation notice.",
        "action_schema": {"message": json.dumps({"agent": "cross_agent", "task_id": "cross_agent_mod_escalation", "payload": {"content_label": "harmful", "escalate": True, "moderation_notice": "..."}})},
    },
]


@app.get("/tasks")
def list_tasks():
    return {
        "environment": "Meta Multi-Agent v3.0",
        "total_tasks": len(TASK_REGISTRY),
        "agents": ["email_triage", "code_review", "data_cleaning", "content_moderation", "ticket_triage", "cross_agent"],
        "how_to_step": (
            'POST /step with body: {"action": {"message": "<json_string>"}} '
            'where json_string = {"agent": "...", "task_id": "...", "payload": {...}}'
        ),
        "tasks": TASK_REGISTRY,
    }


@app.post("/grader")
async def grader(request: Request):
    """Score an action without persistent side effects."""
    body   = await request.json()
    msg    = body.get("message") or body.get("action", {}).get("message", "{}")
    env    = MetaEnvironment()
    env.reset()
    action = MetaAction(message=msg)
    obs    = env.step(action)
    return {
        "task_id":         obs.task_id,
        "agent":           obs.agent,
        "score":           obs.score,
        "reward":          obs.reward,
        "feedback":        obs.feedback,
        "partial_credits": obs.partial_credits,
        "difficulty":      obs.difficulty,
    }


@app.post("/baseline")
async def baseline():
    api_key = (
        os.environ.get("OPENAI_API_KEY")
        or os.environ.get("GROQ_API_KEY")
        or os.environ.get("HF_TOKEN")
    )
    if not api_key:
        return JSONResponse(
            status_code=400,
            content={"error": "Set one of: OPENAI_API_KEY, GROQ_API_KEY, or HF_TOKEN."},
        )
    api_base_url = os.environ.get("API_BASE_URL", "https://api.groq.com/openai/v1")
    model_name   = os.environ.get("MODEL_NAME",   "llama-3.3-70b-versatile")
    try:
        sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        from baseline import run_all_baselines
        scores = run_all_baselines(api_key=api_key, api_base_url=api_base_url, model_name=model_name)
        avg = round(sum(s["score"] for s in scores) / len(scores), 3)
        return {
            "environment":     "Meta Multi-Agent v3.0",
            "model":           model_name,
            "api_base":        api_base_url,
            "average_score":   avg,
            "total_tasks":     len(scores),
            "baseline_scores": scores,
        }
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


def main(host: str = "0.0.0.0", port: int = 7860) -> None:
    import uvicorn
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=7860)
    args = parser.parse_args()
    main(port=args.port)