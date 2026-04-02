# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.

"""
FastAPI application for Meta Multi-Agent Environment v2.

Standard OpenEnv endpoints (from create_app):
    POST /reset    - Reset environment
    POST /step     - Execute action (action.message = JSON string)
    GET  /state    - Current state
    GET  /schema   - Action/observation schemas
    GET  /health   - Health check
    GET  /metadata - Environment metadata
    WS   /ws       - WebSocket persistent session

Custom Meta endpoints:
    GET  /tasks    - All 12 tasks with exact payload schemas
    POST /grader   - Score an action without side effects
    POST /baseline - Run Groq/OpenAI baseline across all 12 tasks
    GET  /ui       - Gradio interactive frontend
    GET  /         - Redirects to /ui
"""

import os
import sys
import json

try:
    from openenv.core.env_server.http_server import create_app
except Exception as e:
    raise ImportError("openenv-core required. Run: pip install openenv-core") from e

try:
    from models import MetaAction, MetaObservation
    from server.Meta_environment import MetaEnvironment
except ImportError:
    from ..models import MetaAction, MetaObservation
    from .Meta_environment import MetaEnvironment

from fastapi import Request
from fastapi.responses import JSONResponse, RedirectResponse

# ─── Create base OpenEnv app ──────────────────────────────────────────────────
app = create_app(
    MetaEnvironment,
    MetaAction,
    MetaObservation,
    env_name="Meta",
    max_concurrent_envs=20,
)

# ─── Mount Gradio UI at /ui ───────────────────────────────────────────────────
try:
    from server.gradio_ui import mount_gradio
    mount_gradio(app)
except ImportError:
    try:
        from .gradio_ui import mount_gradio
        mount_gradio(app)
    except ImportError as e:
        print(f"[WARN] Gradio UI not mounted: {e}. Install gradio: pip install gradio")

# ─── Root redirect ────────────────────────────────────────────────────────────
@app.get("/")
def root():
    """Redirect root to the Gradio UI."""
    return RedirectResponse(url="/ui")

# ─── Task Registry ────────────────────────────────────────────────────────────
TASK_REGISTRY = [
    {
        "id": "email_triage_easy",
        "name": "Email Classification",
        "agent": "email_triage",
        "difficulty": "easy",
        "description": "Classify a single email as spam, important, or newsletter.",
        "action_schema": {
            "message": json.dumps({
                "agent": "email_triage",
                "task_id": "email_triage_easy",
                "payload": {"classification": "spam | important | newsletter"}
            })
        }
    },
    {
        "id": "email_triage_medium",
        "name": "Email Prioritization",
        "agent": "email_triage",
        "difficulty": "medium",
        "description": "Prioritize 10 workplace emails from most to least urgent.",
        "action_schema": {
            "message": json.dumps({
                "agent": "email_triage",
                "task_id": "email_triage_medium",
                "payload": {"order": ["m1", "m5", "m3", "m10", "m6", "m8", "m2", "m9", "m4", "m7"]}
            })
        }
    },
    {
        "id": "email_triage_hard",
        "name": "Email Reply Drafting",
        "agent": "email_triage",
        "difficulty": "hard",
        "description": "Draft a professional, empathetic reply to a complex customer complaint.",
        "action_schema": {
            "message": json.dumps({
                "agent": "email_triage",
                "task_id": "email_triage_hard",
                "payload": {"reply": "<full reply text>"}
            })
        }
    },
    {
        "id": "code_review_easy",
        "name": "Syntax Error Detection",
        "agent": "code_review",
        "difficulty": "easy",
        "description": "Find the syntax error(s) in a Python code snippet.",
        "action_schema": {
            "message": json.dumps({
                "agent": "code_review",
                "task_id": "code_review_easy",
                "payload": {"errors": ["description of syntax error"]}
            })
        }
    },
    {
        "id": "code_review_medium",
        "name": "Logic Bug Detection",
        "agent": "code_review",
        "difficulty": "medium",
        "description": "Find all 4 logical bugs in the code and suggest fixes.",
        "action_schema": {
            "message": json.dumps({
                "agent": "code_review",
                "task_id": "code_review_medium",
                "payload": {"bugs": [{"location": "function_name", "issue": "description", "fix": "suggested fix"}]}
            })
        }
    },
    {
        "id": "code_review_hard",
        "name": "Security Vulnerability Detection",
        "agent": "code_review",
        "difficulty": "hard",
        "description": "Identify all 5 security vulnerabilities.",
        "action_schema": {
            "message": json.dumps({
                "agent": "code_review",
                "task_id": "code_review_hard",
                "payload": {"vulnerabilities": [{"type": "sql_injection", "location": "function_name", "fix": "use parameterized queries"}]}
            })
        }
    },
    {
        "id": "data_cleaning_easy",
        "name": "Missing Value & Duplicate Detection",
        "agent": "data_cleaning",
        "difficulty": "easy",
        "description": "Find all missing values (by field+row) and identify duplicate rows.",
        "action_schema": {
            "message": json.dumps({
                "agent": "data_cleaning",
                "task_id": "data_cleaning_easy",
                "payload": {"missing": ["age (row 2)", "name (row 4)"], "duplicates": [1, 3]}
            })
        }
    },
    {
        "id": "data_cleaning_medium",
        "name": "Data Type Normalization",
        "agent": "data_cleaning",
        "difficulty": "medium",
        "description": "Identify 5 data quality issues and return cleaned dataset.",
        "action_schema": {
            "message": json.dumps({
                "agent": "data_cleaning",
                "task_id": "data_cleaning_medium",
                "payload": {"issues": {"field_name": "description of issue"}, "cleaned_data": []}
            })
        }
    },
    {
        "id": "data_cleaning_hard",
        "name": "Outlier Detection & Imputation",
        "agent": "data_cleaning",
        "difficulty": "hard",
        "description": "Detect outliers, find missing values, impute and return clean dataset.",
        "action_schema": {
            "message": json.dumps({
                "agent": "data_cleaning",
                "task_id": "data_cleaning_hard",
                "payload": {"outliers": [4, 8], "missing": [6, 11], "cleaned_data": []}
            })
        }
    },
    {
        "id": "content_moderation_easy",
        "name": "Explicit Content Detection",
        "agent": "content_moderation",
        "difficulty": "easy",
        "description": "Classify 7 posts as safe or harmful.",
        "action_schema": {
            "message": json.dumps({
                "agent": "content_moderation",
                "task_id": "content_moderation_easy",
                "payload": {"classifications": [{"id": "c1", "label": "harmful"}]}
            })
        }
    },
    {
        "id": "content_moderation_medium",
        "name": "Subtle Toxicity Detection",
        "agent": "content_moderation",
        "difficulty": "medium",
        "description": "Detect subtle toxicity, sarcasm, and implicit hostility across 8 posts.",
        "action_schema": {
            "message": json.dumps({
                "agent": "content_moderation",
                "task_id": "content_moderation_medium",
                "payload": {"classifications": [{"id": "m1", "label": "harmful", "reason": "sarcastic insult"}]}
            })
        }
    },
    {
        "id": "content_moderation_hard",
        "name": "Context-Aware Moderation",
        "agent": "content_moderation",
        "difficulty": "hard",
        "description": "Same text, two different contexts — determine the correct label for each.",
        "action_schema": {
            "message": json.dumps({
                "agent": "content_moderation",
                "task_id": "content_moderation_hard",
                "payload": {"decisions": [{"id": "h1", "context_a_label": "safe", "context_b_label": "harmful"}]}
            })
        }
    },
]


