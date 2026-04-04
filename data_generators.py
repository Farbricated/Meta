"""
data_generators.py — Deterministic procedural data generators for Meta v3.1
Replaces small hand-crafted datasets with richly varied, reproducible data.

Design principles
-----------------
* Every generator takes an `episode_id: str` and seeds Python's stdlib `random`
  with `hash(episode_id + salt)` so the same episode always yields the same data.
* No third-party libs needed — stdlib only (random, string, datetime, hashlib).
* Each generator returns (agent_ctx, grader_ctx) tuples matching existing grader
  contracts so graders need zero changes.

Drop-in replacement usage in Meta_environment.py::_load_context():
    Replace the hardcoded-data blocks with:
        from data_generators import gen_<task>(episode_id)
        agent_ctx, grader_ctx = gen_<task>(episode_id)

Generators provided
-------------------
Email domain
    gen_email_easy(episode_id)     — 1 email, 3-way class, 30 sender/subject combos
    gen_email_medium(episode_id)   — 10 emails, varying priority pool
    gen_email_hard(episode_id)     — customer complaint, 8 scenario templates

Code domain
    gen_code_easy(episode_id)      — 6 code snippet variants
    gen_code_medium(episode_id)    — deterministic (same code, no variant needed)
    gen_code_hard(episode_id)      — deterministic (same code, no variant needed)

Data-cleaning domain
    gen_data_easy(episode_id)      — 6-10 rows, random nulls + one dup pair
    gen_data_medium(episode_id)    — 5 rows, randomised messy formats per field
    gen_data_hard(episode_id)      — 12-16 rows, IQR-detected outliers

Content moderation domain
    gen_mod_easy(episode_id)       — 7 posts drawn from larger pool
    gen_mod_medium(episode_id)     — 8 posts drawn from larger pool
    (hard is already adversarial/static — left unchanged)

Ticket domain
    gen_ticket_easy(episode_id)    — 1 ticket from 8-variant pool
    gen_ticket_medium(episode_id)  — deterministic (same 8 tickets, no variant)
    gen_ticket_hard(episode_id)    — deterministic (same 6 incidents, no variant)
"""

from __future__ import annotations

import hashlib
import random
import string
from copy import deepcopy
from datetime import date, timedelta
from typing import Any


# ── Seeding helper ─────────────────────────────────────────────────────────────

def _rng(episode_id: str, salt: str = "") -> random.Random:
    seed = int(hashlib.md5((episode_id + salt).encode()).hexdigest(), 16)
    return random.Random(seed)


# ═══════════════════════════════════════════════════════════════════════════════
# EMAIL EASY  — 30+ variant pool
# ═══════════════════════════════════════════════════════════════════════════════

