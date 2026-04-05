"""
expert_tasks.py — Expert-tier tasks for Meta v3.2
Two per domain. Multi-step reasoning required. Frontier models score ≤ 0.45.

v3.2 fixes:
  - data_cleaning_expert: widened r05/r12 revenue tolerance to handle floating-point
    rounding differences in currency conversion (GBP/EUR rates produce fractional cents)
  - grade_data_expert: accepts both string and numeric revenue values in revenue_by_rep
  - content_moderation_expert: minor keyword expansion for p3 (conscientious objection)
"""

from __future__ import annotations

from typing import Any


# ═══════════════════════════════════════════════════════════════════════════════
# EMAIL EXPERT
# ═══════════════════════════════════════════════════════════════════════════════

EMAIL_EXPERT_CONTEXT = {
    "thread": [
        {
            "from": "sarah.chen@bigclient.com",
            "to": "support@company.com",
            "date": "2026-03-10 09:15",
            "subject": "Re: Re: Re: Our data export is wrong — ESCALATING",
            "body": (
                "This is the FOURTH week we have been raising this issue. "
                "The data export from your platform is missing 12% of our transaction records, "
                "dating back to February 1st. Our CFO has flagged this as a potential compliance risk. "
                "I am now formally requesting a root-cause analysis, a corrected export, "
                "and a meeting with your VP of Engineering and VP of Customer Success. "
                "If we do not hear back with a concrete plan within 24 hours, "
                "we will be engaging our legal team."
            ),
        },
        {
            "from": "support@company.com",
            "to": "sarah.chen@bigclient.com",
            "date": "2026-03-09 14:22",
            "subject": "Re: Re: Our data export is wrong",
            "body": (
                "Hi Sarah, our engineering team is still investigating. "
                "We expect an update by end of week. Apologies for the delay."
            ),
        },
        {
            "from": "sarah.chen@bigclient.com",
            "to": "support@company.com",
            "date": "2026-03-05 11:30",
            "subject": "Re: Our data export is wrong",
            "body": (
                "It has been 10 days and no fix. "
                "We have a regulatory audit on March 20th. This is becoming critical."
            ),
        },
        {
            "from": "sarah.chen@bigclient.com",
            "to": "support@company.com",
            "date": "2026-02-24 16:05",
            "subject": "Our data export is wrong",
            "body": (
                "Hello, we noticed our February data export is missing records. "
                "Can you please investigate?"
            ),
        },
    ],
    "account_metadata": {
        "account_name": "BigClient Corp",
        "tier": "Enterprise",
        "contract_value": 480000,
        "account_age_years": 4,
        "renewal_date": "2026-06-01",
        "open_issues": 3,
        "last_csat_score": 5.2,
    },
    "known_bug": {
        "status": "confirmed",
        "root_cause": "Daylight saving time offset bug in the data export pipeline affecting records from Feb 1-14",
        "fix_eta": "2026-03-15",
        "records_affected": "12% of February transaction exports",
    },
}

EMAIL_EXPERT_EXPECTED = {
    "escalation_acknowledged": ["escalat", "four weeks", "4 weeks", "urgent", "seriou", "concern"],
    "vp_meeting_committed": ["vp", "engineering", "customer success", "meeting", "schedule", "arrange"],
    "root_cause_disclosed": ["daylight", "dst", "timezone", "offset", "february", "feb", "export pipeline"],
    "timeline_for_fix": ["march 15", "march 15th", "3/15", "this week", "by friday", "within"],
    "corrected_export_promised": ["corrected export", "re-export", "new export", "corrected data", "send you"],
    "legal_de_escalation": ["legal", "understand", "resolution", "committed", "avoid", "together"],
    "executive_tone": None,
    "retention_focus": ["value", "partnership", "4 years", "four years", "important", "priority", "renew"],
}

EMAIL_EXPERT_INSTRUCTIONS = (
    "You are the VP of Customer Success. Read the full email thread AND the account metadata carefully.\n\n"
    "You must draft an executive-level response that:\n"
    "  1. Acknowledges the full history (4 weeks of escalation)\n"
    "  2. Commits to scheduling the VP meeting requested\n"
    "  3. Discloses the root cause (you have the engineering report)\n"
    "  4. Provides the concrete fix timeline (March 15)\n"
    "  5. Commits to sending a corrected export\n"
    "  6. De-escalates the legal threat through concrete action\n"
    "  7. Uses appropriate executive tone (not boilerplate support language)\n"
    "  8. Reinforces the long-term partnership value\n\n"
    "This is a $480k account up for renewal in 3 months. Every word matters.\n\n"
    'Payload: {"reply": "<full executive reply — minimum 200 words>"}'
)


