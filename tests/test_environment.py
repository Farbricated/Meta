"""
tests/test_environment.py — Meta v3.2
pytest suite covering all 24 tasks including expert tier.
New in v3.2:
  - Expert task smoke tests (email, code, data, content_mod, ticket)
  - Reward clamping test (never exceeds 1.0)
  - data_cleaning_expert revenue tolerance test
  - ticket_triage_medium tk2 team assignment test
"""

from __future__ import annotations

import json
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from server.Meta_environment import MetaEnvironment
from models import MetaAction, MetaObservation

# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def env() -> MetaEnvironment:
    e = MetaEnvironment()
    e.reset()
    return e


ALL_TASK_IDS = [
    "email_triage_easy",   "email_triage_medium",   "email_triage_hard",   "email_triage_expert",
    "code_review_easy",    "code_review_medium",     "code_review_hard",    "code_review_expert",
    "data_cleaning_easy",  "data_cleaning_medium",   "data_cleaning_hard",  "data_cleaning_expert",
    "content_moderation_easy", "content_moderation_medium", "content_moderation_hard", "content_moderation_expert",
    "ticket_triage_easy",  "ticket_triage_medium",   "ticket_triage_hard",  "ticket_triage_expert",
    "cross_agent_chain",   "cross_agent_email_data", "cross_agent_code_email", "cross_agent_mod_escalation",
]

DETERMINISTIC_TASK_IDS = [
    "code_review_medium", "code_review_hard",
    "ticket_triage_medium", "ticket_triage_hard",
    "cross_agent_email_data", "cross_agent_code_email",
]

