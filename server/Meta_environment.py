"""
Meta Multi-Agent Environment v3.1

Five real-world AI agent domains, 24 tasks total:
  1. Email Triage        — classify, prioritize, draft replies, executive escalation
  2. Code Review         — syntax errors, logic bugs, security vulns, advanced audit
  3. Data Cleaning       — missing values, type normalization, outlier imputation, cross-dataset join
  4. Content Moderation  — explicit, subtle toxicity, context-aware, policy rulings
  5. Ticket Triage       — Jira-style priority, routing, incident analysis, PIR

Cross-agent chained tasks (4 total):
  cross_agent_chain          — email triage + code review
  cross_agent_email_data     — email priority + data cleaning
  cross_agent_code_email     — vulnerability detection + security disclosure email
  cross_agent_mod_escalation — content moderation + moderation notice drafting

v3.1 fixes:
  - Expert grader dispatch wired into _grade()
  - grade_data_easy accepts per-episode context (fixes 0-score on procedural rows)
  - All graders accept per-episode context (grade_mod_easy/medium, grade_data_hard)
"""

from __future__ import annotations

import json
import random
from typing import Any
from uuid import uuid4

from openenv.core.env_server.interfaces import Environment
from openenv.core.env_server.types import State

from models import MetaAction, MetaObservation

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


# ═══════════════════════════════════════════════════════════════════════════
# STATIC DATA  (fallback / determinism tests)
# ═══════════════════════════════════════════════════════════════════════════

EMAIL_MEDIUM_EMAILS = [
    {"id": "m1",  "subject": "[ALERT] Production server DOWN",                    "sender": "ops@company.com",       "body": "All services unresponsive since 2 AM. Revenue impact: $10k/min.",              "priority": 1,  "category": "critical"},
    {"id": "m2",  "subject": "Team lunch this Friday?",                            "sender": "colleague@company.com", "body": "Hey, thinking of doing a team lunch Friday. You in?",                        "priority": 9,  "category": "social"},
    {"id": "m3",  "subject": "Acme Corp contract renewal — URGENT",               "sender": "sales@company.com",     "body": "Acme contract expires Friday. They need signature or they walk.",              "priority": 2,  "category": "business"},
    {"id": "m4",  "subject": "Weekly SaaS digest",                                 "sender": "news@saasdigest.com",   "body": "Top SaaS stories this week...",                                              "priority": 10, "category": "newsletter"},
    {"id": "m5",  "subject": "[WARNING] Security alert: unusual login",            "sender": "security@company.com", "body": "Unauthorized login attempt from IP 45.33.32.156. Verify immediately.",         "priority": 1,  "category": "critical"},
    {"id": "m6",  "subject": "Invoice #INV-4521 overdue",                          "sender": "billing@vendor.com",   "body": "Invoice of $5,400 was due 3 days ago. Payment needed to avoid suspension.",  "priority": 3,  "category": "finance"},
    {"id": "m7",  "subject": "Happy Work Anniversary!",                            "sender": "hr@company.com",       "body": "Celebrating your 3 years with us!",                                          "priority": 10, "category": "social"},
    {"id": "m8",  "subject": "Q4 product launch deck — review needed",            "sender": "marketing@company.com","body": "Please review launch slides before Thursday. Launch is next Monday.",         "priority": 3,  "category": "business"},
    {"id": "m9",  "subject": "Free AI productivity webinar",                       "sender": "promo@webinar.io",     "body": "Join our free webinar on AI tools this Thursday.",                           "priority": 8,  "category": "newsletter"},
    {"id": "m10", "subject": "Legal: Partnership agreement needs signature TODAY", "sender": "legal@company.com",    "body": "The partnership agreement must be countersigned by EOD or the deal falls through.", "priority": 2, "category": "legal"},
]
EMAIL_MEDIUM_CORRECT_ORDER = ["m1", "m5", "m3", "m10", "m6", "m8", "m2", "m9", "m4", "m7"]

CODE_MEDIUM = {
    "code": (
        "def find_max(numbers):\n"
        "    max_val = 0\n"
        "    for num in numbers:\n"
        "        if num > max_val:\n"
        "            max_val = num\n"
        "    return max_val\n\n"
        "def get_user(users, user_id):\n"
        "    for user in users:\n"
        "        if user['id'] = user_id:\n"
        "            return user\n"
        "    return None\n\n"
        "def divide(a, b):\n"
        "    return a / b\n\n"
        "def process_list(items):\n"
        "    results = []\n"
        "    for i in range(len(items) + 1):\n"
        "        results.append(items[i] * 2)\n"
        "    return results\n"
    ),
}

CODE_HARD = {
    "code": (
        "import sqlite3\nimport subprocess\nimport pickle\nimport requests\nimport hashlib\nimport os\n\n"
        "def get_user_by_name(name):\n"
        "    conn = sqlite3.connect('users.db')\n"
        "    cursor = conn.cursor()\n"
        "    query = \"SELECT * FROM users WHERE name = '\" + name + \"'\"\n"
        "    cursor.execute(query)\n"
        "    return cursor.fetchall()\n\n"
        "def render_comment(comment):\n"
        "    return '<div class=\"comment\">' + comment + '</div>'\n\n"
        "def login(username, password):\n"
        "    conn = sqlite3.connect('users.db')\n"
        "    cursor = conn.cursor()\n"
        "    query = f\"SELECT * FROM users WHERE username='{username}' AND password='{password}'\"\n"
        "    cursor.execute(query)\n"
        "    return cursor.fetchone() is not None\n\n"
        "def run_report(report_name):\n"
        "    subprocess.call('generate_report.sh ' + report_name, shell=True)\n\n"
        "def load_user_data(data_bytes):\n"
        "    return pickle.loads(data_bytes)\n\n"
        "def check_password(stored_hash, input_password):\n"
        "    return stored_hash == hashlib.md5(input_password.encode()).hexdigest()\n\n"
        "def read_report_file(filename):\n"
        "    with open(f'/reports/{filename}') as f:\n"
        "        return f.read()\n\n"
        "def fetch_user_avatar(avatar_url):\n"
        "    response = requests.get(avatar_url)\n"
        "    return response.content\n"
    ),
}

DATA_EASY = {
    "data": [
        {"id": 1, "name": "Alice", "age": 30,   "email": "alice@example.com",   "salary": 70000},
        {"id": 2, "name": "Bob",   "age": None,  "email": "bob@example.com",     "salary": 85000},
        {"id": 3, "name": "Alice", "age": 30,    "email": "alice@example.com",   "salary": 70000},
        {"id": 4, "name": None,    "age": 25,    "email": "charlie@example.com", "salary": 60000},
        {"id": 5, "name": "Dave",  "age": 40,    "email": None,                  "salary": 90000},
        {"id": 6, "name": "Eve",   "age": 28,    "email": "eve@example.com",     "salary": None},
    ],
    "answers": {
        "missing":    ["age (row 2)", "name (row 4)", "email (row 5)", "salary (row 6)"],
        "duplicates": [1, 3],
    },
}

DATA_MEDIUM = {
    "data": [
        {"id": 1, "name": "Alice",   "age": "thirty",    "salary": "50000",   "join_date": "2020/01/15", "active": "yes"},
        {"id": 2, "name": "Bob",     "age": 25,           "salary": "$60,000", "join_date": "15-03-2021", "active": True},
        {"id": 3, "name": "Charlie", "age": "28",         "salary": "70000",   "join_date": "2019-07-22", "active": "TRUE"},
        {"id": 4, "name": "dave",    "age": 35,           "salary": "80,000",  "join_date": "2022/11/01", "active": False},
        {"id": 5, "name": "EVE",     "age": "twenty-two", "salary": "45000",   "join_date": "01/06/2023", "active": "no"},
    ],
    "issues": {
        "age":       "mixed types: strings 'thirty', '28', 'twenty-two' should be integers",
        "salary":    "inconsistent formats: '$60,000' and '80,000' have symbols/commas",
        "join_date": "three different date formats",
        "name":      "inconsistent casing: 'dave' lowercase, 'EVE' all caps",
        "active":    "mixed types: True/False booleans mixed with strings 'yes'/'no'/'TRUE'",
    },
}

