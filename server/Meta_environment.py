# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.

"""
Meta Multi-Agent Environment Implementation.

Four real-world AI agent tasks:
  1. Email Triage     - classify, prioritize, and draft email replies
  2. Code Review      - detect syntax errors, logic bugs, security vulnerabilities
  3. Data Cleaning    - find missing values, fix types, detect outliers
  4. Content Moderation - detect explicit, subtle, and context-aware harmful content
"""

import random
from uuid import uuid4
from openenv.core.env_server.interfaces import Environment
from openenv.core.env_server.types import State

try:
    from ..models import MetaAction, MetaObservation
except ImportError:
    from models import MetaAction, MetaObservation


# ══════════════════════════════════════════════════════════════════════════════
# TASK DATA
# ══════════════════════════════════════════════════════════════════════════════

EMAILS = {
    "easy": [
        {"id": "e1", "subject": "You won $1,000,000!!!", "sender": "promo@totally-legit-lottery.com", "body": "Click here to claim your prize now! Limited time offer!", "label": "spam"},
        {"id": "e2", "subject": "Q3 Budget Review Meeting — Urgent", "sender": "cfo@company.com", "body": "Please review the attached Q3 budget before our meeting tomorrow at 9 AM.", "label": "important"},
        {"id": "e3", "subject": "Your weekly digest from Medium", "sender": "noreply@medium.com", "body": "Top stories this week: AI trends, productivity hacks, and more.", "label": "newsletter"},
    ],
    "medium": [
        {"id": "m1", "subject": "Server is DOWN", "sender": "ops@company.com", "body": "Production server unresponsive since 2 AM.", "priority": 1, "category": "critical"},
        {"id": "m2", "subject": "Team lunch tomorrow?", "sender": "colleague@company.com", "body": "Hey, want to grab lunch tomorrow at noon?", "priority": 5, "category": "social"},
        {"id": "m3", "subject": "Client contract renewal due Friday", "sender": "sales@company.com", "body": "Acme Corp contract expires Friday. Need approval ASAP.", "priority": 2, "category": "business"},
        {"id": "m4", "subject": "Weekly newsletter", "sender": "news@techdigest.com", "body": "This week in tech...", "priority": 8, "category": "newsletter"},
        {"id": "m5", "subject": "Security breach detected", "sender": "security@company.com", "body": "Unusual login attempts detected on your account.", "priority": 1, "category": "critical"},
        {"id": "m6", "subject": "Invoice #4521 due", "sender": "billing@vendor.com", "body": "Invoice of $5,400 due in 3 days.", "priority": 3, "category": "finance"},
        {"id": "m7", "subject": "Happy Birthday!", "sender": "hr@company.com", "body": "Wishing you a wonderful birthday!", "priority": 9, "category": "social"},
        {"id": "m8", "subject": "Product launch presentation review", "sender": "marketing@company.com", "body": "Please review slides before Thursday's launch meeting.", "priority": 3, "category": "business"},
        {"id": "m9", "subject": "Free webinar: Boost productivity", "sender": "promo@webinar.com", "body": "Register now for our free webinar!", "priority": 10, "category": "newsletter"},
        {"id": "m10", "subject": "Urgent: Legal document needs signature", "sender": "legal@company.com", "body": "Contract must be signed by EOD today.", "priority": 2, "category": "legal"},
    ],
    "hard": {
        "id": "h1",
        "subject": "Extremely disappointed — Order #78234",
        "sender": "angry.customer@email.com",
        "body": (
            "I have been a loyal customer for 5 years and I am absolutely furious. "
            "My order #78234 arrived broken for the SECOND time this month. "
            "Your customer service team has been dismissive and unhelpful. "
            "I demand a full refund, a replacement, AND compensation for the inconvenience. "
            "If this is not resolved within 24 hours, I will be filing a complaint with "
            "the consumer court and leaving reviews on every platform I can find."
        ),
        "expected_elements": ["acknowledge_frustration", "apologize", "offer_refund", "offer_replacement", "provide_timeline", "professional_tone"],
    },
}

