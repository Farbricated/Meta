# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.

"""
Meta Multi-Agent Environment v2.

Four real-world AI agent domains, 12 tasks total (easy/medium/hard each):
  1. Email Triage        - classify, prioritize, draft replies
  2. Code Review         - syntax errors, logic bugs, security vulnerabilities
  3. Data Cleaning       - missing values, type normalization, outlier imputation
  4. Content Moderation  - explicit, subtle toxicity, context-aware moderation
"""

import json
import random
from uuid import uuid4
from openenv.core.env_server.interfaces import Environment
from openenv.core.env_server.types import State

try:
    from models import MetaAction, MetaObservation
except ImportError:
    from ..models import MetaAction, MetaObservation


# ==============================================================================
# TASK DATA
# ==============================================================================

EMAIL_EASY_VARIANTS = [
    {"id": "e1", "subject": "You won $1,000,000!!!", "sender": "promo@totally-legit-lottery.com",
     "body": "Click here to claim your prize now! Limited time offer!", "label": "spam"},
    {"id": "e2", "subject": "Q3 Budget Review - Urgent Action Required", "sender": "cfo@company.com",
     "body": "Please review the attached Q3 budget before our board meeting tomorrow at 9 AM.", "label": "important"},
    {"id": "e3", "subject": "Your weekly digest from Medium", "sender": "noreply@medium.com",
     "body": "Top stories this week: AI trends, Python tips, and startup news.", "label": "newsletter"},
    {"id": "e4", "subject": "CONGRATULATIONS! iPhone 15 Pro is yours!", "sender": "winner@prize-alert.net",
     "body": "You have been selected. Click now to claim your free iPhone!", "label": "spam"},
    {"id": "e5", "subject": "Action Required: Sign the NDA before Friday", "sender": "legal@company.com",
     "body": "Please sign the attached NDA before Friday's partnership meeting. Deadline is strict.", "label": "important"},
    {"id": "e6", "subject": "TechCrunch Newsletter - March 2026", "sender": "newsletter@techcrunch.com",
     "body": "This week's top stories in tech, AI, and startups.", "label": "newsletter"},
]

EMAIL_MEDIUM_EMAILS = [
    {"id": "m1", "subject": "[ALERT] Production server DOWN", "sender": "ops@company.com",
     "body": "All services unresponsive since 2 AM. Revenue impact: $10k/min.", "priority": 1, "category": "critical"},
    {"id": "m2", "subject": "Team lunch this Friday?", "sender": "colleague@company.com",
     "body": "Hey, thinking of doing a team lunch Friday. You in?", "priority": 9, "category": "social"},
    {"id": "m3", "subject": "Acme Corp contract renewal - URGENT", "sender": "sales@company.com",
     "body": "Acme contract expires Friday. They need signature or they walk.", "priority": 2, "category": "business"},
    {"id": "m4", "subject": "Weekly SaaS digest", "sender": "news@saasdigest.com",
     "body": "Top SaaS stories this week...", "priority": 10, "category": "newsletter"},
    {"id": "m5", "subject": "[WARNING] Security alert: unusual login", "sender": "security@company.com",
     "body": "Unauthorized login attempt from IP 45.33.32.156. Verify immediately.", "priority": 1, "category": "critical"},
    {"id": "m6", "subject": "Invoice #INV-4521 overdue", "sender": "billing@vendor.com",
     "body": "Invoice of $5,400 was due 3 days ago. Payment needed to avoid service suspension.", "priority": 3, "category": "finance"},
    {"id": "m7", "subject": "Happy Work Anniversary! ", "sender": "hr@company.com",
     "body": "Celebrating your 3 years with us!", "priority": 10, "category": "social"},
    {"id": "m8", "subject": "Q4 product launch deck - review needed", "sender": "marketing@company.com",
     "body": "Please review launch slides before Thursday. Launch is next Monday.", "priority": 3, "category": "business"},
    {"id": "m9", "subject": "Free AI productivity webinar", "sender": "promo@webinar.io",
     "body": "Join our free webinar on AI tools this Thursday.", "priority": 8, "category": "newsletter"},
    {"id": "m10", "subject": "Legal: Partnership agreement needs signature TODAY", "sender": "legal@company.com",
     "body": "The partnership agreement must be countersigned by EOD or the deal falls through.", "priority": 2, "category": "legal"},
]

