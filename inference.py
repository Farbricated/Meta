"""
inference.py — Meta OpenEnv Hackathon Submission v3.2
24 tasks: 5 domains × 4 (easy/medium/hard/expert) + 4 cross-agent chained tasks.

Provider priority (auto-detected from env vars):
  1. GROQ_API_KEY  → https://api.groq.com/openai/v1  (llama-3.3-70b-versatile) [FREE]
  2. HF_TOKEN      → API_BASE_URL                     (Qwen/Qwen2.5-72B-Instruct)
  3. OPENAI_API_KEY → https://api.openai.com/v1       (gpt-4o-mini)

Logging format:
  [START] task=<task_id> env=meta model=<model>
  [STEP]  step=<n> action=<action_str> reward=<0.00> done=<true|false> error=<msg|null>
  [END]   success=<true|false> steps=<n> score=<0.00> rewards=<r1,r2,...>

v3.2: handles both TPM (per-minute) and TPD (per-day) Groq rate limits correctly.
      TPM → short backoff and retry.
      TPD → wait for the exact reset time reported in the error, then retry.
"""

from __future__ import annotations

import json
import os
import re
import sys
import time
from typing import Optional

# ── Load .env ─────────────────────────────────────────────────────────────────
_env_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
if os.path.exists(_env_file):
    with open(_env_file, encoding="utf-8", errors="ignore") as _f:
        for _line in _f:
            _line = _line.strip()
            if _line and not _line.startswith("#") and "=" in _line:
                _k, _, _v = _line.partition("=")
                os.environ.setdefault(_k.strip(), _v.strip())

# ── Provider resolution ───────────────────────────────────────────────────────
_groq_key   = os.environ.get("GROQ_API_KEY", "")
_hf_token   = os.environ.get("HF_TOKEN", "")
_openai_key = os.environ.get("OPENAI_API_KEY", "")
_api_base   = os.environ.get("API_BASE_URL", "")
_model_name = os.environ.get("MODEL_NAME", "")

if _groq_key:
    API_BASE_URL = "https://api.groq.com/openai/v1"
    MODEL_NAME   = _model_name or "llama-3.3-70b-versatile"
    API_KEY      = _groq_key
    PROVIDER     = "groq"
elif _hf_token:
    API_BASE_URL = _api_base or "https://router.huggingface.co/v1"
    MODEL_NAME   = _model_name or "Qwen/Qwen2.5-72B-Instruct"
    API_KEY      = _hf_token
    PROVIDER     = "huggingface"
elif _openai_key:
    API_BASE_URL = "https://api.openai.com/v1"
    MODEL_NAME   = _model_name or "gpt-4o-mini"
    API_KEY      = _openai_key
    PROVIDER     = "openai"
else:
    API_BASE_URL = _api_base or "https://router.huggingface.co/v1"
    MODEL_NAME   = _model_name or "Qwen/Qwen2.5-72B-Instruct"
    API_KEY      = ""
    PROVIDER     = "none"

HF_TOKEN = API_KEY

TASK_IDS = [
    "email_triage_easy",        "email_triage_medium",        "email_triage_hard",         "email_triage_expert",
    "code_review_easy",         "code_review_medium",         "code_review_hard",          "code_review_expert",
    "data_cleaning_easy",       "data_cleaning_medium",       "data_cleaning_hard",        "data_cleaning_expert",
    "content_moderation_easy",  "content_moderation_medium",  "content_moderation_hard",   "content_moderation_expert",
    "ticket_triage_easy",       "ticket_triage_medium",       "ticket_triage_hard",        "ticket_triage_expert",
    "cross_agent_chain",        "cross_agent_email_data",     "cross_agent_code_email",    "cross_agent_mod_escalation",
]

SYSTEM_PROMPT = (
    "You are an expert AI agent completing structured real-world tasks.\n"
    "You MUST respond with ONLY a valid JSON object as the payload.\n"
    "Rules:\n"
    "1. Start your response with { and end with }\n"
    "2. No markdown, no code fences (no ```), no explanation text\n"
    "3. No preamble — just the JSON object\n"
    "4. The JSON must be valid and parseable\n"
    "5. Follow the payload format exactly as described in the instructions"
)

SUCCESS_SCORE_THRESHOLD = 0.5

# Groq free tier: 30 req/min TPM limit → 2s is safe per request
# TPD limit is 100k tokens/day — handled separately via TPD detection
GROQ_SLEEP    = 2.0
DEFAULT_SLEEP = 1.0

# Max seconds to wait for TPD reset before giving up (20 min)
MAX_TPD_WAIT = 1200


# ── Rate limit parsing ────────────────────────────────────────────────────────

def _parse_wait_seconds(err_str: str) -> float:
    """Extract the suggested wait time in seconds from a Groq 429 error message."""
    # Format: "Please try again in 12m50.688s" or "56.16s" or "1m5.664s"
    match = re.search(r"try again in ([\d.]+)m([\d.]+)s", err_str)
    if match:
        return float(match.group(1)) * 60 + float(match.group(2))
    match = re.search(r"try again in ([\d.]+)s", err_str)
    if match:
        return float(match.group(1))
    return 0.0


