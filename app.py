import os
import sys
sys.path.insert(0, os.path.dirname(__file__))

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import Any, Dict, List
import uvicorn

from models import Action, Observation, Reward, StepResult, TaskInfo, BaselineScore
from environments.email_triage.env import EmailTriageEnv
from environments.code_review.env import CodeReviewEnv
from environments.data_cleaning.env import DataCleaningEnv
from environments.content_moderation.env import ContentModerationEnv

app = FastAPI(
    title="Digital Yodha — OpenEnv",
    description="Multi-domain AI agent environment: Email Triage, Code Review, Data Cleaning, Content Moderation",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Environment registry
ENVS = {
    "email_triage": EmailTriageEnv(),
    "code_review": CodeReviewEnv(),
    "data_cleaning": DataCleaningEnv(),
    "content_moderation": ContentModerationEnv(),
}

TASK_REGISTRY: List[Dict] = [
    {"id": "email_triage_easy",        "name": "Email Classification",       "difficulty": "easy",   "agent": "email_triage",       "description": "Classify a single email as spam, important, or newsletter", "action_schema": {"classification": "str: 'spam' | 'important' | 'newsletter'"}},
    {"id": "email_triage_medium",      "name": "Email Prioritization",       "difficulty": "medium", "agent": "email_triage",       "description": "Prioritize 10 emails by urgency", "action_schema": {"order": "list[str]: email ids sorted by priority"}},
    {"id": "email_triage_hard",        "name": "Email Reply Drafting",       "difficulty": "hard",   "agent": "email_triage",       "description": "Draft a professional reply to a complex customer complaint", "action_schema": {"reply": "str: full email reply text"}},
    {"id": "code_review_easy",         "name": "Syntax Error Detection",     "difficulty": "easy",   "agent": "code_review",        "description": "Detect syntax errors in a Python function", "action_schema": {"errors": "list[str]: descriptions of syntax errors"}},
    {"id": "code_review_medium",       "name": "Logic Bug Detection",        "difficulty": "medium", "agent": "code_review",        "description": "Find logical bugs and suggest fixes", "action_schema": {"bugs": "list[{location, issue, fix}]"}},
    {"id": "code_review_hard",         "name": "Security Vulnerability Detection", "difficulty": "hard", "agent": "code_review", "description": "Spot security vulnerabilities like SQL injection", "action_schema": {"vulnerabilities": "list[{type, location, fix}]"}},
    {"id": "data_cleaning_easy",       "name": "Missing Value Detection",    "difficulty": "easy",   "agent": "data_cleaning",      "description": "Find missing values and duplicate rows", "action_schema": {"missing": "list[str]", "duplicates": "list[int]"}},
    {"id": "data_cleaning_medium",     "name": "Data Type Normalization",    "difficulty": "medium", "agent": "data_cleaning",      "description": "Fix data types and normalize columns", "action_schema": {"issues": "dict[str,str]", "cleaned_data": "list[dict]"}},
    {"id": "data_cleaning_hard",       "name": "Outlier Detection & Imputation", "difficulty": "hard", "agent": "data_cleaning",   "description": "Detect outliers, impute values, produce clean dataset", "action_schema": {"outliers": "list[int]", "missing": "list[int]", "cleaned_data": "list[dict]"}},
    {"id": "content_moderation_easy",  "name": "Explicit Content Detection","difficulty": "easy",   "agent": "content_moderation", "description": "Detect explicit hate speech or offensive content", "action_schema": {"classifications": "list[{id, label}]"}},
    {"id": "content_moderation_medium","name": "Subtle Toxicity Detection",  "difficulty": "medium", "agent": "content_moderation", "description": "Detect subtle toxicity and sarcasm-based insults", "action_schema": {"classifications": "list[{id, label, reason}]"}},
    {"id": "content_moderation_hard",  "name": "Context-Aware Moderation",  "difficulty": "hard",   "agent": "content_moderation", "description": "Context-aware moderation of ambiguous content", "action_schema": {"decisions": "list[{id, context_a_label, context_b_label}]"}},
]

def get_env(task_id: str):
    for agent_key in ENVS:
        if task_id.startswith(agent_key):
            return ENVS[agent_key]
    raise HTTPException(status_code=404, detail=f"No environment found for task_id: {task_id}")


@app.get("/")
def root():
    return {"name": "Digital Yodha OpenEnv", "version": "1.0.0", "status": "running", "tasks": len(TASK_REGISTRY)}


@app.post("/reset")
def reset(body: Dict[str, str]):
    task_id = body.get("task_id")
    if not task_id:
        raise HTTPException(status_code=400, detail="task_id required")
    env = get_env(task_id)
    obs = env.reset(task_id)
    return obs.dict()


@app.post("/step")
def step(action: Action):
    env = get_env(action.task_id)
    result = env.step(action)
    return result.dict()


@app.get("/state")
def state(task_id: str):
    env = get_env(task_id)
    return env.state()


@app.get("/tasks")
def tasks():
    return {"tasks": TASK_REGISTRY}


@app.post("/grader")
def grader(action: Action):
    env = get_env(action.task_id)
    env.reset(action.task_id)
    result = env.step(action)
    return {"task_id": action.task_id, "score": result.reward.score, "feedback": result.reward.feedback, "partial_credits": result.reward.partial_credits}


@app.post("/baseline")
def baseline():
    """Run baseline inference using OpenAI API and return scores for all tasks."""
    try:
        from baseline.run_baseline import run_all_baselines
        scores = run_all_baselines()
        return {"baseline_scores": scores}
    except Exception as e:
        return {"error": str(e), "message": "Set OPENAI_API_KEY env variable and ensure openai package is installed."}


if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=7860, reload=False)
