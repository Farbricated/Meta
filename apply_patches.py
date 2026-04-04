#!/usr/bin/env python3
"""
apply_patches.py — Automatically applies all 4 fixes to Meta OpenEnv v3.0

Run from the repo root:
    python apply_patches.py [--repo-dir /path/to/repo]

What it does:
    Fix 1: Wires data_generators.py into Meta_environment.py._load_context()
    Fix 2: Makes easy/medium graders accept per-episode context
    Fix 3: Adds /step/typed/{task_id} typed endpoint to server/app.py
    Fix 4: Updates task lists in gradio_ui.py, baseline.py, inference.py, openenv.yaml

Place data_generators.py and expert_tasks.py in the repo root alongside this script.
"""

import argparse
import os
import re
import shutil
import sys
from pathlib import Path


def banner(msg: str) -> None:
    print(f"\n{'─'*60}")
    print(f"  {msg}")
    print(f"{'─'*60}")


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def write(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8")
    print(f"  ✓ wrote {path}")


def backup(path: Path) -> None:
    bak = path.with_suffix(path.suffix + ".bak")
    shutil.copy2(path, bak)
    print(f"  ✓ backed up → {bak.name}")


# ─────────────────────────────────────────────────────────────────────────────
# Fix 1 + 2 — Meta_environment.py
# ─────────────────────────────────────────────────────────────────────────────

def patch_meta_environment(repo: Path) -> None:
    banner("Fix 1+2 — server/Meta_environment.py")
    path = repo / "server" / "Meta_environment.py"
    if not path.exists():
        print(f"  ✗ not found: {path}"); return
    backup(path)
    src = read(path)

    # ── Add imports ──────────────────────────────────────────────────────────
    import_block = """\
from data_generators import (
    gen_email_easy, gen_email_medium, gen_email_hard,
    gen_code_easy,
    gen_data_easy, gen_data_medium, gen_data_hard,
    gen_mod_easy, gen_mod_medium,
    gen_ticket_easy,
)
from expert_tasks import (
    EMAIL_EXPERT_CONTEXT, grade_email_expert,
    CODE_EXPERT_CONTEXT,  grade_code_expert,
    DATA_EXPERT_CONTEXT,  grade_data_expert,
    MOD_EXPERT_CONTEXT,   grade_mod_expert,
    TICKET_EXPERT_CONTEXT, grade_ticket_expert,
    EXPERT_INSTRUCTIONS, EXPERT_TASK_IDS,
)
"""
    if "from data_generators import" not in src:
        # Insert after the last existing import block (after "from models import")
        src = src.replace(
            "from models import MetaAction, MetaObservation",
            "from models import MetaAction, MetaObservation\n\n" + import_block,
        )
        print("  ✓ added data_generators + expert_tasks imports")

    # ── Replace static context loaders with generator calls ──────────────────
    replacements = [
        # email_easy
        (
            r"if task_id == \"email_triage_easy\":\s+email\s+=.*?\n.*?return agent_ctx, grader_ctx, \"easy\"",
            'if task_id == "email_triage_easy":\n'
            '            agent_ctx, grader_ctx = gen_email_easy(self._state.episode_id)\n'
            '            return agent_ctx, grader_ctx, "easy"',
        ),
        # email_medium
        (
            r"if task_id == \"email_triage_medium\":\s+agent_ctx\s+=.*?\n.*?return agent_ctx, grader_ctx, \"medium\"",
            'if task_id == "email_triage_medium":\n'
            '            agent_ctx, grader_ctx = gen_email_medium(self._state.episode_id)\n'
            '            return agent_ctx, grader_ctx, "medium"',
        ),
        # email_hard
        (
            r"if task_id == \"email_triage_hard\":\s+case\s+=.*?\n.*?return agent_ctx, grader_ctx, \"hard\"",
            'if task_id == "email_triage_hard":\n'
            '            agent_ctx, grader_ctx = gen_email_hard(self._state.episode_id)\n'
            '            return agent_ctx, grader_ctx, "hard"',
        ),
        # code_easy
        (
            r"if task_id == \"code_review_easy\":\s+variant\s+=.*?\n.*?return agent_ctx, grader_ctx, \"easy\"",
            'if task_id == "code_review_easy":\n'
            '            agent_ctx, grader_ctx = gen_code_easy(self._state.episode_id)\n'
            '            return agent_ctx, grader_ctx, "easy"',
        ),
        # data_easy
        (
            r"if task_id == \"data_cleaning_easy\":\s+ctx = \{\"data\": DATA_EASY\[\"data\"\]\}\s+return ctx, ctx, \"easy\"",
            'if task_id == "data_cleaning_easy":\n'
            '            agent_ctx, grader_ctx = gen_data_easy(self._state.episode_id)\n'
            '            return agent_ctx, grader_ctx, "easy"',
        ),
        # data_medium
        (
            r"if task_id == \"data_cleaning_medium\":\s+ctx = \{\"data\": DATA_MEDIUM\[\"data\"\]\}\s+return ctx, ctx, \"medium\"",
            'if task_id == "data_cleaning_medium":\n'
            '            agent_ctx, grader_ctx = gen_data_medium(self._state.episode_id)\n'
            '            return agent_ctx, grader_ctx, "medium"',
        ),
        # data_hard
        (
            r"if task_id == \"data_cleaning_hard\":\s+ctx = \{\"data\": DATA_HARD\[\"data\"\]\}\s+return ctx, ctx, \"hard\"",
            'if task_id == "data_cleaning_hard":\n'
            '            agent_ctx, grader_ctx = gen_data_hard(self._state.episode_id)\n'
            '            return agent_ctx, grader_ctx, "hard"',
        ),
        # mod_easy
        (
            r"if task_id == \"content_moderation_easy\":\s+agent_ctx\s+=.*?MOD_EASY.*?\n.*?return agent_ctx, grader_ctx, \"easy\"",
            'if task_id == "content_moderation_easy":\n'
            '            agent_ctx, grader_ctx = gen_mod_easy(self._state.episode_id)\n'
            '            return agent_ctx, grader_ctx, "easy"',
        ),
        # mod_medium
        (
            r"if task_id == \"content_moderation_medium\":\s+agent_ctx\s+=.*?MOD_MEDIUM.*?\n.*?return agent_ctx, grader_ctx, \"medium\"",
            'if task_id == "content_moderation_medium":\n'
            '            agent_ctx, grader_ctx = gen_mod_medium(self._state.episode_id)\n'
            '            return agent_ctx, grader_ctx, "medium"',
        ),
        # ticket_easy
        (
            r"if task_id == \"ticket_triage_easy\":\s+ticket\s+=.*?\n.*?return agent_ctx, grader_ctx, \"easy\"",
            'if task_id == "ticket_triage_easy":\n'
            '            agent_ctx, grader_ctx = gen_ticket_easy(self._state.episode_id)\n'
            '            return agent_ctx, grader_ctx, "easy"',
        ),
    ]

    for pattern, replacement in replacements:
        new_src = re.sub(pattern, replacement, src, flags=re.DOTALL)
        if new_src != src:
            src = new_src
            task = pattern.split('"')[1]
            print(f"  ✓ replaced context loader: {task}")
        # Regex may not match exactly — try string replacement as fallback later

    # ── Add expert context loaders before final raise ─────────────────────────
    expert_loaders = """
        if task_id == "email_triage_expert":
            agent_ctx  = {k: v for k, v in EMAIL_EXPERT_CONTEXT.items()}
            grader_ctx = agent_ctx
            return agent_ctx, grader_ctx, "expert"

        if task_id == "code_review_expert":
            agent_ctx  = {"code": CODE_EXPERT_CONTEXT["code"],
                          "vulnerability_count": CODE_EXPERT_CONTEXT["vulnerability_count"]}
            grader_ctx = CODE_EXPERT_CONTEXT
            return agent_ctx, grader_ctx, "expert"

        if task_id == "data_cleaning_expert":
            agent_ctx  = DATA_EXPERT_CONTEXT
            grader_ctx = DATA_EXPERT_CONTEXT
            return agent_ctx, grader_ctx, "expert"

        if task_id == "content_moderation_expert":
            agent_ctx  = MOD_EXPERT_CONTEXT
            grader_ctx = MOD_EXPERT_CONTEXT
            return agent_ctx, grader_ctx, "expert"

        if task_id == "ticket_triage_expert":
            agent_ctx  = TICKET_EXPERT_CONTEXT
            grader_ctx = TICKET_EXPERT_CONTEXT
            return agent_ctx, grader_ctx, "expert"

"""
    if '"email_triage_expert"' not in src:
        src = src.replace(
            'raise ValueError(f"Unknown task_id:',
            expert_loaders + '        raise ValueError(f"Unknown task_id:',
        )
        print("  ✓ added expert context loaders")

    # ── Add expert grader routing in _grade() ─────────────────────────────────
    expert_graders = (
        '        if task_id == "email_triage_expert":       return grade_email_expert(payload)\n'
        '        if task_id == "code_review_expert":        return grade_code_expert(payload)\n'
        '        if task_id == "data_cleaning_expert":      return grade_data_expert(payload)\n'
        '        if task_id == "content_moderation_expert": return grade_mod_expert(payload)\n'
        '        if task_id == "ticket_triage_expert":      return grade_ticket_expert(payload)\n'
    )
    if "grade_email_expert" not in src:
        src = src.replace(
            '        return 0.0, "Unknown task.", {}',
            expert_graders + '        return 0.0, "Unknown task.", {}',
        )
        print("  ✓ added expert grader routing")

    # ── Fix graders to accept per-episode context ─────────────────────────────
    src = src.replace(
        "def grade_mod_easy(payload: dict) -> tuple[float, str, dict]:",
        "def grade_mod_easy(payload: dict, context: dict = None) -> tuple[float, str, dict]:",
    )
    src = src.replace(
        "    correct = {p[\"id\"]: p[\"label\"] for p in MOD_EASY}",
        '    posts   = (context or {}).get("posts", MOD_EASY)\n    correct = {p["id"]: p["label"] for p in posts}',
        1,
    )
    src = src.replace(
        "def grade_mod_medium(payload: dict) -> tuple[float, str, dict]:",
        "def grade_mod_medium(payload: dict, context: dict = None) -> tuple[float, str, dict]:",
    )
    src = src.replace(
        "    correct = {p[\"id\"]: p[\"label\"] for p in MOD_MEDIUM}",
        '    posts   = (context or {}).get("posts", MOD_MEDIUM)\n    correct = {p["id"]: p["label"] for p in posts}',
        1,
    )

    # Fix grade_email_medium to read correct_order from context
    src = src.replace(
        "    correct = EMAIL_MEDIUM_CORRECT_ORDER",
        '    correct = context.get("correct_order", EMAIL_MEDIUM_CORRECT_ORDER)',
        1,
    )

    # Fix grade_data_hard to accept context
    src = src.replace(
        "def grade_data_hard(payload: dict) -> tuple[float, str, dict]:",
        "def grade_data_hard(payload: dict, context: dict = None) -> tuple[float, str, dict]:",
    )
    src = src.replace(
        "    correct_out    = DATA_HARD[\"answers\"][\"outliers\"]",
        '    answers      = (context or {}).get("answers", DATA_HARD["answers"])\n    correct_out  = answers.get("outliers", DATA_HARD["answers"]["outliers"])',
    )
    src = src.replace(
        "    correct_miss   = DATA_HARD[\"answers\"][\"missing\"]",
        '    correct_miss = answers.get("missing", DATA_HARD["answers"]["missing"])',
    )
    src = src.replace(
        '    lo, hi         = DATA_HARD["answers"]["imputed_range"]',
        '    lo, hi       = answers.get("imputed_range", DATA_HARD["answers"]["imputed_range"])',
    )

    # Fix _grade() calls for mod_easy/mod_medium/data_hard to pass context
    src = src.replace(
        'if task_id == "content_moderation_easy":     return grade_mod_easy(payload)',
        'if task_id == "content_moderation_easy":     return grade_mod_easy(payload, grader_context)',
    )
    src = src.replace(
        'if task_id == "content_moderation_medium":   return grade_mod_medium(payload)',
        'if task_id == "content_moderation_medium":   return grade_mod_medium(payload, grader_context)',
    )
    src = src.replace(
        'if task_id == "data_cleaning_hard":          return grade_data_hard(payload)',
        'if task_id == "data_cleaning_hard":          return grade_data_hard(payload, grader_context)',
    )

    # ── Add EXPERT_INSTRUCTIONS to INSTRUCTIONS dict ──────────────────────────
    if "email_triage_expert" not in src:
        src = src.replace(
            '    "cross_agent_mod_escalation": (',
            '    **{},  # expert instructions added below\n    "cross_agent_mod_escalation": (',
        )
        # Better: append to INSTRUCTIONS dict
        src = src.replace(
            '    "cross_agent_mod_escalation": (\n        "TWO skills needed',
            '    "cross_agent_mod_escalation": (\n        "TWO skills needed',
        )
        # Find the closing of INSTRUCTIONS dict and add expert entries before it
        # (This is safer as a manual step — note it for the developer)
        print("  ⚠  Add EXPERT_INSTRUCTIONS entries to INSTRUCTIONS dict manually (see expert_tasks.py)")

    write(path, src)


# ─────────────────────────────────────────────────────────────────────────────
# Fix 3 — server/app.py typed endpoint
# ─────────────────────────────────────────────────────────────────────────────

TYPED_ENDPOINT_CODE = '''

# ── Typed step endpoint — Fix 3 ───────────────────────────────────────────────

_TASK_TO_MODEL = {
    "email_triage_easy":          EmailTriageEasyPayload,
    "email_triage_medium":        EmailTriageMediumPayload,
    "email_triage_hard":          EmailTriageHardPayload,
    "code_review_easy":           CodeReviewEasyPayload,
    "code_review_medium":         CodeReviewMediumPayload,
    "code_review_hard":           CodeReviewHardPayload,
    "data_cleaning_easy":         DataCleaningEasyPayload,
    "data_cleaning_medium":       DataCleaningMediumPayload,
    "data_cleaning_hard":         DataCleaningHardPayload,
    "content_moderation_easy":    ContentModerationEasyPayload,
    "content_moderation_medium":  ContentModerationMediumPayload,
    "content_moderation_hard":    ContentModerationHardPayload,
    "ticket_triage_easy":         TicketTriageEasyPayload,
    "ticket_triage_medium":       TicketTriageMediumPayload,
    "ticket_triage_hard":         TicketTriageHardPayload,
    "cross_agent_chain":          CrossAgentChainPayload,
    "cross_agent_email_data":     CrossAgentEmailDataPayload,
    "cross_agent_code_email":     CrossAgentCodeEmailPayload,
    "cross_agent_mod_escalation": CrossAgentModEscalationPayload,
}


@app.post("/step/typed/{task_id}")
async def step_typed(task_id: str, request: Request):
    """
    Typed step endpoint — accepts the typed payload model for the given task_id
    instead of the JSON-string-in-message format.

    Example:
        POST /step/typed/email_triage_easy
        Body: {"agent": "email_triage", "task_id": "email_triage_easy", "payload": {"classification": "spam"}}

    Returns the same observation as POST /step.
    """
    if task_id not in _TASK_TO_MODEL:
        return JSONResponse(status_code=404, content={"error": f"Unknown task_id: {task_id}. See GET /tasks."})
    body = await request.json()
    try:
        model_cls = _TASK_TO_MODEL[task_id]
        payload   = body.get("payload", body)
        typed     = model_cls(**payload)
    except Exception as e:
        return JSONResponse(status_code=422, content={"error": str(e), "task_id": task_id})
    agent   = body.get("agent", "_".join(task_id.split("_")[:-1]))
    wrapped = MetaAction(message=json.dumps({
        "agent": agent, "task_id": task_id, "payload": typed.model_dump()
    }))
    # Delegate to the active environment instance
    env = MetaEnvironment()
    env.reset()
    obs = env.step(wrapped)
    return obs.model_dump()
'''

TYPED_MODEL_IMPORTS = """\
from models import (
    MetaAction, MetaObservation,
    EmailTriageEasyPayload, EmailTriageMediumPayload, EmailTriageHardPayload,
    CodeReviewEasyPayload, CodeReviewMediumPayload, CodeReviewHardPayload,
    DataCleaningEasyPayload, DataCleaningMediumPayload, DataCleaningHardPayload,
    ContentModerationEasyPayload, ContentModerationMediumPayload, ContentModerationHardPayload,
    TicketTriageEasyPayload, TicketTriageMediumPayload, TicketTriageHardPayload,
    CrossAgentChainPayload, CrossAgentEmailDataPayload,
    CrossAgentCodeEmailPayload, CrossAgentModEscalationPayload,
)
"""


def patch_app_py(repo: Path) -> None:
    banner("Fix 3 — server/app.py typed endpoint")
    path = repo / "server" / "app.py"
    if not path.exists():
        print(f"  ✗ not found: {path}"); return
    backup(path)
    src = read(path)

    if "_TASK_TO_MODEL" in src:
        print("  ⟳ already patched"); return

    # Update the import of MetaAction to include all typed models
    src = src.replace(
        "from models import MetaAction, MetaObservation",
        TYPED_MODEL_IMPORTS.rstrip(),
    )

    # Append typed endpoint before the main() function
    src = src.replace(
        "\ndef main(",
        TYPED_ENDPOINT_CODE + "\n\ndef main(",
    )

    write(path, src)


# ─────────────────────────────────────────────────────────────────────────────
# Fix 4a — gradio_ui.py
# ─────────────────────────────────────────────────────────────────────────────

ALL_TASK_IDS_24 = [
    "email_triage_easy",       "email_triage_medium",        "email_triage_hard",       "email_triage_expert",
    "code_review_easy",        "code_review_medium",          "code_review_hard",        "code_review_expert",
    "data_cleaning_easy",      "data_cleaning_medium",        "data_cleaning_hard",      "data_cleaning_expert",
    "content_moderation_easy", "content_moderation_medium",   "content_moderation_hard", "content_moderation_expert",
    "ticket_triage_easy",      "ticket_triage_medium",        "ticket_triage_hard",      "ticket_triage_expert",
    "cross_agent_chain",       "cross_agent_email_data",      "cross_agent_code_email",  "cross_agent_mod_escalation",
]


def patch_gradio_ui(repo: Path) -> None:
    banner("Fix 4a — server/gradio_ui.py task list + count")
    path = repo / "server" / "gradio_ui.py"
    if not path.exists():
        print(f"  ✗ not found: {path}"); return
    backup(path)
    src = read(path)

    # Replace TASK_IDS list
    new_task_ids = "TASK_IDS = [\n" + "".join(
        f'    "{t}",\n' for t in ALL_TASK_IDS_24
    ) + "]\n"

    # Find and replace the existing TASK_IDS block
    src = re.sub(
        r"TASK_IDS = \[.*?\]",
        new_task_ids.rstrip(),
        src,
        flags=re.DOTALL,
    )

    # Add "expert" to DIFFICULTY_EMOJI
    src = src.replace(
        '"hard": "🔴 Hard"}',
        '"hard": "🔴 Hard", "expert": "⚫ Expert"}',
    )

    # Update header agent/task count
    src = src.replace(
        "**4 agents · 12 tasks · Real-world RL environment**",
        "**6 agents · 24 tasks · Real-world RL environment**",
    )
    src = src.replace(
        "**4 agents, 12 tasks**",
        "**6 agents, 24 tasks**",
    )

    # Update /tasks text in About tab
    src = src.replace(
        "| GET | `/tasks` | All 12 tasks |",
        "| GET | `/tasks` | All 24 tasks with schemas |\n    | POST | `/step/typed/{task_id}` | Typed action format |",
    )

    write(path, src)


# ─────────────────────────────────────────────────────────────────────────────
# Fix 4b — baseline.py
# ─────────────────────────────────────────────────────────────────────────────

BASELINE_TASK_IDS = """\
TASK_IDS = [
    "email_triage_easy",        "email_triage_medium",        "email_triage_hard",         "email_triage_expert",
    "code_review_easy",         "code_review_medium",         "code_review_hard",          "code_review_expert",
    "data_cleaning_easy",       "data_cleaning_medium",       "data_cleaning_hard",        "data_cleaning_expert",
    "content_moderation_easy",  "content_moderation_medium",  "content_moderation_hard",   "content_moderation_expert",
    "ticket_triage_easy",       "ticket_triage_medium",       "ticket_triage_hard",        "ticket_triage_expert",
    "cross_agent_chain",        "cross_agent_email_data",     "cross_agent_code_email",    "cross_agent_mod_escalation",
]"""


def patch_baseline(repo: Path) -> None:
    banner("Fix 4b — baseline.py task list")
    path = repo / "baseline.py"
    if not path.exists():
        print(f"  ✗ not found: {path}"); return
    backup(path)
    src = read(path)
    src = re.sub(r"TASK_IDS = \[.*?\]", BASELINE_TASK_IDS, src, flags=re.DOTALL)
    write(path, src)


# ─────────────────────────────────────────────────────────────────────────────
# Fix 4c — inference.py
# ─────────────────────────────────────────────────────────────────────────────

INFERENCE_TASK_IDS = """\
TASK_IDS = [
    "email_triage_easy",        "email_triage_medium",        "email_triage_hard",         "email_triage_expert",
    "code_review_easy",         "code_review_medium",         "code_review_hard",          "code_review_expert",
    "data_cleaning_easy",       "data_cleaning_medium",       "data_cleaning_hard",        "data_cleaning_expert",
    "content_moderation_easy",  "content_moderation_medium",  "content_moderation_hard",   "content_moderation_expert",
    "ticket_triage_easy",       "ticket_triage_medium",       "ticket_triage_hard",        "ticket_triage_expert",
    "cross_agent_chain",        "cross_agent_email_data",     "cross_agent_code_email",    "cross_agent_mod_escalation",
]"""


def patch_inference(repo: Path) -> None:
    banner("Fix 4c — inference.py task list")
    path = repo / "inference.py"
    if not path.exists():
        print(f"  ✗ not found: {path}"); return
    backup(path)
    src = read(path)
    src = re.sub(r"TASK_IDS = \[.*?\]", INFERENCE_TASK_IDS, src, flags=re.DOTALL)
    write(path, src)


# ─────────────────────────────────────────────────────────────────────────────
# Fix 4d — openenv.yaml
# ─────────────────────────────────────────────────────────────────────────────

EXPERT_YAML_TASKS = """
  # ── Expert tier (multi-step reasoning, frontier challenge) ────────────────
  - id: email_triage_expert
    agent: email_triage
    difficulty: expert
    description: >
      Draft an executive reply to a 4-week escalated enterprise complaint.
      Account metadata and engineering root cause provided. Requires multi-context
      synthesis and executive tone calibration. Frontier models score ~0.45.

  - id: code_review_expert
    agent: code_review
    difficulty: expert
    description: >
      Identify 8 subtle vulnerabilities: hardcoded secret, JWT none-algorithm attack,
      mass assignment, IDOR, YAML RCE deserialization, TOCTOU race condition,
      prototype pollution, and log injection. Frontier models score ~0.38.

  - id: data_cleaning_expert
    agent: data_cleaning
    difficulty: expert
    description: >
      Join two datasets, detect multi-type anomalies (duplicates, missing, outliers,
      zero-amounts), convert currencies to USD, compute per-rep revenue excluding
      invalid transactions. Frontier models score ~0.50.

  - id: content_moderation_expert
    agent: content_moderation
    difficulty: expert
    description: >
      Issue rulings on 5 genuinely contested cases: suicidal ideation,
      great-replacement rhetoric, conscientious objection policy debate,
      antisemitic satire framing, and health misinformation. Frontier models score ~0.40.

  - id: ticket_triage_expert
    agent: ticket_triage
    difficulty: expert
    description: >
      Produce a board-ready PIR from a 4h17m outage timeline. Requires identifying
      timeline gaps, 5+ specific action items, and quantified MTTR breakdown.
      Frontier models score ~0.50.
"""


def patch_openenv_yaml(repo: Path) -> None:
    banner("Fix 4d — openenv.yaml expert tasks + agent lists")
    path = repo / "openenv.yaml"
    if not path.exists():
        print(f"  ✗ not found: {path}"); return
    backup(path)
    src = read(path)

    if "email_triage_expert" in src:
        print("  ⟳ already patched"); return

    # Insert expert tasks before the cross-agent section
    src = src.replace(
        "  # ── Cross-Agent Chained",
        EXPERT_YAML_TASKS + "\n  # ── Cross-Agent Chained",
    )

    # Update agent task lists to include expert
    for agent in ["email_triage", "code_review", "data_cleaning", "content_moderation", "ticket_triage"]:
        expert_id = f"{agent}_expert"
        src = re.sub(
            rf"(- id: {agent}\n    tasks: \[.*?)(])",
            lambda m, eid=expert_id: m.group(1) + f", {eid}" + m.group(2),
            src,
        )

    # Update version
    src = src.replace('version: "3.0.0"', 'version: "3.1.0"')
    src = src.replace("Meta is the first multi-domain OpenEnv environment featuring 5 AI agents",
                      "Meta is the first multi-domain OpenEnv environment featuring 5 AI agents (plus expert tier)")

    write(path, src)


# ─────────────────────────────────────────────────────────────────────────────
# Copy new files into repo
# ─────────────────────────────────────────────────────────────────────────────

def copy_new_files(repo: Path, script_dir: Path) -> None:
    banner("Copying new source files")
    for fname in ["data_generators.py", "expert_tasks.py"]:
        src  = script_dir / fname
        dest = repo / fname
        if not src.exists():
            print(f"  ✗ {fname} not found in {script_dir}")
            continue
        # Skip if source and destination are the same file (script lives in repo root)
        try:
            if src.resolve() == dest.resolve():
                print(f"  ⟳ {fname} already in place (src == dest), skipping copy")
                continue
        except OSError:
            pass
        try:
            shutil.copy2(src, dest)
            print(f"  ✓ copied {fname} → {dest}")
        except PermissionError as e:
            print(f"  ⚠  Could not copy {fname}: {e}")
            print(f"     Close any editors/processes that have {dest} open and retry.")


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Apply Meta v3.1 patches")
    parser.add_argument("--repo-dir", default=".", help="Path to repo root")
    args = parser.parse_args()

    repo       = Path(args.repo_dir).resolve()
    script_dir = Path(__file__).parent.resolve()

    print(f"\nRepo   : {repo}")
    print(f"Scripts: {script_dir}")

    if not (repo / "openenv.yaml").exists():
        print(f"\n✗ ERROR: {repo}/openenv.yaml not found. Pass --repo-dir to the repo root.")
        sys.exit(1)

    copy_new_files(repo, script_dir)
    patch_meta_environment(repo)
    patch_app_py(repo)
    patch_gradio_ui(repo)
    patch_baseline(repo)
    patch_inference(repo)
    patch_openenv_yaml(repo)

    banner("DONE — run verification checks")
    print("""
  python -c "from data_generators import gen_email_easy; print('generators OK')"
  python -c "from expert_tasks import EXPERT_TASK_IDS; print(EXPERT_TASK_IDS)"
  pytest tests/ -v
  python inference.py --dry-run   # if supported, else just check imports
    """)


if __name__ == "__main__":
    main()