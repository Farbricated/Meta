"""
Meta v2 — Baseline Inference Script
Runs GPT-4o-mini against all 12 tasks and reports scores.

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
    "You are an expert AI agent completing structured real-world tasks.\n"
    "You will receive task context and instructions.\n"
    "Respond ONLY with a valid JSON object as the action payload — no explanation, no markdown, no code fences.\n"
    "Your response must be a single raw JSON object."
)


def extract_json(text: str) -> dict:
    """Robustly extract JSON from model response."""
    text = text.strip()
    try:
        return json.loads(text)
    except Exception:
        pass
    # Strip markdown fences
    match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except Exception:
            pass
    # Find first { ... }
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except Exception:
            pass
    return {}


def run_task(client, task_id: str) -> dict:
    from server.Meta_environment import MetaEnvironment, INSTRUCTIONS
    from models import MetaAction

    # Load context via a probe step
    env = MetaEnvironment()
    env.reset()
    probe_msg = json.dumps({"agent": "_".join(task_id.split("_")[:-1]), "task_id": task_id, "payload": {"_probe": True}})
    probe_obs = env.step(MetaAction(message=probe_msg))

    instructions = INSTRUCTIONS.get(task_id, probe_obs.instructions)
    context = probe_obs.context

    user_prompt = (
        f"Task ID: {task_id}\n"
        f"Difficulty: {probe_obs.difficulty}\n\n"
        f"Instructions:\n{instructions}\n\n"
        f"Context:\n{json.dumps(context, indent=2)}\n\n"
        "Respond with ONLY the payload JSON object (the value of the 'payload' key)."
    )

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.0,
            max_tokens=2000,
        )
        raw = response.choices[0].message.content
        payload = extract_json(raw)
    except Exception as e:
        payload = {}
        raw = str(e)

    # Grade with real action
    agent = "_".join(task_id.split("_")[:-1])
    env2 = MetaEnvironment()
    env2.reset()
    # Re-set context
    env2._current_context = context
    env2._current_task_id = task_id

    action_msg = json.dumps({"agent": agent, "task_id": task_id, "payload": payload})
    result_obs = env2.step(MetaAction(message=action_msg))

    return {
        "task_id": task_id,
        "agent": agent,
        "difficulty": result_obs.difficulty,
        "score": result_obs.score,
        "feedback": result_obs.feedback,
        "partial_credits": result_obs.partial_credits,
        "reward": result_obs.reward,
    }


def run_all_baselines(api_key: str = None) -> list:
    from openai import OpenAI

    api_key = api_key or os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise EnvironmentError("OPENAI_API_KEY not set.")

    client = OpenAI(api_key=api_key)
    results = []

    print("\n🚀 Meta Multi-Agent v2 — Baseline Inference")
    print("=" * 60)
    for task_id in TASK_IDS:
        print(f"  ▶ {task_id:<35}", end=" ", flush=True)
        result = run_task(client, task_id)
        results.append(result)
        bar = "█" * int(result["score"] * 10) + "░" * (10 - int(result["score"] * 10))
        print(f"[{bar}] {result['score']:.2f}  {result['feedback']}")

    avg = sum(r["score"] for r in results) / len(results)
    print("=" * 60)
    print(f"  📊 Average Score: {avg:.3f}  |  Tasks: {len(results)}")
    print("=" * 60)
    return results


if __name__ == "__main__":
    scores = run_all_baselines()
    print("\nFull JSON Results:")
    print(json.dumps(scores, indent=2))
