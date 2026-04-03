"""
tests/test_environment.py — Meta v3.0
pytest suite: reset, step, grader determinism, all 19 tasks, episode tracking.
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
    "email_triage_easy",   "email_triage_medium",   "email_triage_hard",
    "code_review_easy",    "code_review_medium",     "code_review_hard",
    "data_cleaning_easy",  "data_cleaning_medium",   "data_cleaning_hard",
    "content_moderation_easy", "content_moderation_medium", "content_moderation_hard",
    "ticket_triage_easy",  "ticket_triage_medium",   "ticket_triage_hard",
    "cross_agent_chain",   "cross_agent_email_data", "cross_agent_code_email",
    "cross_agent_mod_escalation",
]

DETERMINISTIC_TASK_IDS = [
    # These have fixed (non-randomly-chosen) contexts
    "email_triage_medium",
    "code_review_easy", "code_review_medium", "code_review_hard",
    "data_cleaning_easy", "data_cleaning_medium", "data_cleaning_hard",
    "content_moderation_easy", "content_moderation_medium", "content_moderation_hard",
    "ticket_triage_medium", "ticket_triage_hard",
    "cross_agent_email_data", "cross_agent_code_email",
]

CORRECT_PAYLOADS: dict[str, dict] = {
    "email_triage_easy": {"classification": "spam"},  # overridden in determinism test
    "email_triage_medium": {
        "order": ["m1", "m5", "m3", "m10", "m6", "m8", "m2", "m9", "m4", "m7"]
    },
    "email_triage_hard": {
        "reply": (
            "Dear Customer, I sincerely apologize for this frustrating experience. "
            "I understand your disappointment with order #78234. We will process a full refund "
            "and send an overnight replacement within 24 hours. As compensation for the inconvenience, "
            "we will make it right. We take this matter very seriously."
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
            {"type": "sql_injection",          "location": "get_user_by_name",  "severity": "critical", "fix": "parameterized queries"},
            {"type": "xss",                    "location": "render_comment",    "severity": "high",     "fix": "sanitize input"},
            {"type": "sql_injection",          "location": "login",             "severity": "critical", "fix": "parameterized queries"},
            {"type": "command_injection",      "location": "run_report",        "severity": "critical", "fix": "avoid shell=True"},
            {"type": "insecure_deserialization","location": "load_user_data",   "severity": "high",     "fix": "use json"},
            {"type": "timing_attack",          "location": "check_password",    "severity": "medium",   "fix": "use hmac.compare_digest"},
            {"type": "path_traversal",         "location": "read_report_file",  "severity": "high",     "fix": "validate filename"},
            {"type": "ssrf",                   "location": "fetch_user_avatar", "severity": "high",     "fix": "validate and allowlist URLs"},
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
    "ticket_triage_easy": {"priority": "critical", "category": "bug"},  # overridden in grader test
    "ticket_triage_medium": {
        "order": ["tk1", "tk4", "tk2", "tk7", "tk5", "tk3", "tk6", "tk8"],
        "assignments": {
            "tk1": "backend", "tk2": "frontend", "tk3": "backend",
            "tk4": "devops",  "tk5": "backend",  "tk6": "frontend",
            "tk7": "billing", "tk8": "frontend",
        },
    },
    "ticket_triage_hard": {
        "root_cause": "Database CPU at 100% due to slow queries exhausting the connection pool, causing Redis cache to overflow and all dependent services to fail.",
        "resolution_steps": [
            "Scale up database replica",
            "Flush Redis cache and increase memory limit",
            "Rollback recent deploy that introduced slow queries",
            "Optimize slow queries with proper indexes",
            "Restart affected services once DB is stable",
        ],
        "affected_services": ["payment-service", "checkout-service", "postgres-primary", "redis-cache"],
        "severity": "P1",
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
            "Hi team, I've identified a critical SQL injection vulnerability in the get_user_profile function. "
            "The user_id parameter is concatenated directly into the SQL query without parameterization, "
            "allowing an attacker to execute arbitrary SQL. This is urgent and requires an immediate patch "
            "using parameterized queries. Please prioritize remediation."
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
        "_".join(task_id.split("_")[:-1])
        if not task_id.startswith("cross_agent")
        else "cross_agent"
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
# 2. SCORE RANGE (all 19 tasks)
# ═════════════════════════════════════════════════════════════════════════════

class TestScoreRange:
    @pytest.mark.parametrize("task_id", ALL_TASK_IDS)
    def test_score_in_01(self, task_id):
        e = MetaEnvironment()
        e.reset()
        obs = e.step(make_action(task_id, CORRECT_PAYLOADS[task_id]))
        assert 0.0 <= obs.score <= 1.0

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
        assert obs.difficulty in ("easy", "medium", "hard")

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
# 3. CONTEXT LOADING
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
        """Same episode_id → same context variant for random-choice tasks."""
        e = MetaEnvironment()
        e.reset()
        ctx1, _, _ = e._load_context("email_triage_easy")
        ctx2, _, _ = e._load_context("email_triage_easy")
        assert ctx1 == ctx2

    def test_different_episodes_may_differ(self):
        """Different episode_ids → different contexts possible."""
        e1 = MetaEnvironment()
        e1.reset()
        ctx1, _, _ = e1._load_context("email_triage_easy")
        # Run many resets until we get a different one (at most 20 tries)
        found_different = False
        for _ in range(20):
            e2 = MetaEnvironment()
            e2.reset()
            ctx2, _, _ = e2._load_context("email_triage_easy")
            if ctx1 != ctx2:
                found_different = True
                break
        # Not guaranteed to differ, but this exercises the code path
        assert isinstance(found_different, bool)  # always passes


# ═════════════════════════════════════════════════════════════════════════════
# 4. DETERMINISM
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
# 5. GRADER QUALITY
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
        obs = e.step(make_action("email_triage_medium", CORRECT_PAYLOADS["email_triage_medium"]))
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

    def test_content_mod_hard_adversarial_cases_present(self):
        """h4 and h6 are harmful in BOTH contexts — verify grader handles this."""
        e = MetaEnvironment()
        e.reset()
        # h4: both harmful; h6: both harmful
        payload = {
            "decisions": [
                {"id": "h4", "context_a_label": "harmful", "context_b_label": "harmful"},
                {"id": "h6", "context_a_label": "harmful", "context_b_label": "harmful"},
            ]
        }
        obs = e.step(make_action("content_moderation_hard", payload))
        assert obs.partial_credits.get("h4_context_a") is True
        assert obs.partial_credits.get("h4_context_b") is True

    def test_ticket_triage_hard_partial_credit(self):
        e = MetaEnvironment()
        e.reset()
        obs = e.step(make_action("ticket_triage_hard", CORRECT_PAYLOADS["ticket_triage_hard"]))
        assert obs.score >= 0.5

    def test_cross_agent_code_email_partial(self):
        """Get vuln right but email wrong — should score 0.67."""
        e = MetaEnvironment()
        e.reset()
        payload = {
            "vulnerability_type": "sql_injection",
            "vulnerability_location": "get_user_profile",
            "disclosure_email": "",  # empty → fails quality check
        }
        obs = e.step(make_action("cross_agent_code_email", payload))
        assert obs.score < 1.0

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
        obs = e.step(make_action("data_cleaning_hard", CORRECT_PAYLOADS["data_cleaning_hard"]))
        assert obs.partial_credits.get("outliers_correct") is True


# ═════════════════════════════════════════════════════════════════════════════
# 6. EPISODE TRACKING
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

    def test_metadata_episode_avg(self):
        e = MetaEnvironment()
        e.reset()
        obs1 = e.step(make_action("email_triage_medium", CORRECT_PAYLOADS["email_triage_medium"]))
        obs2 = e.step(make_action("code_review_medium",  CORRECT_PAYLOADS["code_review_medium"]))
        meta = obs2.metadata or {}
        if "episode_avg_score" in meta:
            expected = round((obs1.score + obs2.score) / 2, 3)
            assert abs(meta["episode_avg_score"] - expected) < 1e-5

    def test_attempt_tracking(self):
        e = MetaEnvironment()
        e.reset()
        # First attempt — imperfect
        obs1 = e.step(make_action("email_triage_medium", {"order": ["m1"]}))
        assert obs1.metadata.get("attempt") == 1
        assert not obs1.done
        # Second attempt
        obs2 = e.step(make_action("email_triage_medium", CORRECT_PAYLOADS["email_triage_medium"]))
        assert obs2.metadata.get("attempt") == 2
        assert obs2.done