"""
Meta Multi-Agent Environment v3.0

Five real-world AI agent domains, 16 tasks total:
  1. Email Triage        — classify, prioritize, draft replies
  2. Code Review         — syntax errors, logic bugs, security vulnerabilities (harder)
  3. Data Cleaning       — missing values, type normalization, outlier imputation
  4. Content Moderation  — explicit, subtle toxicity, context-aware moderation (harder)
  5. Ticket Triage       — NEW: Jira-style bug ticket priority, routing, incident analysis

Cross-agent chained tasks (4 total):
  cross_agent_chain          — email triage + code review
  cross_agent_email_data     — email priority + data cleaning
  cross_agent_code_email     — vulnerability detection + security disclosure email
  cross_agent_mod_escalation — content moderation + moderation notice drafting

v3.0 improvements:
  - Deterministic context loading via episode_id hash (no random.choice breaking reproducibility)
  - 5th domain: Ticket Triage (Jira-style)
  - 4 cross-agent chained tasks (was 1)
  - Harder hard tasks: 8 vulnerabilities in code_hard, adversarial content_mod_hard
  - Trajectory-aware reward shaping with improvement bonuses
  - Clean single-import pattern (PYTHONPATH set correctly in Dockerfile)
  - Full type hints on all grader functions
"""

from __future__ import annotations

import json
import random
from typing import Any
from uuid import uuid4

from openenv.core.env_server.interfaces import Environment
from openenv.core.env_server.types import State

from models import MetaAction, MetaObservation


# ═════════════════════════════════════════════════════════════════════════════
# DATA
# ═════════════════════════════════════════════════════════════════════════════

EMAIL_EASY_VARIANTS = [
    {
        "id": "e1",
        "subject": "You won $1,000,000!!!",
        "sender": "promo@totally-legit-lottery.com",
        "body": "Click here to claim your prize now! Limited time offer!",
        "label": "spam",
    },
    {
        "id": "e2",
        "subject": "Q3 Budget Review — Urgent Action Required",
        "sender": "cfo@company.com",
        "body": "Please review the attached Q3 budget before our board meeting tomorrow at 9 AM.",
        "label": "important",
    },
    {
        "id": "e3",
        "subject": "Your weekly digest from Medium",
        "sender": "noreply@medium.com",
        "body": "Top stories this week: AI trends, Python tips, and startup news.",
        "label": "newsletter",
    },
    {
        "id": "e4",
        "subject": "CONGRATULATIONS! iPhone 15 Pro is yours!",
        "sender": "winner@prize-alert.net",
        "body": "You have been selected. Click now to claim your free iPhone!",
        "label": "spam",
    },
    {
        "id": "e5",
        "subject": "Action Required: Sign the NDA before Friday",
        "sender": "legal@company.com",
        "body": "Please sign the attached NDA before Friday's partnership meeting. Deadline is strict.",
        "label": "important",
    },
    {
        "id": "e6",
        "subject": "TechCrunch Newsletter — March 2026",
        "sender": "newsletter@techcrunch.com",
        "body": "This week's top stories in tech, AI, and startups.",
        "label": "newsletter",
    },
]

EMAIL_MEDIUM_EMAILS = [
    {"id": "m1",  "subject": "[ALERT] Production server DOWN",          "sender": "ops@company.com",      "body": "All services unresponsive since 2 AM. Revenue impact: $10k/min.",             "priority": 1,  "category": "critical"},
    {"id": "m2",  "subject": "Team lunch this Friday?",                  "sender": "colleague@company.com","body": "Hey, thinking of doing a team lunch Friday. You in?",                         "priority": 9,  "category": "social"},
    {"id": "m3",  "subject": "Acme Corp contract renewal — URGENT",      "sender": "sales@company.com",    "body": "Acme contract expires Friday. They need signature or they walk.",               "priority": 2,  "category": "business"},
    {"id": "m4",  "subject": "Weekly SaaS digest",                       "sender": "news@saasdigest.com",  "body": "Top SaaS stories this week...",                                               "priority": 10, "category": "newsletter"},
    {"id": "m5",  "subject": "[WARNING] Security alert: unusual login",  "sender": "security@company.com","body": "Unauthorized login attempt from IP 45.33.32.156. Verify immediately.",          "priority": 1,  "category": "critical"},
    {"id": "m6",  "subject": "Invoice #INV-4521 overdue",                "sender": "billing@vendor.com",   "body": "Invoice of $5,400 was due 3 days ago. Payment needed to avoid suspension.",   "priority": 3,  "category": "finance"},
    {"id": "m7",  "subject": "Happy Work Anniversary!",                  "sender": "hr@company.com",       "body": "Celebrating your 3 years with us!",                                           "priority": 10, "category": "social"},
    {"id": "m8",  "subject": "Q4 product launch deck — review needed",   "sender": "marketing@company.com","body": "Please review launch slides before Thursday. Launch is next Monday.",          "priority": 3,  "category": "business"},
    {"id": "m9",  "subject": "Free AI productivity webinar",             "sender": "promo@webinar.io",     "body": "Join our free webinar on AI tools this Thursday.",                            "priority": 8,  "category": "newsletter"},
    {"id": "m10", "subject": "Legal: Partnership agreement needs signature TODAY", "sender": "legal@company.com", "body": "The partnership agreement must be countersigned by EOD or the deal falls through.", "priority": 2, "category": "legal"},
]

EMAIL_MEDIUM_CORRECT_ORDER = ["m1", "m5", "m3", "m10", "m6", "m8", "m2", "m9", "m4", "m7"]

EMAIL_HARD_CASES = [
    {
        "id": "h1",
        "subject": "Completely unacceptable — Order #78234",
        "sender": "furious.customer@email.com",
        "body": (
            "I have been a loyal customer for 5 years and I am absolutely furious. "
            "My order #78234 arrived broken for the SECOND time this month. "
            "Your support team has been dismissive and unhelpful every time I called. "
            "I demand a full refund, a replacement sent overnight, AND compensation. "
            "If this is not resolved within 24 hours, I will file a consumer court complaint."
        ),
        "expected_elements": {
            "acknowledge_frustration": ["understand", "frustrat", "disappoint", "concern", "feel"],
            "apologize": ["sorry", "apologize", "apology", "sincerely"],
            "offer_refund": ["refund", "money back", "full refund"],
            "offer_replacement": ["replacement", "replace", "new order", "send another", "overnight"],
            "provide_timeline": ["24 hours", "48 hours", "within", "today", "tomorrow", "business day"],
            "professional_tone": None,
            "compensation_acknowledged": ["compensat", "inconvenience", "make it right", "goodwill"],
        },
    },
    {
        "id": "h2",
        "subject": "Billing error — charged twice for subscription",
        "sender": "billing.complaint@customer.com",
        "body": (
            "I was charged twice for my annual subscription this month — once on March 1st "
            "and again on March 15th. I have the bank statements as proof. "
            "This is a clear billing error on your end. I need an immediate refund of the "
            "duplicate charge and a written confirmation that this won't happen again. "
            "I've been waiting 2 weeks for a response from your support team."
        ),
        "expected_elements": {
            "acknowledge_frustration": ["understand", "concern", "apologize", "sorry"],
            "apologize": ["sorry", "apologize", "apology"],
            "offer_refund": ["refund", "reimburse", "credit"],
            "confirm_investigation": ["investigat", "look into", "check", "review", "verify"],
            "provide_timeline": ["within", "hours", "days", "business day"],
            "professional_tone": None,
            "written_confirmation": ["confirm", "written", "email confirmation", "receipt"],
        },
    },
]