@app.get("/tasks")
def list_tasks():
    """List all 12 tasks with descriptions and exact action payload schemas."""
    return {
        "environment": "Meta Multi-Agent v2",
        "total_tasks": len(TASK_REGISTRY),
        "agents": ["email_triage", "code_review", "data_cleaning", "content_moderation"],
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
    """
    Run baseline LLM across all 12 tasks.
    Reads API key from: OPENAI_API_KEY → GROQ_API_KEY → HF_TOKEN (in that order).
    Reads base URL from: API_BASE_URL (default: https://api.groq.com/openai/v1)
    Reads model from:    MODEL_NAME   (default: llama-3.3-70b-versatile)
    """
    # Accept any of the three key env vars
    api_key = (
        os.environ.get("OPENAI_API_KEY")
        or os.environ.get("GROQ_API_KEY")
        or os.environ.get("HF_TOKEN")
    )
    if not api_key:
        return JSONResponse(
            status_code=400,
            content={
                "error": (
                    "No API key found. Set one of: "
                    "OPENAI_API_KEY, GROQ_API_KEY, or HF_TOKEN. "
                    "Get a free Groq key at https://console.groq.com"
                )
            }
        )

    api_base_url = os.environ.get("API_BASE_URL", "https://api.groq.com/openai/v1")
    model_name   = os.environ.get("MODEL_NAME",   "llama-3.3-70b-versatile")

    try:
        sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        from baseline import run_all_baselines
        scores = run_all_baselines(
            api_key=api_key,
            api_base_url=api_base_url,
            model_name=model_name,
        )
        avg = round(sum(s["score"] for s in scores) / len(scores), 3)
        return {
            "environment":     "Meta Multi-Agent v2",
            "model":           model_name,
            "api_base":        api_base_url,
            "average_score":   avg,
            "total_tasks":     len(scores),
            "baseline_scores": scores,
        }
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


def main(host: str = "0.0.0.0", port: int = 7860):
    import uvicorn
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=7860)
    args = parser.parse_args()
    main(port=args.port)