CORRECT_PAYLOADS: dict[str, dict] = {
    "email_triage_easy": {"classification": "spam"},
    "email_triage_medium": {
        "order": ["m1", "m5", "m3", "m10", "m6", "m8", "m2", "m9", "m4", "m7"]
    },
    "email_triage_hard": {
        "reply": (
            "Dear Customer, I sincerely apologize for this frustrating experience. "
            "I understand your disappointment with the order. We will process a full refund "
            "and send an overnight replacement within 24 hours. As compensation for the inconvenience, "
            "we will make it right. We take this matter very seriously."
        )
    },
    "email_triage_expert": {
        "reply": (
            "Dear Sarah, I am writing to personally acknowledge the severity of this situation. "
            "Four weeks is far too long for an issue of this magnitude to remain unresolved, and I "
            "sincerely apologize on behalf of our entire organization. "
            "I have reviewed the engineering report and can now disclose the root cause: a daylight "
            "saving time offset bug in our data export pipeline affected records from February 1-14. "
            "Our engineering team has a confirmed fix scheduled for March 15th. I will personally "
            "ensure a corrected export is delivered to you immediately upon deployment. "
            "I would like to schedule a meeting with our VP of Engineering and VP of Customer Success "
            "at your earliest convenience to walk you through the fix and our prevention plan. "
            "I understand you mentioned engaging your legal team — I hope this concrete action plan "
            "demonstrates our full commitment to resolution. BigClient Corp has been a valued partner "
            "for four years, and your upcoming renewal in June is a priority for us. "
            "I am personally committed to ensuring this is resolved to your complete satisfaction. "
            "Please reply with your availability for a call this week."
        )
    },
    "code_review_easy": {"errors": ["missing colon after for statement syntax error"]},
    "code_review_medium": {
        "bugs": [
            {"location": "find_max",     "issue": "max_val=0 fails for all-negative lists",    "fix": "use float('-inf')"},
            {"location": "get_user",     "issue": "= used instead of == for comparison",        "fix": "use =="},
            {"location": "divide",       "issue": "no division by zero guard",                  "fix": "check b == 0"},
            {"location": "process_list", "issue": "off-by-one: range(len(items)+1) IndexError", "fix": "use range(len(items))"},
        ]
    },
    "code_review_hard": {
        "vulnerabilities": [
            {"type": "sql_injection",           "location": "get_user_by_name",  "severity": "critical", "fix": "parameterized queries"},
            {"type": "xss",                     "location": "render_comment",    "severity": "high",     "fix": "sanitize input"},
            {"type": "sql_injection",           "location": "login",             "severity": "critical", "fix": "parameterized queries"},
            {"type": "command_injection",       "location": "run_report",        "severity": "critical", "fix": "avoid shell=True"},
            {"type": "insecure_deserialization","location": "load_user_data",    "severity": "high",     "fix": "use json"},
            {"type": "timing_attack",           "location": "check_password",    "severity": "medium",   "fix": "use hmac.compare_digest"},
            {"type": "path_traversal",          "location": "read_report_file",  "severity": "high",     "fix": "validate filename"},
            {"type": "ssrf",                    "location": "fetch_user_avatar", "severity": "high",     "fix": "validate and allowlist URLs"},
        ]
    },
    "code_review_expert": {
        "vulnerabilities": [
            {"type": "hardcoded_secret",       "location": "create_token",        "severity": "critical", "fix": "use env var SECRET_KEY"},
            {"type": "jwt_none_algorithm",     "location": "verify_token",        "severity": "critical", "fix": "remove 'none' from algorithms list"},
            {"type": "mass_assignment",        "location": "update_user_profile", "severity": "high",     "fix": "whitelist allowed fields"},
            {"type": "idor",                   "location": "get_invoice",         "severity": "high",     "fix": "check invoice ownership before returning"},
            {"type": "unsafe_deserialization", "location": "load_config",         "severity": "critical", "fix": "use yaml.safe_load"},
            {"type": "race_condition",         "location": "save_report",         "severity": "medium",   "fix": "use atomic file write with O_EXCL flag"},
            {"type": "prototype_pollution",    "location": "merge_settings",      "severity": "medium",   "fix": "validate keys before merge"},
            {"type": "log_injection",          "location": "log_action",          "severity": "low",      "fix": "sanitize username and action before logging"},
        ]
    },
    "data_cleaning_easy": {
        "missing": ["age (row 2)", "name (row 4)", "email (row 5)", "salary (row 6)"],
        "duplicates": [1, 3],
    },
    "data_cleaning_medium": {
        "issues": {
            "age":       "mixed types: strings like thirty and twenty-two should be integers",
            "salary":    "inconsistent format: $60,000 has dollar sign and commas",
            "join_date": "multiple inconsistent date formats",
            "name":      "inconsistent casing: dave lowercase, EVE all caps",
            "active":    "mixed types: booleans and strings yes/no/TRUE",
        },
        "cleaned_data": [
            {"id": 1, "name": "Alice",   "age": 0,  "salary": 50000, "join_date": "2020-01-15", "active": True},
            {"id": 2, "name": "Bob",     "age": 25, "salary": 60000, "join_date": "2021-03-15", "active": True},
            {"id": 3, "name": "Charlie", "age": 28, "salary": 70000, "join_date": "2019-07-22", "active": True},
            {"id": 4, "name": "Dave",    "age": 35, "salary": 80000, "join_date": "2022-11-01", "active": False},
            {"id": 5, "name": "Eve",     "age": 0,  "salary": 45000, "join_date": "2023-06-01", "active": False},
        ],
    },
    "data_cleaning_hard": {
        "outliers": [4, 8],
        "missing":  [6, 11],
        "cleaned_data": [
            {"id": 1, "value": 10.5},  {"id": 2, "value": 11.2},
            {"id": 3, "value": 10.8},  {"id": 4, "value": 10.9},
            {"id": 5, "value": 10.1},  {"id": 6, "value": 10.8},
            {"id": 7, "value": 11.5},  {"id": 8, "value": 10.9},
            {"id": 9, "value": 10.9},  {"id": 10, "value": 11.0},
            {"id": 11, "value": 10.8}, {"id": 12, "value": 10.7},
        ],
    },
    "data_cleaning_expert": {
        "data_quality_issues": [
            "T006 duplicate of T001 — same customer, amount, date, rep",
            "T003 missing amount",
            "T010 zero amount transaction",
            "T007 statistical outlier: $99,999.99 far exceeds IQR",
        ],
        "suspicious_transactions": [
            {"txn_id": "T007", "reason": "outlier: $99,999.99 is >50x the median transaction value"},
            {"txn_id": "T006", "reason": "duplicate of T001: same customer, amount, date, rep"},
            {"txn_id": "T010", "reason": "zero amount transaction — likely data entry error"},
        ],
        "revenue_by_rep": {
            "R05": 3625.50,   # T001(1200) + T002(850.50) + T005(475) + T009(1100)
            "R12": 3904.94,   # T004(2300 GBP × 1.265 = 2909.50) + T008(920 EUR × 1.082 = 995.44)
        },
        "excluded_transactions": ["T003", "T006", "T007", "T010"],
    },
    "content_moderation_easy": {
        "classifications": [
            {"id": "c1", "label": "harmful"}, {"id": "c2", "label": "safe"},
            {"id": "c3", "label": "harmful"}, {"id": "c4", "label": "safe"},
            {"id": "c5", "label": "harmful"}, {"id": "c6", "label": "safe"},
            {"id": "c7", "label": "harmful"},
        ]
    },
    "content_moderation_medium": {
        "classifications": [
            {"id": "m1", "label": "harmful"}, {"id": "m2", "label": "harmful"},
            {"id": "m3", "label": "safe"},    {"id": "m4", "label": "harmful"},
            {"id": "m5", "label": "harmful"}, {"id": "m6", "label": "safe"},
            {"id": "m7", "label": "harmful"}, {"id": "m8", "label": "safe"},
        ]
    },
    "content_moderation_hard": {
        "decisions": [
            {"id": "h1", "context_a_label": "safe",    "context_b_label": "harmful"},
            {"id": "h2", "context_a_label": "safe",    "context_b_label": "harmful"},
            {"id": "h3", "context_a_label": "safe",    "context_b_label": "harmful"},
            {"id": "h4", "context_a_label": "harmful", "context_b_label": "harmful"},
            {"id": "h5", "context_a_label": "safe",    "context_b_label": "harmful"},
            {"id": "h6", "context_a_label": "harmful", "context_b_label": "harmful"},
        ]
    },
    "content_moderation_expert": {
        "rulings": [
            {"id": "p1", "ruling": "keep_with_intervention", "principle": "harm_reduction",
             "justification": "This is an expression of distress, not encouragement of self-harm. Crisis intervention resources should be surfaced rather than removing the post, which could isolate the user further."},
            {"id": "p2", "ruling": "remove", "principle": "platform_context_amplifies_harm",
             "justification": "The 'great replacement' rhetoric combined with an implicit call to action on an extremist-adjacent platform creates serious radicalization risk. Context amplifies the harm beyond what the text alone suggests."},
            {"id": "p3", "ruling": "keep", "principle": "policy_opinion_vs_personal_attack",
             "justification": "This is a systemic policy opinion about a professional group's employment practice, not a targeted personal attack on any individual. It engages in legitimate debate about conscientious objection policy."},
            {"id": "p4", "ruling": "remove", "principle": "hate_symbol_not_protected_by_satire_framing",
             "justification": "The puppet master trope is an antisemitic stereotype that remains harmful regardless of the political target. Satire framing does not protect content that invokes hate symbols."},
            {"id": "p5", "ruling": "remove", "principle": "health_misinformation_direct_harm_risk",
             "justification": "False cancer detection claims could delay life-saving medical treatment. The direct, measurable harm risk from this health misinformation outweighs any autonomy argument."},
        ]
    },
    "ticket_triage_easy": {"priority": "critical", "category": "bug"},
    "ticket_triage_medium": {
        "order": ["tk1", "tk4", "tk2", "tk7", "tk5", "tk3", "tk6", "tk8"],
        "assignments": {
            "tk1": "backend", "tk2": "frontend", "tk3": "backend",
            "tk4": "devops",  "tk5": "backend",  "tk6": "frontend",
            "tk7": "billing", "tk8": "frontend",
        },
    },
    "ticket_triage_hard": {
        "root_cause": "Database CPU at 100% due to N+1 query in ORM migration exhausting connection pool, causing Redis cache overflow and all dependent services to fail.",
        "resolution_steps": [
            "Scale up database replica to absorb query load",
            "Reset DB connection pool which was not restored after rollback",
            "Flush Redis cache and increase memory limit",
            "Rollback v4.2.1 deploy using documented runbook",
            "Optimize N+1 query with proper ORM eager loading and indexes",
        ],
        "affected_services": ["payment-service", "checkout-service", "postgres-primary", "redis-cache"],
        "severity": "P1",
    },
    "ticket_triage_expert": {
        "root_cause": "Introduction of an N+1 query in the new DB migration via ORM layer caused database CPU to hit 100%, exhausting the connection pool and cascading failures across all dependent services.",
        "contributing_factors": [
            "No load testing performed before production deploy of v4.2.1",
            "Missing rollback runbook caused 20-minute delay in executing rollback at 14:50",
            "DB connection pool reset not included in rollback checklist — persisted issue post-rollback",
            "Alert threshold set too high (18% error rate) — should fire at 1% for P1 detection",
            "N+1 query introduced without code review catching the ORM migration impact",
        ],
        "timeline_gaps": [
            {"time": "14:50-15:10", "gap": "20-minute delay in starting rollback due to missing runbook — the single largest preventable gap in the incident"},
            {"time": "15:45-16:00", "gap": "Connection pool not reset after rollback — not on checklist, causing continued 12% error rate for 15 minutes"},
        ],
        "action_items": [
            "Create and publish rollback runbook for all production services within 1 week",
            "Add DB connection pool reset to the rollback checklist immediately",
            "Lower PagerDuty alert threshold from 18% to 1% error rate for checkout service",
            "Add mandatory load testing gate to CI/CD pipeline before any DB migration deploys",
            "Implement canary deployments for all releases touching the ORM layer",
            "Add N+1 query detection to code review checklist and static analysis tooling",
        ],
        "severity_justification": "P1: $47,000 revenue lost, 8,200 customers affected, 4h17m MTTR. Direct revenue impact and full checkout outage qualify as P1 under our incident severity matrix.",
        "mttr_analysis": "Total 257 minutes: detection 12 min, escalation 10 min, diagnosis 13 min, rollback decision to execution 20 min (runbook delay — largest gap), rollback execution 35 min, connection pool discovery 15 min, connection pool reset + restart 30 min, stabilization 107 min. The 20-minute runbook delay was the largest single preventable gap.",
    },
    "cross_agent_chain": {
        "email_classification": "important",
        "bugs": [{"location": "calculate_fee", "issue": "division by zero when rate is 0", "fix": "guard against rate == 0"}],
    },
    "cross_agent_email_data": {
        "email_priority": "critical",
        "data_issues": {
            "revenue": "inconsistent formats: $80,000 has dollar sign",
            "region":  "inconsistent casing: NORTH, south, East, WEST",
            "closed_date": "multiple date formats",
        },
        "cleaned_data": [
            {"id": 1, "rep": "Alice",   "revenue": 150000, "region": "North", "closed_date": "2024-12-31"},
            {"id": 2, "rep": "Bob",     "revenue": 80000,  "region": "South", "closed_date": "2024-12-31"},
            {"id": 3, "rep": "Charlie", "revenue": None,   "region": "East",  "closed_date": "2024-12-30"},
            {"id": 4, "rep": "Diana",   "revenue": 120000, "region": "West",  "closed_date": "2024-12-30"},
        ],
    },
    "cross_agent_code_email": {
        "vulnerability_type": "sql_injection",
        "vulnerability_location": "get_user_profile",
        "disclosure_email": (
            "Hi team, I've identified a critical SQL injection vulnerability in get_user_profile. "
            "The user_id parameter is concatenated directly into the SQL query without parameterization, "
            "allowing arbitrary SQL execution. This requires an immediate patch using parameterized queries "
            "to remediate the security vulnerability. Please prioritize this fix urgently."
        ),
    },
    "cross_agent_mod_escalation": {
        "content_label": "harmful",
        "escalate": True,
        "moderation_notice": (
            "Your post has been removed because it violates our community guidelines. "
            "Threatening language is strictly prohibited on our platform."
        ),
    },
}