CODE_EASY_VARIANTS = [
    {
        "code": "def calculate_average(numbers):\n    total = 0\n    for num in numbers\n        total += num\n    return total / len(numbers)\n",
        "hint": "missing colon after for statement",
        "keywords": ["colon", "for loop", "syntax", "for statement"],
    },
    {
        "code": "def greet(name)\n    print(f'Hello, {name}!')\n\ngreet('World')\n",
        "hint": "missing colon after function definition",
        "keywords": ["colon", "def", "function", "syntax"],
    },
    {
        "code": "numbers = [1, 2, 3, 4, 5]\nif len(numbers) > 0\n    print('Not empty')\n",
        "hint": "missing colon after if statement",
        "keywords": ["colon", "if statement", "syntax"],
    },
]

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
    "bugs": {
        "max_val_init":     "find_max initializes max_val=0, fails for all-negative lists",
        "assignment_vs_eq": "get_user uses = (assignment) instead of == (comparison)",
        "zero_division":    "divide() has no guard against division by zero",
        "off_by_one":       "process_list iterates range(len(items)+1) causing IndexError",
    },
}

# HARDER: 8 vulnerabilities now (was 5) — frontier models won't trivially score 1.0
CODE_HARD = {
    "code": (
        "import sqlite3\n"
        "import subprocess\n"
        "import pickle\n"
        "import requests\n"
        "import hashlib\n"
        "import os\n\n"
        "# Vulnerability 1: SQL injection\n"
        "def get_user_by_name(name):\n"
        "    conn = sqlite3.connect('users.db')\n"
        "    cursor = conn.cursor()\n"
        "    query = \"SELECT * FROM users WHERE name = '\" + name + \"'\"\n"
        "    cursor.execute(query)\n"
        "    return cursor.fetchall()\n\n"
        "# Vulnerability 2: XSS\n"
        "def render_comment(comment):\n"
        "    return '<div class=\"comment\">' + comment + '</div>'\n\n"
        "# Vulnerability 3: SQL injection\n"
        "def login(username, password):\n"
        "    conn = sqlite3.connect('users.db')\n"
        "    cursor = conn.cursor()\n"
        "    query = f\"SELECT * FROM users WHERE username='{username}' AND password='{password}'\"\n"
        "    cursor.execute(query)\n"
        "    return cursor.fetchone() is not None\n\n"
        "# Vulnerability 4: Command injection\n"
        "def run_report(report_name):\n"
        "    subprocess.call('generate_report.sh ' + report_name, shell=True)\n\n"
        "# Vulnerability 5: Insecure deserialization\n"
        "def load_user_data(data_bytes):\n"
        "    return pickle.loads(data_bytes)\n\n"
        "# Vulnerability 6: Timing attack on password comparison\n"
        "def check_password(stored_hash, input_password):\n"
        "    return stored_hash == hashlib.md5(input_password.encode()).hexdigest()\n\n"
        "# Vulnerability 7: Path traversal\n"
        "def read_report_file(filename):\n"
        "    with open(f'/reports/{filename}') as f:\n"
        "        return f.read()\n\n"
        "# Vulnerability 8: SSRF\n"
        "def fetch_user_avatar(avatar_url):\n"
        "    response = requests.get(avatar_url)\n"
        "    return response.content\n"
    ),
    "vulnerabilities": {
        "sql_injection_get_user":      {"type": "sql_injection",          "location": "get_user_by_name",  "severity": "critical"},
        "xss_render_comment":          {"type": "xss",                    "location": "render_comment",    "severity": "high"},
        "sql_injection_login":         {"type": "sql_injection",          "location": "login",             "severity": "critical"},
        "command_injection":           {"type": "command_injection",      "location": "run_report",        "severity": "critical"},
        "insecure_deserialization":    {"type": "insecure_deserialization","location": "load_user_data",   "severity": "high"},
        "timing_attack":               {"type": "timing_attack",          "location": "check_password",    "severity": "medium"},
        "path_traversal":              {"type": "path_traversal",         "location": "read_report_file",  "severity": "high"},
        "ssrf":                        {"type": "ssrf",                   "location": "fetch_user_avatar", "severity": "high"},
    },
}

DATA_EASY = {
    "data": [
        {"id": 1, "name": "Alice",  "age": 30,   "email": "alice@example.com",   "salary": 70000},
        {"id": 2, "name": "Bob",    "age": None,  "email": "bob@example.com",     "salary": 85000},
        {"id": 3, "name": "Alice",  "age": 30,    "email": "alice@example.com",   "salary": 70000},
        {"id": 4, "name": None,     "age": 25,    "email": "charlie@example.com", "salary": 60000},
        {"id": 5, "name": "Dave",   "age": 40,    "email": None,                  "salary": 90000},
        {"id": 6, "name": "Eve",    "age": 28,    "email": "eve@example.com",     "salary": None},
    ],
    "answers": {
        "missing":    ["age (row 2)", "name (row 4)", "email (row 5)", "salary (row 6)"],
        "duplicates": [1, 3],
    },
}

DATA_MEDIUM = {
    "data": [
        {"id": 1, "name": "Alice",   "age": "thirty",     "salary": "50000",   "join_date": "2020/01/15", "active": "yes"},
        {"id": 2, "name": "Bob",     "age": 25,            "salary": "$60,000", "join_date": "15-03-2021", "active": True},
        {"id": 3, "name": "Charlie", "age": "28",          "salary": "70000",   "join_date": "2019-07-22", "active": "TRUE"},
        {"id": 4, "name": "dave",    "age": 35,            "salary": "80,000",  "join_date": "2022/11/01", "active": False},
        {"id": 5, "name": "EVE",     "age": "twenty-two",  "salary": "45000",   "join_date": "01/06/2023", "active": "no"},
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
        {"id": 1,  "value": 10.5},  {"id": 2,  "value": 11.2},
        {"id": 3,  "value": 10.8},  {"id": 4,  "value": 999.0},
        {"id": 5,  "value": 10.1},  {"id": 6,  "value": None},
        {"id": 7,  "value": 11.5},  {"id": 8,  "value": -500.0},
        {"id": 9,  "value": 10.9},  {"id": 10, "value": 11.0},
        {"id": 11, "value": None},  {"id": 12, "value": 10.7},
    ],
    "answers": {
        "outliers":      {4, 8},
        "missing":       {6, 11},
        "imputed_range": (10.0, 12.0),
    },
}

MOD_EASY = [
    {"id": "c1", "text": "I hate you so much, I want to hurt you!",             "label": "harmful"},
    {"id": "c2", "text": "Great weather today! Loving this sunshine",            "label": "safe"},
    {"id": "c3", "text": "All people from that group should be eliminated.",     "label": "harmful"},
    {"id": "c4", "text": "Can someone recommend a good Python beginner book?",  "label": "safe"},
    {"id": "c5", "text": "You're an absolute idiot and nobody likes you.",      "label": "harmful"},
    {"id": "c6", "text": "I just finished a 5k run — feeling amazing!",         "label": "safe"},
    {"id": "c7", "text": "People like you should just disappear forever.",      "label": "harmful"},
]

MOD_MEDIUM = [
    {"id": "m1", "text": "Oh sure, like THAT went well. Classic genius move.",              "label": "harmful"},
    {"id": "m2", "text": "I'm so done with these people. Absolutely insufferable.",         "label": "harmful"},
    {"id": "m3", "text": "That presentation was... very unique.",                           "label": "safe"},
    {"id": "m4", "text": "Some people just shouldn't be allowed to have opinions.",        "label": "harmful"},
    {"id": "m5", "text": "Oh wow, another 'brilliant' idea from upper management",         "label": "harmful"},
    {"id": "m6", "text": "Congrats on the promotion! Well deserved!",                      "label": "safe"},
    {"id": "m7", "text": "Not everyone is cut out for this kind of work, clearly.",        "label": "harmful"},
    {"id": "m8", "text": "Thanks for the feedback, I'll take it into account.",            "label": "safe"},
]