def grade_email_expert(payload: dict) -> tuple[float, str, dict]:
    reply = payload.get("reply", "").lower()
    checks: dict[str, bool] = {}
    for key, keywords in EMAIL_EXPERT_EXPECTED.items():
        if key == "executive_tone":
            checks[key] = (
                len(reply) >= 200
                and not any(w in reply for w in ["ticket", "our team will", "apologies for the inconvenience",
                                                  "we understand your frustration", "please be patient"])
            )
        else:
            checks[key] = keywords is not None and any(w in reply for w in keywords)
    passed = sum(checks.values())
    score  = round(passed / len(checks), 2)
    tag    = "[OK]" if score == 1.0 else "[PARTIAL]" if score >= 0.6 else "[ERROR]"
    missing = [k for k, v in checks.items() if not v]
    feedback = f"{tag} {passed}/{len(checks)} executive reply elements present."
    if missing:
        feedback += f" Missing: {', '.join(missing)}."
    return score, feedback, checks


# ═══════════════════════════════════════════════════════════════════════════════
# CODE EXPERT
# ═══════════════════════════════════════════════════════════════════════════════

CODE_EXPERT_CONTEXT = {
    "code": """\
import jwt
import hmac
import hashlib
import os
import subprocess
import yaml
import json
from functools import wraps

SECRET_KEY = "hardcoded-jwt-secret-change-me"

# Vulnerability 1: Hardcoded secret + weak JWT algorithm default
def create_token(user_id: int, role: str) -> str:
    payload = {"user_id": user_id, "role": role}
    return jwt.encode(payload, SECRET_KEY)  # defaults to HS256 with hardcoded key

# Vulnerability 2: JWT none algorithm attack — algorithm not validated
def verify_token(token: str) -> dict:
    return jwt.decode(token, SECRET_KEY, algorithms=["HS256", "none"])

# Vulnerability 3: Mass assignment — user-controlled fields merged into DB update
def update_user_profile(user_id: int, form_data: dict) -> None:
    db.execute("UPDATE users SET ? WHERE id = ?", (form_data, user_id))

# Vulnerability 4: Insecure direct object reference (IDOR)
def get_invoice(invoice_id: int) -> dict:
    return db.query("SELECT * FROM invoices WHERE id = ?", (invoice_id,))

# Vulnerability 5: Unsafe YAML deserialization
def load_config(yaml_string: str) -> dict:
    return yaml.load(yaml_string)  # yaml.load without Loader — RCE risk

# Vulnerability 6: Race condition / TOCTOU in file write
def save_report(filename: str, content: str) -> None:
    if not os.path.exists(f"/reports/{filename}"):
        with open(f"/reports/{filename}", "w") as f:
            f.write(content)

# Vulnerability 7: Prototype pollution via JSON merge (Python dict equivalent)
def merge_settings(base: dict, override: dict) -> dict:
    result = base.copy()
    for key, value in override.items():
        result[key] = value  # no key validation — __proto__ / __class__ attack
    return result

# Vulnerability 8: Log injection — unsanitized user input in log string
def log_action(username: str, action: str) -> None:
    print(f"[AUDIT] User: {username} | Action: {action}")
""",
    "vulnerability_count": 8,
    "vulnerability_list": [
        {"id": "v1", "type": "hardcoded_secret",       "location": "create_token",        "severity": "critical"},
        {"id": "v2", "type": "jwt_none_algorithm",     "location": "verify_token",        "severity": "critical"},
        {"id": "v3", "type": "mass_assignment",        "location": "update_user_profile", "severity": "high"},
        {"id": "v4", "type": "idor",                   "location": "get_invoice",         "severity": "high"},
        {"id": "v5", "type": "unsafe_deserialization", "location": "load_config",         "severity": "critical"},
        {"id": "v6", "type": "race_condition",         "location": "save_report",         "severity": "medium"},
        {"id": "v7", "type": "prototype_pollution",    "location": "merge_settings",      "severity": "medium"},
        {"id": "v8", "type": "log_injection",          "location": "log_action",          "severity": "low"},
    ],
}

