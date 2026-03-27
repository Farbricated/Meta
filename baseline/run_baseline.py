"""
Digital Yodha — Baseline Inference Script
Runs an OpenAI model against all 12 tasks and reports scores.
Usage:
    export OPENAI_API_KEY=sk-...
    python baseline/run_baseline.py
"""

import os
import sys
import json
import re

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from openai import OpenAI
from environments.email_triage.env import EmailTriageEnv
from environments.code_review.env import CodeReviewEnv
from environments.data_cleaning.env import DataCleaningEnv
from environments.content_moderation.env import ContentModerationEnv
from models import Action

TASK_IDS = [
    "email_triage_easy", "email_triage_medium", "email_triage_hard",
    "code_review_easy", "code_review_medium", "code_review_hard",
    "data_cleaning_easy", "data_cleaning_medium", "data_cleaning_hard",
    "content_moderation_easy", "content_moderation_medium", "content_moderation_hard",
]

ENV_MAP = {
    "email_triage": EmailTriageEnv(),
    "code_review": CodeReviewEnv(),
    "data_cleaning": DataCleaningEnv(),
    "content_moderation": ContentModerationEnv(),
}


def get_env(task_id: str):
    for key in ENV_MAP:
        if task_id.startswith(key):
            return ENV_MAP[key]
    raise ValueError(f"No env for task: {task_id}")


def extract_json(text: str) -> dict:
    """Extract JSON from model response."""
    # Try direct parse
    try:
        return json.loads(text)
    except Exception:
        pass
    # Try extracting from code block
    match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except Exception:
            pass
    # Try finding first { ... }
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except Exception:
            pass
    return {}


def run_task(client: OpenAI, task_id: str) -> dict:
    env = get_env(task_id)
    agent_name = task_id.rsplit("_", 1)[0]  # e.g. email_triage

    obs = env.reset(task_id)

    system_prompt = (
        "You are an AI agent completing tasks in a structured environment. "
        "You will be given an observation and instructions. "
        "Respond ONLY with a valid JSON object matching the action payload schema described in the instructions. "
        "Do not include any explanation or markdown — just the raw JSON object."
    )

    user_prompt = f"""Task: {obs.task_id}
Difficulty: {obs.difficulty}
Instructions: {obs.instructions}

Context:
{json.dumps(obs.context, indent=2)}

Respond with a JSON object as the action payload."""

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.0,
            max_tokens=1500,
        )
        raw = response.choices[0].message.content
        payload = extract_json(raw)
    except Exception as e:
        payload = {}
        raw = str(e)

    action = Action(agent=agent_name, task_id=task_id, payload=payload)
    result = env.step(action)

    return {
        "task_id": task_id,
        "score": result.reward.score,
        "feedback": result.reward.feedback,
        "partial_credits": result.reward.partial_credits,
        "raw_response": raw[:300] if isinstance(raw, str) else "",
    }


def run_all_baselines() -> list:
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise EnvironmentError("OPENAI_API_KEY environment variable not set.")

    client = OpenAI(api_key=api_key)
    results = []

    print("\n🚀 Digital Yodha — Baseline Inference\n" + "=" * 50)
    for task_id in TASK_IDS:
        print(f"Running: {task_id}...", end=" ", flush=True)
        result = run_task(client, task_id)
        results.append(result)
        print(f"Score: {result['score']:.2f} — {result['feedback']}")

    total = sum(r["score"] for r in results)
    avg = total / len(results)
    print(f"\n{'='*50}")
    print(f"Average Score: {avg:.3f} across {len(results)} tasks")
    print("=" * 50)

    return results


if __name__ == "__main__":
    scores = run_all_baselines()
    print("\nFull Results:")
    print(json.dumps(scores, indent=2))
