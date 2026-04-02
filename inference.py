"""
inference.py — Meta OpenEnv Hackathon Submission
Runs inference against all 12 tasks of the Meta environment.

Usage:
    # Copy .env.example to .env and fill in your Groq key, then:
    python inference.py
"""

import os
import sys
import json
import re
import time

# ── Env vars (MANDATORY — checked by automated validators) ───────────────────
API_BASE_URL = os.environ.get("API_BASE_URL", "https://api.groq.com/openai/v1")
MODEL_NAME   = os.environ.get("MODEL_NAME",   "llama-3.3-70b-versatile")
HF_TOKEN     = os.environ.get("HF_TOKEN",     "")

TASK_IDS = [
    "email_triage_easy",
    "email_triage_medium",
    "email_triage_hard",
    "code_review_easy",
    "code_review_medium",
    "code_review_hard",
    "data_cleaning_easy",
    "data_cleaning_medium",
    "data_cleaning_hard",
    "content_moderation_easy",
    "content_moderation_medium",
    "content_moderation_hard",
]

SYSTEM_PROMPT = (
    "You are an expert AI agent completing structured real-world tasks.\n"
    "You will receive task context and instructions.\n"
    "Respond ONLY with a valid JSON object as the action payload — "
    "no explanation, no markdown, no code fences.\n"
    "Your response must be a single raw JSON object."
)

# ── Progress bar helpers ──────────────────────────────────────────────────────

def progress_bar(current: int, total: int, width: int = 40) -> str:
    filled = int(width * current / total)
    bar    = "█" * filled + "░" * (width - filled)
    pct    = int(100 * current / total)
    return f"[{bar}] {pct:3d}%  ({current}/{total})"


def score_bar(score: float, width: int = 10) -> str:
    filled = int(width * score)
    return "█" * filled + "░" * (width - filled)


# ── JSON extraction ───────────────────────────────────────────────────────────

def extract_json(text: str) -> dict:
    text = text.strip()
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


# ── Single-task inference ─────────────────────────────────────────────────────

def run_task(client, task_id: str, env, INSTRUCTIONS) -> dict:
    agent = "_".join(task_id.split("_")[:-1])

    # Probe to load context
    try:
        from models import MetaAction
        env.reset()
        probe_msg = json.dumps({
            "agent":   agent,
            "task_id": task_id,
            "payload": {"_probe": True},
        })
        probe_obs  = env.step(MetaAction(message=probe_msg))
        instructions = INSTRUCTIONS.get(task_id, probe_obs.instructions)
        context      = probe_obs.context
        difficulty   = probe_obs.difficulty
    except Exception as e:
        return {
            "task_id":        task_id,
            "agent":          agent,
            "difficulty":     "unknown",
            "score":          0.0,
            "feedback":       f"Probe failed: {e}",
            "partial_credits": {},
            "reward":         0.0,
            "error":          str(e),
        }

    user_prompt = (
        f"Task ID: {task_id}\n"
        f"Difficulty: {difficulty}\n\n"
        f"Instructions:\n{instructions}\n\n"
        f"Context:\n{json.dumps(context, indent=2)}\n\n"
        "Respond with ONLY the payload JSON object."
    )

    # Call model via Groq (OpenAI-compatible)
    payload = {}
    raw     = ""
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
        payload = extract_json(raw)
    except Exception as e:
        payload = {}
        raw     = str(e)

    # Grade
    try:
        from server.Meta_environment import MetaEnvironment
        from models import MetaAction

        env2 = MetaEnvironment()
        env2.reset()
        env2._current_agent_context  = context
        env2._current_grader_context = context
        env2._current_task_id        = task_id

        action_msg = json.dumps({
            "agent":   agent,
            "task_id": task_id,
            "payload": payload,
        })
        result_obs = env2.step(MetaAction(message=action_msg))
        score      = result_obs.score
        feedback   = result_obs.feedback
        partial    = result_obs.partial_credits
        reward     = result_obs.reward
        difficulty = result_obs.difficulty
    except Exception as e:
        score    = 0.0
        feedback = f"Grading error: {e}"
        partial  = {}
        reward   = 0.0

    return {
        "task_id":         task_id,
        "agent":           agent,
        "difficulty":      difficulty,
        "score":           score,
        "feedback":        feedback,
        "partial_credits": partial,
        "reward":          reward,
    }