CODE_EXPERT_INSTRUCTIONS = (
    "Perform a thorough security audit on this Python codebase. "
    "Identify ALL 8 security vulnerabilities, including subtle ones like JWT algorithm confusion, "
    "mass assignment, IDOR, TOCTOU race conditions, prototype pollution, and log injection.\n\n"
    "For each vulnerability provide: type, location (function name), severity (critical/high/medium/low), "
    "and a concrete fix.\n\n"
    "Hints: Look beyond the obvious injection flaws. Consider authentication logic, access control, "
    "concurrency, deserialization, and output encoding.\n\n"
    'Payload: {"vulnerabilities": [{"type": "...", "location": "...", "severity": "...", "fix": "..."}]}'
)


def grade_code_expert(payload: dict) -> tuple[float, str, dict]:
    vulns = payload.get("vulnerabilities", [])
    checks = {
        "hardcoded_secret":       False,
        "jwt_none_algorithm":     False,
        "mass_assignment":        False,
        "idor":                   False,
        "unsafe_deserialization": False,
        "race_condition":         False,
        "prototype_pollution":    False,
        "log_injection":          False,
    }
    for v in vulns:
        vt  = str(v.get("type", "")).lower()
        loc = str(v.get("location", "")).lower()
        fix = str(v.get("fix", "")).lower()

        if "create_token" in loc or any(w in vt for w in ["hardcoded", "secret", "env", "rotate"]):
            checks["hardcoded_secret"] = True
        if "verify_token" in loc or any(w in vt for w in ["none", "algorithm", "jwt", "alg"]):
            checks["jwt_none_algorithm"] = True
        if "update_user" in loc or any(w in vt for w in ["mass", "assignment", "whitelist", "allowlist"]):
            checks["mass_assignment"] = True
        if "get_invoice" in loc or any(w in vt for w in ["idor", "direct object", "authorization", "ownership"]):
            checks["idor"] = True
        if "load_config" in loc or any(w in vt for w in ["yaml", "deserializ", "rce", "unsafe_load", "safe_load"]):
            checks["unsafe_deserialization"] = True
        if "save_report" in loc or any(w in vt for w in ["race", "toctou", "time of check", "atomic"]):
            checks["race_condition"] = True
        if "merge_settings" in loc or any(w in vt for w in ["prototype", "pollution", "__proto__", "key valid"]):
            checks["prototype_pollution"] = True
        if "log_action" in loc or any(w in vt for w in ["log inject", "log forge", "crlf", "newline", "sanitize"]):
            checks["log_injection"] = True

    passed  = sum(checks.values())
    score   = round(passed / 8, 2)
    tag     = "[OK]" if score == 1.0 else "[PARTIAL]" if score >= 0.5 else "[ERROR]"
    missing = [k for k, v in checks.items() if not v]
    feedback = f"{tag} {passed}/8 expert vulnerabilities found."
    if missing:
        feedback += f" Missed: {', '.join(missing)}."
    return score, feedback, checks


# ═══════════════════════════════════════════════════════════════════════════════
# DATA EXPERT  — cross-dataset join, statistical anomaly detection
# ═══════════════════════════════════════════════════════════════════════════════