CODE_TASKS = {
    "easy": {
        "code": "def calculate_average(numbers):\n    total = 0\n    for num in numbers\n        total += num\n    return total / len(numbers)\n",
        "errors": ["missing colon after for loop"],
    },
    "medium": {
        "code": (
            "def find_max(numbers):\n    max_val = 0\n    for num in numbers:\n        if num > max_val:\n            max_val = num\n    return max_val\n\n"
            "def get_user(users, user_id):\n    for user in users:\n        if user['id'] = user_id:\n            return user\n    return None\n\n"
            "def divide(a, b):\n    return a / b\n"
        ),
        "bugs": ["find_max initializes max_val to 0 — fails for all-negative lists", "get_user uses = instead of ==", "divide has no zero division guard"],
    },
    "hard": {
        "code": (
            "import sqlite3\n\n"
            "def get_user_by_name(name):\n    conn = sqlite3.connect('users.db')\n    cursor = conn.cursor()\n"
            "    query = \"SELECT * FROM users WHERE name = '\" + name + \"'\"\n    cursor.execute(query)\n    return cursor.fetchall()\n\n"
            "def render_comment(comment):\n    return '<div>' + comment + '</div>'\n\n"
            "def login(username, password):\n    conn = sqlite3.connect('users.db')\n    cursor = conn.cursor()\n"
            "    query = f\"SELECT * FROM users WHERE username='{username}' AND password='{password}'\"\n"
            "    cursor.execute(query)\n    user = cursor.fetchone()\n    if user:\n        return True\n    return False\n"
        ),
        "vulnerabilities": [
            {"type": "sql_injection", "location": "get_user_by_name"},
            {"type": "xss", "location": "render_comment"},
            {"type": "sql_injection", "location": "login"},
        ],
    },
}

DATA_TASKS = {
    "easy": {
        "data": [
            {"id": 1, "name": "Alice", "age": 30, "email": "alice@example.com"},
            {"id": 2, "name": "Bob", "age": None, "email": "bob@example.com"},
            {"id": 3, "name": "Alice", "age": 30, "email": "alice@example.com"},
            {"id": 4, "name": None, "age": 25, "email": "charlie@example.com"},
            {"id": 5, "name": "Dave", "age": 40, "email": None},
        ],
        "missing": ["age (row 2)", "name (row 4)", "email (row 5)"],
        "duplicates": [1, 3],
    },
    "medium": {
        "data": [
            {"id": 1, "name": "Alice", "age": "thirty", "salary": "50000", "join_date": "2020/01/15"},
            {"id": 2, "name": "Bob", "age": 25, "salary": "$60,000", "join_date": "15-03-2021"},
            {"id": 3, "name": "Charlie", "age": "28", "salary": "70000", "join_date": "2019-07-22"},
            {"id": 4, "name": "dave", "age": 35, "salary": "80,000", "join_date": "2022/11/01"},
        ],
    },
    "hard": {
        "data": [
            {"id": 1, "value": 10.5}, {"id": 2, "value": 11.2}, {"id": 3, "value": 10.8},
            {"id": 4, "value": 999.0}, {"id": 5, "value": 10.1}, {"id": 6, "value": None},
            {"id": 7, "value": 11.5}, {"id": 8, "value": -500.0}, {"id": 9, "value": 10.9},
            {"id": 10, "value": 11.0},
        ],
        "outliers": [4, 8],
        "missing": [6],
        "imputed_range": (10.0, 12.0),
    },
}

MODERATION_TASKS = {
    "easy": [
        {"id": "c1", "text": "I hate you so much, I want to hurt you!", "label": "harmful"},
        {"id": "c2", "text": "Great weather today, loving this sunshine!", "label": "safe"},
        {"id": "c3", "text": "All people from that group should be eliminated.", "label": "harmful"},
        {"id": "c4", "text": "Can someone recommend a good Python tutorial?", "label": "safe"},
        {"id": "c5", "text": "You're an idiot and nobody likes you.", "label": "harmful"},
    ],
    "medium": [
        {"id": "m1", "text": "Oh sure, like THAT went well. Classic genius move.", "label": "harmful"},
        {"id": "m2", "text": "I'm so done with these people. They make me sick.", "label": "harmful"},
        {"id": "m3", "text": "That presentation was... interesting.", "label": "safe"},
        {"id": "m4", "text": "Some people just shouldn't be allowed to speak.", "label": "harmful"},
        {"id": "m5", "text": "Oh wow, another 'brilliant' idea from management.", "label": "harmful"},
        {"id": "m6", "text": "I totally agree with everything you said!", "label": "safe"},
    ],
    "hard": [
        {
            "id": "h1", "text": "You should just disappear.",
            "context_a": {"platform": "gaming_chat", "prior_message": "Your game character lost the round"},
            "label_a": "safe",
            "context_b": {"platform": "social_media", "prior_message": "I'm feeling really lonely and depressed"},
            "label_b": "harmful",
        },
        {
            "id": "h2", "text": "We need to take these people out.",
            "context_a": {"platform": "event_planning", "prior_message": "Who should we invite to the company dinner?"},
            "label_a": "safe",
            "context_b": {"platform": "political_forum", "prior_message": "These protesters are getting out of hand."},
            "label_b": "harmful",
        },
    ],
}