# HARDER: adversarial cases including dog-whistles and coordinated inauthentic patterns
MOD_HARD = [
    {
        "id": "h1",
        "text": "You should just disappear.",
        "context_a": {"platform": "gaming_chat",       "prior_message": "Your character died in the dungeon. Respawn?"},
        "label_a": "safe",
        "context_b": {"platform": "crisis_support_chat","prior_message": "I've been feeling worthless and invisible lately"},
        "label_b": "harmful",
    },
    {
        "id": "h2",
        "text": "We need to take these people out.",
        "context_a": {"platform": "hr_slack",          "prior_message": "Which team members should join the client dinner?"},
        "label_a": "safe",
        "context_b": {"platform": "extremist_forum",   "prior_message": "These immigrants are ruining our country."},
        "label_b": "harmful",
    },
    {
        "id": "h3",
        "text": "Let's eliminate the competition.",
        "context_a": {"platform": "business_slack",    "prior_message": "Q4 sales strategy meeting"},
        "label_a": "safe",
        "context_b": {"platform": "political_rally_chat","prior_message": "The opposition party is destroying our values."},
        "label_b": "harmful",
    },
    # NEW adversarial cases — much harder
    {
        "id": "h4",
        "text": "Finally, the great replacement is happening in our neighborhood.",
        "context_a": {"platform": "news_comments",     "prior_message": "New families moving into Maplewood as housing market cools."},
        "label_a": "harmful",   # dog-whistle regardless of context
        "context_b": {"platform": "urban_planning_forum","prior_message": "Demographics shifting as millennials move to suburbs."},
        "label_b": "harmful",   # still a white-nationalist dog-whistle
    },
    {
        "id": "h5",
        "text": "Everyone should follow our example and do the same thing at noon tomorrow.",
        "context_a": {"platform": "community_events",  "prior_message": "We're all doing a neighborhood cleanup. Join us!"},
        "label_a": "safe",
        "context_b": {"platform": "extremist_channel", "prior_message": "The government building is unguarded on weekends."},
        "label_b": "harmful",   # coordinated inauthentic / incitement
    },
    {
        "id": "h6",
        "text": "These people breed like rabbits and will replace us if we don't act.",
        "context_a": {"platform": "biology_classroom", "prior_message": "Comparing reproductive rates of different animal species"},
        "label_a": "harmful",   # dehumanizing regardless — not biology
        "context_b": {"platform": "political_forum",   "prior_message": "Immigration policy discussion thread"},
        "label_b": "harmful",
    },
]

# ── NEW: Ticket Triage Domain ─────────────────────────────────────────────────

TICKET_EASY_VARIANTS = [
    {
        "id": "t1",
        "title": "App crashes on login for all users",
        "description": "Since the 2.3.1 deploy, 100% of login attempts throw a 500 error. Users cannot access the platform.",
        "reporter": "ops-monitoring@company.com",
        "correct_priority": "critical",
        "correct_category": "bug",
    },
    {
        "id": "t2",
        "title": "Add dark mode to the dashboard",
        "description": "Multiple users have requested a dark mode option. Would improve accessibility.",
        "reporter": "product@company.com",
        "correct_priority": "low",
        "correct_category": "feature_request",
    },
    {
        "id": "t3",
        "title": "How do I export my data as CSV?",
        "description": "I can't find the export button anywhere in the UI. Where is it?",
        "reporter": "user123@customer.com",
        "correct_priority": "low",
        "correct_category": "question",
    },
    {
        "id": "t4",
        "title": "Charged twice for last month's invoice",
        "description": "Account #AC-4421 shows two charges of $299 on March 1st. Please refund duplicate.",
        "reporter": "finance@customer.com",
        "correct_priority": "high",
        "correct_category": "billing",
    },
]

TICKET_MEDIUM_TICKETS = [
    {"id": "tk1", "title": "Database connection pool exhausted — prod down",   "type": "bug",            "team": "backend",  "priority_rank": 1},
    {"id": "tk2", "title": "Wrong currency symbol shown for EU customers",     "type": "bug",            "team": "frontend", "priority_rank": 3},
    {"id": "tk3", "title": "Add OAuth2 support for enterprise SSO",            "type": "feature_request","team": "backend",  "priority_rank": 5},
    {"id": "tk4", "title": "SSL cert expires in 48 hours on api.company.com",  "type": "bug",            "team": "devops",   "priority_rank": 2},
    {"id": "tk5", "title": "Invoice PDF generation fails for invoices > 50 lines","type": "bug",         "team": "backend",  "priority_rank": 4},
    {"id": "tk6", "title": "Redesign onboarding flow to reduce drop-off",      "type": "feature_request","team": "frontend", "priority_rank": 7},
    {"id": "tk7", "title": "Customer billed $0 instead of $299 — revenue leak","type": "bug",            "team": "billing",  "priority_rank": 3},
    {"id": "tk8", "title": "Add CSV export for analytics dashboard",            "type": "feature_request","team": "frontend", "priority_rank": 8},
]

TICKET_MEDIUM_CORRECT_ORDER = ["tk1", "tk4", "tk2", "tk7", "tk5", "tk3", "tk6", "tk8"]
TICKET_MEDIUM_CORRECT_TEAMS = {
    "tk1": "backend", "tk2": "frontend", "tk3": "backend",
    "tk4": "devops",  "tk5": "backend",  "tk6": "frontend",
    "tk7": "billing", "tk8": "frontend",
}

TICKET_HARD_INCIDENT = {
    "tickets": [
        {"id": "INC-001", "title": "Payment service returning 503",          "created": "14:00", "service": "payment-service"},
        {"id": "INC-002", "title": "Database CPU at 100% on primary replica","created": "14:01", "service": "postgres-primary"},
        {"id": "INC-003", "title": "Checkout flow failing for all users",    "created": "14:02", "service": "checkout-service"},
        {"id": "INC-004", "title": "Redis memory at 99% — evictions spiking","created": "14:03", "service": "redis-cache"},
        {"id": "INC-005", "title": "Background job queue backed up 50k jobs","created": "14:05", "service": "job-queue"},
        {"id": "INC-006", "title": "CDN edge nodes reporting origin timeouts","created": "14:06", "service": "cdn"},
    ],
    "expected": {
        "root_cause_keywords": [
            "database", "postgres", "cpu", "memory", "redis", "cache",
            "connection pool", "exhausted", "query", "slow query", "replica",
        ],
        "affected_services": {"payment-service", "checkout-service", "postgres-primary", "redis-cache"},
        "severity": "P1",
        "resolution_keywords": [
            "scale", "replica", "failover", "restart", "flush", "cache",
            "query", "optimize", "rollback", "connection", "limit",
        ],
    },
}

# ── Cross-agent data ──────────────────────────────────────────────────────────

CROSS_AGENT_CHAIN_CASES = [
    {
        "id": "ca1",
        "email": {
            "subject": "Bug report: payment processor crashing",
            "sender": "dev@company.com",
            "body": "Our payment processor keeps throwing a ZeroDivisionError in production. See attached code snippet.",
        },
        "email_label": "important",
        "code": (
            "def calculate_fee(amount, rate):\n"
            "    return amount / rate\n\n"
            "def process_payment(amount, fee_rate):\n"
            "    fee = calculate_fee(amount, fee_rate)\n"
            "    return amount - fee\n"
        ),
        "code_bug": "zero_division",
        "code_bug_keywords": ["zero", "division", "divide", "rate", "denominator", "fee_rate", "guard"],
        "code_location": "calculate_fee",
    },
    {
        "id": "ca2",
        "email": {
            "subject": "Weekly newsletter: Python tips",
            "sender": "newsletter@pythonweekly.com",
            "body": "This week: list comprehensions, async patterns, and a buggy code snippet for you to fix!",
        },
        "email_label": "newsletter",
        "code": (
            "def get_first(items):\n"
            "    return items[0]\n\n"
            "def summarize(data):\n"
            "    total = sum(data)\n"
            "    first = get_first(data)\n"
            "    return total, first\n"
        ),
        "code_bug": "empty_list",
        "code_bug_keywords": ["empty", "index", "indexerror", "list", "bound", "check", "length", "len", "guard"],
        "code_location": "get_first",
    },
]