EMAIL_MEDIUM_CORRECT_ORDER = ["m1", "m5", "m3", "m10", "m6", "m8", "m2", "m9", "m4", "m7"]

EMAIL_HARD_CASES = [
    {
        "id": "h1",
        "subject": "Completely unacceptable - Order #78234",
        "sender": "furious.customer@email.com",
        "body": (
            "I have been a loyal customer for 5 years and I am absolutely furious. "
            "My order #78234 arrived broken for the SECOND time this month. "
            "Your support team has been dismissive and unhelpful every time I called. "
            "I demand a full refund, a replacement sent overnight, AND compensation. "
            "If this is not resolved within 24 hours, I will file a consumer court complaint "
            "and post reviews everywhere I can."
        ),
        "expected_elements": {
            "acknowledge_frustration": ["understand", "frustrat", "disappoint", "concern", "feel"],
            "apologize": ["sorry", "apologize", "apology", "sincerely"],
            "offer_refund": ["refund", "money back", "full refund"],
            "offer_replacement": ["replacement", "replace", "new order", "send another", "overnight"],
            "provide_timeline": ["24 hours", "48 hours", "within", "today", "tomorrow", "business day"],
            "professional_tone": None,
            "compensation_acknowledged": ["compensat", "inconvenience", "make it right", "goodwill"],
        }
    },
    {
        "id": "h2",
        "subject": "Billing error - charged twice for subscription",
        "sender": "billing.complaint@customer.com",
        "body": (
            "I was charged twice for my annual subscription this month - once on March 1st "
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
        }
    }
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
        "max_val_init": "find_max initializes max_val=0, fails for all-negative lists",
        "assignment_vs_eq": "get_user uses = (assignment) instead of == (comparison)",
        "zero_division": "divide() has no guard against division by zero",
        "off_by_one": "process_list iterates range(len(items)+1) causing IndexError",
    }
}

CODE_HARD = {
    "code": (
        "import sqlite3\n"
        "import subprocess\n\n"
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
        "import pickle\n"
        "def load_user_data(data_bytes):\n"
        "    return pickle.loads(data_bytes)\n"
    ),
    "vulnerabilities": {
        "sql_injection_get_user": {"type": "sql_injection", "location": "get_user_by_name", "severity": "critical"},
        "xss_render_comment":    {"type": "xss", "location": "render_comment", "severity": "high"},
        "sql_injection_login":   {"type": "sql_injection", "location": "login", "severity": "critical"},
        "command_injection":     {"type": "command_injection", "location": "run_report", "severity": "critical"},
        "insecure_deserialization": {"type": "insecure_deserialization", "location": "load_user_data", "severity": "high"},
    }
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
        "missing": ["age (row 2)", "name (row 4)", "email (row 5)", "salary (row 6)"],
        "duplicates": [1, 3],
    }
}

DATA_MEDIUM = {
    "data": [
        {"id": 1, "name": "Alice",   "age": "thirty", "salary": "50000",  "join_date": "2020/01/15", "active": "yes"},
        {"id": 2, "name": "Bob",     "age": 25,        "salary": "$60,000","join_date": "15-03-2021", "active": True},
        {"id": 3, "name": "Charlie", "age": "28",      "salary": "70000",  "join_date": "2019-07-22", "active": "TRUE"},
        {"id": 4, "name": "dave",    "age": 35,        "salary": "80,000", "join_date": "2022/11/01", "active": False},
        {"id": 5, "name": "EVE",     "age": "twenty-two","salary": "45000","join_date": "01/06/2023", "active": "no"},
    ],
    "issues": {
        "age": "mixed types: strings 'thirty', '28', 'twenty-two' should be integers",
        "salary": "inconsistent formats: '$60,000' and '80,000' have symbols/commas",
        "join_date": "three different date formats: YYYY/MM/DD, DD-MM-YYYY, YYYY-MM-DD, MM/DD/YYYY",
        "name": "inconsistent casing: 'dave' lowercase, 'EVE' all caps",
        "active": "mixed types: True/False booleans mixed with strings 'yes'/'no'/'TRUE'",
    }
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
        "outliers": {4, 8},
        "missing": {6, 11},
        "imputed_range": (10.0, 12.0),
    }
}