DATA_HARD = {
    "data": [
        {"id": 1,  "value": 10.5}, {"id": 2,  "value": 11.2},
        {"id": 3,  "value": 10.8}, {"id": 4,  "value": 999.0},
        {"id": 5,  "value": 10.1}, {"id": 6,  "value": None},
        {"id": 7,  "value": 11.5}, {"id": 8,  "value": -500.0},
        {"id": 9,  "value": 10.9}, {"id": 10, "value": 11.0},
        {"id": 11, "value": None}, {"id": 12, "value": 10.7},
    ],
    "answers": {"outliers": {4, 8}, "missing": {6, 11}, "imputed_range": (10.0, 12.0)},
}

MOD_EASY = [
    {"id": "c1", "text": "I hate you so much, I want to hurt you!",            "label": "harmful"},
    {"id": "c2", "text": "Great weather today! Loving this sunshine",           "label": "safe"},
    {"id": "c3", "text": "All people from that group should be eliminated.",    "label": "harmful"},
    {"id": "c4", "text": "Can someone recommend a good Python beginner book?", "label": "safe"},
    {"id": "c5", "text": "You're an absolute idiot and nobody likes you.",     "label": "harmful"},
    {"id": "c6", "text": "I just finished a 5k run — feeling amazing!",        "label": "safe"},
    {"id": "c7", "text": "People like you should just disappear forever.",     "label": "harmful"},
]

MOD_MEDIUM = [
    {"id": "m1", "text": "Oh sure, like THAT went well. Classic genius move.",             "label": "harmful"},
    {"id": "m2", "text": "I'm so done with these people. Absolutely insufferable.",        "label": "harmful"},
    {"id": "m3", "text": "That presentation was... very unique.",                          "label": "safe"},
    {"id": "m4", "text": "Some people just shouldn't be allowed to have opinions.",       "label": "harmful"},
    {"id": "m5", "text": "Oh wow, another 'brilliant' idea from upper management",        "label": "harmful"},
    {"id": "m6", "text": "Congrats on the promotion! Well deserved!",                     "label": "safe"},
    {"id": "m7", "text": "Not everyone is cut out for this kind of work, clearly.",       "label": "harmful"},
    {"id": "m8", "text": "Thanks for the feedback, I'll take it into account.",           "label": "safe"},
]

MOD_HARD = [
    {"id": "h1", "text": "You should just disappear.",
     "context_a": {"platform": "gaming_chat",        "prior_message": "Your character died in the dungeon. Respawn?"},
     "label_a": "safe",
     "context_b": {"platform": "crisis_support_chat","prior_message": "I've been feeling worthless and invisible lately"},
     "label_b": "harmful"},
    {"id": "h2", "text": "We need to take these people out.",
     "context_a": {"platform": "hr_slack",           "prior_message": "Which team members should join the client dinner?"},
     "label_a": "safe",
     "context_b": {"platform": "extremist_forum",    "prior_message": "These immigrants are ruining our country."},
     "label_b": "harmful"},
    {"id": "h3", "text": "Let's eliminate the competition.",
     "context_a": {"platform": "business_slack",     "prior_message": "Q4 sales strategy meeting"},
     "label_a": "safe",
     "context_b": {"platform": "political_rally_chat","prior_message": "The opposition party is destroying our values."},
     "label_b": "harmful"},
    {"id": "h4", "text": "Finally, the great replacement is happening in our neighborhood.",
     "context_a": {"platform": "news_comments",      "prior_message": "New families moving into Maplewood as housing market cools."},
     "label_a": "harmful",
     "context_b": {"platform": "urban_planning_forum","prior_message": "Demographics shifting as millennials move to suburbs."},
     "label_b": "harmful"},
    {"id": "h5", "text": "Everyone should follow our example and do the same thing at noon tomorrow.",
     "context_a": {"platform": "community_events",   "prior_message": "We're all doing a neighborhood cleanup. Join us!"},
     "label_a": "safe",
     "context_b": {"platform": "extremist_channel",  "prior_message": "The government building is unguarded on weekends."},
     "label_b": "harmful"},
    {"id": "h6", "text": "These people breed like rabbits and will replace us if we don't act.",
     "context_a": {"platform": "biology_classroom",  "prior_message": "Comparing reproductive rates of different animal species"},
     "label_a": "harmful",
     "context_b": {"platform": "political_forum",    "prior_message": "Immigration policy discussion thread"},
     "label_b": "harmful"},
]

TICKET_MEDIUM_TICKETS = [
    {"id": "tk1", "title": "Database connection pool exhausted — prod down",    "type": "bug",            "team": "backend",  "priority_rank": 1},
    {"id": "tk2", "title": "Wrong currency symbol shown for EU customers",      "type": "bug",            "team": "frontend", "priority_rank": 3},
    {"id": "tk3", "title": "Add OAuth2 support for enterprise SSO",             "type": "feature_request","team": "backend",  "priority_rank": 5},
    {"id": "tk4", "title": "SSL cert expires in 48 hours on api.company.com",   "type": "bug",            "team": "devops",   "priority_rank": 2},
    {"id": "tk5", "title": "Invoice PDF generation fails for invoices > 50 lines","type": "bug",          "team": "backend",  "priority_rank": 4},
    {"id": "tk6", "title": "Redesign onboarding flow to reduce drop-off",       "type": "feature_request","team": "frontend", "priority_rank": 7},
    {"id": "tk7", "title": "Customer billed $0 instead of $299 — revenue leak", "type": "bug",            "team": "billing",  "priority_rank": 3},
    {"id": "tk8", "title": "Add CSV export for analytics dashboard",             "type": "feature_request","team": "frontend", "priority_rank": 8},
]
TICKET_MEDIUM_CORRECT_ORDER = ["tk1", "tk4", "tk2", "tk7", "tk5", "tk3", "tk6", "tk8"]
TICKET_MEDIUM_CORRECT_TEAMS = {
    "tk1": "backend", "tk2": "frontend", "tk3": "backend",
    "tk4": "devops",  "tk5": "backend",  "tk6": "frontend",
    "tk7": "billing", "tk8": "frontend",
}

TICKET_HARD_INCIDENT = {
    "tickets": [
        {"id": "INC-001", "title": "Payment service returning 503",           "created": "14:00", "service": "payment-service"},
        {"id": "INC-002", "title": "Database CPU at 100% on primary replica", "created": "14:01", "service": "postgres-primary"},
        {"id": "INC-003", "title": "Checkout flow failing for all users",     "created": "14:02", "service": "checkout-service"},
        {"id": "INC-004", "title": "Redis memory at 99% — evictions spiking", "created": "14:03", "service": "redis-cache"},
        {"id": "INC-005", "title": "Background job queue backed up 50k jobs", "created": "14:05", "service": "job-queue"},
        {"id": "INC-006", "title": "CDN edge nodes reporting origin timeouts","created": "14:06", "service": "cdn"},
    ],
    "expected": {
        "root_cause_keywords": ["database","postgres","cpu","memory","redis","cache","connection pool","exhausted","query","slow query","replica"],
        "affected_services": {"payment-service","checkout-service","postgres-primary","redis-cache"},
        "severity": "P1",
        "resolution_keywords": ["scale","replica","failover","restart","flush","cache","query","optimize","rollback","connection","limit"],
    },
}