CROSS_AGENT_EMAIL_DATA_CASES = [
    {
        "id": "ced1",
        "email": {
            "subject": "[URGENT] Sales data export corrupted — board meeting tomorrow",
            "sender": "vp-sales@company.com",
            "body": "The Q4 sales export is corrupted. I need it fixed before the 9 AM board meeting tomorrow.",
        },
        "email_priority": "critical",
        "attachment_data": [
            {"id": 1, "rep": "Alice",  "revenue": "150000",   "region": "NORTH", "closed_date": "2024/12/31"},
            {"id": 2, "rep": "bob",    "revenue": "$80,000",  "region": "south", "closed_date": "31-12-2024"},
            {"id": 3, "rep": "Charlie","revenue": None,       "region": "East",  "closed_date": "2024-12-30"},
            {"id": 4, "rep": "Diana",  "revenue": "120000",   "region": "WEST",  "closed_date": "12/30/2024"},
        ],
        "expected_issues": {"revenue": True, "region": True, "closed_date": True},
    },
]

CROSS_AGENT_CODE_EMAIL_CASES = [
    {
        "id": "cce1",
        "code": (
            "def get_user_profile(user_id):\n"
            "    conn = sqlite3.connect('app.db')\n"
            "    query = \"SELECT * FROM users WHERE id = \" + user_id\n"
            "    cursor = conn.execute(query)\n"
            "    return cursor.fetchone()\n"
        ),
        "primary_vulnerability": "sql_injection",
        "location": "get_user_profile",
        "disclosure_keywords": [
            "sql injection", "parameterized", "vulnerability",
            "security", "patch", "remediat", "fix", "urgent",
        ],
    },
]

CROSS_AGENT_MOD_ESCALATION_CASES = [
    {
        "id": "cme1",
        "post": {
            "id": "p1",
            "text": "I know where you live and I will make you regret this post.",
            "platform": "social_media",
            "context": "Reply to a political opinion post",
        },
        "correct_label": "harmful",
        "should_escalate": True,
        "notice_keywords": [
            "violat", "policy", "removed", "community", "guidelines",
            "threat", "harm", "prohibit",
        ],
    },
    {
        "id": "cme2",
        "post": {
            "id": "p2",
            "text": "Great recipe! Can't wait to try this at home.",
            "platform": "cooking_forum",
            "context": "Reply to a pasta recipe post",
        },
        "correct_label": "safe",
        "should_escalate": False,
        "notice_keywords": [],
    },
]


# ═════════════════════════════════════════════════════════════════════════════
# GRADERS
# ═════════════════════════════════════════════════════════════════════════════

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
    """
    Kendall's tau-based ordering score.
    Counts concordant pairs (relative order matches) vs total pairs.
    Much fairer than exact position matching — rewards getting the overall
    priority ranking right even when a few adjacent items swap.
    Score range: 0.0 (fully reversed) to 1.0 (perfect order).
    """
    n = len(correct)
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
    correct = EMAIL_MEDIUM_CORRECT_ORDER
    if not order:
        return 0.0, "[FAIL] No order provided.", {}
    top2_ok  = set(order[:2]) == {"m1", "m5"}
    top5_ok  = order[:5] == correct[:5]
    full_ok  = order == correct
    tau      = _kendall_tau_score(order, correct)
    hits     = sum(1 for i, e in enumerate(order) if i < len(correct) and e == correct[i])
    partial  = {"top2_critical": top2_ok, "top5_correct": top5_ok, "full_order": full_ok}
    if full_ok:
        return 1.0, "[OK] Perfect prioritization!", partial
    if top5_ok:
        score = round(0.8 + tau * 0.2, 2)
        return score, f"[PARTIAL] Top 5 correct. Kendall tau: {tau:.2f}.", partial
    if top2_ok:
        # Tau-based score: 0.5 minimum when criticals placed first, scaled up by pair agreement
        score = round(max(0.5, tau), 2)
        return score, f"[PARTIAL] Critical emails (m1, m5) first. {hits}/10 exact positions. Tau: {tau:.2f}.", partial
    score = round(tau * 0.8, 2)
    return score, f"[ERROR] {hits}/10 exact positions correct. Kendall tau: {tau:.2f}.", partial


def grade_email_hard(payload: dict, context: dict) -> tuple[float, str, dict]:
    reply    = payload.get("reply", "").lower()
    case     = context["email"]
    expected = case.get("expected_elements", {})
    checks: dict[str, bool] = {}
    for key, keywords in expected.items():
        if key == "professional_tone":
            checks[key] = (
                len(reply) > 80
                and not any(w in reply for w in ["not my problem", "whatever", "too bad", "deal with it"])
            )
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
        if loc == "find_max" or any(w in t for w in ["max_val", "negative", "minus", "zero init", "float('-inf')", "all-negative", "all negative", "initialization", "find_max"]):
            checks["max_val_init"] = True
        if loc == "get_user" or any(w in t for w in ["assignment", "==", "comparison", "= user_id", "single equal", "get_user"]):
            checks["assignment_vs_eq"] = True
        if loc == "divide" or any(w in t for w in ["zero", "division", "divide", "zerodivision", "b == 0", "divisor", "denominator", "div by zero"]):
            checks["zero_division"] = True
        if loc == "process_list" or any(w in t for w in ["off by one", "off-by-one", "index", "range", "len + 1", "indexerror", "out of bounds", "boundary", "len(items) + 1", "process_list"]):
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
    """Now grading 8 vulnerabilities — significantly harder than before."""
    vulns  = payload.get("vulnerabilities", [])
    checks = {
        "sql_injection_get_user":   False,
        "xss_render_comment":       False,
        "sql_injection_login":      False,
        "command_injection":        False,
        "insecure_deserialization": False,
        "timing_attack":            False,
        "path_traversal":           False,
        "ssrf":                     False,
    }
    for v in vulns:
        vt  = str(v.get("type", "")).lower()
        loc = str(v.get("location", "")).lower()
        if "get_user" in loc or "get_user_by_name" in loc:
            checks["sql_injection_get_user"] = True
        if ("render" in loc or "comment" in loc) and any(w in vt for w in ["xss", "cross", "script", "html", "inject", "sanitiz", "encod", "output"]):
            checks["xss_render_comment"] = True
        if "render" in loc and "comment" in loc:
            checks["xss_render_comment"] = True
        if "login" in loc:
            checks["sql_injection_login"] = True
        if "report" in loc and any(w in vt for w in ["command", "injection", "shell"]):
            checks["command_injection"] = True
        if "report" in loc and "run" in loc:
            checks["command_injection"] = True
        if "load" in loc and any(w in vt for w in ["pickle", "deserializ", "serial"]):
            checks["insecure_deserialization"] = True
        if "load_user" in loc:
            checks["insecure_deserialization"] = True
        if "check_password" in loc or any(w in vt for w in ["timing", "time", "constant"]):
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


def grade_data_easy(payload: dict) -> tuple[float, str, dict]:
    missing_given = [str(m).lower() for m in payload.get("missing", [])]
    dups_given    = set(str(d) for d in payload.get("duplicates", []))
    mc = {
        "age_row2":    any("age" in m and "2" in m for m in missing_given),
        "name_row4":   any("name" in m and "4" in m for m in missing_given),
        "email_row5":  any("email" in m and "5" in m for m in missing_given),
        "salary_row6": any("salary" in m and "6" in m for m in missing_given),
    }
    dup_ok   = dups_given in [{"1", "3"}, {"3", "1"}] or dups_given == {1, 3}
    passed   = sum(mc.values())
    score    = round((passed / 4 * 0.7) + (0.3 if dup_ok else 0.0), 2)
    tag      = "[OK]" if score == 1.0 else "[PARTIAL]" if score >= 0.5 else "[ERROR]"
    feedback = f"{tag} Missing: {passed}/4, Duplicates: {'[OK]' if dup_ok else '[FAIL]'}."
    return score, feedback, {**mc, "duplicates_correct": dup_ok}