# ══════════════════════════════════════════════════════════════════════════════
# GRADERS
# ══════════════════════════════════════════════════════════════════════════════

def grade_email_easy(payload, context):
    correct = context["email"]["label"]
    given = payload.get("classification", "").strip().lower()
    return (1.0 if given == correct else 0.0), f"Expected '{correct}', got '{given}'."

def grade_email_medium(payload, context):
    order = payload.get("order", [])
    correct = ["m1", "m5", "m3", "m6", "m10", "m8", "m2", "m4", "m7", "m9"]
    if order == correct:
        return 1.0, "Perfect prioritization!"
    top3 = order[:3] == correct[:3]
    top5 = order[:5] == correct[:5]
    if top5: return 0.75, "Top 5 correct."
    if top3: return 0.5, "Top 3 critical emails correct."
    hits = sum(1 for i, e in enumerate(order) if i < len(correct) and e == correct[i])
    return round(hits / 10, 2), f"{hits}/10 in correct position."

def grade_email_hard(payload, context):
    reply = payload.get("reply", "").lower()
    checks = {
        "acknowledge_frustration": any(w in reply for w in ["understand", "frustrat", "disappoint", "concern"]),
        "apologize": any(w in reply for w in ["sorry", "apologize", "apology"]),
        "offer_refund": any(w in reply for w in ["refund", "money back"]),
        "offer_replacement": any(w in reply for w in ["replacement", "replace", "send another"]),
        "provide_timeline": any(w in reply for w in ["24 hours", "within", "by", "today", "tomorrow", "48 hours"]),
        "professional_tone": len(reply) > 100 and "not my problem" not in reply,
    }
    passed = sum(checks.values())
    return round(passed / 6, 2), f"{passed}/6 reply elements present."

def grade_code_easy(payload):
    errors = " ".join(payload.get("errors", [])).lower()
    found = "colon" in errors or "for loop" in errors or "syntax" in errors
    return (1.0 if found else 0.0), "Syntax error found." if found else "Syntax error not identified."

def grade_code_medium(payload):
    bugs = payload.get("bugs", [])
    checks = {"max_val": False, "assignment": False, "zero_division": False}
    for b in bugs:
        t = (str(b.get("issue", "")) + str(b.get("location", ""))).lower()
        if any(w in t for w in ["max_val", "negative", "zero", "initialization"]): checks["max_val"] = True
        if any(w in t for w in ["assignment", "==", "comparison"]): checks["assignment"] = True
        if any(w in t for w in ["zero", "division", "divide"]): checks["zero_division"] = True
    passed = sum(checks.values())
    return round(passed / 3, 2), f"{passed}/3 bugs found."

def grade_code_hard(payload):
    vulns = payload.get("vulnerabilities", [])
    checks = {"sql_get_user": False, "xss": False, "sql_login": False}
    for v in vulns:
        vt = str(v.get("type", "")).lower()
        loc = str(v.get("location", "")).lower()
        if "sql" in vt and "get_user" in loc: checks["sql_get_user"] = True
        if "xss" in vt or ("script" in str(v).lower() and "render" in loc): checks["xss"] = True
        if "sql" in vt and "login" in loc: checks["sql_login"] = True
    passed = sum(checks.values())
    return round(passed / 3, 2), f"{passed}/3 vulnerabilities found."

def grade_data_easy(payload):
    missing = [str(m).lower() for m in payload.get("missing", [])]
    duplicates = set(str(d) for d in payload.get("duplicates", []))
    mc = {
        "age_row2": any("age" in m and "2" in m for m in missing),
        "name_row4": any("name" in m and "4" in m for m in missing),
        "email_row5": any("email" in m and "5" in m for m in missing),
    }
    dup_ok = duplicates == {"1", "3"} or duplicates == {1, 3}
    passed = sum(mc.values())
    score = round((passed / 3 * 0.7) + (0.3 if dup_ok else 0.0), 2)
    return score, f"Missing: {passed}/3, Duplicates: {'correct' if dup_ok else 'incorrect'}."