_EMAIL_EASY_POOL = [
    # (subject, sender, body, label)
    ("You won $1,000,000!!!", "promo@totally-legit-lottery.com",
     "Click here to claim your prize now! Limited time offer!", "spam"),
    ("Q3 Budget Review — Urgent Action Required", "cfo@company.com",
     "Please review the attached Q3 budget before our board meeting tomorrow at 9 AM.", "important"),
    ("Your weekly digest from Medium", "noreply@medium.com",
     "Top stories this week: AI trends, Python tips, and startup news.", "newsletter"),
    ("CONGRATULATIONS! iPhone 15 Pro is yours!", "winner@prize-alert.net",
     "You have been selected. Click now to claim your free iPhone!", "spam"),
    ("Action Required: Sign the NDA before Friday", "legal@company.com",
     "Please sign the attached NDA before Friday's partnership meeting. Deadline is strict.", "important"),
    ("TechCrunch Newsletter — March 2026", "newsletter@techcrunch.com",
     "This week's top stories in tech, AI, and startups.", "newsletter"),
    ("Claim your $500 Amazon gift card NOW", "deals@amazingoffers.biz",
     "You are today's lucky winner. No purchase necessary. Act fast!", "spam"),
    ("Production incident P1 — please join bridge", "oncall@company.com",
     "We have a P1 production incident. Please join the war room immediately.", "important"),
    ("Developer digest: April 2026", "digest@devweekly.io",
     "This week: Rust 2.0 release, LLM benchmarks, and open-source highlights.", "newsletter"),
    ("FREE vacation cruise — you've been selected!", "winner@vacation-cruise.net",
     "Claim your free cruise for two. Just pay shipping and handling.", "spam"),
    ("Board approval needed: Series B term sheet", "ceo@company.com",
     "Our Series B term sheet requires your signature before the 5 PM deadline today.", "important"),
    ("Product Hunt daily digest", "digest@producthunt.com",
     "Today's top products: AI code review, async stand-ups, no-code CRM.", "newsletter"),
    ("Congratulations — Survey reward $250!", "rewards@surveypanel.net",
     "You qualify for a $250 reward. Complete our 2-minute survey to claim.", "spam"),
    ("HR: Performance review cycle starts Monday", "hr@company.com",
     "The annual performance review cycle begins Monday. Please complete your self-assessment.", "important"),
    ("Hacker News digest: top 10 links this week", "weekly@hackernews.app",
     "Rust, WASM, and the AI bubble: top discussions from the community.", "newsletter"),
    ("Double billing detected on account #AC-8821", "billing@ourplatform.com",
     "We noticed a duplicate charge on your account. Reply to initiate a refund.", "spam"),
    ("Legal: Partnership agreement signature required EOD", "legal@company.com",
     "The partnership agreement with Nexus Corp must be countersigned by 5 PM today.", "important"),
    ("SaaS Weekly — your industry roundup", "editor@saasweekly.com",
     "Churn rates, AI copilots, and the future of vertical SaaS.", "newsletter"),
    ("You have unclaimed crypto rewards!", "support@cryptorewards.io",
     "Wallet 0x4f…a2 has 0.3 ETH waiting. Connect now to claim.", "spam"),
    ("Security alert: admin password reset requested", "security@company.com",
     "An admin-level password reset was requested from IP 198.51.100.42. Verify or block.", "important"),
    ("The Batch — AI newsletter by deeplearning.ai", "batch@deeplearning.ai",
     "Andrew Ng on scaling laws, fine-tuning tips, and this week's papers.", "newsletter"),
    ("Limited offer: 90% off VPN subscription", "deals@vpndeals.biz",
     "Today only: get lifetime VPN access for $1.99. Offer expires midnight.", "spam"),
    ("Vendor invoice #INV-7721 overdue by 14 days", "ar@vendor.com",
     "Invoice #INV-7721 for $12,400 is now 14 days overdue. Please remit payment to avoid service interruption.", "important"),
    ("The Algorithm Newsletter — weekly edition", "hello@thealgorithm.co",
     "ML papers, job listings, and a tutorial on RLHF.", "newsletter"),
    ("Your package was held — verify address", "delivery@postalnow.net",
     "Your package is held due to an address discrepancy. Click to confirm.", "spam"),
    ("Compliance: GDPR audit documentation due Friday", "compliance@company.com",
     "Please upload your GDPR data-processing records to the compliance portal by Friday.", "important"),
    ("Morning Brew — your daily business digest", "hello@morningbrew.com",
     "Markets, tech, and the big stories you need to know today.", "newsletter"),
    ("Account suspended — click to restore", "support@accountalert.biz",
     "Unusual activity detected. Your account has been temporarily suspended.", "spam"),
    ("CTO sync needed: infrastructure cost overrun", "cto@company.com",
     "AWS bill came in 340% over budget. Need your sign-off on emergency cost controls.", "important"),
    ("The Hustle — daily newsletter", "news@thehustle.co",
     "Today's biggest business stories, curated for founders and operators.", "newsletter"),
]


def gen_email_easy(episode_id: str) -> tuple[dict, dict]:
    rng = _rng(episode_id, "email_easy")
    email = dict(zip(["subject", "sender", "body", "label"],
                     rng.choice(_EMAIL_EASY_POOL)))
    email["id"] = "e1"
    agent_ctx  = {"email": {k: v for k, v in email.items() if k != "label"}}
    grader_ctx = {"email": email}
    return agent_ctx, grader_ctx


# ═══════════════════════════════════════════════════════════════════════════════
# EMAIL MEDIUM  — varied priority pools
# ═══════════════════════════════════════════════════════════════════════════════

_CRITICAL_POOL = [
    {"subject": "[ALERT] Production server DOWN", "sender": "ops@company.com",
     "body": "All services unresponsive since 2 AM. Revenue impact: $10k/min.", "priority": 1, "category": "critical"},
    {"subject": "[P1] Database primary down — all writes failing", "sender": "oncall@company.com",
     "body": "The primary DB replica crashed. No write operations possible site-wide.", "priority": 1, "category": "critical"},
    {"subject": "[WARNING] Security alert: unusual login attempt", "sender": "security@company.com",
     "body": "Unauthorised login attempt from IP 45.33.32.156. Verify immediately.", "priority": 1, "category": "critical"},
    {"subject": "[ALERT] DDoS attack in progress", "sender": "security@company.com",
     "body": "We are under a DDoS attack. Site response time is 30s+. Join the war room.", "priority": 1, "category": "critical"},
]