def grade_data_medium(payload: dict) -> tuple[float, str, dict]:
    issues  = {k.lower(): str(v).lower() for k, v in payload.get("issues", {}).items()}
    cleaned = payload.get("cleaned_data", [])
    checks  = {
        "age_type": (
            "age" in issues and any(w in issues["age"] for w in [
                "string", "integer", "int", "thirty", "type", "numeric",
                "non-numeric", "word", "text", "convert", "mixed", "number",
                "twenty", "str", "should be int", "not int", "invalid",
            ])
        ),
        "salary_format": (
            "salary" in issues and any(w in issues["salary"] for w in [
                "format", "comma", "$", "inconsistent", "symbol", "currency",
                "dollar", "sign", "strip", "remove", "clean",
            ])
        ),
        "date_format": (
            "join_date" in issues and any(w in issues["join_date"] for w in [
                "format", "inconsistent", "date", "yyyy", "dd-mm",
                "standardize", "iso", "different", "multiple",
            ])
        ),
        "name_case": (
            "name" in issues and any(w in issues["name"] for w in [
                "capital", "case", "dave", "eve", "lower", "upper",
                "casing", "title", "inconsistent", "normalize",
            ])
        ),
        "active_type": (
            "active" in issues and any(w in issues["active"] for w in [
                "bool", "string", "yes", "true", "type", "mixed",
                "boolean", "convert", "inconsistent", "str",
            ])
        ),
        "data_cleaned": len(cleaned) == 5,
    }
    passed   = sum(checks.values())
    score    = round(passed / 6, 2)
    tag      = "[OK]" if score == 1.0 else "[PARTIAL]" if score >= 0.5 else "[ERROR]"
    feedback = f"{tag} {passed}/6 data quality checks passed."
    return score, feedback, checks


def grade_data_hard(payload: dict) -> tuple[float, str, dict]:
    outliers_given = set(int(x) for x in payload.get("outliers", []))
    missing_given  = set(int(x) for x in payload.get("missing", []))
    cleaned        = payload.get("cleaned_data", [])
    correct_out    = DATA_HARD["answers"]["outliers"]
    correct_miss   = DATA_HARD["answers"]["missing"]
    lo, hi         = DATA_HARD["answers"]["imputed_range"]
    outlier_ok     = outliers_given == correct_out
    missing_ok     = missing_given == correct_miss
    imputed_rows   = {r["id"]: r.get("value") for r in cleaned if r.get("id") in correct_miss}
    imputed_ok     = (
        all(v is not None and lo <= float(v) <= hi for v in imputed_rows.values())
        and len(imputed_rows) == len(correct_miss)
    )
    checks   = {"outliers_correct": outlier_ok, "missing_correct": missing_ok, "imputation_valid": imputed_ok}
    passed   = sum(checks.values())
    score    = round(passed / 3, 2)
    tag      = "[OK]" if score == 1.0 else "[PARTIAL]" if score >= 0.67 else "[ERROR]"
    feedback = f"{tag} {passed}/3 data operations correct."
    return score, feedback, checks


def grade_mod_easy(payload: dict) -> tuple[float, str, dict]:
    clf     = {c["id"]: c.get("label", "").lower() for c in payload.get("classifications", [])}
    correct = {p["id"]: p["label"] for p in MOD_EASY}
    per     = {id_: clf.get(id_) == label for id_, label in correct.items()}
    hits    = sum(per.values())
    score   = round(hits / len(correct), 2)
    tag     = "[OK]" if score == 1.0 else "[PARTIAL]" if score >= 0.7 else "[ERROR]"
    return score, f"{tag} {hits}/{len(correct)} posts correctly classified.", per


def grade_mod_medium(payload: dict) -> tuple[float, str, dict]:
    clf     = {c["id"]: c.get("label", "").lower() for c in payload.get("classifications", [])}
    correct = {p["id"]: p["label"] for p in MOD_MEDIUM}
    per     = {id_: clf.get(id_) == label for id_, label in correct.items()}
    hits    = sum(per.values())
    score   = round(hits / len(correct), 2)
    tag     = "[OK]" if score == 1.0 else "[PARTIAL]" if score >= 0.6 else "[ERROR]"
    return score, f"{tag} {hits}/{len(correct)} subtle posts correctly classified.", per


def grade_mod_hard(payload: dict) -> tuple[float, str, dict]:
    """Now 6 cases (12 checks) — adversarial dog-whistles included."""
    decisions = {d["id"]: d for d in payload.get("decisions", [])}
    checks: dict[str, bool] = {}
    for case in MOD_HARD:
        cid = case["id"]
        d   = decisions.get(cid, {})
        checks[f"{cid}_context_a"] = d.get("context_a_label", "").lower() == case["label_a"]
        checks[f"{cid}_context_b"] = d.get("context_b_label", "").lower() == case["label_b"]
    passed   = sum(checks.values())
    total    = len(checks)
    score    = round(passed / total, 2)
    tag      = "[OK]" if score == 1.0 else "[PARTIAL]" if score >= 0.5 else "[ERROR]"
    return score, f"{tag} {passed}/{total} context-aware decisions correct.", checks


def grade_ticket_easy(payload: dict, context: dict) -> tuple[float, str, dict]:
    ticket   = context["ticket"]
    p_given  = payload.get("priority", "").strip().lower()
    c_given  = payload.get("category", "").strip().lower()
    p_ok     = p_given == ticket["correct_priority"]
    c_ok     = c_given == ticket["correct_category"]
    checks   = {"priority_correct": p_ok, "category_correct": c_ok}
    score    = round(sum(checks.values()) / 2, 2)
    tag      = "[OK]" if score == 1.0 else "[PARTIAL]" if score == 0.5 else "[ERROR]"
    p_str    = "✓" if p_ok else f"✗ (expected {ticket['correct_priority']})"
    c_str    = "✓" if c_ok else f"✗ (expected {ticket['correct_category']})"
    feedback = f"{tag} Priority: {p_str}, Category: {c_str}"
    return score, feedback, checks


def grade_ticket_medium(payload: dict) -> tuple[float, str, dict]:
    order   = payload.get("order", [])
    assigns = payload.get("assignments", {})
    correct_order = TICKET_MEDIUM_CORRECT_ORDER
    correct_teams = TICKET_MEDIUM_CORRECT_TEAMS
    # Order grading via Kendall tau (60% weight)
    tau      = _kendall_tau_score(order, correct_order)
    top3_ok  = order[:3] == correct_order[:3]
    full_ok  = order == correct_order
    hits     = sum(1 for i, e in enumerate(order) if i < len(correct_order) and e == correct_order[i])
    order_score = 1.0 if full_ok else round(tau, 2)
    # Team assignment grading (40% weight) — per-ticket breakdown
    team_checks = {tid: assigns.get(tid) == team for tid, team in correct_teams.items()}
    team_hits   = sum(team_checks.values())
    team_score  = round(team_hits / len(correct_teams), 2)
    wrong_teams = [f"{tid}(got={assigns.get(tid)},expected={correct_teams[tid]})"
                   for tid, ok in team_checks.items() if not ok]
    score    = round(order_score * 0.6 + team_score * 0.4, 2)
    checks   = {"top3_correct": top3_ok, "full_order": full_ok,
                 "team_assignments": team_score == 1.0, **{f"team_{tid}": ok for tid, ok in team_checks.items()}}
    tag      = "[OK]" if score >= 0.95 else "[PARTIAL]" if score >= 0.5 else "[ERROR]"
    feedback = f"{tag} Order: {hits}/8 exact, Tau: {tau:.2f}, Teams: {team_hits}/8 correct."
    if wrong_teams:
        feedback += f" Wrong teams: {', '.join(wrong_teams)}."
    return score, feedback, checks


def grade_ticket_hard(payload: dict) -> tuple[float, str, dict]:
    root_cause = payload.get("root_cause", "").lower()
    resolution = [step.lower() for step in payload.get("resolution_steps", [])]
    affected   = {s.lower() for s in payload.get("affected_services", [])}
    severity   = payload.get("severity", "").upper()
    expected   = TICKET_HARD_INCIDENT["expected"]
    # Root cause check
    rc_hits    = sum(1 for kw in expected["root_cause_keywords"] if kw in root_cause)
    rc_ok      = rc_hits >= 3
    # Affected services
    expected_svcs = {s.lower() for s in expected["affected_services"]}
    svc_hits   = len(affected & expected_svcs)
    svc_ok     = svc_hits >= 3
    # Severity
    sev_ok     = severity == expected["severity"]
    # Resolution steps
    res_text   = " ".join(resolution)
    res_hits   = sum(1 for kw in expected["resolution_keywords"] if kw in res_text)
    res_ok     = res_hits >= 3 and len(resolution) >= 3
    checks     = {"root_cause_ok": rc_ok, "affected_services_ok": svc_ok, "severity_ok": sev_ok, "resolution_ok": res_ok}
    passed     = sum(checks.values())
    score      = round(passed / 4, 2)
    tag        = "[OK]" if score == 1.0 else "[PARTIAL]" if score >= 0.5 else "[ERROR]"
    feedback   = f"{tag} {passed}/4 incident analysis checks passed. RC keywords: {rc_hits}, Svcs: {svc_hits}/4, Res steps: {len(resolution)}."
    return score, feedback, checks