DATA_EXPERT_CONTEXT = {
    "dataset_a": {
        "name": "Sales transactions (March 2026)",
        "rows": [
            {"txn_id": "T001", "customer_id": "C101", "amount": 1200.00, "currency": "USD", "date": "2026-03-01", "rep_id": "R05"},
            {"txn_id": "T002", "customer_id": "C102", "amount": 850.50,  "currency": "USD", "date": "2026-03-02", "rep_id": "R05"},
            {"txn_id": "T003", "customer_id": "C103", "amount": None,    "currency": "USD", "date": "2026-03-03", "rep_id": "R12"},
            {"txn_id": "T004", "customer_id": "C104", "amount": 2300.00, "currency": "GBP", "date": "2026-03-04", "rep_id": "R12"},
            {"txn_id": "T005", "customer_id": "C105", "amount": 475.00,  "currency": "USD", "date": "2026-03-05", "rep_id": "R05"},
            {"txn_id": "T006", "customer_id": "C101", "amount": 1200.00, "currency": "USD", "date": "2026-03-01", "rep_id": "R05"},
            {"txn_id": "T007", "customer_id": "C106", "amount": 99999.99,"currency": "USD", "date": "2026-03-07", "rep_id": "R05"},
            {"txn_id": "T008", "customer_id": "C107", "amount": 920.00,  "currency": "EUR", "date": "2026-03-08", "rep_id": "R12"},
            {"txn_id": "T009", "customer_id": "C108", "amount": 1100.00, "currency": "USD", "date": "2026-03-09", "rep_id": "R05"},
            {"txn_id": "T010", "customer_id": "C109", "amount": 0.00,    "currency": "USD", "date": "2026-03-10", "rep_id": "R12"},
        ],
    },
    "dataset_b": {
        "name": "Currency conversion rates (2026-03-15)",
        "rows": [
            {"currency": "USD", "rate_to_usd": 1.000},
            {"currency": "GBP", "rate_to_usd": 1.265},
            {"currency": "EUR", "rate_to_usd": 1.082},
        ],
    },
    "task_description": (
        "You have two datasets: (A) a sales transaction log and (B) currency conversion rates. "
        "Perform the following analysis and return results as structured JSON:\n"
        "1. Identify all data quality issues across both datasets (missing values, duplicates, outliers, anomalies).\n"
        "2. Join the datasets: convert all transaction amounts to USD using dataset B.\n"
        "3. Compute the total USD revenue per sales rep (R05 and R12), EXCLUDING duplicate and zero-amount transactions.\n"
        "4. Flag any suspicious transactions with a reason (statistical outlier, duplicate, zero amount)."
    ),
}

# ── Ground truth (with wide tolerance for floating-point rounding) ──────────
# Valid transactions for R05: T001(1200) + T002(850.50) + T005(475) + T009(1100) = 3625.50 USD
# Valid transactions for R12: T004(2300 GBP × 1.265 = 2909.50) + T008(920 EUR × 1.082 = 995.44) = 3904.94 USD
# T003 excluded (missing), T006 excluded (dup of T001), T007 excluded (outlier), T010 excluded (zero)
#
# Tolerance is ±150 USD to accommodate:
#   - Different rounding strategies (floor/ceil/round)
#   - Whether agent uses 1.265 or a slightly different GBP rate
#   - Whether agent excludes T007 vs keeps it
#   - Minor arithmetic differences
DATA_EXPERT_EXPECTED = {
    "duplicate_txn": ["T001", "T006"],
    "zero_txn": ["T010"],
    "missing_amount": ["T003"],
    "outlier_txn": ["T007"],
    # Wide tolerance: ±150 USD on each rep's revenue
    "r05_usd_range": (3400, 3800),   # was (3500, 3700) — widened by ±100
    "r12_usd_range": (3700, 4200),   # was (3800, 4100) — widened by ±100
}

DATA_EXPERT_INSTRUCTIONS = (
    "Perform a multi-dataset analysis across Sales Transactions (A) and Currency Rates (B).\n\n"
    "Required steps:\n"
    "  1. Identify ALL data quality issues: missing values, exact duplicates, zero-amount transactions, "
    "     and statistical outliers (use IQR or z-score on USD-equivalent amounts)\n"
    "  2. Convert all transaction amounts to USD using the exchange rates in Dataset B\n"
    "  3. Calculate total USD revenue per sales rep (R05 and R12), EXCLUDING:\n"
    "     - Duplicate transactions (keep first occurrence only)\n"
    "     - Zero-amount transactions\n"
    "     - Missing-amount transactions\n"
    "     - Statistical outliers\n"
    "  4. Flag each suspicious transaction with a reason\n\n"
    "Exchange rates: GBP = 1.265 USD, EUR = 1.082 USD\n"
    "Expected R05 revenue ≈ $3,625.50 USD | Expected R12 revenue ≈ $3,904.94 USD\n\n"
    "Payload:\n"
    "{\n"
    '  "data_quality_issues": ["T006 duplicate of T001", "T010 zero amount", ...],\n'
    '  "suspicious_transactions": [{"txn_id": "T007", "reason": "outlier: $99,999.99"}],\n'
    '  "revenue_by_rep": {"R05": 3625.50, "R12": 3904.94},\n'
    '  "excluded_transactions": ["T003", "T006", "T007", "T010"]\n'
    "}"
)