def make_action(task_id: str, payload: dict) -> MetaAction:
    agent = (
        "cross_agent" if task_id.startswith("cross_agent")
        else "_".join(task_id.split("_")[:-1])
    )
    return MetaAction(message=json.dumps({"agent": agent, "task_id": task_id, "payload": payload}))


# ═════════════════════════════════════════════════════════════════════════════
# 1. RESET
# ═════════════════════════════════════════════════════════════════════════════

class TestReset:
    def test_returns_meta_observation(self):
        e = MetaEnvironment()
        obs = e.reset()
        assert isinstance(obs, MetaObservation)

    def test_returns_zero_score(self):
        e = MetaEnvironment()
        obs = e.reset()
        assert obs.score == 0.0

    def test_clears_episode_scores(self):
        e = MetaEnvironment()
        e.reset()
        e.step(make_action("email_triage_easy", {"classification": "spam"}))
        e.reset()
        assert e._episode_scores == []

    def test_new_episode_id_each_reset(self):
        e = MetaEnvironment()
        e.reset()
        id1 = e.state.episode_id
        e.reset()
        id2 = e.state.episode_id
        assert id1 != id2

    def test_step_count_zero_after_reset(self):
        e = MetaEnvironment()
        e.reset()
        e.step(make_action("email_triage_easy", {"classification": "spam"}))
        e.reset()
        assert e.state.step_count == 0

    def test_instructions_present(self):
        e = MetaEnvironment()
        obs = e.reset()
        assert len(obs.instructions) > 10