CROSS_AGENT_CHAIN_CASES = [
    {"id": "ca1",
     "email": {"subject": "Bug report: payment processor crashing", "sender": "dev@company.com",
               "body": "Our payment processor keeps throwing a ZeroDivisionError. See attached code snippet."},
     "email_label": "important",
     "code": "def calculate_fee(amount, rate):\n    return amount / rate\n\ndef process_payment(amount, fee_rate):\n    fee = calculate_fee(amount, fee_rate)\n    return amount - fee\n",
     "code_bug": "zero_division",
     "code_bug_keywords": ["zero","division","divide","rate","denominator","fee_rate","guard"],
     "code_location": "calculate_fee"},
    {"id": "ca2",
     "email": {"subject": "Weekly newsletter: Python tips", "sender": "newsletter@pythonweekly.com",
               "body": "This week: list comprehensions, async patterns, and a buggy code snippet for you to fix!"},
     "email_label": "newsletter",
     "code": "def get_first(items):\n    return items[0]\n\ndef summarize(data):\n    total = sum(data)\n    first = get_first(data)\n    return total, first\n",
     "code_bug": "empty_list",
     "code_bug_keywords": ["empty","index","indexerror","list","bound","check","length","len","guard"],
     "code_location": "get_first"},
]

CROSS_AGENT_EMAIL_DATA_CASES = [
    {"id": "ced1",
     "email": {"subject": "[URGENT] Sales data export corrupted — board meeting tomorrow",
               "sender": "vp-sales@company.com",
               "body": "The Q4 sales export is corrupted. I need it fixed before the 9 AM board meeting tomorrow."},
     "email_priority": "critical",
     "attachment_data": [
         {"id": 1, "rep": "Alice",   "revenue": "150000",  "region": "NORTH", "closed_date": "2024/12/31"},
         {"id": 2, "rep": "bob",     "revenue": "$80,000", "region": "south", "closed_date": "31-12-2024"},
         {"id": 3, "rep": "Charlie", "revenue": None,      "region": "East",  "closed_date": "2024-12-30"},
         {"id": 4, "rep": "Diana",   "revenue": "120000",  "region": "WEST",  "closed_date": "12/30/2024"},
     ],
     "expected_issues": {"revenue": True, "region": True, "closed_date": True}},
]

CROSS_AGENT_CODE_EMAIL_CASES = [
    {"id": "cce1",
     "code": "def get_user_profile(user_id):\n    conn = sqlite3.connect('app.db')\n    query = \"SELECT * FROM users WHERE id = \" + user_id\n    cursor = conn.execute(query)\n    return cursor.fetchone()\n",
     "primary_vulnerability": "sql_injection",
     "location": "get_user_profile",
     "disclosure_keywords": ["sql injection","parameterized","vulnerability","security","patch","remediat","fix","urgent"]},
]

CROSS_AGENT_MOD_ESCALATION_CASES = [
    {"id": "cme1",
     "post": {"id": "p1", "text": "I know where you live and I will make you regret this post.",
              "platform": "social_media", "context": "Reply to a political opinion post"},
     "correct_label": "harmful", "should_escalate": True,
     "notice_keywords": ["violat","policy","removed","community","guidelines","threat","harm","prohibit"]},
    {"id": "cme2",
     "post": {"id": "p2", "text": "Great recipe! Can't wait to try this at home.",
              "platform": "cooking_forum", "context": "Reply to a pasta recipe post"},
     "correct_label": "safe", "should_escalate": False, "notice_keywords": []},
]


# ═══════════════════════════════════════════════════════════════════════════
# GRADERS
# ═══════════════════════════════════════════════════════════════════════════

def grade_email_easy(payload: dict, context: dict) -> tuple[float, str, dict]:
    correct = context["email"]["label"]
    given   = payload.get("classification", "").strip().lower()
    valid   = ["spam", "important", "newsletter"]
    if given == correct:
        return 1.0, f"[OK] Correct! '{correct}' is right.", {}
    if given in valid:
        return 0.0, f"[FAIL] Wrong. Expected '{correct}', got '{given}'.", {"classification": False}
    return 0.0, f"[FAIL] Invalid label '{given}'. Must be: spam | important | newsletter.", {"classification": False}


def _kendall_tau_score(order: list, correct: list) -> float:
    pos = {e: i for i, e in enumerate(correct)}
    concordant = discordant = 0
    for i in range(len(order)):
        for j in range(i + 1, len(order)):
            if order[i] not in pos or order[j] not in pos:
                continue
            if pos[order[i]] < pos[order[j]]:
                concordant += 1
            else:
                discordant += 1
    total = concordant + discordant
    return concordant / total if total > 0 else 0.0


def grade_email_medium(payload: dict, context: dict) -> tuple[float, str, dict]:
    order   = payload.get("order", [])
    correct = context.get("correct_order", EMAIL_MEDIUM_CORRECT_ORDER)
    if not order:
        return 0.0, "[FAIL] No order provided.", {}
    top2_ok = set(order[:2]) == {correct[0], correct[1]}
    top5_ok = order[:5] == correct[:5]
    full_ok = order == correct
    tau     = _kendall_tau_score(order, correct)
    hits    = sum(1 for i, e in enumerate(order) if i < len(correct) and e == correct[i])
    partial = {"top2_critical": top2_ok, "top5_correct": top5_ok, "full_order": full_ok}
    if full_ok:
        return 1.0, "[OK] Perfect prioritization!", partial
    if top5_ok:
        return round(0.8 + tau * 0.2, 2), f"[PARTIAL] Top 5 correct. Tau: {tau:.2f}.", partial
    if top2_ok:
        return round(max(0.5, tau), 2), f"[PARTIAL] Critical emails first. {hits}/10 exact. Tau: {tau:.2f}.", partial
    return round(tau * 0.8, 2), f"[ERROR] {hits}/10 exact positions correct. Tau: {tau:.2f}.", partial


def grade_email_hard(payload: dict, context: dict) -> tuple[float, str, dict]:
    reply    = payload.get("reply", "").lower()
    case     = context["email"]
    expected = case.get("expected_elements", {})
    checks: dict[str, bool] = {}
    for key, keywords in expected.items():
        if key == "professional_tone":
            checks[key] = len(reply) > 80 and not any(w in reply for w in ["not my problem", "whatever", "too bad", "deal with it"])
        else:
            checks[key] = keywords is not None and any(w in reply for w in keywords)
    passed   = sum(checks.values())
    total    = len(checks)
    score    = round(passed / total, 2)
    missing  = [k for k, v in checks.items() if not v]
    tag      = "[OK]" if score == 1.0 else "[PARTIAL]" if score >= 0.6 else "[ERROR]"
    feedback = f"{tag} {passed}/{total} reply elements present."
    if missing:
        feedback += f" Missing: {', '.join(missing)}."
    return score, feedback, checks


def grade_code_easy(payload: dict, context: dict) -> tuple[float, str, dict]:
    errors   = " ".join(str(e) for e in payload.get("errors", [])).lower()
    keywords = context.get("keywords", ["colon", "syntax"])
    found    = any(k in errors for k in keywords)
    if not payload.get("errors"):
        return 0.0, "[FAIL] No errors reported.", {"syntax_error_found": False}
    if found:
        return 1.0, "[OK] Syntax error correctly identified.", {"syntax_error_found": True}
    return 0.3, "[PARTIAL] Error mentioned but key issue not clearly described.", {"syntax_error_found": False}