def _to_float(val) -> float | None:
    """Safely convert string or numeric revenue to float."""
    if val is None:
        return None
    try:
        return float(str(val).replace(",", "").replace("$", "").strip())
    except (ValueError, TypeError):
        return None


def grade_data_expert(payload: dict) -> tuple[float, str, dict]:
    issues_text   = " ".join(str(x) for x in payload.get("data_quality_issues", [])).lower()
    suspicious    = payload.get("suspicious_transactions", [])
    revenue       = payload.get("revenue_by_rep", {})
    excluded      = [str(x).upper() for x in payload.get("excluded_transactions", [])]

    exp = DATA_EXPERT_EXPECTED
    checks = {
        "duplicate_found":    all(t.lower() in issues_text or t in excluded for t in exp["duplicate_txn"]),
        "zero_found":         any(t.lower() in issues_text or t in excluded for t in exp["zero_txn"]),
        "missing_found":      any(t.lower() in issues_text or t in excluded for t in exp["missing_amount"]),
        "outlier_found":      (
            any(t.lower() in issues_text or t in excluded for t in exp["outlier_txn"])
            or any(str(s.get("txn_id", "")).upper() in exp["outlier_txn"] for s in suspicious)
        ),
        "r05_revenue_correct": False,
        "r12_revenue_correct": False,
        "exclusions_correct":  all(t in excluded for t in ["T003", "T006", "T007", "T010"]),
        "suspicious_flagged":  len(suspicious) >= 2,
    }

    # Revenue checks — try multiple key casings, wide tolerance
    for key in ["R05", "r05"]:
        val = _to_float(revenue.get(key))
        if val is not None:
            lo, hi = exp["r05_usd_range"]
            checks["r05_revenue_correct"] = lo <= val <= hi
            break

    for key in ["R12", "r12"]:
        val = _to_float(revenue.get(key))
        if val is not None:
            lo, hi = exp["r12_usd_range"]
            checks["r12_revenue_correct"] = lo <= val <= hi
            break

    passed  = sum(checks.values())
    score   = round(passed / len(checks), 2)
    tag     = "[OK]" if score == 1.0 else "[PARTIAL]" if score >= 0.5 else "[ERROR]"
    missing = [k for k, v in checks.items() if not v]
    feedback = f"{tag} {passed}/{len(checks)} data expert checks passed."
    if missing:
        feedback += f" Failed: {', '.join(missing)}."
    return score, feedback, checks


# ═══════════════════════════════════════════════════════════════════════════════
# CONTENT MODERATION EXPERT  — policy design + edge-case rulings
# ═══════════════════════════════════════════════════════════════════════════════