# ═════════════════════════════════════════════════════════════════════════════
# 2. SCORE RANGE (all 24 tasks)
# ═════════════════════════════════════════════════════════════════════════════

class TestScoreRange:
    @pytest.mark.parametrize("task_id", ALL_TASK_IDS)
    def test_score_in_01(self, task_id):
        e = MetaEnvironment()
        e.reset()
        obs = e.step(make_action(task_id, CORRECT_PAYLOADS[task_id]))
        assert 0.0 <= obs.score <= 1.0, f"{task_id} score {obs.score} out of range"

    @pytest.mark.parametrize("task_id", ALL_TASK_IDS)
    def test_observation_type(self, task_id):
        e = MetaEnvironment()
        e.reset()
        obs = e.step(make_action(task_id, CORRECT_PAYLOADS[task_id]))
        assert isinstance(obs, MetaObservation)

    @pytest.mark.parametrize("task_id", ALL_TASK_IDS)
    def test_feedback_nonempty(self, task_id):
        e = MetaEnvironment()
        e.reset()
        obs = e.step(make_action(task_id, CORRECT_PAYLOADS[task_id]))
        assert len(obs.feedback) > 0

    @pytest.mark.parametrize("task_id", ALL_TASK_IDS)
    def test_difficulty_valid(self, task_id):
        e = MetaEnvironment()
        e.reset()
        obs = e.step(make_action(task_id, CORRECT_PAYLOADS[task_id]))
        assert obs.difficulty in ("easy", "medium", "hard", "expert")

    @pytest.mark.parametrize("task_id", ALL_TASK_IDS)
    def test_partial_credits_dict(self, task_id):
        e = MetaEnvironment()
        e.reset()
        obs = e.step(make_action(task_id, CORRECT_PAYLOADS[task_id]))
        assert isinstance(obs.partial_credits, dict)

    def test_empty_payload_negative_reward(self):
        e = MetaEnvironment()
        e.reset()
        obs = e.step(make_action("email_triage_easy", {}))
        assert obs.reward <= 0.0

    def test_invalid_json_error_obs(self):
        e = MetaEnvironment()
        e.reset()
        obs = e.step(MetaAction(message="not json }{"))
        assert obs.score == 0.0

    def test_unknown_task_zero_score(self):
        e = MetaEnvironment()
        e.reset()
        obs = e.step(make_action("totally_fake_task", {"x": 1}))
        assert obs.score == 0.0