MOD_EASY = [
    {"id": "c1", "text": "I hate you so much, I want to hurt you!",              "label": "harmful"},
    {"id": "c2", "text": "Great weather today! Loving this sunshine ",          "label": "safe"},
    {"id": "c3", "text": "All people from that group should be eliminated.",      "label": "harmful"},
    {"id": "c4", "text": "Can someone recommend a good Python beginner book?",   "label": "safe"},
    {"id": "c5", "text": "You're an absolute idiot and nobody likes you.",       "label": "harmful"},
    {"id": "c6", "text": "I just finished a 5k run - feeling amazing!",          "label": "safe"},
    {"id": "c7", "text": "People like you should just disappear forever.",       "label": "harmful"},
]

MOD_MEDIUM = [
    {"id": "m1", "text": "Oh sure, like THAT went well. Classic genius move.",               "label": "harmful"},
    {"id": "m2", "text": "I'm so done with these people. Absolutely insufferable.",          "label": "harmful"},
    {"id": "m3", "text": "That presentation was... very unique.",                            "label": "safe"},
    {"id": "m4", "text": "Some people just shouldn't be allowed to have opinions.",         "label": "harmful"},
    {"id": "m5", "text": "Oh wow, another 'brilliant' idea from upper management ",       "label": "harmful"},
    {"id": "m6", "text": "Congrats on the promotion! Well deserved!",                       "label": "safe"},
    {"id": "m7", "text": "Not everyone is cut out for this kind of work, clearly.",         "label": "harmful"},
    {"id": "m8", "text": "Thanks for the feedback, I'll take it into account.",             "label": "safe"},
]

MOD_HARD = [
    {
        "id": "h1",
        "text": "You should just disappear.",
        "context_a": {"platform": "gaming_chat", "prior_message": "Your character died in the dungeon. Respawn?"},
        "label_a": "safe",
        "reason_a": "Gaming context - disappear refers to the character, not the person",
        "context_b": {"platform": "crisis_support_chat", "prior_message": "I've been feeling worthless and invisible lately"},
        "label_b": "harmful",
        "reason_b": "Mental health context - could reinforce suicidal ideation",
    },
    {
        "id": "h2",
        "text": "We need to take these people out.",
        "context_a": {"platform": "hr_slack", "prior_message": "Which team members should join the client dinner?"},
        "label_a": "safe",
        "reason_a": "HR context - 'take out' means to dinner",
        "context_b": {"platform": "extremist_forum", "prior_message": "These immigrants are ruining our country."},
        "label_b": "harmful",
        "reason_b": "Extremist context - 'take out' implies physical violence",
    },
    {
        "id": "h3",
        "text": "Let's eliminate the competition.",
        "context_a": {"platform": "business_slack", "prior_message": "Q4 sales strategy meeting"},
        "label_a": "safe",
        "reason_a": "Business context - standard competitive language",
        "context_b": {"platform": "political_rally_chat", "prior_message": "The opposition party is destroying our values."},
        "label_b": "harmful",
        "reason_b": "Political context - incitement to violence against political opponents",
    },
]


# ==============================================================================
# GRADERS
# ==============================================================================

def grade_email_easy(payload, context):
    correct = context["email"]["label"]
    given = payload.get("classification", "").strip().lower()
    valid = ["spam", "important", "newsletter"]
    if given == correct:
        return 1.0, f"[OK] Correct! '{correct}' is right.", {}
    elif given in valid:
        return 0.0, f"[FAIL] Wrong. Expected '{correct}', got '{given}'.", {"classification": False}
    else:
        return 0.0, f"[FAIL] Invalid label '{given}'. Must be: spam | important | newsletter.", {"classification": False}


def grade_email_medium(payload, context):
    order = payload.get("order", [])
    correct = EMAIL_MEDIUM_CORRECT_ORDER
    if not order:
        return 0.0, "[FAIL] No order provided.", {}

    top2_ok = set(order[:2]) == {"m1", "m5"}
    top5_ok = order[:5] == correct[:5]
    full_ok = order == correct
    hits = sum(1 for i, e in enumerate(order) if i < len(correct) and e == correct[i])

    partial = {"top2_critical": top2_ok, "top5_correct": top5_ok, "full_order": full_ok}

    if full_ok:
        return 1.0, "[OK] Perfect prioritization!", partial
    elif top5_ok:
        return 0.8, f"[PARTIAL] Top 5 correct. Full order has {10-hits} mismatches.", partial
    elif top2_ok:
        return 0.5, f"[PARTIAL] Critical emails (m1, m5) correctly placed first. {hits}/10 positions correct.", partial
    else:
        score = round(hits / 10, 2)
        return score, f"[ERROR] {hits}/10 emails in correct position.", partial