def grade_code_medium(payload: dict) -> tuple[float, str, dict]:
    bugs   = payload.get("bugs", [])
    checks = {"max_val_init": False, "assignment_vs_eq": False, "zero_division": False, "off_by_one": False}
    for b in bugs:
        t   = (str(b.get("issue", "")) + str(b.get("location", "")) + str(b.get("fix", ""))).lower()
        loc = str(b.get("location", "")).lower()
        if loc == "find_max" or any(w in t for w in ["max_val","negative","minus","zero init","float('-inf')","all-negative","all negative","initialization","find_max"]):
            checks["max_val_init"] = True
        if loc == "get_user" or any(w in t for w in ["assignment","==","comparison","= user_id","single equal","get_user"]):
            checks["assignment_vs_eq"] = True
        if loc == "divide" or any(w in t for w in ["zero","division","divide","zerodivision","b == 0","divisor","denominator","div by zero"]):
            checks["zero_division"] = True
        if loc == "process_list" or any(w in t for w in ["off by one","off-by-one","index","range","len + 1","indexerror","out of bounds","boundary","len(items) + 1","process_list"]):
            checks["off_by_one"] = True
    passed   = sum(checks.values())
    score    = round(passed / 4, 2)
    tag      = "[OK]" if score == 1.0 else "[PARTIAL]" if score >= 0.5 else "[ERROR]"
    feedback = f"{tag} {passed}/4 bugs found."
    missing  = [k for k, v in checks.items() if not v]
    if missing:
        feedback += f" Missed: {', '.join(missing)}."
    return score, feedback, checks


def grade_code_hard(payload: dict) -> tuple[float, str, dict]:
    vulns  = payload.get("vulnerabilities", [])
    checks = {
        "sql_injection_get_user": False, "xss_render_comment": False,
        "sql_injection_login": False,    "command_injection": False,
        "insecure_deserialization": False,"timing_attack": False,
        "path_traversal": False,          "ssrf": False,
    }
    for v in vulns:
        vt  = str(v.get("type", "")).lower()
        loc = str(v.get("location", "")).lower()
        if "get_user" in loc or "get_user_by_name" in loc:
            checks["sql_injection_get_user"] = True
        if ("render" in loc or "comment" in loc) and any(w in vt for w in ["xss","cross","script","html","inject","sanitiz","encod","output"]):
            checks["xss_render_comment"] = True
        if "render" in loc and "comment" in loc:
            checks["xss_render_comment"] = True
        if "login" in loc:
            checks["sql_injection_login"] = True
        if ("report" in loc and any(w in vt for w in ["command","injection","shell"])) or ("report" in loc and "run" in loc):
            checks["command_injection"] = True
        if ("load" in loc and any(w in vt for w in ["pickle","deserializ","serial"])) or "load_user" in loc:
            checks["insecure_deserialization"] = True
        if "check_password" in loc or any(w in vt for w in ["timing","time","constant"]):
            checks["timing_attack"] = True
        if "read_report" in loc or "path" in vt or "traversal" in vt or "directory" in vt:
            checks["path_traversal"] = True
        if "fetch" in loc or "avatar" in loc or "ssrf" in vt or "request_forgery" in vt:
            checks["ssrf"] = True
    passed   = sum(checks.values())
    score    = round(passed / 8, 2)
    tag      = "[OK]" if score == 1.0 else "[PARTIAL]" if score >= 0.5 else "[ERROR]"
    feedback = f"{tag} {passed}/8 vulnerabilities found."
    missing  = [k for k, v in checks.items() if not v]
    if missing:
        feedback += f" Missed: {', '.join(missing)}."
    return score, feedback, checks


def grade_data_easy(payload: dict, context: dict = None) -> tuple[float, str, dict]:
    """Context-aware grader — works with both static DATA_EASY and procedural rows."""
    missing_given = [str(m).lower() for m in payload.get("missing", [])]
    dups_given    = set(str(d) for d in payload.get("duplicates", []))

    # Use per-episode answers if provided, else fall back to static DATA_EASY
    answers          = (context or {}).get("answers", DATA_EASY["answers"])
    correct_missing  = [m.lower() for m in answers.get("missing", DATA_EASY["answers"]["missing"])]
    correct_dups     = answers.get("duplicates", DATA_EASY["answers"]["duplicates"])

    # Grade each expected missing entry individually
    mc = {}
    for expected in correct_missing:
        # e.g. "age (row 3)" → field="age", row="3"
        clean = expected.replace("(", "").replace(")", "")
        parts = clean.split()
        field = parts[0] if parts else ""
        row   = parts[2] if len(parts) >= 3 else ""
        key   = f"{field}_row{row}"
        mc[key] = any(field in m and row in m for m in missing_given)

    dup_ok  = dups_given == {str(d) for d in correct_dups} or dups_given == set(correct_dups)
    passed  = sum(mc.values())
    total   = len(mc) if mc else 4
    score   = round((passed / total * 0.7) + (0.3 if dup_ok else 0.0), 2)
    tag     = "[OK]" if score == 1.0 else "[PARTIAL]" if score >= 0.5 else "[ERROR]"
    feedback = f"{tag} Missing: {passed}/{total}, Duplicates: {'[OK]' if dup_ok else '[FAIL]'}."
    return score, feedback, {**mc, "duplicates_correct": dup_ok}


def grade_data_medium(payload: dict) -> tuple[float, str, dict]:
    issues  = {k.lower(): str(v).lower() for k, v in payload.get("issues", {}).items()}
    cleaned = payload.get("cleaned_data", [])
    checks  = {
        "age_type":      "age" in issues and any(w in issues["age"] for w in ["string","integer","int","thirty","type","numeric","non-numeric","word","text","convert","mixed","number","twenty","str","should be int","not int","invalid"]),
        "salary_format": "salary" in issues and any(w in issues["salary"] for w in ["format","comma","$","inconsistent","symbol","currency","dollar","sign","strip","remove","clean"]),
        "date_format":   "join_date" in issues and any(w in issues["join_date"] for w in ["format","inconsistent","date","yyyy","dd-mm","standardize","iso","different","multiple"]),
        "name_case":     "name" in issues and any(w in issues["name"] for w in ["capital","case","dave","eve","lower","upper","casing","title","inconsistent","normalize"]),
        "active_type":   "active" in issues and any(w in issues["active"] for w in ["bool","string","yes","true","type","mixed","boolean","convert","inconsistent","str"]),
        "data_cleaned":  len(cleaned) == 5,
    }
    passed   = sum(checks.values())
    score    = round(passed / 6, 2)
    tag      = "[OK]" if score == 1.0 else "[PARTIAL]" if score >= 0.5 else "[ERROR]"
    return score, f"{tag} {passed}/6 data quality checks passed.", checks


def grade_data_hard(payload: dict, context: dict = None) -> tuple[float, str, dict]:
    outliers_given = set(int(x) for x in payload.get("outliers", []))
    missing_given  = set(int(x) for x in payload.get("missing", []))
    cleaned        = payload.get("cleaned_data", [])
    answers        = (context or {}).get("answers", DATA_HARD["answers"])
    correct_out    = answers.get("outliers",      DATA_HARD["answers"]["outliers"])
    correct_miss   = answers.get("missing",       DATA_HARD["answers"]["missing"])
    lo, hi         = answers.get("imputed_range", DATA_HARD["answers"]["imputed_range"])
    outlier_ok     = outliers_given == correct_out
    missing_ok     = missing_given  == correct_miss
    imputed_rows   = {r["id"]: r.get("value") for r in cleaned if r.get("id") in correct_miss}
    imputed_ok     = (
        all(v is not None and lo <= float(v) <= hi for v in imputed_rows.values())
        and len(imputed_rows) == len(correct_miss)
    )
    checks   = {"outliers_correct": outlier_ok, "missing_correct": missing_ok, "imputation_valid": imputed_ok}
    passed   = sum(checks.values())
    score    = round(passed / 3, 2)
    tag      = "[OK]" if score == 1.0 else "[PARTIAL]" if score >= 0.67 else "[ERROR]"
    return score, f"{tag} {passed}/3 data operations correct.", checks