# ═════════════════════════════════════════════════════════════════════════════
# 3. REWARD CLAMPING — must never exceed 1.0
# ═════════════════════════════════════════════════════════════════════════════

class TestRewardClamping:
    @pytest.mark.parametrize("task_id", ALL_TASK_IDS)
    def test_reward_never_exceeds_1(self, task_id):
        """Reward must always be in [0.0, 1.0] — no reward shaping should breach this."""
        e = MetaEnvironment()
        e.reset()
        obs = e.step(make_action(task_id, CORRECT_PAYLOADS[task_id]))
        assert obs.reward <= 1.0, f"{task_id}: reward {obs.reward} exceeded 1.0"

    @pytest.mark.parametrize("task_id", ALL_TASK_IDS)
    def test_reward_never_below_0(self, task_id):
        e = MetaEnvironment()
        e.reset()
        obs = e.step(make_action(task_id, CORRECT_PAYLOADS[task_id]))
        assert obs.reward >= 0.0, f"{task_id}: reward {obs.reward} below 0.0"

    def test_perfect_score_reward_clamped(self):
        """Speed bonus on perfect score should not push reward above 1.0."""
        e = MetaEnvironment()
        e.reset()
        obs = e.step(make_action("code_review_medium", CORRECT_PAYLOADS["code_review_medium"]))
        assert obs.score == 1.0
        assert obs.reward <= 1.0

    def test_compute_reward_directly(self):
        """Unit test _compute_reward clamp."""
        e = MetaEnvironment()
        e.reset()
        # score=1.0, attempt=1 → base = 1.0 + 0.05 = 1.05 → clamped to 1.0
        result = e._compute_reward(1.0, "email_triage_easy", 1)
        assert result <= 1.0
        # score=0.0, attempt=2 → base = 0.0 - 0.05 = -0.05 → clamped to 0.0
        result2 = e._compute_reward(0.0, "email_triage_easy", 2)
        assert result2 >= 0.0