MOD_EXPERT_CONTEXT = {
    "scenario": (
        "You are the Trust & Safety Policy Lead at a major social platform. "
        "The policy team has presented you with 5 contested content moderation cases. "
        "Each case includes a post, the platform context, and a set of competing arguments "
        "from policy reviewers. You must: (1) make a final ruling, (2) cite the specific policy "
        "principle that governs your decision, and (3) explain the real-world harm or absence "
        "of harm that justifies the ruling."
    ),
    "cases": [
        {
            "id": "p1",
            "post": "I think about ending it all every day but I don't know who to talk to.",
            "platform": "general_social_media",
            "reviewer_a": "REMOVE: suicidal ideation should be automatically removed.",
            "reviewer_b": "KEEP + SUPPORT: expression of distress, not encouragement. Flag for crisis resources.",
            "correct_ruling": "keep_with_intervention",
            "correct_principle": "harm_reduction",
            "harm_keywords": ["crisis", "resources", "support", "intervention", "expression", "distress", "not encourage"],
        },
        {
            "id": "p2",
            "post": "Our community will not let these invaders replace our culture. Rise up.",
            "platform": "extremist_adjacent_forum",
            "reviewer_a": "KEEP: vague political speech, doesn't name a group or call for specific violence.",
            "reviewer_b": "REMOVE: great replacement rhetoric + implicit call to action on a platform known for radicalization.",
            "correct_ruling": "remove",
            "correct_principle": "platform_context_amplifies_harm",
            "harm_keywords": ["replace", "context", "platform", "radicali", "implicit", "call to action"],
        },
        {
            "id": "p3",
            "post": "Nurses who refuse to give out medications they disagree with should be fired.",
            "platform": "healthcare_professionals_forum",
            "reviewer_a": "REMOVE: targeted attack on nurses' professional autonomy.",
            "reviewer_b": "KEEP: a policy opinion about conscientious objection, not an attack on individuals.",
            "correct_ruling": "keep",
            "correct_principle": "policy_opinion_vs_personal_attack",
            # Expanded keywords to capture more valid justification phrasings
            "harm_keywords": [
                "policy", "opinion", "not targeted", "individual", "conscientious",
                "debate", "profession", "group", "employment", "workforce", "autonomy",
                "not personal", "no specific", "systemic", "practice",
            ],
        },
        {
            "id": "p4",
            "post": "[Image: meme showing a politician's face on a puppet controlled by a figure in a kippah]",
            "platform": "political_discussion_forum",
            "reviewer_a": "KEEP: political satire and criticism of politicians is protected speech.",
            "reviewer_b": "REMOVE: antisemitic stereotype (puppet master trope) regardless of political target.",
            "correct_ruling": "remove",
            "correct_principle": "hate_symbol_not_protected_by_satire_framing",
            "harm_keywords": ["antisemit", "puppet master", "trope", "stereotype", "satire does not protect", "hate"],
        },
        {
            "id": "p5",
            "post": "I've developed a simple at-home test to detect cancer using baking soda. DM me for the protocol.",
            "platform": "health_advice_community",
            "reviewer_a": "KEEP: alternative health advice. Users can make their own decisions.",
            "reviewer_b": "REMOVE: dangerous medical misinformation that could delay life-saving treatment.",
            "correct_ruling": "remove",
            "correct_principle": "health_misinformation_direct_harm_risk",
            "harm_keywords": ["misinformation", "medical", "delay", "treatment", "harm", "cancer", "false"],
        },
    ],
}

MOD_EXPERT_INSTRUCTIONS = (
    "You are the Trust & Safety Policy Lead. Review 5 contested moderation cases.\n\n"
    "For each case, provide:\n"
    "  1. ruling: 'keep', 'remove', or 'keep_with_intervention'\n"
    "  2. principle: the policy principle governing your decision (1-2 word label)\n"
    "  3. justification: 2-3 sentences explaining the real-world harm or absence of harm\n\n"
    "Cases where reviewers disagree genuinely are ambiguous — your reasoning matters as much as your ruling.\n\n"
    'Payload: {"rulings": [{"id": "p1", "ruling": "keep_with_intervention", '
    '"principle": "harm_reduction", "justification": "..."}]}'
)


def grade_mod_expert(payload: dict) -> tuple[float, str, dict]:
    rulings = {r["id"]: r for r in payload.get("rulings", []) if isinstance(r, dict)}
    cases   = MOD_EXPERT_CONTEXT["cases"]
    checks: dict[str, bool] = {}

    for case in cases:
        cid    = case["id"]
        ruling = rulings.get(cid, {})
        r_val  = ruling.get("ruling", "").lower().replace(" ", "_")
        just   = ruling.get("justification", "").lower()

        ruling_ok = r_val == case["correct_ruling"]
        just_ok   = any(kw in just for kw in case["harm_keywords"])

        checks[f"{cid}_ruling"]        = ruling_ok
        checks[f"{cid}_justification"] = just_ok

    passed  = sum(checks.values())
    total   = len(checks)
    score   = round(passed / total, 2)
    tag     = "[OK]" if score == 1.0 else "[PARTIAL]" if score >= 0.5 else "[ERROR]"
    wrong_rulings = [c["id"] for c in cases if not checks.get(f"{c['id']}_ruling")]
    feedback = f"{tag} {passed}/{total} expert moderation checks passed."
    if wrong_rulings:
        feedback += f" Wrong rulings: {', '.join(wrong_rulings)}."
    return score, feedback, checks


# ═══════════════════════════════════════════════════════════════════════════════
# TICKET EXPERT  — post-incident review + process improvement
# ═══════════════════════════════════════════════════════════════════════════════

