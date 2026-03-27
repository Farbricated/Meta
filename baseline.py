"""
Meta — Baseline Inference Script
Runs OpenAI model against all 12 tasks and reports scores.

Usage:
    export OPENAI_API_KEY=sk-...
    python baseline.py
"""

import os
import sys
import json
import re

sys.path.insert(0, os.path.dirname(__file__))

TASK_IDS = [
    "email_triage_easy", "email_triage_medium", "email_triage_hard",
    "code_review_easy", "code_review_medium", "code_review_hard",
    "data_cleaning_easy", "data_cleaning_medium", "data_cleaning_hard",
    "content_moderation_easy", "content_moderation_medium", "content_moderation_hard",
]

SYSTEM_PROMPT = (
    "You are an AI agent completing structured real-world tasks. "
    "You will receive a task context and instructions. "
    "Respond ONLY with a valid JSON object as the action payload — no explanation, no markdown."
)


def extract_json(text: str) -> dict:
    try:
        return json.loads(text)
    except Exception:
        pass
    match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except Exception:
            pass
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except Exception:
            pass
    return {}


def run_task(client, task_id: str) -> dict:
    from server.Meta_environment import MetaEnvironment
    from models import MetaAction

    env = MetaEnvironment()
    env.reset()

    # Load context by doing a dummy step first
    agent = "_".join(task_id.split("_")[:-1])
    dummy = MetaAction(agent=agent, task_id=task_id, payload={})
    obs = env.step(dummy)

    user_prompt = f"""Task ID: {task_id}
Difficulty: {obs.difficulty}
Instructions: {obs.instructions}

Context:
{json.dumps(obs.context, indent=2)}

Respond with a JSON payload object only."""

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
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

    # Grade the real action
    env2 = MetaEnvironment()
    env2.reset()
    action = MetaAction(agent=agent, task_id=task_id, payload=payload)
    result = env2.step(action)

    return {
        "task_id": task_id,
        "agent": agent,
        "score": result.score,
        "feedback": result.feedback,
        "reward": result.reward,
    }


def run_all_baselines(api_key: str = None) -> list:
    from openai import OpenAI

    api_key = api_key or os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise EnvironmentError("OPENAI_API_KEY not set.")

    client = OpenAI(api_key=api_key)
    results = []

    print("\n🚀 Meta — Baseline Inference\n" + "=" * 50)
    for task_id in TASK_IDS:
        print(f"  Running: {task_id}...", end=" ", flush=True)
        result = run_task(client, task_id)
        results.append(result)
        print(f"Score: {result['score']:.2f} — {result['feedback']}")

    avg = sum(r["score"] for r in results) / len(results)
    print(f"\n{'='*50}\nAverage Score: {avg:.3f} / {len(results)} tasks\n{'='*50}")
    return results


if __name__ == "__main__":
    scores = run_all_baselines()
    print(json.dumps(scores, indent=2))