# ═════════════════════════════════════════════════════════════════════════════
# 4. EXPERT TASK SMOKE TESTS
# ═════════════════════════════════════════════════════════════════════════════

class TestExpertTasks:
    def test_email_expert_context_loads(self):
        e = MetaEnvironment()
        e.reset()
        ctx, grader, diff = e._load_context("email_triage_expert")
        assert diff == "expert"
        assert "thread" in ctx
        assert "account_metadata" in ctx

    def test_email_expert_perfect_score(self):
        e = MetaEnvironment()
        e.reset()
        obs = e.step(make_action("email_triage_expert", CORRECT_PAYLOADS["email_triage_expert"]))
        assert obs.score == 1.0, f"email_expert score was {obs.score}: {obs.feedback}"

    def test_code_expert_context_loads(self):
        e = MetaEnvironment()
        e.reset()
        ctx, grader, diff = e._load_context("code_review_expert")
        assert diff == "expert"
        assert "code" in ctx
        assert "vulnerability_count" in ctx

    def test_code_expert_perfect_score(self):
        e = MetaEnvironment()
        e.reset()
        obs = e.step(make_action("code_review_expert", CORRECT_PAYLOADS["code_review_expert"]))
        assert obs.score == 1.0, f"code_expert score was {obs.score}: {obs.feedback}"

    def test_data_expert_context_loads(self):
        e = MetaEnvironment()
        e.reset()
        ctx, grader, diff = e._load_context("data_cleaning_expert")
        assert diff == "expert"
        assert "dataset_a" in ctx
        assert "dataset_b" in ctx

    def test_data_expert_perfect_score(self):
        e = MetaEnvironment()
        e.reset()
        obs = e.step(make_action("data_cleaning_expert", CORRECT_PAYLOADS["data_cleaning_expert"]))
        assert obs.score == 1.0, f"data_expert score was {obs.score}: {obs.feedback}"

    def test_data_expert_revenue_tolerance(self):
        """Revenue grader should accept values within ±150 of exact answer."""
        e = MetaEnvironment()
        e.reset()
        # Slightly off revenue values (rounding differences in currency conversion)
        payload = {**CORRECT_PAYLOADS["data_cleaning_expert"],
                   "revenue_by_rep": {"R05": 3610.0, "R12": 3920.0}}
        obs = e.step(make_action("data_cleaning_expert", payload))
        assert obs.partial_credits.get("r05_revenue_correct") is True
        assert obs.partial_credits.get("r12_revenue_correct") is True

    def test_data_expert_revenue_string_accepted(self):
        """Revenue grader should accept string-formatted numbers."""
        e = MetaEnvironment()
        e.reset()
        payload = {**CORRECT_PAYLOADS["data_cleaning_expert"],
                   "revenue_by_rep": {"R05": "3,625.50", "R12": "3904.94"}}
        obs = e.step(make_action("data_cleaning_expert", payload))
        assert obs.partial_credits.get("r05_revenue_correct") is True

    def test_content_mod_expert_context_loads(self):
        e = MetaEnvironment()
        e.reset()
        ctx, grader, diff = e._load_context("content_moderation_expert")
        assert diff == "expert"
        assert "cases" in ctx
        assert len(ctx["cases"]) == 5

    def test_content_mod_expert_perfect_score(self):
        e = MetaEnvironment()
        e.reset()
        obs = e.step(make_action("content_moderation_expert", CORRECT_PAYLOADS["content_moderation_expert"]))
        assert obs.score == 1.0, f"content_mod_expert score was {obs.score}: {obs.feedback}"

    def test_ticket_expert_context_loads(self):
        e = MetaEnvironment()
        e.reset()
        ctx, grader, diff = e._load_context("ticket_triage_expert")
        assert diff == "expert"
        assert "post_incident_report" in ctx

    def test_ticket_expert_perfect_score(self):
        e = MetaEnvironment()
        e.reset()
        obs = e.step(make_action("ticket_triage_expert", CORRECT_PAYLOADS["ticket_triage_expert"]))
        assert obs.score == 1.0, f"ticket_expert score was {obs.score}: {obs.feedback}"

    def test_expert_score_in_range(self):
        """All expert tasks should return scores in [0, 1]."""
        expert_ids = [t for t in ALL_TASK_IDS if t.endswith("_expert")]
        for task_id in expert_ids:
            e = MetaEnvironment()
            e.reset()
            obs = e.step(make_action(task_id, CORRECT_PAYLOADS[task_id]))
            assert 0.0 <= obs.score <= 1.0, f"{task_id}: {obs.score}"