_URGENT_POOL = [
    {"subject": "Acme Corp contract renewal — URGENT", "sender": "sales@company.com",
     "body": "Acme contract expires Friday. They need signature or they walk.", "priority": 2, "category": "business"},
    {"subject": "Legal: Partnership agreement needs signature TODAY", "sender": "legal@company.com",
     "body": "The partnership agreement must be countersigned by EOD or the deal falls through.", "priority": 2, "category": "legal"},
    {"subject": "Series B term sheet — board sign-off required by 5 PM", "sender": "ceo@company.com",
     "body": "VCs need the countersigned term sheet by 5 PM today or the round lapses.", "priority": 2, "category": "legal"},
]

_FINANCE_POOL = [
    {"subject": "Invoice #INV-4521 overdue", "sender": "billing@vendor.com",
     "body": "Invoice of $5,400 was due 3 days ago. Payment needed to avoid suspension.", "priority": 3, "category": "finance"},
    {"subject": "AWS bill 340% over budget", "sender": "finance@company.com",
     "body": "Last month's cloud bill was $82k vs $24k budget. Need approval to proceed.", "priority": 3, "category": "finance"},
    {"subject": "Customer double-charged — refund dispute open", "sender": "billing@company.com",
     "body": "Customer #C-1121 was charged twice. Finance blocked. Needs VP sign-off.", "priority": 3, "category": "finance"},
]

_BUSINESS_POOL = [
    {"subject": "Q4 product launch deck — review needed", "sender": "marketing@company.com",
     "body": "Please review launch slides before Thursday. Launch is next Monday.", "priority": 4, "category": "business"},
    {"subject": "Quarterly board deck — slides need your input", "sender": "ea@company.com",
     "body": "Board meeting is Tuesday. Your section on growth metrics needs updating.", "priority": 4, "category": "business"},
    {"subject": "Key account at risk — needs executive call", "sender": "cs@company.com",
     "body": "TechGiant Corp is threatening churn. They want an exec call this week.", "priority": 4, "category": "business"},
]

_SOCIAL_POOL = [
    {"subject": "Team lunch this Friday?", "sender": "colleague@company.com",
     "body": "Hey, thinking of doing a team lunch Friday. You in?", "priority": 9, "category": "social"},
    {"subject": "Happy Work Anniversary!", "sender": "hr@company.com",
     "body": "Celebrating your 3 years with us!", "priority": 9, "category": "social"},
    {"subject": "Office trivia night — Thursday 7 PM", "sender": "social@company.com",
     "body": "Join us for office trivia Thursday evening. Pizza provided!", "priority": 9, "category": "social"},
]

_NEWSLETTER_POOL = [
    {"subject": "Weekly SaaS digest", "sender": "news@saasdigest.com",
     "body": "Top SaaS stories this week...", "priority": 10, "category": "newsletter"},
    {"subject": "Free AI productivity webinar", "sender": "promo@webinar.io",
     "body": "Join our free webinar on AI tools this Thursday.", "priority": 10, "category": "newsletter"},
    {"subject": "The Batch: AI news weekly", "sender": "batch@deeplearning.ai",
     "body": "Andrew Ng on scaling, fine-tuning, and paper highlights.", "priority": 10, "category": "newsletter"},
]


def gen_email_medium(episode_id: str) -> tuple[dict, dict]:
    """
    Always picks 2 critical, 1 urgent, 1 finance, 2 business, 2 social, 2 newsletter = 10 emails.
    Correct ordering: criticals first, then urgent, finance, business, social, newsletter.
    """
    rng = _rng(episode_id, "email_medium")
    crits   = rng.sample(_CRITICAL_POOL, k=min(2, len(_CRITICAL_POOL)))
    urgents = rng.sample(_URGENT_POOL,   k=min(1, len(_URGENT_POOL)))
    fins    = rng.sample(_FINANCE_POOL,  k=min(1, len(_FINANCE_POOL)))
    bizs    = rng.sample(_BUSINESS_POOL, k=min(2, len(_BUSINESS_POOL)))
    socials = rng.sample(_SOCIAL_POOL,   k=min(2, len(_SOCIAL_POOL)))
    news    = rng.sample(_NEWSLETTER_POOL,k=min(2, len(_NEWSLETTER_POOL)))

    ordered = crits + urgents + fins + bizs + socials + news
    emails = []
    correct_order = []
    for i, e in enumerate(ordered):
        eid = f"m{i+1}"
        emails.append({"id": eid, **e})
        correct_order.append(eid)

    # Shuffle for presentation; keep correct_order as ground truth
    display = emails[:]
    rng.shuffle(display)

    agent_ctx  = {"emails": [{k: v for k, v in e.items() if k not in ("priority", "category")} for e in display]}
    grader_ctx = {"emails": emails, "correct_order": correct_order}
    return agent_ctx, grader_ctx