def grade_data_medium(payload):
    issues = {k.lower(): str(v).lower() for k, v in payload.get("issues", {}).items()}
    cleaned = payload.get("cleaned_data", [])
    checks = {
        "age_type": "age" in issues and any(w in issues["age"] for w in ["string", "integer", "thirty"]),
        "salary_format": "salary" in issues and any(w in issues["salary"] for w in ["format", "comma", "$", "inconsistent"]),
        "date_format": "join_date" in issues and any(w in issues["join_date"] for w in ["format", "inconsistent", "date"]),
        "name_case": "name" in issues and any(w in issues["name"] for w in ["capital", "case", "dave", "lower"]),
        "data_cleaned": len(cleaned) == 4,
    }
    passed = sum(checks.values())
    return round(passed / 5, 2), f"{passed}/5 data quality checks passed."

def grade_data_hard(payload):
    outliers = set(int(x) for x in payload.get("outliers", []))
    missing = set(int(x) for x in payload.get("missing", []))
    cleaned = payload.get("cleaned_data", [])
    row6 = next((r for r in cleaned if r.get("id") == 6), None)
    imputed_ok = row6 is not None and row6.get("value") is not None and 10.0 <= float(row6["value"]) <= 12.0
    checks = {"outliers": outliers == {4, 8}, "missing": missing == {6}, "imputation": imputed_ok}
    passed = sum(checks.values())
    return round(passed / 3, 2), f"{passed}/3 data operations correct."

def grade_moderation_easy(payload):
    clf = {c["id"]: c["label"].lower() for c in payload.get("classifications", [])}
    correct = {p["id"]: p["label"] for p in MODERATION_TASKS["easy"]}
    hits = sum(1 for id_, label in correct.items() if clf.get(id_) == label)
    return round(hits / len(correct), 2), f"{hits}/{len(correct)} posts correctly classified."

def grade_moderation_medium(payload):
    clf = {c["id"]: c["label"].lower() for c in payload.get("classifications", [])}
    correct = {p["id"]: p["label"] for p in MODERATION_TASKS["medium"]}
    hits = sum(1 for id_, label in correct.items() if clf.get(id_) == label)
    return round(hits / len(correct), 2), f"{hits}/{len(correct)} subtle posts correctly classified."

def grade_moderation_hard(payload):
    decisions = {d["id"]: d for d in payload.get("decisions", [])}
    checks = {}
    for case in MODERATION_TASKS["hard"]:
        cid = case["id"]
        d = decisions.get(cid, {})
        checks[f"{cid}_a"] = d.get("context_a_label", "").lower() == case["label_a"]
        checks[f"{cid}_b"] = d.get("context_b_label", "").lower() == case["label_b"]
    passed = sum(checks.values())
    return round(passed / len(checks), 2), f"{passed}/{len(checks)} context-aware decisions correct."


# ══════════════════════════════════════════════════════════════════════════════
# ENVIRONMENT
# ══════════════════════════════════════════════════════════════════════════════