def grade_mod_easy(payload: dict, context: dict = None) -> tuple[float, str, dict]:
    clf     = {c["id"]: c.get("label", "").lower() for c in payload.get("classifications", [])}
    posts   = (context or {}).get("posts", MOD_EASY)
    correct = {p["id"]: p["label"] for p in posts}
    per     = {id_: clf.get(id_) == label for id_, label in correct.items()}
    hits    = sum(per.values())
    score   = round(hits / len(correct), 2)
    tag     = "[OK]" if score == 1.0 else "[PARTIAL]" if score >= 0.7 else "[ERROR]"
    return score, f"{tag} {hits}/{len(correct)} posts correctly classified.", per


def grade_mod_medium(payload: dict, context: dict = None) -> tuple[float, str, dict]:
    clf     = {c["id"]: c.get("label", "").lower() for c in payload.get("classifications", [])}
    posts   = (context or {}).get("posts", MOD_MEDIUM)
    correct = {p["id"]: p["label"] for p in posts}
    per     = {id_: clf.get(id_) == label for id_, label in correct.items()}
    hits    = sum(per.values())
    score   = round(hits / len(correct), 2)
    tag     = "[OK]" if score == 1.0 else "[PARTIAL]" if score >= 0.6 else "[ERROR]"
    return score, f"{tag} {hits}/{len(correct)} subtle posts correctly classified.", per


def grade_mod_hard(payload: dict) -> tuple[float, str, dict]:
    decisions = {d["id"]: d for d in payload.get("decisions", [])}
    checks: dict[str, bool] = {}
    for case in MOD_HARD:
        cid = case["id"]
        d   = decisions.get(cid, {})
        checks[f"{cid}_context_a"] = d.get("context_a_label", "").lower() == case["label_a"]
        checks[f"{cid}_context_b"] = d.get("context_b_label", "").lower() == case["label_b"]
    passed = sum(checks.values())
    total  = len(checks)
    score  = round(passed / total, 2)
    tag    = "[OK]" if score == 1.0 else "[PARTIAL]" if score >= 0.5 else "[ERROR]"
    return score, f"{tag} {passed}/{total} context-aware decisions correct.", checks


def grade_ticket_easy(payload: dict, context: dict) -> tuple[float, str, dict]:
    ticket  = context["ticket"]
    p_given = payload.get("priority", "").strip().lower()
    c_given = payload.get("category", "").strip().lower()
    p_ok    = p_given == ticket["correct_priority"]
    c_ok    = c_given == ticket["correct_category"]
    checks  = {"priority_correct": p_ok, "category_correct": c_ok}
    score   = round(sum(checks.values()) / 2, 2)
    tag     = "[OK]" if score == 1.0 else "[PARTIAL]" if score == 0.5 else "[ERROR]"
    p_str   = "✓" if p_ok else f"✗ (expected {ticket['correct_priority']})"
    c_str   = "✓" if c_ok else f"✗ (expected {ticket['correct_category']})"
    return score, f"{tag} Priority: {p_str}, Category: {c_str}", checks


def grade_ticket_medium(payload: dict) -> tuple[float, str, dict]:
    order   = payload.get("order", [])
    assigns = payload.get("assignments", {})
    tau         = _kendall_tau_score(order, TICKET_MEDIUM_CORRECT_ORDER)
    top3_ok     = order[:3] == TICKET_MEDIUM_CORRECT_ORDER[:3]
    full_ok     = order == TICKET_MEDIUM_CORRECT_ORDER
    hits        = sum(1 for i, e in enumerate(order) if i < len(TICKET_MEDIUM_CORRECT_ORDER) and e == TICKET_MEDIUM_CORRECT_ORDER[i])
    order_score = 1.0 if full_ok else round(tau, 2)
    team_checks = {tid: assigns.get(tid) == team for tid, team in TICKET_MEDIUM_CORRECT_TEAMS.items()}
    team_hits   = sum(team_checks.values())
    team_score  = round(team_hits / len(TICKET_MEDIUM_CORRECT_TEAMS), 2)
    wrong_teams = [f"{tid}(got={assigns.get(tid)},expected={TICKET_MEDIUM_CORRECT_TEAMS[tid]})" for tid, ok in team_checks.items() if not ok]
    score       = round(order_score * 0.6 + team_score * 0.4, 2)
    checks      = {"top3_correct": top3_ok, "full_order": full_ok, "team_assignments": team_score == 1.0,
                   **{f"team_{tid}": ok for tid, ok in team_checks.items()}}
    tag         = "[OK]" if score >= 0.95 else "[PARTIAL]" if score >= 0.5 else "[ERROR]"
    feedback    = f"{tag} Order: {hits}/8 exact, Tau: {tau:.2f}, Teams: {team_hits}/8 correct."
    if wrong_teams:
        feedback += f" Wrong teams: {', '.join(wrong_teams)}."
    return score, feedback, checks


def grade_ticket_hard(payload: dict) -> tuple[float, str, dict]:
    root_cause = payload.get("root_cause", "").lower()
    resolution = [step.lower() for step in payload.get("resolution_steps", [])]
    affected   = {s.lower() for s in payload.get("affected_services", [])}
    severity   = payload.get("severity", "").upper()
    expected   = TICKET_HARD_INCIDENT["expected"]
    rc_hits    = sum(1 for kw in expected["root_cause_keywords"] if kw in root_cause)
    rc_ok      = rc_hits >= 3
    svc_hits   = len(affected & {s.lower() for s in expected["affected_services"]})
    svc_ok     = svc_hits >= 3
    sev_ok     = severity == expected["severity"]
    res_text   = " ".join(resolution)
    res_hits   = sum(1 for kw in expected["resolution_keywords"] if kw in res_text)
    res_ok     = res_hits >= 3 and len(resolution) >= 3
    checks     = {"root_cause_ok": rc_ok, "affected_services_ok": svc_ok, "severity_ok": sev_ok, "resolution_ok": res_ok}
    passed     = sum(checks.values())
    score      = round(passed / 4, 2)
    tag        = "[OK]" if score == 1.0 else "[PARTIAL]" if score >= 0.5 else "[ERROR]"
    return score, f"{tag} {passed}/4 incident checks. RC: {rc_hits}, Svcs: {svc_hits}/4, Steps: {len(resolution)}.", checks


def grade_cross_agent_chain(payload: dict, context: dict) -> tuple[float, str, dict]:
    case        = context["case"]
    email_given = payload.get("email_classification", "").strip().lower()
    email_ok    = email_given == case["email_label"]
    bugs        = payload.get("bugs", [])
    bug_ok      = False
    for b in bugs:
        t   = (str(b.get("issue", "")) + str(b.get("location", "")) + str(b.get("fix", ""))).lower()
        loc = str(b.get("location", "")).lower()
        if loc == case["code_location"].lower() or any(w in t for w in case["code_bug_keywords"]):
            bug_ok = True
            break
    checks   = {"email_correct": email_ok, "bug_found": bug_ok}
    passed   = sum(checks.values())
    score    = round(passed / 2, 2)
    tag      = "[OK]" if score == 1.0 else "[PARTIAL]" if score == 0.5 else "[ERROR]"
    feedback = f"{tag} {passed}/2 cross-agent checks passed."
    if not email_ok:
        feedback += f" Email: expected '{case['email_label']}', got '{email_given}'."
    if not bug_ok:
        feedback += f" Code bug in '{case['code_location']}' not identified."
    return score, feedback, checks