def grade_cross_agent_chain(payload: dict, context: dict) -> tuple[float, str, dict]:
    case          = context["case"]
    email_given   = payload.get("email_classification", "").strip().lower()
    email_ok      = email_given == case["email_label"]
    bugs          = payload.get("bugs", [])
    bug_ok        = False
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
    expected_issues = case["expected_issues"]

    # Handle two formats models use:
    # Format A (correct): {"revenue": "inconsistent...", "region": "casing..."}
    # Format B (wrong):   {"field": "revenue", "issue": "inconsistent..."}
    if isinstance(raw_issues, dict):
        # Check if it's format B — has "field" key instead of field names as keys
        if "field" in raw_issues and "issue" in raw_issues:
            # Convert: extract the field name from the "field" value
            field_val = str(raw_issues.get("field", "")).lower()
            issue_val = str(raw_issues.get("issue", "")).lower()
            data_issues = {field_val: issue_val}
        else:
            data_issues = {k.lower(): str(v).lower() for k, v in raw_issues.items()}
    elif isinstance(raw_issues, list):
        # Format C: [{"field": "revenue", "issue": "..."}]
        data_issues = {}
        for item in raw_issues:
            if isinstance(item, dict):
                f = str(item.get("field", "")).lower()
                v = str(item.get("issue", item.get("description", ""))).lower()
                if f:
                    data_issues[f] = v
    else:
        data_issues = {}

    issue_hits = sum(1 for field in expected_issues if field in data_issues)
    issues_ok  = issue_hits >= 2
    cleaned_ok = len(cleaned) == len(case["attachment_data"])
    checks     = {"priority_correct": priority_ok, "issues_identified": issues_ok, "data_cleaned": cleaned_ok}
    passed     = sum(checks.values())
    score      = round(passed / 3, 2)
    tag        = "[OK]" if score == 1.0 else "[PARTIAL]" if score >= 0.67 else "[ERROR]"
    feedback   = f"{tag} {passed}/3 cross-agent email+data checks passed."
    if not issues_ok:
        feedback += f" Issues found: {issue_hits}/{len(expected_issues)} fields identified."
    return score, feedback, checks


def grade_cross_agent_code_email(payload: dict, context: dict) -> tuple[float, str, dict]:
    case     = context["case"]
    vuln_type = payload.get("vulnerability_type", "").lower()
    location  = payload.get("vulnerability_location", "").lower()
    email     = payload.get("disclosure_email", "").lower()
    type_ok   = case["primary_vulnerability"] in vuln_type or "sql" in vuln_type
    loc_ok    = case["location"].lower() in location
    email_hits = sum(1 for kw in case["disclosure_keywords"] if kw in email)
    email_ok   = email_hits >= 4 and len(email) >= 80
    checks     = {"vulnerability_identified": type_ok, "location_correct": loc_ok, "disclosure_email_quality": email_ok}
    passed     = sum(checks.values())
    score      = round(passed / 3, 2)
    tag        = "[OK]" if score == 1.0 else "[PARTIAL]" if score >= 0.67 else "[ERROR]"
    feedback   = f"{tag} {passed}/3 code+email checks passed. Email keywords: {email_hits}."
    return score, feedback, checks


def grade_cross_agent_mod_escalation(payload: dict, context: dict) -> tuple[float, str, dict]:
    case          = context["case"]
    label_given   = payload.get("content_label", "").strip().lower()
    escalate      = payload.get("escalate", None)
    notice        = payload.get("moderation_notice", "").lower()
    label_ok      = label_given == case["correct_label"]
    escalate_ok   = escalate == case["should_escalate"]
    if case["should_escalate"]:
        notice_hits = sum(1 for kw in case["notice_keywords"] if kw in notice)
        notice_ok   = notice_hits >= 3
    else:
        notice_ok   = len(notice) == 0 or notice.strip() == ""
    checks   = {"label_correct": label_ok, "escalation_correct": escalate_ok, "notice_quality": notice_ok}
    passed   = sum(checks.values())
    score    = round(passed / 3, 2)
    tag      = "[OK]" if score == 1.0 else "[PARTIAL]" if score >= 0.67 else "[ERROR]"
    feedback = f"{tag} {passed}/3 moderation+escalation checks passed."
    return score, feedback, checks


# ═════════════════════════════════════════════════════════════════════════════
# INSTRUCTIONS
# ═════════════════════════════════════════════════════════════════════════════