# ── Main runner ───────────────────────────────────────────────────────────────

def run_all(api_base_url: str, model_name: str, hf_token: str) -> list:
    if not hf_token:
        print("❌ ERROR: HF_TOKEN is not set.")
        print("   Set it to your Groq API key (get one free at https://console.groq.com)")
        print("   export HF_TOKEN=gsk_...")
        sys.exit(1)

    try:
        from openai import OpenAI
    except ImportError:
        print("ERROR: openai package not installed. Run: pip install openai")
        sys.exit(1)

    # Groq is OpenAI-compatible — just point base_url at Groq
    client = OpenAI(
        api_key=hf_token,
        base_url=api_base_url,
    )

    # Local imports
    try:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from server.Meta_environment import MetaEnvironment, INSTRUCTIONS
    except ImportError as e:
        print(f"ERROR: Could not import Meta environment: {e}")
        print("Make sure you're running from the repo root: python inference.py")
        sys.exit(1)

    env     = MetaEnvironment()
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
        result  = run_task(client, task_id, env, INSTRUCTIONS)
        elapsed = time.time() - t0

        results.append(result)

        bar  = score_bar(result["score"])
        diff = result["difficulty"].upper()[:4]
        print(
            f"  ✓ [{diff:4s}] {task_id:<35} "
            f"[{bar}] {result['score']:.2f}  "
            f"({elapsed:.1f}s)  {result['feedback'][:60]}"
        )
        sys.stdout.flush()

        # Small delay to respect Groq rate limits (free tier: 30 req/min)
        time.sleep(2)

    total_time = time.time() - start
    avg_score  = sum(r["score"] for r in results) / len(results)

    print()
    print(f"  {progress_bar(len(TASK_IDS), len(TASK_IDS))}")
    print()
    print("╔══════════════════════════════════════════════════════════════════╗")
    print(f"║  📊 Average Score : {avg_score:.4f}                                    ║")
    print(f"║  ⏱  Total Time    : {total_time:.1f}s                                      ║")
    print(f"║  ✅ Tasks Passed  : {sum(1 for r in results if r['score'] >= 0.5)}/{len(results)}                                       ║")
    print("╚══════════════════════════════════════════════════════════════════╝")
    print()

    # Per-agent summary
    agents = ["email_triage", "code_review", "data_cleaning", "content_moderation"]
    print("  Per-Agent Summary:")
    for ag in agents:
        ag_results = [r for r in results if r["agent"] == ag]
        ag_avg     = sum(r["score"] for r in ag_results) / len(ag_results) if ag_results else 0
        ag_bar     = score_bar(ag_avg)
        print(f"    {ag:<30} [{ag_bar}] {ag_avg:.2f}")

    print()
    return results


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    # Load .env file if present
    env_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
    if os.path.exists(env_file):
        with open(env_file) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, _, val = line.partition("=")
                    os.environ.setdefault(key.strip(), val.strip())

    # Re-read after .env load
    API_BASE_URL = os.environ.get("API_BASE_URL", "https://api.groq.com/openai/v1")
    MODEL_NAME   = os.environ.get("MODEL_NAME",   "llama-3.3-70b-versatile")
    HF_TOKEN     = os.environ.get("HF_TOKEN",     "")

    results = run_all(API_BASE_URL, MODEL_NAME, HF_TOKEN)

    print("Full Results JSON:")
    print(json.dumps(results, indent=2))