def grade_cross_agent_email_data(payload: dict, context: dict) -> tuple[float, str, dict]:
    case        = context["case"]
    priority    = payload.get("email_priority", "").strip().lower()
    raw_issues  = payload.get("data_issues", {})
    cleaned     = payload.get("cleaned_data", [])
    priority_ok = priority == case["email_priority"].lower()
    if isinstance(raw_issues, dict):
        if "field" in raw_issues and "issue" in raw_issues:
            data_issues = {str(raw_issues.get("field", "")).lower(): str(raw_issues.get("issue", "")).lower()}
        else:
            data_issues = {k.lower(): str(v).lower() for k, v in raw_issues.items()}
    elif isinstance(raw_issues, list):
        data_issues = {}
        for item in raw_issues:
            if isinstance(item, dict):
                f = str(item.get("field", "")).lower()
                v = str(item.get("issue", item.get("description", ""))).lower()
                if f:
                    data_issues[f] = v
    else:
        data_issues = {}
    issue_hits = sum(1 for field in case["expected_issues"] if field in data_issues)
    issues_ok  = issue_hits >= 2
    cleaned_ok = len(cleaned) == len(case["attachment_data"])
    checks     = {"priority_correct": priority_ok, "issues_identified": issues_ok, "data_cleaned": cleaned_ok}
    passed     = sum(checks.values())
    score      = round(passed / 3, 2)
    tag        = "[OK]" if score == 1.0 else "[PARTIAL]" if score >= 0.67 else "[ERROR]"
    feedback   = f"{tag} {passed}/3 email+data checks passed."
    if not issues_ok:
        feedback += f" Issues found: {issue_hits}/{len(case['expected_issues'])} fields."
    return score, feedback, checks


def grade_cross_agent_code_email(payload: dict, context: dict) -> tuple[float, str, dict]:
    case       = context["case"]
    vuln_type  = payload.get("vulnerability_type", "").lower()
    location   = payload.get("vulnerability_location", "").lower()
    email      = payload.get("disclosure_email", "").lower()
    type_ok    = case["primary_vulnerability"] in vuln_type or "sql" in vuln_type
    loc_ok     = case["location"].lower() in location
    email_hits = sum(1 for kw in case["disclosure_keywords"] if kw in email)
    email_ok   = email_hits >= 4 and len(email) >= 80
    checks     = {"vulnerability_identified": type_ok, "location_correct": loc_ok, "disclosure_email_quality": email_ok}
    passed     = sum(checks.values())
    score      = round(passed / 3, 2)
    tag        = "[OK]" if score == 1.0 else "[PARTIAL]" if score >= 0.67 else "[ERROR]"
    return score, f"{tag} {passed}/3 code+email checks. Email keywords: {email_hits}.", checks


def grade_cross_agent_mod_escalation(payload: dict, context: dict) -> tuple[float, str, dict]:
    case          = context["case"]
    label_given   = payload.get("content_label", "").strip().lower()
    escalate      = payload.get("escalate", None)
    notice        = payload.get("moderation_notice", "").lower()
    label_ok      = label_given == case["correct_label"]
    escalate_ok   = escalate == case["should_escalate"]
    if case["should_escalate"]:
        notice_ok = sum(1 for kw in case["notice_keywords"] if kw in notice) >= 3
    else:
        notice_ok = len(notice) == 0 or notice.strip() == ""
    checks   = {"label_correct": label_ok, "escalation_correct": escalate_ok, "notice_quality": notice_ok}
    passed   = sum(checks.values())
    score    = round(passed / 3, 2)
    tag      = "[OK]" if score == 1.0 else "[PARTIAL]" if score >= 0.67 else "[ERROR]"
    return score, f"{tag} {passed}/3 moderation+escalation checks passed.", checks


# ═══════════════════════════════════════════════════════════════════════════
# INSTRUCTIONS
# ═══════════════════════════════════════════════════════════════════════════

INSTRUCTIONS: dict[str, str] = {
    "email_triage_easy": "Classify the email as exactly one of: 'spam', 'important', or 'newsletter'.\nPayload: {\"classification\": \"spam\"}",
    "email_triage_medium": (
        "Prioritize the 10 emails from most urgent (first) to least urgent (last).\n"
        "Tier 1 CRITICAL: active production outages, security breaches\n"
        "Tier 2 URGENT: legal agreements expiring TODAY\n"
        "Tier 3 HIGH: overdue financial obligations\n"
        "Tier 4 HIGH: business deliverables with hard deadlines\n"
        "Tier 5 LOW: social (lunch, anniversaries)\n"
        "Tier 6 IGNORE: newsletters and promotional content\n"
        "Return ALL email IDs ordered most-to-least urgent.\n"
        "Payload: {\"order\": [\"m1\", \"m5\", ...]}"
    ),
    "email_triage_hard": "Draft a professional, empathetic reply to the customer complaint. Address ALL concerns.\nPayload: {\"reply\": \"<full reply text>\"}",
    "code_review_easy": "Identify the syntax error(s) in the Python code.\nPayload: {\"errors\": [\"description of syntax error\"]}",
    "code_review_medium": (
        "Find ALL 4 logical bugs — one per function. Report location, issue, and fix.\n"
        "  1. find_max — wrong initialization (fails all-negative lists)\n"
        "  2. get_user — = used instead of ==\n"
        "  3. divide — no zero-division guard\n"
        "  4. process_list — off-by-one in range\n"
        "Payload: {\"bugs\": [{\"location\": \"fn_name\", \"issue\": \"...\", \"fix\": \"...\"}]}"
    ),
    "code_review_hard": (
        "Identify ALL 8 security vulnerabilities:\n"
        "  1. sql_injection in get_user_by_name\n"
        "  2. xss in render_comment\n"
        "  3. sql_injection in login\n"
        "  4. command_injection in run_report\n"
        "  5. insecure_deserialization in load_user_data\n"
        "  6. timing_attack in check_password\n"
        "  7. path_traversal in read_report_file\n"
        "  8. ssrf in fetch_user_avatar\n"
        "Payload: {\"vulnerabilities\": [{\"type\": \"...\", \"location\": \"...\", \"severity\": \"...\", \"fix\": \"...\"}]}"
    ),
    "data_cleaning_easy": "Find all missing (null) values by field+row, and identify duplicate row IDs.\nPayload: {\"missing\": [\"age (row 2)\", \"name (row 4)\"], \"duplicates\": [1, 3]}",
    "data_cleaning_medium": "Identify all 5 data quality issues and return the fully cleaned dataset (5 rows).\nPayload: {\"issues\": {\"age\": \"mixed types...\"}, \"cleaned_data\": [...]}",
    "data_cleaning_hard": "Detect outliers (IQR/z-score), find missing values, impute, return cleaned dataset.\nPayload: {\"outliers\": [4, 8], \"missing\": [6, 11], \"cleaned_data\": [...]}",
    "content_moderation_easy": "Classify each post as 'safe' or 'harmful'.\nPayload: {\"classifications\": [{\"id\": \"c1\", \"label\": \"harmful\"}]}",
    "content_moderation_medium": (
        "Classify each post as 'safe' or 'harmful'. Watch for sarcasm, subtle toxicity, implicit hostility.\n"
        "HARMFUL: sarcasm that mocks/demeans ('Classic genius move'), passive aggression ('not cut out for this')\n"
        "SAFE: mild opinion without a target ('very unique' about a presentation), genuine positivity\n"
        "Payload: {\"classifications\": [{\"id\": \"m1\", \"label\": \"harmful\", \"reason\": \"...\"}]}"
    ),
    "content_moderation_hard": (
        "Each case shows the SAME text in TWO different contexts. Determine the correct label for EACH context.\n"
        "RULES:\n"
        "  1. Dehumanizing language and dog-whistles are ALWAYS harmful regardless of context.\n"
        "  2. Comparing humans to animals, 'replacement' rhetoric = always harmful in ALL contexts.\n"
        "  3. Ambiguous phrasing ('disappear', 'take out', 'eliminate the competition') = context-dependent.\n"
        "Payload: {\"decisions\": [{\"id\": \"h1\", \"context_a_label\": \"safe\", \"context_b_label\": \"harmful\"}]}"
    ),
    "ticket_triage_easy": "Classify the support ticket: priority (critical/high/medium/low) and category (bug/feature_request/question/billing).\nPayload: {\"priority\": \"critical\", \"category\": \"bug\"}",
    "ticket_triage_medium": (
        "Order 8 tickets by priority (most urgent first) and assign each to the correct team.\n"
        "backend=server APIs/DB, frontend=browser UI/display, devops=SSL/infra, billing=charges/refunds\n"
        "Payload: {\"order\": [\"tk1\", \"tk4\", ...], \"assignments\": {\"tk1\": \"backend\", ...}}"
    ),
    "ticket_triage_hard": "Analyse the linked incident tickets: root cause, resolution steps, affected services, severity (P1-P4).\nPayload: {\"root_cause\": \"...\", \"resolution_steps\": [...], \"affected_services\": [...], \"severity\": \"P1\"}",
    "cross_agent_chain": "TWO skills:\n  1. Classify the email: 'spam', 'important', or 'newsletter'\n  2. Find the main bug in the attached code (location + issue + fix)\nPayload: {\"email_classification\": \"important\", \"bugs\": [{\"location\": \"fn\", \"issue\": \"...\", \"fix\": \"...\"}]}",
    "cross_agent_email_data": (
        "TWO skills:\n"
        "  1. Classify the email urgency: 'critical', 'high', 'medium', 'low'\n"
        "  2. Identify data quality issues and return cleaned data\n"
        "IMPORTANT: data_issues must use field names as keys: {\"revenue\": \"...\", \"region\": \"...\"}\n"
        "Payload: {\"email_priority\": \"critical\", \"data_issues\": {\"revenue\": \"...\", \"region\": \"...\"}, \"cleaned_data\": [...]}"
    ),
    "cross_agent_code_email": "TWO skills:\n  1. Identify the primary security vulnerability type and its location\n  2. Draft a professional security disclosure email (min 80 chars)\nPayload: {\"vulnerability_type\": \"sql_injection\", \"vulnerability_location\": \"fn_name\", \"disclosure_email\": \"...\"}",
    "cross_agent_mod_escalation": "TWO skills:\n  1. Classify the content as 'safe' or 'harmful'\n  2. Decide escalation (true/false) and draft a moderation notice if harmful\nPayload: {\"content_label\": \"harmful\", \"escalate\": true, \"moderation_notice\": \"Your post was removed because...\"}",
    **EXPERT_INSTRUCTIONS,
}