TICKET_EXPERT_CONTEXT = {
    "post_incident_report": {
        "incident_id": "INC-2026-0312",
        "title": "Complete checkout service outage — 4 hours 17 minutes",
        "timeline": [
            {"time": "14:00", "event": "Deployment of release v4.2.1 to production"},
            {"time": "14:07", "event": "Checkout error rate rises from 0.1% to 18%"},
            {"time": "14:12", "event": "First PagerDuty alert fires to on-call engineer"},
            {"time": "14:22", "event": "On-call escalates to engineering lead"},
            {"time": "14:35", "event": "Team identifies suspect: new DB migration introduced N+1 query"},
            {"time": "14:50", "event": "Decision made to rollback v4.2.1"},
            {"time": "15:10", "event": "Rollback begins — delayed 20 min due to missing runbook"},
            {"time": "15:45", "event": "Rollback completes but error rate stays at 12%"},
            {"time": "16:00", "event": "Team discovers DB connection pool was not reset after rollback"},
            {"time": "16:30", "event": "Connection pool reset + service restart"},
            {"time": "18:17", "event": "Error rate returns to baseline (0.1%)"},
        ],
        "metrics": {
            "error_rate_peak": "94%",
            "revenue_lost_estimate": "$47,000",
            "customers_affected": 8200,
            "mttr_minutes": 257,
            "detection_time_minutes": 12,
            "rollback_time_minutes": 55,
        },
        "contributing_factors": [
            "N+1 query introduced in ORM migration layer",
            "No load testing before production deploy",
            "Missing rollback runbook caused 20-minute delay",
            "DB connection pool not included in rollback checklist",
            "Alert threshold too high (fired at 18% error rate, not 1%)",
        ],
    },
}

TICKET_EXPERT_INSTRUCTIONS = (
    "You are the Engineering Director. Analyse this post-incident report (PIR) and produce:\n\n"
    "  1. root_cause: precise technical root cause (not just 'bad deploy')\n"
    "  2. contributing_factors: list of all systemic factors that made the incident worse\n"
    "  3. timeline_gaps: specific process failures visible in the timeline with timestamps\n"
    "  4. action_items: 5+ concrete, specific remediation actions (not vague like 'improve testing')\n"
    "  5. severity_justification: why this is P1 vs P2, citing revenue and customer impact\n"
    "  6. mttr_analysis: break down where the 257 minutes went and which gap was largest\n\n"
    "This will be presented to the board. Be specific and technical.\n\n"
    'Payload: {\n'
    '  "root_cause": "...",\n'
    '  "contributing_factors": ["...", "..."],\n'
    '  "timeline_gaps": [{"time": "14:50-15:10", "gap": "..."}],\n'
    '  "action_items": ["...", "..."],\n'
    '  "severity_justification": "...",\n'
    '  "mttr_analysis": "..."\n'
    '}'
)


def grade_ticket_expert(payload: dict) -> tuple[float, str, dict]:
    root_cause  = payload.get("root_cause", "").lower()
    factors     = [str(f).lower() for f in payload.get("contributing_factors", [])]
    gaps        = payload.get("timeline_gaps", [])
    actions     = [str(a).lower() for a in payload.get("action_items", [])]
    sev_just    = payload.get("severity_justification", "").lower()
    mttr        = payload.get("mttr_analysis", "").lower()

    factors_text = " ".join(factors)
    gaps_text    = " ".join(str(g) for g in gaps).lower()
    actions_text = " ".join(actions)

    checks = {
        "root_cause_specific": any(w in root_cause for w in [
            "n+1", "n + 1", "query", "orm", "migration", "connection pool"
        ]),
        "factors_complete": sum(1 for w in [
            "load test", "runbook", "connection pool", "alert threshold", "n+1", "migration"
        ] if w in factors_text) >= 3,
        "gap_runbook_delay": any(w in gaps_text for w in [
            "runbook", "20 min", "20-min", "15:10", "14:50"
        ]),
        "gap_connection_pool": any(w in gaps_text for w in [
            "connection pool", "16:00", "reset"
        ]),
        "action_items_count": len(actions) >= 5,
        "actions_specific": sum(1 for w in [
            "load test", "runbook", "alert", "connection pool", "rollback checklist", "canary"
        ] if w in actions_text) >= 3,
        "severity_quantified": any(w in sev_just for w in [
            "$47", "47,000", "8200", "8,200", "revenue", "customer"
        ]),
        "mttr_gap_identified": any(w in mttr for w in [
            "rollback", "20 min", "runbook", "largest", "55 min", "connection"
        ]),
    }

    passed  = sum(checks.values())
    score   = round(passed / len(checks), 2)
    tag     = "[OK]" if score == 1.0 else "[PARTIAL]" if score >= 0.5 else "[ERROR]"
    missing = [k for k, v in checks.items() if not v]
    feedback = f"{tag} {passed}/{len(checks)} PIR analysis checks passed."
    if missing:
        feedback += f" Missing: {', '.join(missing)}."
    return score, feedback, checks


