# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.

"""
FastAPI application for the Meta Multi-Agent Environment.

Endpoints:
    - POST /reset: Reset the environment
    - POST /step: Execute an action
    - GET /state: Get current environment state
    - GET /schema: Get action/observation schemas
    - GET /tasks: List all 12 tasks with action schemas
    - POST /grader: Score an action without side effects
    - POST /baseline: Run baseline inference (requires OPENAI_API_KEY)
    - WS /ws: WebSocket endpoint for persistent sessions
"""

try:
    from openenv.core.env_server.http_server import create_app
except Exception as e:
    raise ImportError(
        "openenv-core is required. Install with:\n    pip install openenv-core\n"
    ) from e

try:
    from ..models import MetaAction, MetaObservation
    from .Meta_environment import MetaEnvironment
except ModuleNotFoundError:
    from models import MetaAction, MetaObservation
    from server.Meta_environment import MetaEnvironment

import os
import json
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

# Create the base OpenEnv app
app = create_app(
    MetaEnvironment,
    MetaAction,
    MetaObservation,
    env_name="Meta",
    max_concurrent_envs=10,
)

# ─── Task Registry ────────────────────────────────────────────────────────────

TASK_REGISTRY = [
    {"id": "email_triage_easy",        "name": "Email Classification",         "difficulty": "easy",   "agent": "email_triage",        "description": "Classify a single email as spam, important, or newsletter",        "action_schema": {"agent": "email_triage", "task_id": "email_triage_easy",        "payload": {"classification": "str: 'spam' | 'important' | 'newsletter'"}}},
    {"id": "email_triage_medium",      "name": "Email Prioritization",         "difficulty": "medium", "agent": "email_triage",        "description": "Prioritize 10 emails by urgency",                                  "action_schema": {"agent": "email_triage", "task_id": "email_triage_medium",      "payload": {"order": "list[str]: email ids sorted by priority"}}},
    {"id": "email_triage_hard",        "name": "Email Reply Drafting",         "difficulty": "hard",   "agent": "email_triage",        "description": "Draft a professional reply to a complex customer complaint",       "action_schema": {"agent": "email_triage", "task_id": "email_triage_hard",        "payload": {"reply": "str: full email reply"}}},
    {"id": "code_review_easy",         "name": "Syntax Error Detection",       "difficulty": "easy",   "agent": "code_review",         "description": "Detect syntax errors in a Python function",                        "action_schema": {"agent": "code_review",  "task_id": "code_review_easy",         "payload": {"errors": "list[str]"}}},
    {"id": "code_review_medium",       "name": "Logic Bug Detection",          "difficulty": "medium", "agent": "code_review",         "description": "Find logical bugs and suggest fixes",                              "action_schema": {"agent": "code_review",  "task_id": "code_review_medium",       "payload": {"bugs": "list[{location, issue, fix}]"}}},
    {"id": "code_review_hard",         "name": "Security Vulnerability Detection", "difficulty": "hard", "agent": "code_review",      "description": "Spot SQL injection, XSS, and other security vulnerabilities",      "action_schema": {"agent": "code_review",  "task_id": "code_review_hard",         "payload": {"vulnerabilities": "list[{type, location, fix}]"}}},
    {"id": "data_cleaning_easy",       "name": "Missing Value Detection",      "difficulty": "easy",   "agent": "data_cleaning",       "description": "Find missing values and duplicate rows in a dataset",             "action_schema": {"agent": "data_cleaning","task_id": "data_cleaning_easy",       "payload": {"missing": "list[str]", "duplicates": "list[int]"}}},
    {"id": "data_cleaning_medium",     "name": "Data Type Normalization",      "difficulty": "medium", "agent": "data_cleaning",       "description": "Fix incorrect data types and normalize columns",                   "action_schema": {"agent": "data_cleaning","task_id": "data_cleaning_medium",     "payload": {"issues": "dict[str,str]", "cleaned_data": "list[dict]"}}},
    {"id": "data_cleaning_hard",       "name": "Outlier Detection & Imputation","difficulty": "hard",  "agent": "data_cleaning",       "description": "Detect outliers, impute missing values, produce clean dataset",   "action_schema": {"agent": "data_cleaning","task_id": "data_cleaning_hard",       "payload": {"outliers": "list[int]", "missing": "list[int]", "cleaned_data": "list[dict]"}}},
    {"id": "content_moderation_easy",  "name": "Explicit Content Detection",   "difficulty": "easy",   "agent": "content_moderation",  "description": "Classify posts as safe or harmful (explicit content)",            "action_schema": {"agent": "content_moderation","task_id": "content_moderation_easy",  "payload": {"classifications": "list[{id, label}]"}}},
    {"id": "content_moderation_medium","name": "Subtle Toxicity Detection",    "difficulty": "medium", "agent": "content_moderation",  "description": "Detect subtle toxicity and sarcasm-based insults",                "action_schema": {"agent": "content_moderation","task_id": "content_moderation_medium","payload": {"classifications": "list[{id, label, reason}]"}}},
    {"id": "content_moderation_hard",  "name": "Context-Aware Moderation",     "difficulty": "hard",   "agent": "content_moderation",  "description": "Same text, two contexts — determine correct label for each",     "action_schema": {"agent": "content_moderation","task_id": "content_moderation_hard",  "payload": {"decisions": "list[{id, context_a_label, context_b_label}]"}}},
]


@app.get("/tasks")
def list_tasks():
    """Return all 12 tasks with action schemas."""
    return {"tasks": TASK_REGISTRY, "total": len(TASK_REGISTRY)}


@app.post("/grader")
async def grader(request: Request):
    """Score an action for a task without persistent side effects."""
    body = await request.json()
    env = MetaEnvironment()
    env.reset()
    action = MetaAction(**body)
    obs = env.step(action)
    return {
        "task_id": action.task_id,
        "agent": action.agent,
        "score": obs.score,
        "feedback": obs.feedback,
        "reward": obs.reward,
    }


@app.post("/baseline")
async def baseline():
    """Run baseline inference using OpenAI API across all 12 tasks."""
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        return JSONResponse(
            status_code=400,
            content={"error": "OPENAI_API_KEY environment variable not set."}
        )
    try:
        from baseline import run_all_baselines
        scores = run_all_baselines(api_key)
        return {"baseline_scores": scores, "total_tasks": len(scores)}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


def main(host: str = "0.0.0.0", port: int = 8000):
    import uvicorn
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()
    main(port=args.port)
