"""
inference.py — Meta OpenEnv Hackathon Submission v2.1
Handles multi-step retry episodes and cross-agent chained task.
"""

import os
import sys
import json
import re
import time

# ── Load .env ─────────────────────────────────────────────────────────────────
_env_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
if os.path.exists(_env_file):
    with open(_env_file) as _f:
        for _line in _f:
            _line = _line.strip()
            if _line and not _line.startswith("#") and "=" in _line:
                _k, _, _v = _line.partition("=")
                os.environ.setdefault(_k.strip(), _v.strip())

# ── Mandatory env vars ────────────────────────────────────────────────────────
API_BASE_URL = os.environ.get("API_BASE_URL", "https://router.huggingface.co/v1")
MODEL_NAME   = os.environ.get("MODEL_NAME",   "Qwen/Qwen2.5-72B-Instruct")
HF_TOKEN     = os.environ.get("HF_TOKEN",     "")

TASK_IDS = [
    "email_triage_easy", "email_triage_medium", "email_triage_hard",
    "code_review_easy", "code_review_medium", "code_review_hard",
    "data_cleaning_easy", "data_cleaning_medium", "data_cleaning_hard",
    "content_moderation_easy", "content_moderation_medium", "content_moderation_hard",
    "cross_agent_chain",
]

SYSTEM_PROMPT = (
    "You are an expert AI agent completing structured real-world tasks.\n"
    "You MUST respond with ONLY a valid JSON object as the payload.\n"
    "Rules:\n"
    "1. Start your response with { and end with }\n"
    "2. No markdown, no code fences (no ```), no explanation text\n"
    "3. No preamble — just the JSON object\n"
    "4. The JSON must be valid and parseable"
)

# ── Helpers ───────────────────────────────────────────────────────────────────

def progress_bar(current, total, width=40):
    filled = int(width * current / total)
    return f"[{'█'*filled}{'░'*(width-filled)}] {int(100*current/total):3d}%  ({current}/{total})"

def score_bar(score, width=10):
    filled = int(width * score)
    return "█" * filled + "░" * (width - filled)

def extract_json(text):
    """Robustly extract a JSON object from model output."""
    if not text:
        return {}
    text = text.strip()

    # Strategy 1: direct parse
    try:
        r = json.loads(text)
        if isinstance(r, dict):
            return r
    except Exception:
        pass

    # Strategy 2: strip markdown fences
    cleaned = re.sub(r"^```(?:json)?\s*\n?", "", text, flags=re.IGNORECASE)
    cleaned = re.sub(r"\n?```\s*$", "", cleaned, flags=re.MULTILINE).strip()
    try:
        r = json.loads(cleaned)
        if isinstance(r, dict):
            return r
    except Exception:
        pass

    # Strategy 3: brace-depth walking (handles nested objects reliably)
    start = text.find("{")
    if start != -1:
        depth = 0
        for i, ch in enumerate(text[start:], start):
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    candidate = text[start:i+1]
                    try:
                        r = json.loads(candidate)
                        if isinstance(r, dict):
                            return r
                    except Exception:
                        pass
                    break

    return {}


def unwrap_payload(payload):
    """If model returned the full action envelope, extract the inner payload."""
    if payload and "payload" in payload and isinstance(payload["payload"], dict):
        return payload["payload"]
    return payload


def call_model(client, task_id, difficulty, instructions, agent_ctx, feedback=None):
    """Call model. If feedback is provided, this is a retry attempt."""
    retry_note = ""
    if feedback:
        retry_note = (
            f"\nPREVIOUS ATTEMPT FEEDBACK: {feedback}\n"
            "Fix the issues described above in your new response.\n"
        )

    user_prompt = (
        f"Task: {task_id}\n"
        f"Difficulty: {difficulty}\n\n"
        f"Instructions:\n{instructions}\n"
        f"{retry_note}\n"
        f"Data to work with:\n{json.dumps(agent_ctx, indent=2)}\n\n"
        "Respond with ONLY the payload JSON object. Start with { and end with }."
    )

    try:
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user",   "content": user_prompt},
            ],
            temperature=0.0,
            max_tokens=2000,
        )
        raw     = response.choices[0].message.content or ""
        payload = unwrap_payload(extract_json(raw))

        if not payload:
            print(f"\n    [DEBUG] Empty JSON. Raw: {repr(raw[:200])}")
        else:
            print(f"\n    [DEBUG] Attempt payload keys: {list(payload.keys())}")

        return payload
    except Exception as e:
        print(f"\n    [ERROR] API call failed: {e}")
        return {}


# ── Single task (handles multi-step retry) ────────────────────────────────────