INSTRUCTIONS: dict[str, str] = {
    "email_triage_easy": (
        "Classify the email as exactly one of: 'spam', 'important', or 'newsletter'.\n"
        'Payload: {"classification": "spam"}'
    ),
    "email_triage_medium": (
        "Prioritize the 10 emails from most urgent (first) to least urgent (last).\n"
        "Priority tiers — assign each email to a tier first, then order within tiers by deadline/impact:\n"
        "  Tier 1 (CRITICAL): Active production outages, active security breaches — immediate revenue/safety impact\n"
        "  Tier 2 (URGENT): Legal agreements or contracts expiring TODAY — deal falls through if unsigned\n"
        "  Tier 3 (HIGH): Overdue financial obligations threatening service suspension\n"
        "  Tier 4 (HIGH): Business deliverables with hard deadlines this week\n"
        "  Tier 5 (LOW): Social — lunch invites, work anniversaries\n"
        "  Tier 6 (IGNORE): Passive newsletters and promotional content\n"
        "Within Tier 2: 'TODAY' deadlines rank above 'Friday' deadlines.\n"
        "Within Tier 4: launch review decks rank above other reviews by proximity to launch date.\n"
        "Return ALL 10 email IDs ordered most-to-least urgent.\n"
        'Payload: {"order": ["m1", "m5", ...]}'
    ),
    "email_triage_hard": (
        "Draft a professional, empathetic reply to the customer complaint. Address ALL concerns.\n"
        'Payload: {"reply": "<full reply text>"}'
    ),
    "code_review_easy": (
        "Identify the syntax error(s) in the Python code.\n"
        'Payload: {"errors": ["description of syntax error"]}'
    ),
    "code_review_medium": (
        "Find ALL 4 logical bugs — one per function. Report location, issue, and fix.\n"
        "  1. find_max — wrong initialization (fails all-negative lists)\n"
        "  2. get_user — = used instead of ==\n"
        "  3. divide — no zero-division guard\n"
        "  4. process_list — off-by-one in range\n"
        'Payload: {"bugs": [{"location": "fn_name", "issue": "...", "fix": "..."}]}'
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
        'Payload: {"vulnerabilities": [{"type": "...", "location": "...", "severity": "...", "fix": "..."}]}'
    ),
    "data_cleaning_easy": (
        "Find all missing (null) values by field+row, and identify duplicate row IDs.\n"
        'Payload: {"missing": ["age (row 2)", "name (row 4)"], "duplicates": [1, 3]}'
    ),
    "data_cleaning_medium": (
        "Identify all 5 data quality issues and return the fully cleaned dataset (5 rows).\n"
        'Payload: {"issues": {"age": "mixed types..."}, "cleaned_data": [...]}'
    ),
    "data_cleaning_hard": (
        "Detect outliers (IQR/z-score), find missing values, impute, return cleaned dataset.\n"
        'Payload: {"outliers": [4, 8], "missing": [6, 11], "cleaned_data": [...]}'
    ),
    "content_moderation_easy": (
        "Classify each post as 'safe' or 'harmful'.\n"
        'Payload: {"classifications": [{"id": "c1", "label": "harmful"}]}'
    ),
    "content_moderation_medium": (
        "Classify each post as 'safe' or 'harmful'. Watch for sarcasm, subtle toxicity, implicit hostility.\n"
        "IMPORTANT DISTINCTION — not all unusual phrasing is harmful:\n"
        "  HARMFUL: sarcasm that mocks or demeans a person ('Classic genius move', 'brilliant idea')\n"
        "  HARMFUL: passive aggression that excludes or belittles ('not cut out for this', 'shouldn't have opinions')\n"
        "  SAFE: mild, ambiguous comments that express a personal reaction without attacking anyone\n"
        "  SAFE: backhanded compliments about THINGS (not people) — 'very unique' about a presentation is\n"
        "         just a mild opinion, not an attack on a person. No target = not harmful.\n"
        "  SAFE: genuine positivity ('Congrats!', 'Thanks for the feedback')\n"
        'Payload: {"classifications": [{"id": "m1", "label": "harmful", "reason": "..."}]}'
    ),
    "content_moderation_hard": (
        "Each case shows the SAME text in TWO different contexts. Determine the correct label for EACH context.\n"
        "CRITICAL RULES:\n"
        "  1. Some texts are ALWAYS harmful regardless of context — they use dehumanizing language or\n"
        "     dog-whistle rhetoric that is harmful no matter what platform or prior message surrounds them.\n"
        "     TEST: Would a reasonable content moderator flag this text if they saw it with NO context?\n"
        "     If yes, label it 'harmful' in BOTH contexts.\n"
        "  2. KEY SIGNAL — comparing humans to animals ('breed like rabbits'), invoking 'replacement' of\n"
        "     ethnic groups, or using language that strips human dignity is ALWAYS harmful. A 'biology\n"
        "     classroom' or 'urban planning' framing does NOT make dehumanizing rhetoric acceptable.\n"
        "  3. Other texts ARE context-dependent — 'disappear' in gaming vs crisis support, 'take out' in\n"
        "     HR dinner vs extremist forum, 'eliminate the competition' in business vs political violence.\n"
        "     For these, label each context based on the actual meaning in that specific context.\n"
        "  4. When in doubt about a text: ask 'is this language that treats a group of people as less than\n"
        "     human?' If yes → harmful in all contexts. If it's just ambiguous phrasing → context matters.\n"
        'Payload: {"decisions": [{"id": "h1", "context_a_label": "safe", "context_b_label": "harmful"}]}'
    ),
    "ticket_triage_easy": (
        "Classify the support ticket: assign a priority (critical/high/medium/low) and category (bug/feature_request/question/billing).\n"
        'Payload: {"priority": "critical", "category": "bug"}'
    ),
    "ticket_triage_medium": (
        "Order 8 tickets by priority (most urgent first) and assign each to the correct team.\n"
        "Priority reasoning:\n"
        "  1. Production DB down and SSL expiring in 48h are both critical infrastructure\n"
        "  2. Currency display bug (affects all EU users visibly) ranks above billing revenue leak\n"
        "  3. Revenue-leak billing bug ranks above invoice PDF generation bug\n"
        "  4. Feature requests rank below all bugs\n"
        "Team routing — be precise about these common mistakes:\n"
        "  backend  = server-side APIs, DB queries, background job processing\n"
        "  frontend = anything the user SEES in the browser: currency symbols, UI, display bugs, CSV export UI\n"
        "  devops   = SSL certificates, deployments, infrastructure\n"
        "  billing  = payment charges, subscription billing, invoice amounts, refunds\n"
        "  'Wrong currency symbol shown' → frontend (it's a display/rendering bug)\n"
        "  'Customer billed $0 instead of $299' → billing (it's a charge calculation bug)\n"
        "  'Invoice PDF generation fails' → backend (server-side PDF generation)\n"
        "  'Add OAuth2 SSO support' → backend (auth server logic)\n"
        "  'Redesign onboarding flow' → frontend (UI/UX work)\n"
        "  'Add CSV export for analytics' → frontend (UI feature)\n"
        'Payload: {"order": ["tk1", "tk4", "tk2", "tk7", "tk5", "tk3", "tk6", "tk8"], '
        '"assignments": {"tk1": "backend", "tk2": "frontend", "tk3": "backend", '
        '"tk4": "devops", "tk5": "backend", "tk6": "frontend", "tk7": "billing", "tk8": "frontend"}}'
    ),
    "ticket_triage_hard": (
        "Analyse the linked incident tickets and produce: root cause analysis, ordered resolution steps, affected services, and severity (P1-P4).\n"
        'Payload: {"root_cause": "...", "resolution_steps": ["...", "..."], "affected_services": ["...", "..."], "severity": "P1"}'
    ),
    "cross_agent_chain": (
        "TWO skills needed:\n"
        "  1. Classify the email: 'spam', 'important', or 'newsletter'\n"
        "  2. Find the main bug in the attached code (location + issue + fix)\n"
        'Payload: {"email_classification": "important", "bugs": [{"location": "fn", "issue": "...", "fix": "..."}]}'
    ),
    "cross_agent_email_data": (
        "TWO skills needed:\n"
        "  1. Classify the email urgency: 'critical', 'high', 'medium', 'low'\n"
        "  2. Identify data quality issues in the attachment and return cleaned data\n"
        "IMPORTANT: data_issues must use field names as keys, NOT 'field'/'issue' as keys.\n"
        "  CORRECT:   {\"revenue\": \"inconsistent formats\", \"region\": \"inconsistent casing\", \"closed_date\": \"multiple date formats\"}\n"
        "  INCORRECT: {\"field\": \"revenue\", \"issue\": \"inconsistent formats\"}\n"
        'Payload: {"email_priority": "critical", "data_issues": {"revenue": "inconsistent formats", "region": "casing issues", "closed_date": "multiple formats"}, "cleaned_data": [...]}'
    ),
    "cross_agent_code_email": (
        "TWO skills needed:\n"
        "  1. Identify the primary security vulnerability type and its location\n"
        "  2. Draft a professional security disclosure email to the dev team (min 80 chars)\n"
        'Payload: {"vulnerability_type": "sql_injection", "vulnerability_location": "fn_name", "disclosure_email": "..."}'
    ),
    "cross_agent_mod_escalation": (
        "TWO skills needed:\n"
        "  1. Classify the content as 'safe' or 'harmful'\n"
        "  2. Decide whether to escalate (true/false) and draft a moderation notice if harmful (empty string if safe)\n"
        'Payload: {"content_label": "harmful", "escalate": true, "moderation_notice": "Your post was removed because..."}'
    ),
}


# ═════════════════════════════════════════════════════════════════════════════
# ENVIRONMENT
# ═════════════════════════════════════════════════════════════════════════════