# ═════════════════════════════════════════════════════════════════════════════
# 5. CONTEXT LOADING (all 24 tasks)
# ═════════════════════════════════════════════════════════════════════════════

class TestContextLoading:
    @pytest.mark.parametrize("task_id", ALL_TASK_IDS)
    def test_probe_nonempty_context(self, task_id):
        e = MetaEnvironment()
        e.reset()
        agent = "cross_agent" if task_id.startswith("cross_agent") else "_".join(task_id.split("_")[:-1])
        probe = MetaAction(message=json.dumps({"agent": agent, "task_id": task_id, "payload": {"_probe": True}}))
        obs = e.step(probe)
        assert isinstance(obs.context, dict) and len(obs.context) > 0

    @pytest.mark.parametrize("task_id", ALL_TASK_IDS)
    def test_task_id_echoed(self, task_id):
        e = MetaEnvironment()
        e.reset()
        obs = e.step(make_action(task_id, CORRECT_PAYLOADS[task_id]))
        assert obs.task_id == task_id

    def test_deterministic_context_same_episode(self):
        e = MetaEnvironment()
        e.reset()
        ctx1, _, _ = e._load_context("email_triage_easy")
        ctx2, _, _ = e._load_context("email_triage_easy")
        assert ctx1 == ctx2


# ═════════════════════════════════════════════════════════════════════════════
# 6. DETERMINISM (fixed-context tasks)
# ═════════════════════════════════════════════════════════════════════════════

class TestDeterminism:
    @pytest.mark.parametrize("task_id", DETERMINISTIC_TASK_IDS)
    def test_same_score_3x(self, task_id):
        scores = []
        for _ in range(3):
            e = MetaEnvironment()
            e.reset()
            obs = e.step(make_action(task_id, CORRECT_PAYLOADS[task_id]))
            scores.append(obs.score)
        assert scores[0] == scores[1] == scores[2]

    @pytest.mark.parametrize("task_id", DETERMINISTIC_TASK_IDS)
    def test_same_partial_credits_3x(self, task_id):
        partials = []
        for _ in range(3):
            e = MetaEnvironment()
            e.reset()
            obs = e.step(make_action(task_id, CORRECT_PAYLOADS[task_id]))
            partials.append(obs.partial_credits)
        assert partials[0] == partials[1] == partials[2]


# ═════════════════════════════════════════════════════════════════════════════
# 7. GRADER QUALITY
# ═════════════════════════════════════════════════════════════════════════════