# ═══════════════════════════════════════════════════════════════════════════════
# EMAIL HARD  — 8 complaint scenario templates
# ═══════════════════════════════════════════════════════════════════════════════

_EMAIL_HARD_TEMPLATES = [
    {
        "subject": "Completely unacceptable — Order #{order_id}",
        "sender": "furious.customer@email.com",
        "body": (
            "I have been a loyal customer for 5 years and I am absolutely furious. "
            "My order #{order_id} arrived broken for the SECOND time this month. "
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
    {
        "subject": "Data breach — my account was hacked",
        "sender": "angry.user@personal.com",
        "body": (
            "I just discovered that my account was used to make purchases I never authorised. "
            "Someone accessed my account and changed my email and password. "
            "I was only able to regain access because I remembered my security questions. "
            "This is a serious security failure on your part. I demand to know what happened, "
            "how my data was exposed, and what you will do to protect me going forward. "
            "If I do not hear back within 24 hours, I will contact the data protection authority."
        ),
        "expected_elements": {
            "acknowledge_frustration": ["understand", "serious", "concern", "alarming"],
            "apologize": ["sorry", "apologize", "apology"],
            "confirm_investigation": ["investigat", "security team", "look into", "review"],
            "offer_remediation": ["secure", "reset", "protect", "steps", "safeguard"],
            "provide_timeline": ["24 hours", "48 hours", "within", "shortly", "immediately"],
            "professional_tone": None,
            "regulatory_mention": ["authority", "regulat", "notify", "report", "transparent"],
        },
    },
    {
        "subject": "Defective product — 3 replacements still broken",
        "sender": "frustrated.buyer@email.com",
        "body": (
            "This is my THIRD replacement unit and it is still defective. "
            "The first unit arrived with a cracked screen. The second had a faulty battery. "
            "This third unit powers off randomly. "
            "I have spent over 6 hours on support calls. I want a full refund immediately — "
            "no more replacements. I will also be leaving reviews on every platform I can find."
        ),
        "expected_elements": {
            "acknowledge_frustration": ["understand", "frustrat", "disappoint", "three", "3"],
            "apologize": ["sorry", "apologize", "sincerely"],
            "offer_refund": ["refund", "full refund", "money back"],
            "no_more_replacement_push": ["will not", "no further", "respect", "understand", "preference"],
            "provide_timeline": ["within", "24 hours", "48 hours", "business day"],
            "professional_tone": None,
            "de_escalation": ["value", "loyal", "appreciate", "important to us"],
        },
    },
    {
        "subject": "Package lost — 3 weeks and still nothing",
        "sender": "lost.package@customer.net",
        "body": (
            "I placed an order 3 weeks ago and my package has still not arrived. "
            "The tracking has shown 'In Transit' for 18 days without any movement. "
            "I have contacted your support team 4 times. Each time I am told to 'wait a few more days'. "
            "I need this item for an event next week. Either find the package, send a replacement now, "
            "or give me a full refund so I can purchase elsewhere. This is unacceptable."
        ),
        "expected_elements": {
            "acknowledge_frustration": ["understand", "frustrat", "waiting", "3 weeks", "three weeks"],
            "apologize": ["sorry", "apologize", "apology"],
            "offer_refund": ["refund", "full refund"],
            "offer_replacement": ["replacement", "resend", "new shipment", "send another"],
            "provide_timeline": ["24 hours", "48 hours", "immediately", "today", "next day"],
            "professional_tone": None,
            "carrier_investigation": ["carrier", "investigate", "trace", "courier", "tracking"],
        },
    },
    {
        "subject": "Cancelled subscription still being charged",
        "sender": "cancelled.user@email.com",
        "body": (
            "I cancelled my subscription on January 15th and have proof of the cancellation email. "
            "However, I have been charged $99/month for the past 3 months since then. "
            "Total unauthorised charges: $297. I want a full refund of all three charges immediately. "
            "If this is not resolved within 48 hours, I will initiate a chargeback with my bank "
            "and report this to the consumer protection agency."
        ),
        "expected_elements": {
            "acknowledge_frustration": ["understand", "concern", "apologize", "recognised"],
            "apologize": ["sorry", "apologize", "apology"],
            "offer_refund": ["refund", "full refund", "$297", "three charges", "all charges"],
            "confirm_cancellation": ["confirm", "cancellation", "verified", "record"],
            "provide_timeline": ["48 hours", "24 hours", "immediately", "within"],
            "professional_tone": None,
            "prevent_recurrence": ["prevent", "ensure", "will not happen", "steps", "corrective"],
        },
    },
    {
        "subject": "Discriminatory treatment by your staff",
        "sender": "discrimination.complaint@email.com",
        "body": (
            "I visited your store on April 2nd and was followed around by a staff member "
            "while other customers were not treated this way. When I raised this with the manager, "
            "I was told 'it's just store policy'. This felt discriminatory and I am deeply hurt. "
            "I expect a formal apology, an explanation of your training policies, "
            "and assurance that this will not happen to any customer again."
        ),
        "expected_elements": {
            "acknowledge_frustration": ["understand", "serious", "concern", "upset", "hurt"],
            "apologize": ["sorry", "apologize", "sincerely", "formal apology"],
            "confirm_investigation": ["investigat", "review", "look into", "hr", "management"],
            "policy_commitment": ["policy", "training", "standards", "commit", "improve"],
            "provide_timeline": ["within", "48 hours", "days", "shortly"],
            "professional_tone": None,
            "empathy_specific": ["dignity", "respect", "every customer", "valued"],
        },
    },
    {
        "subject": "Software destroyed my data — urgent",
        "sender": "data.loss@business.com",
        "body": (
            "Your software update on March 28th corrupted our entire database backup. "
            "We lost 6 months of customer records. Our business has been at a standstill for 3 days. "
            "We are a paying enterprise customer ($24,000/year). "
            "I need immediate escalation to your engineering team, a post-mortem report, "
            "and a discussion about compensation for our business losses."
        ),
        "expected_elements": {
            "acknowledge_frustration": ["understand", "serious", "impact", "significant", "recognise"],
            "apologize": ["sorry", "sincerely", "deeply apologize"],
            "escalate": ["engineering", "escalate", "senior", "team", "immediately"],
            "post_mortem": ["post-mortem", "root cause", "analysis", "report", "findings"],
            "provide_timeline": ["24 hours", "immediately", "today", "within"],
            "professional_tone": None,
            "compensation_acknowledged": ["compensat", "discuss", "impact", "losses", "make it right"],
        },
    },
]


def gen_email_hard(episode_id: str) -> tuple[dict, dict]:
    rng = _rng(episode_id, "email_hard")
    template = rng.choice(_EMAIL_HARD_TEMPLATES)
    order_id = rng.randint(10000, 99999)
    subject  = template["subject"].format(order_id=order_id)
    body     = template["body"].format(order_id=order_id)
    case = {**template, "subject": subject, "body": body, "sender": template["sender"], "id": "h1"}
    agent_ctx  = {"email": {k: v for k, v in case.items() if k not in ("expected_elements", "id")}}
    grader_ctx = {"email": case}
    return agent_ctx, grader_ctx


# ═══════════════════════════════════════════════════════════════════════════════
# CODE EASY  — 6 snippet variants
# ═══════════════════════════════════════════════════════════════════════════════

_CODE_EASY_POOL = [
    {"code": "def calculate_average(numbers):\n    total = 0\n    for num in numbers\n        total += num\n    return total / len(numbers)\n",
     "keywords": ["colon", "for loop", "syntax", "for statement"]},
    {"code": "def greet(name)\n    print(f'Hello, {name}!')\n\ngreet('World')\n",
     "keywords": ["colon", "def", "function", "syntax"]},
    {"code": "numbers = [1, 2, 3, 4, 5]\nif len(numbers) > 0\n    print('Not empty')\n",
     "keywords": ["colon", "if statement", "syntax"]},
    {"code": "class Animal:\n    def __init__(self, name)\n        self.name = name\n\n    def speak(self):\n        return f'{self.name} speaks'\n",
     "keywords": ["colon", "__init__", "constructor", "function", "def"]},
    {"code": "def read_file(path):\n    with open(path) as f\n        return f.read()\n",
     "keywords": ["colon", "with statement", "context manager", "syntax"]},
    {"code": "def retry(fn, times=3):\n    for i in range(times)\n        try:\n            return fn()\n        except Exception:\n            pass\n",
     "keywords": ["colon", "for loop", "range", "syntax"]},
]


def gen_code_easy(episode_id: str) -> tuple[dict, dict]:
    rng = _rng(episode_id, "code_easy")
    variant    = rng.choice(_CODE_EASY_POOL)
    agent_ctx  = {"code": variant["code"]}
    grader_ctx = {"code": variant["code"], "keywords": variant["keywords"]}
    return agent_ctx, grader_ctx


# ═══════════════════════════════════════════════════════════════════════════════
# DATA EASY  — procedurally generated 6-10 rows
# ═══════════════════════════════════════════════════════════════════════════════

_FIRST_NAMES = ["Alice", "Bob", "Charlie", "Diana", "Eve", "Frank", "Grace", "Hiro", "Iris", "Jake"]
_DOMAINS = ["example.com", "company.net", "test.org", "work.io"]


def gen_data_easy(episode_id: str) -> tuple[dict, dict]:
    rng = _rng(episode_id, "data_easy")
    n = rng.randint(6, 10)
    names = rng.sample(_FIRST_NAMES, k=n)
    base_salary = 50000

    rows = []
    for i, name in enumerate(names, 1):
        rows.append({
            "id": i,
            "name": name,
            "age": rng.randint(22, 55),
            "email": f"{name.lower()}@{rng.choice(_DOMAINS)}",
            "salary": base_salary + rng.randint(0, 50) * 1000,
        })

    # Inject 3-4 nulls in distinct rows and fields
    null_fields = rng.sample(["age", "name", "email", "salary"], k=rng.randint(3, 4))
    null_rows   = rng.sample(list(range(n)), k=len(null_fields))
    missing_answers = []
    for row_idx, field in zip(null_rows, null_fields):
        rows[row_idx][field] = None
        missing_answers.append(f"{field} (row {row_idx + 1})")

    # Inject one duplicate pair
    dup_src = rng.randint(0, n - 2)
    dup_dst = dup_src + 1
    rows[dup_dst] = {**rows[dup_src], "id": dup_dst + 1}
    dup_ids = sorted([rows[dup_src]["id"], rows[dup_dst]["id"]])

    agent_ctx  = {"data": rows}
    grader_ctx = {
        "data": rows,
        "answers": {"missing": sorted(missing_answers), "duplicates": dup_ids},
    }
    return agent_ctx, grader_ctx


# ═══════════════════════════════════════════════════════════════════════════════
# DATA MEDIUM  — randomised messy formats per field
# ═══════════════════════════════════════════════════════════════════════════════

_AGE_STRINGS   = ["thirty", "twenty-two", "forty-five", "nineteen", "fifty"]
_DATE_FORMATS  = [("%Y/%m/%d", "2020/01/15"), ("%d-%m-%Y", "15-03-2021"),
                  ("%Y-%m-%d", "2019-07-22"), ("%Y/%m/%d", "2022/11/01"),
                  ("%d/%m/%Y", "01/06/2023")]
_ACTIVE_MESSY  = ["yes", "no", "TRUE", "FALSE", "1", "0"]


def gen_data_medium(episode_id: str) -> tuple[dict, dict]:
    rng = _rng(episode_id, "data_medium")
    names = rng.sample(_FIRST_NAMES, k=5)

    rows = []
    salaries = [50000, 60000, 70000, 80000, 45000]
    for i, (name, salary) in enumerate(zip(names, salaries), 1):
        # Introduce one of each issue type
        if i == 1:
            age_val = rng.choice(_AGE_STRINGS)        # string age
            sal_val = f"${salary:,}"                   # dollar+comma format
        elif i == 2:
            age_val = 25                               # correct
            sal_val = f"${salary:,}"                   # dollar+comma
        elif i == 3:
            age_val = str(rng.randint(25, 40))         # string digit
            sal_val = str(salary)                      # clean
        elif i == 4:
            age_val = rng.randint(30, 45)              # int — correct
            sal_val = f"{salary:,}"                    # comma only
        else:
            age_val = rng.choice(_AGE_STRINGS)         # string age
            sal_val = str(salary)                      # clean

        _, date_str = rng.choice(_DATE_FORMATS)
        name_messy = name.lower() if i == 4 else name.upper() if i == 5 else name
        active_val = rng.choice(_ACTIVE_MESSY) if i in (1, 3, 5) else rng.choice([True, False])

        rows.append({"id": i, "name": name_messy, "age": age_val, "salary": sal_val,
                     "join_date": date_str, "active": active_val})

    issues = {
        "age":       "mixed types: some ages are word strings, should be integers",
        "salary":    "inconsistent formats: dollar signs and commas present in some values",
        "join_date": "three different date formats used across rows",
        "name":      "inconsistent casing: some names lowercase, some all-caps",
        "active":    "mixed types: booleans and strings ('yes','no','TRUE') mixed",
    }
    agent_ctx  = {"data": rows}
    grader_ctx = {"data": rows, "issues": issues}
    return agent_ctx, grader_ctx


# ═══════════════════════════════════════════════════════════════════════════════
# DATA HARD  — IQR-detectable outliers, missing values
# ═══════════════════════════════════════════════════════════════════════════════

def gen_data_hard(episode_id: str) -> tuple[dict, dict]:
    rng = _rng(episode_id, "data_hard")
    n = rng.randint(12, 16)
    base = round(rng.uniform(9.5, 12.5), 1)
    spread = round(rng.uniform(0.3, 0.8), 2)

    rows = []
    for i in range(1, n + 1):
        val = round(base + rng.gauss(0, spread), 2)
        rows.append({"id": i, "value": val})

    # Pick 2 outlier positions (ensure they're not neighbours)
    positions = list(range(n))
    rng.shuffle(positions)
    o1, o2 = sorted(positions[:2])
    outlier_mult = rng.choice([8, 10, 12, -5, -8])
    rows[o1]["value"] = round(base * abs(outlier_mult) * (1 if outlier_mult > 0 else -1), 1)
    outlier_mult2 = rng.choice([-4, -6, 15, 20])
    rows[o2]["value"] = round(base * abs(outlier_mult2) * (1 if outlier_mult2 > 0 else -1), 1)
    outlier_ids = sorted([o1 + 1, o2 + 1])

    # Pick 2 missing positions (not overlapping outliers)
    available = [i for i in range(n) if i not in (o1, o2)]
    m1, m2 = sorted(rng.sample(available, 2))
    rows[m1]["value"] = None
    rows[m2]["value"] = None
    missing_ids = sorted([m1 + 1, m2 + 1])

    normal_vals = [r["value"] for r in rows if r["value"] is not None and r["id"] not in outlier_ids]
    lo = round(min(normal_vals) - 1.0, 2)
    hi = round(max(normal_vals) + 1.0, 2)

    agent_ctx  = {"data": rows}
    grader_ctx = {
        "data": rows,
        "answers": {
            "outliers":      set(outlier_ids),
            "missing":       set(missing_ids),
            "imputed_range": (lo, hi),
        },
    }
    return agent_ctx, grader_ctx


# ═══════════════════════════════════════════════════════════════════════════════
# CONTENT MODERATION EASY  — draw 7 from a pool of 20
# ═══════════════════════════════════════════════════════════════════════════════

_MOD_EASY_POOL = [
    {"text": "I hate you so much, I want to hurt you!",                      "label": "harmful"},
    {"text": "Great weather today! Loving this sunshine",                     "label": "safe"},
    {"text": "All people from that group should be eliminated.",              "label": "harmful"},
    {"text": "Can someone recommend a good Python beginner book?",            "label": "safe"},
    {"text": "You're an absolute idiot and nobody likes you.",               "label": "harmful"},
    {"text": "I just finished a 5k run — feeling amazing!",                  "label": "safe"},
    {"text": "People like you should just disappear forever.",               "label": "harmful"},
    {"text": "Just dropped off a care package for my neighbor.",             "label": "safe"},
    {"text": "Kill yourself, nobody would miss you.",                        "label": "harmful"},
    {"text": "Anyone else excited for the new season of that show?",         "label": "safe"},
    {"text": "I'm going to find you and make you pay for this.",             "label": "harmful"},
    {"text": "Finally got my herb garden started!",                          "label": "safe"},
    {"text": "These people deserve to suffer for what they've done.",        "label": "harmful"},
    {"text": "Happy birthday to my best friend!",                            "label": "safe"},
    {"text": "Someone should shoot that politician.",                        "label": "harmful"},
    {"text": "Loving the new coffee shop that opened downtown.",             "label": "safe"},
    {"text": "I hope your family gets what's coming to them.",               "label": "harmful"},
    {"text": "Just hit 100 days of learning Spanish — so proud!",           "label": "safe"},
    {"text": "People from that country are all criminals.",                  "label": "harmful"},
    {"text": "The cherry blossoms are out — spring is finally here!",       "label": "safe"},
]


def gen_mod_easy(episode_id: str) -> tuple[dict, dict]:
    rng = _rng(episode_id, "mod_easy")
    # Ensure at least 3 harmful, 3 safe among 7
    harmful = [p for p in _MOD_EASY_POOL if p["label"] == "harmful"]
    safe    = [p for p in _MOD_EASY_POOL if p["label"] == "safe"]
    chosen  = rng.sample(harmful, 4) + rng.sample(safe, 3)
    rng.shuffle(chosen)
    posts = [{"id": f"c{i+1}", **p} for i, p in enumerate(chosen)]
    agent_ctx  = {"posts": [{"id": p["id"], "text": p["text"]} for p in posts]}
    grader_ctx = {"posts": posts}
    return agent_ctx, grader_ctx


# ═══════════════════════════════════════════════════════════════════════════════
# CONTENT MODERATION MEDIUM  — draw 8 from a pool of 20
# ═══════════════════════════════════════════════════════════════════════════════

_MOD_MEDIUM_POOL = [
    {"text": "Oh sure, like THAT went well. Classic genius move.",              "label": "harmful"},
    {"text": "I'm so done with these people. Absolutely insufferable.",         "label": "harmful"},
    {"text": "That presentation was... very unique.",                           "label": "safe"},
    {"text": "Some people just shouldn't be allowed to have opinions.",        "label": "harmful"},
    {"text": "Oh wow, another 'brilliant' idea from upper management",         "label": "harmful"},
    {"text": "Congrats on the promotion! Well deserved!",                      "label": "safe"},
    {"text": "Not everyone is cut out for this kind of work, clearly.",        "label": "harmful"},
    {"text": "Thanks for the feedback, I'll take it into account.",            "label": "safe"},
    {"text": "Some of us actually read the requirements before submitting.",   "label": "harmful"},
    {"text": "Good effort — interesting approach to the problem.",             "label": "safe"},
    {"text": "If you'd done even a little research, you'd know better.",       "label": "harmful"},
    {"text": "Really enjoyed the team retrospective today.",                   "label": "safe"},
    {"text": "Must be nice having a job you're actually qualified for.",       "label": "harmful"},
    {"text": "Great work getting the release out on time!",                    "label": "safe"},
    {"text": "Shocking that anyone thought that plan would work.",             "label": "harmful"},
    {"text": "Just wanted to say — the onboarding docs are really clear.",    "label": "safe"},
    {"text": "The bar for hiring has clearly dropped.",                        "label": "harmful"},
    {"text": "Appreciate everyone's patience during the migration.",           "label": "safe"},
    {"text": "I see we've decided quantity over quality again.",               "label": "harmful"},
    {"text": "The demo went really smoothly — nice job everyone.",            "label": "safe"},
]


def gen_mod_medium(episode_id: str) -> tuple[dict, dict]:
    rng = _rng(episode_id, "mod_medium")
    harmful = [p for p in _MOD_MEDIUM_POOL if p["label"] == "harmful"]
    safe    = [p for p in _MOD_MEDIUM_POOL if p["label"] == "safe"]
    chosen  = rng.sample(harmful, 5) + rng.sample(safe, 3)
    rng.shuffle(chosen)
    posts = [{"id": f"m{i+1}", **p} for i, p in enumerate(chosen)]
    agent_ctx  = {"posts": [{"id": p["id"], "text": p["text"]} for p in posts]}
    grader_ctx = {"posts": posts}
    return agent_ctx, grader_ctx


# ═══════════════════════════════════════════════════════════════════════════════
# TICKET EASY  — 8 variant pool (already existed; keep contract-compatible)
# ═══════════════════════════════════════════════════════════════════════════════

_TICKET_EASY_POOL = [
    {"id": "t1", "title": "App crashes on login for all users",
     "description": "Since the 2.3.1 deploy, 100% of login attempts throw a 500 error.",
     "reporter": "ops-monitoring@company.com", "correct_priority": "critical", "correct_category": "bug"},
    {"id": "t2", "title": "Add dark mode to the dashboard",
     "description": "Multiple users have requested a dark mode option.",
     "reporter": "product@company.com", "correct_priority": "low", "correct_category": "feature_request"},
    {"id": "t3", "title": "How do I export my data as CSV?",
     "description": "I can't find the export button anywhere in the UI.",
     "reporter": "user123@customer.com", "correct_priority": "low", "correct_category": "question"},
    {"id": "t4", "title": "Charged twice for last month's invoice",
     "description": "Account #AC-4421 shows two charges of $299 on March 1st.",
     "reporter": "finance@customer.com", "correct_priority": "high", "correct_category": "billing"},
    {"id": "t5", "title": "Memory leak in mobile app — crashes after 10 min",
     "description": "The iOS app uses 2 GB RAM then crashes. Reproducible on all devices.",
     "reporter": "qa@company.com", "correct_priority": "high", "correct_category": "bug"},
    {"id": "t6", "title": "Add SSO support for Google Workspace",
     "description": "Enterprise customers are requesting Google SSO. High deal-blocker frequency.",
     "reporter": "sales@company.com", "correct_priority": "medium", "correct_category": "feature_request"},
    {"id": "t7", "title": "Refund policy — how long does it take?",
     "description": "A customer is asking about the refund timeline for a cancelled subscription.",
     "reporter": "support@company.com", "correct_priority": "low", "correct_category": "question"},
    {"id": "t8", "title": "Wrong amount charged — $0 instead of $499",
     "description": "New enterprise contract shows $0 on the invoice. Revenue loss.",
     "reporter": "billing@company.com", "correct_priority": "critical", "correct_category": "billing"},
]


def gen_ticket_easy(episode_id: str) -> tuple[dict, dict]:
    rng = _rng(episode_id, "ticket_easy")
    ticket     = rng.choice(_TICKET_EASY_POOL)
    agent_ctx  = {"ticket": {k: v for k, v in ticket.items() if k not in ("correct_priority", "correct_category")}}
    grader_ctx = {"ticket": ticket}
    return agent_ctx, grader_ctx