def grade_email_hard(payload, context):
    reply = payload.get("reply", "").lower()
    case = context["email"]
    expected = case.get("expected_elements", {})
    checks = {}

    for key, keywords in expected.items():
        if key == "professional_tone":
            checks[key] = (
                len(reply) > 80
                and not any(w in reply for w in ["not my problem", "whatever", "too bad", "deal with it"])
            )
        else:
            checks[key] = keywords is not None and any(w in reply for w in keywords)

    passed = sum(checks.values())
    total = len(checks)
    score = round(passed / total, 2)
    missing = [k for k, v in checks.items() if not v]
    feedback = f"{'[OK]' if score == 1.0 else '[PARTIAL]' if score >= 0.6 else '[ERROR]'} {passed}/{total} reply elements present."
    if missing:
        feedback += f" Missing: {', '.join(missing)}."
    return score, feedback, checks


def grade_code_easy(payload, context):
    errors = " ".join(str(e) for e in payload.get("errors", [])).lower()
    keywords = context.get("keywords", ["colon", "syntax"])
    found = any(k in errors for k in keywords)
    if not payload.get("errors"):
        return 0.0, "[FAIL] No errors reported.", {"syntax_error_found": False}
    return (1.0, "[OK] Syntax error correctly identified.", {"syntax_error_found": True}) if found \
        else (0.3, "[PARTIAL] Error mentioned but key issue not clearly described.", {"syntax_error_found": False})


def grade_code_medium(payload):
    bugs = payload.get("bugs", [])
    checks = {
        "max_val_init":    False,
        "assignment_vs_eq": False,
        "zero_division":   False,
        "off_by_one":      False,
    }
    for b in bugs:
        t = (str(b.get("issue", "")) + str(b.get("location", "")) + str(b.get("fix", ""))).lower()
        if any(w in t for w in ["max_val", "negative", "minus", "zero init", "float('-inf')", "none"]): checks["max_val_init"] = True
        if any(w in t for w in ["assignment", "==", "comparison", "= user_id"]): checks["assignment_vs_eq"] = True
        if any(w in t for w in ["zero", "division", "divide", "zerodivision", "b == 0"]): checks["zero_division"] = True
        if any(w in t for w in ["off by one", "off-by-one", "index", "range", "len + 1", "indexerror"]): checks["off_by_one"] = True

    passed = sum(checks.values())
    score = round(passed / 4, 2)
    feedback = f"{'[OK]' if score==1.0 else '[PARTIAL]' if score>=0.5 else '[ERROR]'} {passed}/4 bugs found."
    missing = [k for k, v in checks.items() if not v]
    if missing: feedback += f" Missed: {', '.join(missing)}."
    return score, feedback, checks


def grade_code_hard(payload):
    vulns = payload.get("vulnerabilities", [])
    checks = {
        "sql_injection_get_user":    False,
        "xss_render_comment":        False,
        "sql_injection_login":       False,
        "command_injection":         False,
        "insecure_deserialization":  False,
    }
    for v in vulns:
        vt  = str(v.get("type", "")).lower()
        loc = str(v.get("location", "")).lower()
        if "sql" in vt and "get_user" in loc:                                checks["sql_injection_get_user"] = True
        if ("xss" in vt or "cross" in vt or "script" in vt) and "render" in loc: checks["xss_render_comment"] = True
        if "sql" in vt and "login" in loc:                                   checks["sql_injection_login"] = True
        if ("command" in vt or "injection" in vt or "shell" in vt) and "report" in loc: checks["command_injection"] = True
        if ("pickle" in vt or "deserializ" in vt or "serial" in vt) and "load" in loc: checks["insecure_deserialization"] = True

    passed = sum(checks.values())
    score = round(passed / 5, 2)
    feedback = f"{'[OK]' if score==1.0 else '[PARTIAL]' if score>=0.6 else '[ERROR]'} {passed}/5 vulnerabilities found."
    missing = [k for k, v in checks.items() if not v]
    if missing: feedback += f" Missed: {', '.join(missing)}."
    return score, feedback, checks