# ═══════════════════════════════════════════════════════════════════════════
# ENVIRONMENT
# ═══════════════════════════════════════════════════════════════════════════

class MetaEnvironment(Environment):
    """Meta Multi-Agent Environment v3.1 — 24 tasks across 5 domains + expert tier."""

    SUPPORTS_CONCURRENT_SESSIONS: bool = True

    def __init__(self) -> None:
        self._state                  = State(episode_id=str(uuid4()), step_count=0)
        self._current_task_id: str | None          = None
        self._current_agent_context: dict          = {}
        self._current_grader_context: dict         = {}
        self._episode_scores: list[float]          = []
        self._attempt_counts: dict[str, int]       = {}
        self._first_attempt_scores: dict[str, float] = {}

    def reset(self) -> MetaObservation:
        self._state                  = State(episode_id=str(uuid4()), step_count=0)
        self._current_task_id        = None
        self._current_agent_context  = {}
        self._current_grader_context = {}
        self._episode_scores         = []
        self._attempt_counts         = {}
        self._first_attempt_scores   = {}
        return MetaObservation(
            agent="meta", task_id="", difficulty="", context={},
            instructions=(
                "Welcome to Meta v3.1 — 24 tasks across 5 domains + expert tier.\n"
                "Agents: email_triage | code_review | data_cleaning | content_moderation | ticket_triage | cross_agent\n"
                "Use GET /tasks for all task IDs and payload schemas."
            ),
            feedback="Environment reset. Ready for episode.",
            score=0.0, partial_credits={}, done=False, reward=0.0,
        )

    def _deterministic_choice(self, variants: list, task_id: str) -> Any:
        idx = hash(self._state.episode_id + task_id) % len(variants)
        return variants[idx]

    def _load_context(self, task_id: str) -> tuple[dict, dict, str]:
        """Return (agent_ctx, grader_ctx, difficulty). Fully deterministic."""

        # ── Email Triage ──────────────────────────────────────────────────
        if task_id == "email_triage_easy":
            agent_ctx, grader_ctx = gen_email_easy(self._state.episode_id)
            return agent_ctx, grader_ctx, "easy"
        if task_id == "email_triage_medium":
            agent_ctx, grader_ctx = gen_email_medium(self._state.episode_id)
            return agent_ctx, grader_ctx, "medium"
        if task_id == "email_triage_hard":
            agent_ctx, grader_ctx = gen_email_hard(self._state.episode_id)
            return agent_ctx, grader_ctx, "hard"
        if task_id == "email_triage_expert":
            ctx = {k: v for k, v in EMAIL_EXPERT_CONTEXT.items()}
            return ctx, ctx, "expert"

        # ── Code Review ───────────────────────────────────────────────────
        if task_id == "code_review_easy":
            agent_ctx, grader_ctx = gen_code_easy(self._state.episode_id)
            return agent_ctx, grader_ctx, "easy"
        if task_id == "code_review_medium":
            ctx = {"code": CODE_MEDIUM["code"]}
            return ctx, ctx, "medium"
        if task_id == "code_review_hard":
            ctx = {"code": CODE_HARD["code"]}
            return ctx, ctx, "hard"
        if task_id == "code_review_expert":
            agent_ctx  = {"code": CODE_EXPERT_CONTEXT["code"], "vulnerability_count": CODE_EXPERT_CONTEXT["vulnerability_count"]}
            grader_ctx = CODE_EXPERT_CONTEXT
            return agent_ctx, grader_ctx, "expert"

        # ── Data Cleaning ─────────────────────────────────────────────────
        if task_id == "data_cleaning_easy":
            agent_ctx, grader_ctx = gen_data_easy(self._state.episode_id)
            return agent_ctx, grader_ctx, "easy"
        if task_id == "data_cleaning_medium":
            agent_ctx, grader_ctx = gen_data_medium(self._state.episode_id)
            return agent_ctx, grader_ctx, "medium"
        if task_id == "data_cleaning_hard":
            agent_ctx, grader_ctx = gen_data_hard(self._state.episode_id)
            return agent_ctx, grader_ctx, "hard"
        if task_id == "data_cleaning_expert":
            return DATA_EXPERT_CONTEXT, DATA_EXPERT_CONTEXT, "expert"

        # ── Content Moderation ────────────────────────────────────────────
        if task_id == "content_moderation_easy":
            agent_ctx, grader_ctx = gen_mod_easy(self._state.episode_id)
            return agent_ctx, grader_ctx, "easy"
        if task_id == "content_moderation_medium":
            agent_ctx, grader_ctx = gen_mod_medium(self._state.episode_id)
            return agent_ctx, grader_ctx, "medium"
        if task_id == "content_moderation_hard":
            agent_ctx  = {"cases": [{k: v for k, v in c.items() if k not in ("label_a", "label_b")} for c in MOD_HARD]}
            grader_ctx = {"cases": MOD_HARD}
            return agent_ctx, grader_ctx, "hard"
        if task_id == "content_moderation_expert":
            return MOD_EXPERT_CONTEXT, MOD_EXPERT_CONTEXT, "expert"

        # ── Ticket Triage ─────────────────────────────────────────────────
        if task_id == "ticket_triage_easy":
            agent_ctx, grader_ctx = gen_ticket_easy(self._state.episode_id)
            return agent_ctx, grader_ctx, "easy"
        if task_id == "ticket_triage_medium":
            agent_ctx  = {"tickets": [{k: v for k, v in t.items() if k not in ("priority_rank", "team")} for t in TICKET_MEDIUM_TICKETS]}
            grader_ctx = {"tickets": TICKET_MEDIUM_TICKETS}
            return agent_ctx, grader_ctx, "medium"
        if task_id == "ticket_triage_hard":
            ctx = {"incident_tickets": TICKET_HARD_INCIDENT["tickets"]}
            return ctx, ctx, "hard"
        if task_id == "ticket_triage_expert":
            return TICKET_EXPERT_CONTEXT, TICKET_EXPERT_CONTEXT, "expert"

        # ── Cross-Agent ───────────────────────────────────────────────────
        if task_id == "cross_agent_chain":
            case       = self._deterministic_choice(CROSS_AGENT_CHAIN_CASES, task_id)
            agent_ctx  = {"email": case["email"], "code": case["code"]}
            grader_ctx = {"case": case}
            return agent_ctx, grader_ctx, "hard"
        if task_id == "cross_agent_email_data":
            case       = CROSS_AGENT_EMAIL_DATA_CASES[0]
            agent_ctx  = {"email": case["email"], "attachment_data": case["attachment_data"]}
            grader_ctx = {"case": case}
            return agent_ctx, grader_ctx, "hard"
        if task_id == "cross_agent_code_email":
            case       = CROSS_AGENT_CODE_EMAIL_CASES[0]
            agent_ctx  = {"code": case["code"]}
            grader_ctx = {"case": case}
            return agent_ctx, grader_ctx, "hard"
        if task_id == "cross_agent_mod_escalation":
            case       = self._deterministic_choice(CROSS_AGENT_MOD_ESCALATION_CASES, task_id)
            agent_ctx  = {"post": case["post"]}
            grader_ctx = {"case": case}
            return agent_ctx, grader_ctx, "hard"

        raise ValueError(f"Unknown task_id: '{task_id}'. Use GET /tasks to see valid IDs.")

    def _grade(self, task_id: str, payload: dict, grader_context: dict) -> tuple[float, str, dict]:
        if task_id == "email_triage_easy":           return grade_email_easy(payload, grader_context)
        if task_id == "email_triage_medium":         return grade_email_medium(payload, grader_context)
        if task_id == "email_triage_hard":           return grade_email_hard(payload, grader_context)
        if task_id == "email_triage_expert":         return grade_email_expert(payload)
        if task_id == "code_review_easy":            return grade_code_easy(payload, grader_context)
        if task_id == "code_review_medium":          return grade_code_medium(payload)
        if task_id == "code_review_hard":            return grade_code_hard(payload)
        if task_id == "code_review_expert":          return grade_code_expert(payload)
        if task_id == "data_cleaning_easy":          return grade_data_easy(payload, grader_context)
        if task_id == "data_cleaning_medium":        return grade_data_medium(payload)
        if task_id == "data_cleaning_hard":          return grade_data_hard(payload, grader_context)
        if task_id == "data_cleaning_expert":        return grade_data_expert(payload)
        if task_id == "content_moderation_easy":     return grade_mod_easy(payload, grader_context)
        if task_id == "content_moderation_medium":   return grade_mod_medium(payload, grader_context)
        if task_id == "content_moderation_hard":     return grade_mod_hard(payload)
        if task_id == "content_moderation_expert":   return grade_mod_expert(payload)
        if task_id == "ticket_triage_easy":          return grade_ticket_easy(payload, grader_context)
        if task_id == "ticket_triage_medium":        return grade_ticket_medium(payload)
        if task_id == "ticket_triage_hard":          return grade_ticket_hard(payload)
        if task_id == "ticket_triage_expert":        return grade_ticket_expert(payload)
        if task_id == "cross_agent_chain":           return grade_cross_agent_chain(payload, grader_context)
        if task_id == "cross_agent_email_data":      return grade_cross_agent_email_data(payload, grader_context)
        if task_id == "cross_agent_code_email":      return grade_cross_agent_code_email(payload, grader_context)
        if task_id == "cross_agent_mod_escalation":  return grade_cross_agent_mod_escalation(payload, grader_context)
        return 0.0, "Unknown task.", {}

    def _compute_reward(self, score: float, task_id: str, attempt: int) -> float:
        base = score
        if score == 1.0 and attempt == 1:
            base = min(base + 0.05, 1.0)
        if attempt == 2:
            prev = self._first_attempt_scores.get(task_id, 0.0)
            if score > prev:
                base = min(base + (score - prev) * 0.1, 1.0)
        if score == 0.0 and attempt > 1:
            base = max(base - 0.05, 0.0)
        return round(base, 3)

    def step(self, action: MetaAction) -> MetaObservation:
        self._state.step_count += 1

        try:
            data    = json.loads(action.message)
            agent   = data.get("agent", "")
            task_id = data.get("task_id", "")
            payload = data.get("payload", {})
        except Exception as e:
            return MetaObservation(
                agent="error", task_id="", difficulty="", context={},
                instructions='message must be valid JSON: {"agent":"...","task_id":"...","payload":{...}}',
                feedback=f"JSON parse error: {e}",
                score=0.0, partial_credits={}, done=True, reward=0.0,
            )

        # Probe — load context without grading
        if not payload or payload == {"_probe": True}:
            try:
                agent_ctx, grader_ctx, difficulty = self._load_context(task_id)
                self._current_agent_context  = agent_ctx
                self._current_grader_context = grader_ctx
                self._current_task_id        = task_id
            except ValueError:
                difficulty = ""
                agent_ctx  = {}
            is_probe = payload == {"_probe": True}
            return MetaObservation(
                agent=agent, task_id=task_id, difficulty=difficulty,
                context=agent_ctx,
                instructions=INSTRUCTIONS.get(task_id, "Use GET /tasks for payload schema."),
                feedback="Probe: context loaded. Submit a real payload to get scored." if is_probe else "Empty payload. Use GET /tasks.",
                score=0.0, partial_credits={}, done=is_probe,
                reward=-0.1 if not is_probe else 0.0,
            )

        # Load context
        try:
            if task_id != self._current_task_id:
                agent_ctx, grader_ctx, difficulty = self._load_context(task_id)
                self._current_agent_context  = agent_ctx
                self._current_grader_context = grader_ctx
                self._current_task_id        = task_id
                self._attempt_counts[task_id] = 0
            else:
                agent_ctx  = self._current_agent_context
                grader_ctx = self._current_grader_context
                _, __, difficulty = self._load_context(task_id)
        except ValueError as e:
            return MetaObservation(
                agent=agent, task_id=task_id, difficulty="", context={},
                instructions="Use GET /tasks to see valid task IDs.",
                feedback=str(e), score=0.0, partial_credits={}, done=True, reward=0.0,
            )

        # Grade
        score, feedback, partial_credits = self._grade(task_id, payload, grader_ctx)

        attempt = self._attempt_counts.get(task_id, 0) + 1
        self._attempt_counts[task_id] = attempt
        reward = self._compute_reward(score, task_id, attempt)

        if attempt == 1 and score < 1.0:
            self._first_attempt_scores[task_id] = score
            done   = False
            reward = score * 0.5
            missed = [k for k, v in partial_credits.items() if not v]
            feedback += f" [RETRY AVAILABLE] Score: {score:.2f}. Improve on: {missed}"
        elif attempt == 1 and score == 1.0:
            done = True
            self._episode_scores.append(score)
        else:
            score  = max(score, self._first_attempt_scores.get(task_id, 0.0))
            done   = True
            reward = self._compute_reward(score, task_id, attempt)
            self._episode_scores.append(score)
            feedback += f" [FINAL] Best score from 2 attempts: {score:.2f}."

        return MetaObservation(
            agent=agent, task_id=task_id, difficulty=difficulty,
            context=agent_ctx,
            instructions=INSTRUCTIONS.get(task_id, ""),
            feedback=feedback, score=score,
            partial_credits=partial_credits, done=done, reward=reward,
            metadata={
                "step":              self._state.step_count,
                "attempt":           attempt,
                "episode_avg_score": round(sum(self._episode_scores) / len(self._episode_scores), 3)
                                     if self._episode_scores else 0.0,
            },
        )

    @property
    def state(self) -> State:
        return self._state