def _is_tpd_limit(err_str: str) -> bool:
    """Returns True if the error is a tokens-per-day limit (not per-minute)."""
    return "tokens per day" in err_str.lower() or "tpd" in err_str.lower()


# ── Logging ───────────────────────────────────────────────────────────────────

def log_start(task: str, env: str, model: str) -> None:
    print(f"[START] task={task} env={env} model={model}", flush=True)


def log_step(step: int, action: str, reward: float, done: bool, error: Optional[str]) -> None:
    error_val      = error if error else "null"
    done_val       = str(done).lower()
    action_oneline = action.replace("\n", " ")[:120]
    print(f"[STEP] step={step} action={action_oneline} reward={reward:.2f} done={done_val} error={error_val}", flush=True)


def log_end(success: bool, steps: int, score: float, rewards: list[float]) -> None:
    rewards_str = ",".join(f"{r:.2f}" for r in rewards)
    print(f"[END] success={str(success).lower()} steps={steps} score={score:.2f} rewards={rewards_str}", flush=True)


# ── Helpers ───────────────────────────────────────────────────────────────────

def progress_bar(current: int, total: int, width: int = 40) -> str:
    filled = int(width * current / total)
    return f"[{'█'*filled}{'░'*(width-filled)}] {int(100*current/total):3d}%  ({current}/{total})"


def score_bar(score: float, width: int = 10) -> str:
    filled = int(width * score)
    return "█" * filled + "░" * (width - filled)


def extract_json(text: str) -> dict:
    if not text:
        return {}
    text = text.strip()
    try:
        r = json.loads(text)
        if isinstance(r, dict):
            return r
    except Exception:
        pass
    cleaned = re.sub(r"^```(?:json)?\s*\n?", "", text, flags=re.IGNORECASE)
    cleaned = re.sub(r"\n?```\s*$", "", cleaned, flags=re.MULTILINE).strip()
    try:
        r = json.loads(cleaned)
        if isinstance(r, dict):
            return r
    except Exception:
        pass
    start = text.find("{")
    if start != -1:
        depth = 0
        for i, ch in enumerate(text[start:], start):
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    try:
                        r = json.loads(text[start:i+1])
                        if isinstance(r, dict):
                            return r
                    except Exception:
                        pass
                    break
    return {}


def unwrap_payload(payload: dict) -> dict:
    if payload and "payload" in payload and isinstance(payload["payload"], dict):
        return payload["payload"]
    return payload


def call_model(client, task_id: str, difficulty: str, instructions: str,
               agent_ctx: dict, feedback: Optional[str] = None,
               is_groq: bool = False) -> dict:
    """
    Call the model with adaptive retry on rate limit errors.
    Distinguishes between TPM (per-minute, short wait) and TPD (per-day, long wait).
    """
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

    max_api_retries = 6
    tpm_backoff     = 4.0

    for attempt in range(max_api_retries):
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
            return payload

        except Exception as e:
            err_str = str(e)

            if "429" in err_str or "rate_limit" in err_str.lower():
                wait_secs = _parse_wait_seconds(err_str)

                if _is_tpd_limit(err_str):
                    # Tokens-per-day exhausted — must wait for daily reset
                    if wait_secs > MAX_TPD_WAIT:
                        print(f"\n    [TPD LIMIT] Daily token limit exhausted. "
                              f"Reset in {wait_secs/60:.1f}min — exceeds max wait. Skipping task.")
                        return {}
                    wait_secs = max(wait_secs + 5, 60)  # add 5s buffer
                    print(f"\n    [TPD LIMIT] Daily token limit exhausted. "
                          f"Waiting {wait_secs/60:.1f}min for reset (attempt {attempt+1}/{max_api_retries})...")
                    time.sleep(wait_secs)
                else:
                    # TPM limit — short wait
                    wait_time = max(wait_secs + 0.5, tpm_backoff) if wait_secs > 0 else tpm_backoff
                    wait_time = min(wait_time, 60.0)
                    print(f"\n    [RATE LIMIT] Waiting {wait_time:.1f}s before retry "
                          f"{attempt+1}/{max_api_retries}...")
                    time.sleep(wait_time)
                    tpm_backoff = min(tpm_backoff * 1.5, 60.0)
            else:
                print(f"\n    [ERROR] API call failed: {e}")
                return {}

    print(f"\n    [ERROR] All {max_api_retries} retries exhausted.")
    return {}


# ── Single task episode ───────────────────────────────────────────────────────