def grade_data_easy(payload):
    missing_given = [str(m).lower() for m in payload.get("missing", [])]
    dups_given = set(str(d) for d in payload.get("duplicates", []))

    mc = {
        "age_row2":    any("age" in m and "2" in m for m in missing_given),
        "name_row4":   any("name" in m and "4" in m for m in missing_given),
        "email_row5":  any("email" in m and "5" in m for m in missing_given),
        "salary_row6": any("salary" in m and "6" in m for m in missing_given),
    }
    dup_ok = dups_given in [{"1", "3"}, {"3", "1"}] or dups_given == {1, 3}

    passed_missing = sum(mc.values())
    score = round((passed_missing / 4 * 0.7) + (0.3 if dup_ok else 0.0), 2)
    feedback = f"{'[OK]' if score==1.0 else '[PARTIAL]' if score>=0.5 else '[ERROR]'} Missing: {passed_missing}/4, Duplicates: {'[OK]' if dup_ok else '[FAIL]'}."
    return score, feedback, {**mc, "duplicates_correct": dup_ok}


def grade_data_medium(payload):
    issues = {k.lower(): str(v).lower() for k, v in payload.get("issues", {}).items()}
    cleaned = payload.get("cleaned_data", [])
    checks = {
        "age_type":     "age" in issues and any(w in issues["age"] for w in ["string", "integer", "int", "thirty", "type"]),
        "salary_format":"salary" in issues and any(w in issues["salary"] for w in ["format", "comma", "$", "inconsistent", "symbol"]),
        "date_format":  "join_date" in issues and any(w in issues["join_date"] for w in ["format", "inconsistent", "date", "yyyy", "dd-mm"]),
        "name_case":    "name" in issues and any(w in issues["name"] for w in ["capital", "case", "dave", "eve", "lower", "upper", "casing"]),
        "active_type":  "active" in issues and any(w in issues["active"] for w in ["bool", "string", "yes", "true", "type", "mixed"]),
        "data_cleaned": len(cleaned) == 5,
    }
    passed = sum(checks.values())
    score = round(passed / 6, 2)
    feedback = f"{'[OK]' if score==1.0 else '[PARTIAL]' if score>=0.5 else '[ERROR]'} {passed}/6 data quality checks passed."
    return score, feedback, checks


def grade_data_hard(payload):
    outliers_given = set(int(x) for x in payload.get("outliers", []))
    missing_given  = set(int(x) for x in payload.get("missing", []))
    cleaned = payload.get("cleaned_data", [])

    correct_outliers = DATA_HARD["answers"]["outliers"]
    correct_missing  = DATA_HARD["answers"]["missing"]
    lo, hi = DATA_HARD["answers"]["imputed_range"]

    outlier_ok = outliers_given == correct_outliers
    missing_ok = missing_given  == correct_missing

    imputed_rows = {r["id"]: r.get("value") for r in cleaned if r.get("id") in correct_missing}
    imputed_ok = all(
        v is not None and lo <= float(v) <= hi
        for v in imputed_rows.values()
    ) and len(imputed_rows) == len(correct_missing)

    checks = {"outliers_correct": outlier_ok, "missing_correct": missing_ok, "imputation_valid": imputed_ok}
    passed = sum(checks.values())
    score = round(passed / 3, 2)
    feedback = f"{'[OK]' if score==1.0 else '[PARTIAL]' if score>=0.67 else '[ERROR]'} {passed}/3 data operations correct."
    return score, feedback, checks


def grade_mod_easy(payload):
    clf = {c["id"]: c.get("label", "").lower() for c in payload.get("classifications", [])}
    correct = {p["id"]: p["label"] for p in MOD_EASY}
    per = {id_: clf.get(id_) == label for id_, label in correct.items()}
    hits = sum(per.values())
    score = round(hits / len(correct), 2)
    feedback = f"{'[OK]' if score==1.0 else '[PARTIAL]' if score>=0.7 else '[ERROR]'} {hits}/{len(correct)} posts correctly classified."
    return score, feedback, per