class MetaEnvironment(Environment):
    """
    Meta Multi-Agent Environment.

    Supports 4 real-world agents across 12 tasks (easy/medium/hard each):
      - email_triage
      - code_review
      - data_cleaning
      - content_moderation

    Usage:
        env = MetaEnvironment()
        obs = env.reset()   # returns initial observation (no task set)

        # To run a specific task, pass task_id in the action:
        action = MetaAction(agent="email_triage", task_id="email_triage_easy", payload={...})
        obs = env.step(action)
        print(obs.reward, obs.feedback)
    """

    SUPPORTS_CONCURRENT_SESSIONS: bool = True

    def __init__(self):
        self._state = State(episode_id=str(uuid4()), step_count=0)
        self._current_task_id = None
        self._current_context = {}

    def reset(self) -> MetaObservation:
        """Reset the environment. Returns a welcome observation."""
        self._state = State(episode_id=str(uuid4()), step_count=0)
        self._current_task_id = None
        self._current_context = {}
        return MetaObservation(
            agent="meta",
            task_id="",
            difficulty="",
            context={},
            instructions=(
                "Welcome to Meta Multi-Agent Environment! "
                "Available agents: email_triage, code_review, data_cleaning, content_moderation. "
                "Each has tasks: <agent>_easy, <agent>_medium, <agent>_hard. "
                "Send an action with agent + task_id + payload to begin."
            ),
            feedback="Environment reset. Ready.",
            score=0.0,
            done=False,
            reward=0.0,
        )

    def _load_context(self, task_id: str):
        """Load the context data for a given task."""
        if task_id == "email_triage_easy":
            return {"email": random.choice(EMAILS["easy"])}, "easy"
        elif task_id == "email_triage_medium":
            return {"emails": EMAILS["medium"]}, "medium"
        elif task_id == "email_triage_hard":
            return {"email": EMAILS["hard"]}, "hard"
        elif task_id == "code_review_easy":
            return {"code": CODE_TASKS["easy"]["code"]}, "easy"
        elif task_id == "code_review_medium":
            return {"code": CODE_TASKS["medium"]["code"]}, "medium"
        elif task_id == "code_review_hard":
            return {"code": CODE_TASKS["hard"]["code"]}, "hard"
        elif task_id == "data_cleaning_easy":
            return {"data": DATA_TASKS["easy"]["data"]}, "easy"
        elif task_id == "data_cleaning_medium":
            return {"data": DATA_TASKS["medium"]["data"]}, "medium"
        elif task_id == "data_cleaning_hard":
            return {"data": DATA_TASKS["hard"]["data"]}, "hard"
        elif task_id == "content_moderation_easy":
            return {"posts": MODERATION_TASKS["easy"]}, "easy"
        elif task_id == "content_moderation_medium":
            return {"posts": MODERATION_TASKS["medium"]}, "medium"
        elif task_id == "content_moderation_hard":
            return {"cases": MODERATION_TASKS["hard"]}, "hard"
        else:
            raise ValueError(f"Unknown task_id: {task_id}")

    def _get_instructions(self, task_id: str) -> str:
        instructions = {
            "email_triage_easy": "Classify the email as 'spam', 'important', or 'newsletter'. Payload: {classification: str}",
            "email_triage_medium": "Prioritize 10 emails from most to least urgent. Payload: {order: [list of email ids]}",
            "email_triage_hard": "Draft a professional reply to the customer complaint. Payload: {reply: str}",
            "code_review_easy": "Find syntax errors in the code. Payload: {errors: [str]}",
            "code_review_medium": "Find all logical bugs and suggest fixes. Payload: {bugs: [{location, issue, fix}]}",
            "code_review_hard": "Identify all security vulnerabilities. Payload: {vulnerabilities: [{type, location, fix}]}",
            "data_cleaning_easy": "Find missing values and duplicate rows. Payload: {missing: [str], duplicates: [int]}",
            "data_cleaning_medium": "Identify data type issues and provide cleaned data. Payload: {issues: {field: description}, cleaned_data: [rows]}",
            "data_cleaning_hard": "Detect outliers and impute missing values. Payload: {outliers: [int], missing: [int], cleaned_data: [rows]}",
            "content_moderation_easy": "Classify each post as safe or harmful. Payload: {classifications: [{id, label}]}",
            "content_moderation_medium": "Detect subtle toxicity and sarcasm. Payload: {classifications: [{id, label, reason}]}",
            "content_moderation_hard": "Context-aware moderation — same text, two contexts. Payload: {decisions: [{id, context_a_label, context_b_label}]}",
        }
        return instructions.get(task_id, "Unknown task.")

    def _grade(self, task_id: str, payload: dict, context: dict):
        """Run the grader for a given task and return (score, feedback)."""
        if task_id == "email_triage_easy":       return grade_email_easy(payload, context)
        elif task_id == "email_triage_medium":   return grade_email_medium(payload, context)
        elif task_id == "email_triage_hard":     return grade_email_hard(payload, context)
        elif task_id == "code_review_easy":      return grade_code_easy(payload)
        elif task_id == "code_review_medium":    return grade_code_medium(payload)
        elif task_id == "code_review_hard":      return grade_code_hard(payload)
        elif task_id == "data_cleaning_easy":    return grade_data_easy(payload)
        elif task_id == "data_cleaning_medium":  return grade_data_medium(payload)
        elif task_id == "data_cleaning_hard":    return grade_data_hard(payload)
        elif task_id == "content_moderation_easy":   return grade_moderation_easy(payload)
        elif task_id == "content_moderation_medium": return grade_moderation_medium(payload)
        elif task_id == "content_moderation_hard":   return grade_moderation_hard(payload)
        return 0.0, "Unknown task."

    def step(self, action: MetaAction) -> MetaObservation:  # type: ignore[override]
        """Execute one step: load task context, grade action, return scored observation."""
        self._state.step_count += 1
        task_id = action.task_id

        # Load context fresh if task changed
        if task_id != self._current_task_id:
            self._current_context, difficulty = self._load_context(task_id)
            self._current_task_id = task_id
        else:
            _, difficulty = self._load_context(task_id)

        score, feedback = self._grade(task_id, action.payload, self._current_context)

        return MetaObservation(
            agent=action.agent,
            task_id=task_id,
            difficulty=difficulty,
            context=self._current_context,
            instructions=self._get_instructions(task_id),
            feedback=feedback,
            score=score,
            done=True,
            reward=score,
            metadata={"step": self._state.step_count, "task_id": task_id},
        )

    @property
    def state(self) -> State:
        return self._state