class MetaEnvironment(Environment):
    """
    Meta Multi-Agent Environment v3.0
    5 domains · 16 tasks · 4 cross-agent chained tasks · deterministic context loading
    """
    SUPPORTS_CONCURRENT_SESSIONS: bool = True

    def __init__(self) -> None:
        self._state                  = State(episode_id=str(uuid4()), step_count=0)
        self._current_task_id: str | None = None
        self._current_agent_context: dict  = {}
        self._current_grader_context: dict = {}
        self._episode_scores: list[float]  = []
        self._attempt_counts: dict[str, int]   = {}
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
            agent="meta",
            task_id="",
            difficulty="",
            context={},
            instructions=(
                "Welcome to Meta Multi-Agent Environment v3.0!\n"
                "5 agents × 3 tasks + 4 cross-agent tasks = 19 tasks total.\n"
                "Agents: email_triage | code_review | data_cleaning | "
                "content_moderation | ticket_triage | cross_agent\n"
                "Use GET /tasks to see all task IDs and exact payload schemas.\n"
                "Multi-step episodes: imperfect first attempts earn a retry."
            ),
            feedback="Environment reset. Ready for episode.",
            score=0.0,
            partial_credits={},
            done=False,
            reward=0.0,
        )

    def _deterministic_choice(self, variants: list, task_id: str) -> Any:
        """Pick a variant deterministically based on episode_id hash."""
        idx = hash(self._state.episode_id + task_id) % len(variants)
        return variants[idx]

    def _load_context(self, task_id: str) -> tuple[dict, dict, str]:
        """Return (agent_ctx, grader_ctx, difficulty). Fully deterministic."""
        if task_id == "email_triage_easy":
            email      = self._deterministic_choice(EMAIL_EASY_VARIANTS, task_id)
            agent_ctx  = {"email": {k: v for k, v in email.items() if k != "label"}}
            grader_ctx = {"email": email}
            return agent_ctx, grader_ctx, "easy"

        if task_id == "email_triage_medium":
            agent_ctx  = {"emails": [{k: v for k, v in e.items() if k not in ("priority", "category")} for e in EMAIL_MEDIUM_EMAILS]}
            grader_ctx = {"emails": EMAIL_MEDIUM_EMAILS}
            return agent_ctx, grader_ctx, "medium"

        if task_id == "email_triage_hard":
            case       = self._deterministic_choice(EMAIL_HARD_CASES, task_id)
            agent_ctx  = {"email": {k: v for k, v in case.items() if k != "expected_elements"}}
            grader_ctx = {"email": case}
            return agent_ctx, grader_ctx, "hard"

        if task_id == "code_review_easy":
            variant    = self._deterministic_choice(CODE_EASY_VARIANTS, task_id)
            agent_ctx  = {"code": variant["code"]}
            grader_ctx = {"code": variant["code"], "keywords": variant["keywords"]}
            return agent_ctx, grader_ctx, "easy"

        if task_id == "code_review_medium":
            ctx = {"code": CODE_MEDIUM["code"]}
            return ctx, ctx, "medium"

        if task_id == "code_review_hard":
            ctx = {"code": CODE_HARD["code"]}
            return ctx, ctx, "hard"

        if task_id == "data_cleaning_easy":
            ctx = {"data": DATA_EASY["data"]}
            return ctx, ctx, "easy"

        if task_id == "data_cleaning_medium":
            ctx = {"data": DATA_MEDIUM["data"]}
            return ctx, ctx, "medium"

        if task_id == "data_cleaning_hard":
            ctx = {"data": DATA_HARD["data"]}
            return ctx, ctx, "hard"

        if task_id == "content_moderation_easy":
            agent_ctx  = {"posts": [{k: v for k, v in p.items() if k != "label"} for p in MOD_EASY]}
            grader_ctx = {"posts": MOD_EASY}
            return agent_ctx, grader_ctx, "easy"

        if task_id == "content_moderation_medium":
            agent_ctx  = {"posts": [{k: v for k, v in p.items() if k != "label"} for p in MOD_MEDIUM]}
            grader_ctx = {"posts": MOD_MEDIUM}
            return agent_ctx, grader_ctx, "medium"

        if task_id == "content_moderation_hard":
            agent_ctx  = {"cases": [{k: v for k, v in c.items() if k not in ("label_a", "label_b", "reason_a", "reason_b")} for c in MOD_HARD]}
            grader_ctx = {"cases": MOD_HARD}
            return agent_ctx, grader_ctx, "hard"

        if task_id == "ticket_triage_easy":
            ticket     = self._deterministic_choice(TICKET_EASY_VARIANTS, task_id)
            agent_ctx  = {"ticket": {k: v for k, v in ticket.items() if k not in ("correct_priority", "correct_category")}}
            grader_ctx = {"ticket": ticket}
            return agent_ctx, grader_ctx, "easy"

        if task_id == "ticket_triage_medium":
            agent_ctx  = {"tickets": [{k: v for k, v in t.items() if k not in ("priority_rank", "team")} for t in TICKET_MEDIUM_TICKETS]}
            grader_ctx = {"tickets": TICKET_MEDIUM_TICKETS}
            return agent_ctx, grader_ctx, "medium"

        if task_id == "ticket_triage_hard":
            ctx = {"incident_tickets": TICKET_HARD_INCIDENT["tickets"]}
            return ctx, ctx, "hard"

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
        if task_id == "code_review_easy":            return grade_code_easy(payload, grader_context)
        if task_id == "code_review_medium":          return grade_code_medium(payload)
        if task_id == "code_review_hard":            return grade_code_hard(payload)
        if task_id == "data_cleaning_easy":          return grade_data_easy(payload)
        if task_id == "data_cleaning_medium":        return grade_data_medium(payload)
        if task_id == "data_cleaning_hard":          return grade_data_hard(payload)
        if task_id == "content_moderation_easy":     return grade_mod_easy(payload)
        if task_id == "content_moderation_medium":   return grade_mod_medium(payload)
        if task_id == "content_moderation_hard":     return grade_mod_hard(payload)
        if task_id == "ticket_triage_easy":          return grade_ticket_easy(payload, grader_context)
        if task_id == "ticket_triage_medium":        return grade_ticket_medium(payload)
        if task_id == "ticket_triage_hard":          return grade_ticket_hard(payload)
        if task_id == "cross_agent_chain":           return grade_cross_agent_chain(payload, grader_context)
        if task_id == "cross_agent_email_data":      return grade_cross_agent_email_data(payload, grader_context)
        if task_id == "cross_agent_code_email":      return grade_cross_agent_code_email(payload, grader_context)
        if task_id == "cross_agent_mod_escalation":  return grade_cross_agent_mod_escalation(payload, grader_context)
        return 0.0, "Unknown task.", {}

    def _compute_reward(self, score: float, task_id: str, attempt: int) -> float:
        """Trajectory-aware reward shaping."""
        base = score
        # Speed bonus: perfect on first attempt
        if score == 1.0 and attempt == 1:
            base = min(base + 0.05, 1.0)
        # Improvement bonus: reward getting better on retry
        if attempt == 2:
            prev = self._first_attempt_scores.get(task_id, 0.0)
            if score > prev:
                base = min(base + (score - prev) * 0.1, 1.0)
        # Penalty: repeated failure
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
                agent="error", task_id="", difficulty="",
                context={},
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
                feedback="Probe: context loaded. Submit a real payload to get scored." if is_probe else "Empty payload. Use GET /tasks to see required fields.",
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
                agent=agent, task_id=task_id, difficulty="",
                context={},
                instructions="Use GET /tasks to see valid task IDs.",
                feedback=str(e),
                score=0.0, partial_credits={}, done=True, reward=0.0,
            )

        # Grade
        score, feedback, partial_credits = self._grade(task_id, payload, grader_ctx)

        # Multi-step retry logic
        attempt = self._attempt_counts.get(task_id, 0) + 1
        self._attempt_counts[task_id] = attempt

        reward = self._compute_reward(score, task_id, attempt)

        if attempt == 1 and score < 1.0:
            self._first_attempt_scores[task_id] = score
            done     = False
            reward   = score * 0.5
            missed   = [k for k, v in partial_credits.items() if not v]
            feedback += (
                f" [RETRY AVAILABLE] Score: {score:.2f}. "
                f"Improve on: {missed}"
            )
        elif attempt == 1 and score == 1.0:
            done     = True
            self._episode_scores.append(score)
        else:
            first  = self._first_attempt_scores.get(task_id, 0.0)
            score  = max(score, first)
            done   = True
            reward = self._compute_reward(score, task_id, attempt)
            self._episode_scores.append(score)
            feedback += f" [FINAL] Best score from 2 attempts: {score:.2f}."

        return MetaObservation(
            agent=agent,
            task_id=task_id,
            difficulty=difficulty,
            context=agent_ctx,
            instructions=INSTRUCTIONS.get(task_id, ""),
            feedback=feedback,
            score=score,
            partial_credits=partial_credits,
            done=done,
            reward=reward,
            metadata={
                "step":              self._state.step_count,
                "attempt":           attempt,
                "episode_avg_score": round(
                    sum(self._episode_scores) / len(self._episode_scores), 3
                ) if self._episode_scores else 0.0,
            },
        )

    @property
    def state(self) -> State:
        return self._state