def grade_mod_medium(payload):
    clf = {c["id"]: c.get("label", "").lower() for c in payload.get("classifications", [])}
    correct = {p["id"]: p["label"] for p in MOD_MEDIUM}
    per = {id_: clf.get(id_) == label for id_, label in correct.items()}
    hits = sum(per.values())
    score = round(hits / len(correct), 2)
    feedback = f"{'[OK]' if score==1.0 else '[PARTIAL]' if score>=0.6 else '[ERROR]'} {hits}/{len(correct)} subtle posts correctly classified."
    return score, feedback, per


def grade_mod_hard(payload):
    decisions = {d["id"]: d for d in payload.get("decisions", [])}
    checks = {}
    for case in MOD_HARD:
        cid = case["id"]
        d = decisions.get(cid, {})
        checks[f"{cid}_context_a"] = d.get("context_a_label", "").lower() == case["label_a"]
        checks[f"{cid}_context_b"] = d.get("context_b_label", "").lower() == case["label_b"]
    passed = sum(checks.values())
    total = len(checks)
    score = round(passed / total, 2)
    feedback = f"{'[OK]' if score==1.0 else '[PARTIAL]' if score>=0.5 else '[ERROR]'} {passed}/{total} context-aware decisions correct."
    return score, feedback, checks


# ==============================================================================
# INSTRUCTIONS
# ==============================================================================

INSTRUCTIONS = {
    "email_triage_easy": (
        "Classify the email as exactly one of: 'spam', 'important', or 'newsletter'.\n"
        'Payload format: {"agent": "email_triage", "task_id": "email_triage_easy", "payload": {"classification": "spam"}}'
    ),
    "email_triage_medium": (
        "Prioritize the 10 emails from most urgent (first) to least urgent (last). Return a list of email IDs.\n"
        'Payload format: {"agent": "email_triage", "task_id": "email_triage_medium", "payload": {"order": ["m1", "m5", ...]}}'
    ),
    "email_triage_hard": (
        "Draft a professional, empathetic reply to this customer complaint. Address all their concerns.\n"
        'Payload format: {"agent": "email_triage", "task_id": "email_triage_hard", "payload": {"reply": "<full reply>"}}'
    ),
    "code_review_easy": (
        "Identify the syntax error(s) in the Python code.\n"
        'Payload format: {"agent": "code_review", "task_id": "code_review_easy", "payload": {"errors": ["description of error"]}}'
    ),
    "code_review_medium": (
        "Find ALL logical bugs in the code. For each bug, provide location, issue description, and fix.\n"
        'Payload format: {"agent": "code_review", "task_id": "code_review_medium", "payload": {"bugs": [{"location": "fn_name", "issue": "...", "fix": "..."}]}}'
    ),
    "code_review_hard": (
        "Identify ALL security vulnerabilities. For each, provide type, location, severity, and fix.\n"
        'Payload format: {"agent": "code_review", "task_id": "code_review_hard", "payload": {"vulnerabilities": [{"type": "sql_injection", "location": "fn_name", "fix": "..."}]}}'
    ),
    "data_cleaning_easy": (
        "Find all missing (null) values by field+row, and identify duplicate row IDs.\n"
        'Payload format: {"agent": "data_cleaning", "task_id": "data_cleaning_easy", "payload": {"missing": ["age (row 2)"], "duplicates": [1, 3]}}'
    ),
    "data_cleaning_medium": (
        "Identify all data quality issues by field, and return the fully cleaned dataset.\n"
        'Payload format: {"agent": "data_cleaning", "task_id": "data_cleaning_medium", "payload": {"issues": {"age": "description"}, "cleaned_data": [...]}}'
    ),
    "data_cleaning_hard": (
        "Detect outliers (IQR/z-score), find missing values, and return cleaned dataset with imputed values.\n"
        'Payload format: {"agent": "data_cleaning", "task_id": "data_cleaning_hard", "payload": {"outliers": [4, 8], "missing": [6, 11], "cleaned_data": [...]}}'
    ),
    "content_moderation_easy": (
        "Classify each post as 'safe' or 'harmful'.\n"
        'Payload format: {"agent": "content_moderation", "task_id": "content_moderation_easy", "payload": {"classifications": [{"id": "c1", "label": "harmful"}]}}'
    ),
    "content_moderation_medium": (
        "Classify each post as 'safe' or 'harmful'. Watch for sarcasm, subtle toxicity, and implicit hostility.\n"
        'Payload format: {"agent": "content_moderation", "task_id": "content_moderation_medium", "payload": {"classifications": [{"id": "m1", "label": "harmful", "reason": "..."}]}}'
    ),
    "content_moderation_hard": (
        "Each case has the SAME text in TWO different contexts. Determine correct label for each context.\n"
        'Payload format: {"agent": "content_moderation", "task_id": "content_moderation_hard", "payload": {"decisions": [{"id": "h1", "context_a_label": "safe", "context_b_label": "harmful"}]}}'
    ),
}