def run_task(client, task_id, INSTRUCTIONS):
    from server.Meta_environment import MetaEnvironment
    from models import MetaAction

    agent = "_".join(task_id.split("_")[:-1]) if task_id != "cross_agent_chain" else "cross_agent"

    # Load context
    env = MetaEnvironment()
    env.reset()
    try:
        agent_ctx, grader_ctx, difficulty = env._load_context(task_id)
    except Exception as e:
        return {"task_id": task_id, "agent": agent, "difficulty": "unknown",
                "score": 0.0, "feedback": f"Context load failed: {e}",
                "partial_credits": {}, "reward": 0.0}

    instructions = INSTRUCTIONS.get(task_id, "")

    # Set up grading environment with fixed context
    env2 = MetaEnvironment()
    env2.reset()
    env2._current_agent_context  = agent_ctx
    env2._current_grader_context = grader_ctx
    env2._current_task_id        = task_id

    # Attempt 1
    payload  = call_model(client, task_id, difficulty, instructions, agent_ctx)
    action   = MetaAction(message=json.dumps({"agent": agent, "task_id": task_id, "payload": payload}))
    obs      = env2.step(action)

    # Attempt 2 if retry available (done=False means retry is offered)
    if not obs.done and obs.score < 1.0:
        print(f"\n    [RETRY] Score {obs.score:.2f} — attempting retry with feedback...")
        time.sleep(1)
        payload2 = call_model(client, task_id, difficulty, instructions, agent_ctx, feedback=obs.feedback)
        action2  = MetaAction(message=json.dumps({"agent": agent, "task_id": task_id, "payload": payload2}))
        obs      = env2.step(action2)

    return {
        "task_id":         task_id,
        "agent":           agent,
        "difficulty":      obs.difficulty,
        "score":           obs.score,
        "feedback":        obs.feedback,
        "partial_credits": obs.partial_credits,
        "reward":          obs.reward,
    }


# ── Main ──────────────────────────────────────────────────────────────────────

def run_all(api_base_url, model_name, hf_token):
    if not hf_token or hf_token == "YOUR_HF_TOKEN_HERE":
        print("ERROR: HF_TOKEN is not set.")
        sys.exit(1)

    try:
        from openai import OpenAI
    except ImportError:
        print("ERROR: pip install openai")
        sys.exit(1)

    try:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from server.Meta_environment import INSTRUCTIONS
    except ImportError as e:
        print(f"ERROR: {e}")
        sys.exit(1)

    client  = OpenAI(api_key=hf_token, base_url=api_base_url)
    results = []

    print()
    print("╔══════════════════════════════════════════════════════════════════╗")
    print("║        Meta OpenEnv — Inference Runner (OpenEnv Hackathon 2026) ║")
    print("╠══════════════════════════════════════════════════════════════════╣")
    print(f"║  API Base : {api_base_url:<53}║")
    print(f"║  Model    : {model_name:<53}║")
    print(f"║  Tasks    : {len(TASK_IDS):<53}║")
    print("╚══════════════════════════════════════════════════════════════════╝")
    print()

    start = time.time()

    for i, task_id in enumerate(TASK_IDS):
        print(f"  {progress_bar(i, len(TASK_IDS))}  {task_id}")
        sys.stdout.flush()

        t0      = time.time()
        result  = run_task(client, task_id, INSTRUCTIONS)
        elapsed = time.time() - t0
        results.append(result)

        diff = result["difficulty"].upper()[:4]
        bar  = score_bar(result["score"])
        print(f"  ✓ [{diff:4s}] {task_id:<35} [{bar}] {result['score']:.2f}  ({elapsed:.1f}s)  {result['feedback'][:55]}")
        sys.stdout.flush()
        time.sleep(1)

    total_time = time.time() - start
    avg_score  = sum(r["score"] for r in results) / len(results)

    print()
    print(f"  {progress_bar(len(TASK_IDS), len(TASK_IDS))}")
    print()
    print("╔══════════════════════════════════════════════════════════════════╗")
    print(f"║  📊 Average Score : {avg_score:.4f}{'':37}║")
    print(f"║  ⏱  Total Time    : {total_time:.1f}s{'':39}║")
    print(f"║  ✅ Tasks Passed  : {sum(1 for r in results if r['score'] >= 0.5)}/{len(results)}{'':42}║")
    print("╚══════════════════════════════════════════════════════════════════╝")
    print()

    agents = ["email_triage", "code_review", "data_cleaning", "content_moderation", "cross_agent"]
    print("  Per-Agent Summary:")
    for ag in agents:
        ag_r   = [r for r in results if r["agent"] == ag]
        ag_avg = sum(r["score"] for r in ag_r) / len(ag_r) if ag_r else 0
        print(f"    {ag:<30} [{score_bar(ag_avg)}] {ag_avg:.2f}")
    print()
    return results


if __name__ == "__main__":
    results = run_all(API_BASE_URL, MODEL_NAME, HF_TOKEN)
    print("Full Results JSON:")
    print(json.dumps(results, indent=2))