class TestGraderQuality:
    def test_email_easy_perfect_on_correct_label(self):
        e = MetaEnvironment()
        e.reset()
        _, grader_ctx, _ = e._load_context("email_triage_easy")
        e._current_grader_context = grader_ctx
        e._current_task_id = "email_triage_easy"
        correct = grader_ctx["email"]["label"]
        obs = e.step(make_action("email_triage_easy", {"classification": correct}))
        assert obs.score == 1.0

    def test_email_easy_zero_on_wrong_label(self):
        e = MetaEnvironment()
        e.reset()
        _, grader_ctx, _ = e._load_context("email_triage_easy")
        e._current_grader_context = grader_ctx
        e._current_task_id = "email_triage_easy"
        correct = grader_ctx["email"]["label"]
        wrong = [l for l in ["spam", "important", "newsletter"] if l != correct][0]
        obs = e.step(make_action("email_triage_easy", {"classification": wrong}))
        assert obs.score == 0.0

    def test_email_medium_perfect_order(self):
        e = MetaEnvironment()
        e.reset()
        e.step(make_action("email_triage_medium", {"_probe": True}))
        correct_order = e._current_grader_context["correct_order"]
        obs = e.step(make_action("email_triage_medium", {"order": correct_order}))
        assert obs.score == 1.0

    def test_code_hard_perfect_score(self):
        e = MetaEnvironment()
        e.reset()
        obs = e.step(make_action("code_review_hard", CORRECT_PAYLOADS["code_review_hard"]))
        assert obs.score == 1.0

    def test_code_hard_partial_credit_5_of_8(self):
        e = MetaEnvironment()
        e.reset()
        partial = {"vulnerabilities": CORRECT_PAYLOADS["code_review_hard"]["vulnerabilities"][:5]}
        obs = e.step(make_action("code_review_hard", partial))
        assert 0.0 < obs.score < 1.0

    def test_content_mod_hard_perfect(self):
        e = MetaEnvironment()
        e.reset()
        obs = e.step(make_action("content_moderation_hard", CORRECT_PAYLOADS["content_moderation_hard"]))
        assert obs.score == 1.0

    def test_content_mod_hard_adversarial_cases(self):
        e = MetaEnvironment()
        e.reset()
        payload = {
            "decisions": [
                {"id": "h4", "context_a_label": "harmful", "context_b_label": "harmful"},
                {"id": "h6", "context_a_label": "harmful", "context_b_label": "harmful"},
            ]
        }
        obs = e.step(make_action("content_moderation_hard", payload))
        assert obs.partial_credits.get("h4_context_a") is True
        assert obs.partial_credits.get("h4_context_b") is True

    def test_ticket_triage_medium_tk2_frontend(self):
        """tk2 (EU display bug) must route to frontend, not billing."""
        e = MetaEnvironment()
        e.reset()
        obs = e.step(make_action("ticket_triage_medium", CORRECT_PAYLOADS["ticket_triage_medium"]))
        assert obs.partial_credits.get("team_tk2") is True, (
            f"tk2 should route to frontend. feedback: {obs.feedback}"
        )

    def test_ticket_triage_hard_partial_credit(self):
        e = MetaEnvironment()
        e.reset()
        obs = e.step(make_action("ticket_triage_hard", CORRECT_PAYLOADS["ticket_triage_hard"]))
        assert obs.score >= 0.75

    def test_partial_credit_for_partial_bugs(self):
        e = MetaEnvironment()
        e.reset()
        payload = {"bugs": [
            {"location": "find_max", "issue": "max_val initialized to 0 fails negatives", "fix": "float('-inf')"},
            {"location": "divide",   "issue": "zero division risk", "fix": "check b == 0"},
        ]}
        obs = e.step(make_action("code_review_medium", payload))
        assert 0.0 < obs.score < 1.0

    def test_data_hard_outlier_credit(self):
        e = MetaEnvironment()
        e.reset()
        e.step(make_action("data_cleaning_hard", {"_probe": True}))
        correct_outliers = list(e._current_grader_context["answers"]["outliers"])
        obs = e.step(make_action("data_cleaning_hard", {"outliers": correct_outliers}))
        assert obs.partial_credits.get("outliers_correct") is True

    def test_cross_agent_code_email_partial(self):
        e = MetaEnvironment()
        e.reset()
        payload = {
            "vulnerability_type": "sql_injection",
            "vulnerability_location": "get_user_profile",
            "disclosure_email": "",
        }
        obs = e.step(make_action("cross_agent_code_email", payload))
        assert obs.score < 1.0


# ═════════════════════════════════════════════════════════════════════════════
# 8. EPISODE TRACKING
# ═════════════════════════════════════════════════════════════════════════════

class TestEpisodeTracking:
    def test_step_count_increments(self):
        e = MetaEnvironment()
        e.reset()
        assert e.state.step_count == 0
        e.step(make_action("email_triage_easy", {"classification": "spam"}))
        assert e.state.step_count == 1

    def test_episode_scores_cleared_on_reset(self):
        e = MetaEnvironment()
        e.reset()
        e.step(make_action("email_triage_easy", {"classification": "spam"}))
        assert len(e._episode_scores) == 1
        e.reset()
        assert e._episode_scores == []

    def test_attempt_tracking(self):
        e = MetaEnvironment()
        e.reset()
        obs1 = e.step(make_action("email_triage_medium", {"order": ["m1"]}))
        assert obs1.metadata.get("attempt") == 1
        assert not obs1.done
        obs2 = e.step(make_action("email_triage_medium", CORRECT_PAYLOADS["email_triage_medium"]))
        assert obs2.metadata.get("attempt") == 2
        assert obs2.done