def run_task(client, task_id: str, INSTRUCTIONS: dict, is_groq: bool = False) -> dict:
    from server.Meta_environment import MetaEnvironment
    from models import MetaAction

    agent = (
        "_".join(task_id.split("_")[:-1])
        if not task_id.startswith("cross_agent")
        else "cross_agent"
    )

    env = MetaEnvironment()
    env.reset()
    try:
        agent_ctx, grader_ctx, difficulty = env._load_context(task_id)
    except Exception as e:
        return {
            "task_id": task_id, "agent": agent, "difficulty": "unknown",
            "score": 0.0, "feedback": f"Context load failed: {e}",
            "partial_credits": {}, "reward": 0.0,
        }

    instructions = INSTRUCTIONS.get(task_id, "")

    env2 = MetaEnvironment()
    env2.reset()
    env2._current_agent_context  = agent_ctx
    env2._current_grader_context = grader_ctx
    env2._current_task_id        = task_id

    rewards: list[float] = []
    log_start(task_id, "meta", MODEL_NAME)

    # Attempt 1
    payload = call_model(client, task_id, difficulty, instructions, agent_ctx, is_groq=is_groq)
    action  = MetaAction(message=json.dumps({"agent": agent, "task_id": task_id, "payload": payload}))
    obs     = env2.step(action)
    rewards.append(obs.reward)
    log_step(1, json.dumps(payload)[:80], obs.reward, obs.done, None)

    # Attempt 2 if retry available
    if not obs.done and obs.score < 1.0:
        print(f"\n    [RETRY] Score {obs.score:.2f} — retrying with feedback...")
        time.sleep(GROQ_SLEEP if is_groq else 1.0)
        payload2 = call_model(client, task_id, difficulty, instructions, agent_ctx,
                              feedback=obs.feedback, is_groq=is_groq)
        action2  = MetaAction(message=json.dumps({"agent": agent, "task_id": task_id, "payload": payload2}))
        obs      = env2.step(action2)
        rewards.append(obs.reward)
        log_step(2, json.dumps(payload2)[:80], obs.reward, obs.done, None)

    success = obs.score >= SUCCESS_SCORE_THRESHOLD
    log_end(success, len(rewards), obs.score, rewards)

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

def run_all(api_base_url: str, model_name: str, hf_token: str) -> list[dict]:
    api_key = hf_token or API_KEY
    if not api_key:
        print("ERROR: No API key found.")
        print("  Set one of:")
        print("  GROQ_API_KEY=gsk_...    (free at https://console.groq.com)")
        print("  HF_TOKEN=hf_...         (HuggingFace token)")
        print("  OPENAI_API_KEY=sk-...   (OpenAI)")
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

    is_groq    = "groq.com" in api_base_url
    task_sleep = GROQ_SLEEP if is_groq else DEFAULT_SLEEP

    client  = OpenAI(api_key=api_key, base_url=api_base_url)
    results: list[dict] = []

    print()
    print("╔══════════════════════════════════════════════════════════════════╗")
    print("║        Meta OpenEnv — Inference Runner (OpenEnv Hackathon 2026) ║")
    print("╠══════════════════════════════════════════════════════════════════╣")
    print(f"║  Provider : {PROVIDER:<53}║")
    print(f"║  API Base : {api_base_url:<53}║")
    print(f"║  Model    : {model_name:<53}║")
    print(f"║  Tasks    : {len(TASK_IDS):<53}║")
    print(f"║  Sleep    : {task_sleep}s between tasks (TPM + TPD limit handling)         ║")
    print("╚══════════════════════════════════════════════════════════════════╝")
    print()

    start_all = time.time()

    for i, task_id in enumerate(TASK_IDS):
        print(f"  {progress_bar(i, len(TASK_IDS))}  {task_id}")
        sys.stdout.flush()

        t0      = time.time()
        result  = run_task(client, task_id, INSTRUCTIONS, is_groq=is_groq)
        elapsed = time.time() - t0
        results.append(result)

        diff = result["difficulty"].upper()[:4]
        bar  = score_bar(result["score"])
        print(f"  ✓ [{diff:4s}] {task_id:<40} [{bar}] {result['score']:.2f}  ({elapsed:.1f}s)  {result['feedback'][:50]}")
        sys.stdout.flush()
        time.sleep(task_sleep)

    total_time = time.time() - start_all
    avg_score  = sum(r["score"] for r in results) / len(results)
    passed     = sum(1 for r in results if r["score"] >= SUCCESS_SCORE_THRESHOLD)

    print()
    print(f"  {progress_bar(len(TASK_IDS), len(TASK_IDS))}")
    print()
    print("╔══════════════════════════════════════════════════════════════════╗")
    print(f"║  📊 Average Score : {avg_score:.4f}{'':37}║")
    print(f"║  ⏱  Total Time    : {total_time:.1f}s{'':39}║")
    print(f"║  ✅ Tasks Passed  : {passed}/{len(results)}{'':42}║")
    print("╚══════════════════════════════════════════════════════════════════╝")
    print()

    agents = ["email_triage","code_review","data_cleaning","content_moderation","ticket_triage","cross_agent"]
    print("  Per-Agent Summary:")
    for ag in agents:
        ag_r   = [r for r in results if r["agent"] == ag]
        ag_avg = sum(r["score"] for r in ag_r) / len(ag_r) if ag_r else 0.0
        print(f"    {ag:<35} [{score_bar(ag_avg)}] {ag_avg:.2f}")
    print()
    return results


if __name__ == "__main__":
    results = run_all(API_BASE_URL, MODEL_NAME, HF_TOKEN)
    print("Full Results JSON:")
    print(json.dumps(results, indent=2))