# ==============================================================================
# ENVIRONMENT
# ==============================================================================

class MetaEnvironment(Environment):
    SUPPORTS_CONCURRENT_SESSIONS: bool = True

    def __init__(self):
        self._state = State(episode_id=str(uuid4()), step_count=0)
        self._current_task_id = None
        self._current_agent_context = {}
        self._current_grader_context = {}
        self._episode_scores = []

    def reset(self) -> MetaObservation:
        self._state = State(episode_id=str(uuid4()), step_count=0)
        self._current_task_id = None
        self._current_agent_context = {}
        self._current_grader_context = {}
        self._episode_scores = []
        return MetaObservation(
            agent="meta",
            task_id="",
            difficulty="",
            context={},
            instructions=(
                "Welcome to Meta Multi-Agent Environment v2!\n"
                "4 agents x 3 tasks = 12 tasks total.\n"
                "Agents: email_triage | code_review | data_cleaning | content_moderation\n"
                "Tasks:  <agent>_easy | <agent>_medium | <agent>_hard\n\n"
                'Send actions as: {"action": {"message": "{\\"agent\\": \\"<agent>\\", \\"task_id\\": \\"<task_id>\\", \\"payload\\": {...}}"}}\n'
                "Use GET /tasks to see all tasks and exact payload schemas."
            ),
            feedback="Environment reset. Ready for episode.",
            score=0.0,
            partial_credits={},
            done=False,
            reward=0.0,
        )

    def _load_context(self, task_id: str):
        if task_id == "email_triage_easy":
            email = random.choice(EMAIL_EASY_VARIANTS)
            agent_ctx  = {"email": {k: v for k, v in email.items() if k != "label"}}
            grader_ctx = {"email": email}
            return agent_ctx, grader_ctx, "easy"
        elif task_id == "email_triage_medium":
            agent_ctx  = {"emails": [{k: v for k, v in e.items() if k not in ("priority","category")} for e in EMAIL_MEDIUM_EMAILS]}
            grader_ctx = {"emails": EMAIL_MEDIUM_EMAILS}
            return agent_ctx, grader_ctx, "medium"
        elif task_id == "email_triage_hard":
            case = random.choice(EMAIL_HARD_CASES)
            agent_ctx  = {"email": {k: v for k, v in case.items() if k != "expected_elements"}}
            grader_ctx = {"email": case}
            return agent_ctx, grader_ctx, "hard"
        elif task_id == "code_review_easy":
            variant = random.choice(CODE_EASY_VARIANTS)
            agent_ctx  = {"code": variant["code"]}
            grader_ctx = {"code": variant["code"], "keywords": variant["keywords"]}
            return agent_ctx, grader_ctx, "easy"
        elif task_id == "code_review_medium":
            ctx = {"code": CODE_MEDIUM["code"]}
            return ctx, ctx, "medium"
        elif task_id == "code_review_hard":
            ctx = {"code": CODE_HARD["code"]}
            return ctx, ctx, "hard"
        elif task_id == "data_cleaning_easy":
            ctx = {"data": DATA_EASY["data"]}
            return ctx, ctx, "easy"
        elif task_id == "data_cleaning_medium":
            ctx = {"data": DATA_MEDIUM["data"]}
            return ctx, ctx, "medium"
        elif task_id == "data_cleaning_hard":
            ctx = {"data": DATA_HARD["data"]}
            return ctx, ctx, "hard"
        elif task_id == "content_moderation_easy":
            agent_ctx  = {"posts": [{k: v for k, v in p.items() if k != "label"} for p in MOD_EASY]}
            grader_ctx = {"posts": MOD_EASY}
            return agent_ctx, grader_ctx, "easy"
        elif task_id == "content_moderation_medium":
            agent_ctx  = {"posts": [{k: v for k, v in p.items() if k != "label"} for p in MOD_MEDIUM]}
            grader_ctx = {"posts": MOD_MEDIUM}
            return agent_ctx, grader_ctx, "medium"
        elif task_id == "content_moderation_hard":
            agent_ctx  = {"cases": [{k: v for k, v in c.items() if k not in ("label_a","label_b","reason_a","reason_b")} for c in MOD_HARD]}
            grader_ctx = {"cases": MOD_HARD}
            return agent_ctx, grader_ctx, "hard"
        else:
            raise ValueError(f"Unknown task_id: '{task_id}'. Use GET /tasks to see valid IDs.")

    def _grade(self, task_id, payload, grader_context):
        if task_id == "email_triage_easy":       return grade_email_easy(payload, grader_context)
        elif task_id == "email_triage_medium":   return grade_email_medium(payload, grader_context)
        elif task_id == "email_triage_hard":     return grade_email_hard(payload, grader_context)
        elif task_id == "code_review_easy":      return grade_code_easy(payload, grader_context)
        elif task_id == "code_review_medium":    return grade_code_medium(payload)
        elif task_id == "code_review_hard":      return grade_code_hard(payload)
        elif task_id == "data_cleaning_easy":    return grade_data_easy(payload)
        elif task_id == "data_cleaning_medium":  return grade_data_medium(payload)
        elif task_id == "data_cleaning_hard":    return grade_data_hard(payload)
        elif task_id == "content_moderation_easy":   return grade_mod_easy(payload)
        elif task_id == "content_moderation_medium": return grade_mod_medium(payload)
        elif task_id == "content_moderation_hard":   return grade_mod_hard(payload)
        return 0.0, "Unknown task.", {}

    def step(self, action: MetaAction) -> MetaObservation:  # type: ignore[override]
        self._state.step_count += 1

        try:
            data    = json.loads(action.message)
            agent   = data.get("agent", "")
            task_id = data.get("task_id", "")
            payload = data.get("payload", {})
        except (json.JSONDecodeError, Exception) as e:
            return MetaObservation(
                agent="error", task_id="", difficulty="",
                context={},
                instructions='message must be valid JSON: {"agent": "...", "task_id": "...", "payload": {...}}',
                feedback=f"JSON parse error: {e}. Check your message format.",
                score=0.0, partial_credits={}, done=True, reward=0.0,
            )

        if not payload or payload == {"_probe": True}:
            try:
                agent_ctx, grader_ctx, difficulty = self._load_context(task_id)
                self._current_agent_context  = agent_ctx
                self._current_grader_context = grader_ctx
                self._current_task_id = task_id
            except ValueError:
                difficulty = ""
                agent_ctx  = {}

            is_probe = payload == {"_probe": True}
            return MetaObservation(
                agent=agent, task_id=task_id, difficulty=difficulty,
                context=agent_ctx,
                instructions=INSTRUCTIONS.get(task_id, "Use GET /tasks for payload schema."),
                feedback="Probe: context loaded. Submit a real payload to get scored." if is_probe else "Empty payload. Use GET /tasks to see required payload fields.",
                score=0.0, partial_credits={}, done=is_probe, reward=-0.1 if not is_probe else 0.0,
            )

        try:
            if task_id != self._current_task_id:
                agent_ctx, grader_ctx, difficulty = self._load_context(task_id)
                self._current_agent_context  = agent_ctx
                self._current_grader_context = grader_ctx
                self._current_task_id = task_id
            else:
                agent_ctx  = self._current_agent_context
                grader_ctx = self._current_grader_context
                _, __, difficulty = self._load_context(task_id)
        except ValueError as e:
            return MetaObservation(
                agent=agent, task_id=task_id, difficulty="",
                context={},
                instructions="Use GET /tasks to see valid task IDs.",
                feedback=f"{e}",
                score=0.0, partial_credits={}, done=True, reward=0.0,
            )

        score, feedback, partial_credits = self._grade(task_id, payload, grader_ctx)
        self._episode_scores.append(score)

        return MetaObservation(
            agent=agent,
            task_id=task_id,
            difficulty=difficulty,
            context=agent_ctx,
            instructions=INSTRUCTIONS.get(task_id, ""),
            feedback=feedback,
            score=score,
            partial_credits=partial_credits,
            done=True,
            reward=score,
            metadata={
                "step": self._state.step_count,
                "episode_avg_score": round(sum(self._episode_scores) / len(self._episode_scores), 3),
            },
        )

    @property
    def state(self) -> State:
        return self._state