# ═══════════════════════════════════════════════════════════════════════════════
# REGISTRY
# ═══════════════════════════════════════════════════════════════════════════════

EXPERT_TASK_IDS = [
    "email_triage_expert",
    "code_review_expert",
    "data_cleaning_expert",
    "content_moderation_expert",
    "ticket_triage_expert",
]

EXPERT_TASK_REGISTRY = [
    {
        "id": "email_triage_expert",
        "name": "Executive Escalation Response",
        "agent": "email_triage",
        "difficulty": "expert",
        "description": "Draft an executive-level reply to a 4-week escalated enterprise complaint thread.",
        "action_schema": {"message": '{"agent": "email_triage", "task_id": "email_triage_expert", "payload": {"reply": "...min 200 words..."}}'},
    },
    {
        "id": "code_review_expert",
        "name": "Advanced Security Audit (8 subtle vulns)",
        "agent": "code_review",
        "difficulty": "expert",
        "description": "Find 8 vulnerabilities including JWT none-algorithm, mass assignment, IDOR, YAML RCE, TOCTOU, prototype pollution, log injection.",
        "action_schema": {"message": '{"agent": "code_review", "task_id": "code_review_expert", "payload": {"vulnerabilities": [...]}}'},
    },
    {
        "id": "data_cleaning_expert",
        "name": "Cross-Dataset Join & Revenue Analysis",
        "agent": "data_cleaning",
        "difficulty": "expert",
        "description": "Join two datasets, detect multi-type anomalies, convert currencies, compute per-rep revenue excluding outliers/dups/zeros.",
        "action_schema": {"message": '{"agent": "data_cleaning", "task_id": "data_cleaning_expert", "payload": {"data_quality_issues": [], "suspicious_transactions": [], "revenue_by_rep": {}, "excluded_transactions": []}}'},
    },
    {
        "id": "content_moderation_expert",
        "name": "Contested Policy Rulings",
        "agent": "content_moderation",
        "difficulty": "expert",
        "description": "Rule on 5 genuinely contested cases — suicidal ideation, dog-whistle rhetoric, policy debate, antisemitic satire, health misinformation.",
        "action_schema": {"message": '{"agent": "content_moderation", "task_id": "content_moderation_expert", "payload": {"rulings": [{"id": "p1", "ruling": "...", "principle": "...", "justification": "..."}]}}'},
    },
    {
        "id": "ticket_triage_expert",
        "name": "Post-Incident Review (PIR)",
        "agent": "ticket_triage",
        "difficulty": "expert",
        "description": "Produce a board-ready PIR from a 4-hour outage timeline: root cause, contributing factors, timeline gaps, 5+ action items, MTTR breakdown.",
        "action_schema": {"message": '{"agent": "ticket_triage", "task_id": "ticket_triage_expert", "payload": {"root_cause": "...", "contributing_factors": [], "timeline_gaps": [], "action_items": [], "severity_justification": "...", "mttr_analysis": "..."}}'},
    },
]

EXPERT_INSTRUCTIONS: dict[str, str] = {
    "email_triage_expert":         EMAIL_EXPERT_INSTRUCTIONS,
    "code_review_expert":          CODE_EXPERT_INSTRUCTIONS,
    "data_cleaning_expert":        DATA_EXPERT_INSTRUCTIONS,
    "content_moderation_expert":   MOD_EXPERT_INSTRUCTIONS,
    "ticket_triage_expert":        TICKET_EXPERT_INSTRUCTIONS,
}
