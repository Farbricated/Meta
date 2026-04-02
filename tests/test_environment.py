"""
tests/test_environment.py
pytest test suite for the Meta Multi-Agent OpenEnv environment.

Tests:
  - reset() returns valid observation
  - step() returns scores 0.0–1.0 for all 12 tasks
  - All 12 task IDs load context correctly
  - Graders are deterministic (same input → same output)
  - Episode average score tracked correctly
"""

import sys
import os
import json
import pytest

# Allow imports from repo root
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from server.Meta_environment import MetaEnvironment
from models import MetaAction, MetaObservation

# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def env():
    e = MetaEnvironment()
    e.reset()
    return e


TASK_IDS = [
    "email_triage_easy",
    "email_triage_medium",
    "email_triage_hard",
    "code_review_easy",
    "code_review_medium",
    "code_review_hard",
    "data_cleaning_easy",
    "data_cleaning_medium",
    "data_cleaning_hard",
    "content_moderation_easy",
    "content_moderation_medium",
    "content_moderation_hard",
]

# Representative "correct" payloads per task for determinism checks
CORRECT_PAYLOADS = {
    "email_triage_easy": {
        "classification": "spam"
    },
    "email_triage_medium": {
        "order": ["m1", "m5", "m3", "m10", "m6", "m8", "m2", "m9", "m4", "m7"]
    },
    "email_triage_hard": {
        "reply": (
            "Dear Customer, I sincerely apologize for the inconvenience caused. "
            "I understand your frustration with order #78234. We will send a full refund "
            "and an overnight replacement within 24 hours. As compensation for this "
            "experience, we will make it right. We take this matter very seriously."
        )
    },
    "code_review_easy": {
        "errors": ["missing colon after for statement syntax error"]
    },
    "code_review_medium": {
        "bugs": [
            {"location": "find_max", "issue": "max_val initialized to 0, fails for all-negative lists", "fix": "use float('-inf')"},
            {"location": "get_user", "issue": "assignment = used instead of comparison ==", "fix": "use == for comparison"},
            {"location": "divide", "issue": "no division by zero guard", "fix": "check if b == 0"},
            {"location": "process_list", "issue": "off-by-one error range(len(items)+1) causes IndexError", "fix": "use range(len(items))"},
        ]
    },
    "code_review_hard": {
        "vulnerabilities": [
            {"type": "sql_injection", "location": "get_user_by_name", "fix": "use parameterized queries"},
            {"type": "xss", "location": "render_comment", "fix": "sanitize and escape user input"},
            {"type": "sql_injection", "location": "login", "fix": "use parameterized queries"},
            {"type": "command_injection", "location": "run_report", "fix": "avoid shell=True, use list args"},
            {"type": "insecure_deserialization", "location": "load_user_data", "fix": "use json instead of pickle"},
        ]
    },
    "data_cleaning_easy": {
        "missing": ["age (row 2)", "name (row 4)", "email (row 5)", "salary (row 6)"],
        "duplicates": [1, 3],
    },
    "data_cleaning_medium": {
        "issues": {
            "age":       "mixed types: strings should be integers",
            "salary":    "inconsistent format: has $ and commas",
            "join_date": "inconsistent date formats",
            "name":      "inconsistent casing: dave lowercase, EVE all caps",
            "active":    "mixed types: booleans and strings yes/no",
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
            {"id": 1,  "value": 10.5}, {"id": 2,  "value": 11.2},
            {"id": 3,  "value": 10.8}, {"id": 4,  "value": 10.9},
            {"id": 5,  "value": 10.1}, {"id": 6,  "value": 10.8},
            {"id": 7,  "value": 11.5}, {"id": 8,  "value": 10.9},
            {"id": 9,  "value": 10.9}, {"id": 10, "value": 11.0},
            {"id": 11, "value": 10.8}, {"id": 12, "value": 10.7},
        ],
    },
    "content_moderation_easy": {
        "classifications": [
            {"id": "c1", "label": "harmful"},
            {"id": "c2", "label": "safe"},
            {"id": "c3", "label": "harmful"},
            {"id": "c4", "label": "safe"},
            {"id": "c5", "label": "harmful"},
            {"id": "c6", "label": "safe"},
            {"id": "c7", "label": "harmful"},
        ]
    },
    "content_moderation_medium": {
        "classifications": [
            {"id": "m1", "label": "harmful"},
            {"id": "m2", "label": "harmful"},
            {"id": "m3", "label": "safe"},
            {"id": "m4", "label": "harmful"},
            {"id": "m5", "label": "harmful"},
            {"id": "m6", "label": "safe"},
            {"id": "m7", "label": "harmful"},
            {"id": "m8", "label": "safe"},
        ]
    },
    "content_moderation_hard": {
        "decisions": [
            {"id": "h1", "context_a_label": "safe",   "context_b_label": "harmful"},
            {"id": "h2", "context_a_label": "safe",   "context_b_label": "harmful"},
            {"id": "h3", "context_a_label": "safe",   "context_b_label": "harmful"},
        ]
    },
}

# ── Helper ────────────────────────────────────────────────────────────────────

def make_action(task_id: str, payload: dict) -> MetaAction:
    agent = "_".join(task_id.split("_")[:-1])
    return MetaAction(message=json.dumps({
        "agent": agent,
        "task_id": task_id,
        "payload": payload,
    }))


# ══════════════════════════════════════════════════════════════════════════════
# 1. RESET TESTS
# ══════════════════════════════════════════════════════════════════════════════

class TestReset:

    def test_reset_returns_meta_observation(self):
        env = MetaEnvironment()
        obs = env.reset()
        assert isinstance(obs, MetaObservation)

    def test_reset_returns_zero_score(self):
        env = MetaEnvironment()
        obs = env.reset()
        assert obs.score == 0.0

    def test_reset_clears_episode_scores(self):
        env = MetaEnvironment()
        # Run a task to add a score
        env.reset()
        env.step(make_action("email_triage_easy", {"classification": "spam"}))
        assert len(env._episode_scores) == 1
        # Reset should clear
        env.reset()
        assert len(env._episode_scores) == 0

    def test_reset_new_episode_id(self):
        env = MetaEnvironment()
        obs1 = env.reset()
        id1  = env.state.episode_id
        env.reset()
        id2  = env.state.episode_id
        assert id1 != id2

    def test_reset_step_count_zero(self):
        env = MetaEnvironment()
        env.reset()
        env.step(make_action("email_triage_easy", {"classification": "spam"}))
        env.reset()
        assert env.state.step_count == 0

    def test_reset_observation_has_instructions(self):
        env = MetaEnvironment()
        obs = env.reset()
        assert isinstance(obs.instructions, str)
        assert len(obs.instructions) > 10


# ══════════════════════════════════════════════════════════════════════════════
# 2. STEP / SCORE RANGE TESTS
# ══════════════════════════════════════════════════════════════════════════════

class TestStepScoreRange:

    @pytest.mark.parametrize("task_id", TASK_IDS)
    def test_score_between_0_and_1(self, task_id):
        env = MetaEnvironment()
        env.reset()
        payload = CORRECT_PAYLOADS[task_id]
        obs = env.step(make_action(task_id, payload))
        assert 0.0 <= obs.score <= 1.0, (
            f"{task_id}: score {obs.score} outside [0.0, 1.0]"
        )

    @pytest.mark.parametrize("task_id", TASK_IDS)
    def test_reward_matches_score(self, task_id):
        env = MetaEnvironment()
        env.reset()
        obs = env.step(make_action(task_id, CORRECT_PAYLOADS[task_id]))
        assert obs.reward == obs.score, (
            f"{task_id}: reward {obs.reward} != score {obs.score}"
        )

    @pytest.mark.parametrize("task_id", TASK_IDS)
    def test_empty_payload_returns_negative_reward(self, task_id):
        env = MetaEnvironment()
        env.reset()
        obs = env.step(make_action(task_id, {}))
        assert obs.reward <= 0.0, f"{task_id}: empty payload should return reward ≤ 0"

    @pytest.mark.parametrize("task_id", TASK_IDS)
    def test_correct_payload_scores_above_zero(self, task_id):
        env = MetaEnvironment()
        env.reset()
        obs = env.step(make_action(task_id, CORRECT_PAYLOADS[task_id]))
        assert obs.score > 0.0, (
            f"{task_id}: correct payload should score > 0, got {obs.score}"
        )

    @pytest.mark.parametrize("task_id", TASK_IDS)
    def test_step_returns_meta_observation(self, task_id):
        env = MetaEnvironment()
        env.reset()
        obs = env.step(make_action(task_id, CORRECT_PAYLOADS[task_id]))
        assert isinstance(obs, MetaObservation)

    @pytest.mark.parametrize("task_id", TASK_IDS)
    def test_observation_has_feedback(self, task_id):
        env = MetaEnvironment()
        env.reset()
        obs = env.step(make_action(task_id, CORRECT_PAYLOADS[task_id]))
        assert isinstance(obs.feedback, str) and len(obs.feedback) > 0

    @pytest.mark.parametrize("task_id", TASK_IDS)
    def test_observation_has_difficulty(self, task_id):
        env = MetaEnvironment()
        env.reset()
        obs = env.step(make_action(task_id, CORRECT_PAYLOADS[task_id]))
        assert obs.difficulty in ("easy", "medium", "hard")

    def test_invalid_json_returns_error_obs(self):
        env = MetaEnvironment()
        env.reset()
        bad_action = MetaAction(message="not json at all }{")
        obs = env.step(bad_action)
        assert obs.score == 0.0
        assert "error" in obs.feedback.lower() or "parse" in obs.feedback.lower()


# ══════════════════════════════════════════════════════════════════════════════
# 3. CONTEXT LOADING TESTS
# ══════════════════════════════════════════════════════════════════════════════

class TestContextLoading:

    @pytest.mark.parametrize("task_id", TASK_IDS)
    def test_probe_loads_non_empty_context(self, task_id):
        env = MetaEnvironment()
        env.reset()
        agent = "_".join(task_id.split("_")[:-1])
        probe = MetaAction(message=json.dumps({
            "agent":   agent,
            "task_id": task_id,
            "payload": {"_probe": True},
        }))
        obs = env.step(probe)
        assert isinstance(obs.context, dict)
        assert len(obs.context) > 0, f"{task_id}: context should not be empty"

    @pytest.mark.parametrize("task_id", TASK_IDS)
    def test_probe_returns_instructions(self, task_id):
        env = MetaEnvironment()
        env.reset()
        agent = "_".join(task_id.split("_")[:-1])
        probe = MetaAction(message=json.dumps({
            "agent":   agent,
            "task_id": task_id,
            "payload": {"_probe": True},
        }))
        obs = env.step(probe)
        assert isinstance(obs.instructions, str)
        assert len(obs.instructions) > 20

    @pytest.mark.parametrize("task_id", TASK_IDS)
    def test_task_id_is_echoed_in_observation(self, task_id):
        env = MetaEnvironment()
        env.reset()
        obs = env.step(make_action(task_id, CORRECT_PAYLOADS[task_id]))
        assert obs.task_id == task_id

    def test_unknown_task_id_returns_error(self):
        env = MetaEnvironment()
        env.reset()
        obs = env.step(make_action("totally_fake_task", {"x": 1}))
        assert obs.score == 0.0
        assert obs.task_id == "totally_fake_task"

    @pytest.mark.parametrize("task_id", TASK_IDS)
    def test_partial_credits_is_dict(self, task_id):
        env = MetaEnvironment()
        env.reset()
        obs = env.step(make_action(task_id, CORRECT_PAYLOADS[task_id]))
        assert isinstance(obs.partial_credits, dict)


# ══════════════════════════════════════════════════════════════════════════════
# 4. DETERMINISM TESTS
# ══════════════════════════════════════════════════════════════════════════════

class TestDeterminism:
    """
    Graders must be deterministic: same payload → same score every time.
    Note: email_triage_easy and email_triage_hard use random.choice for context,
    so we test determinism on the grader logic given a fixed grader context,
    not on context selection.
    """

    DETERMINISTIC_TASKS = [
        "email_triage_medium",   # fixed emails list, no random
        "code_review_easy",
        "code_review_medium",
        "code_review_hard",
        "data_cleaning_easy",
        "data_cleaning_medium",
        "data_cleaning_hard",
        "content_moderation_easy",
        "content_moderation_medium",
        "content_moderation_hard",
    ]

    @pytest.mark.parametrize("task_id", DETERMINISTIC_TASKS)
    def test_same_payload_same_score_3x(self, task_id):
        scores = []
        for _ in range(3):
            env = MetaEnvironment()
            env.reset()
            obs = env.step(make_action(task_id, CORRECT_PAYLOADS[task_id]))
            scores.append(obs.score)
        assert scores[0] == scores[1] == scores[2], (
            f"{task_id}: non-deterministic scores across runs: {scores}"
        )

    @pytest.mark.parametrize("task_id", DETERMINISTIC_TASKS)
    def test_same_payload_same_feedback_3x(self, task_id):
        feedbacks = []
        for _ in range(3):
            env = MetaEnvironment()
            env.reset()
            obs = env.step(make_action(task_id, CORRECT_PAYLOADS[task_id]))
            feedbacks.append(obs.feedback)
        assert feedbacks[0] == feedbacks[1] == feedbacks[2], (
            f"{task_id}: non-deterministic feedback: {feedbacks}"
        )

    @pytest.mark.parametrize("task_id", DETERMINISTIC_TASKS)
    def test_same_payload_same_partial_credits(self, task_id):
        partials = []
        for _ in range(3):
            env = MetaEnvironment()
            env.reset()
            obs = env.step(make_action(task_id, CORRECT_PAYLOADS[task_id]))
            partials.append(obs.partial_credits)
        assert partials[0] == partials[1] == partials[2], (
            f"{task_id}: non-deterministic partial_credits: {partials}"
        )


# ══════════════════════════════════════════════════════════════════════════════
# 5. EPISODE AVERAGE SCORE TRACKING
# ══════════════════════════════════════════════════════════════════════════════

class TestEpisodeTracking:

    def test_episode_avg_after_one_step(self):
        env = MetaEnvironment()
        env.reset()
        obs = env.step(make_action("email_triage_easy", {"classification": "spam"}))
        assert len(env._episode_scores) == 1
        meta = obs.metadata or {}
        if "episode_avg_score" in meta:
            assert meta["episode_avg_score"] == obs.score

    def test_episode_avg_accumulates(self):
        env = MetaEnvironment()
        env.reset()
        obs1 = env.step(make_action("email_triage_medium", CORRECT_PAYLOADS["email_triage_medium"]))
        obs2 = env.step(make_action("code_review_medium",  CORRECT_PAYLOADS["code_review_medium"]))
        assert len(env._episode_scores) == 2
        expected_avg = round((obs1.score + obs2.score) / 2, 3)
        meta = obs2.metadata or {}
        if "episode_avg_score" in meta:
            assert abs(meta["episode_avg_score"] - expected_avg) < 1e-6

    def test_episode_scores_cleared_on_reset(self):
        env = MetaEnvironment()
        env.reset()
        env.step(make_action("email_triage_easy", {"classification": "spam"}))
        env.step(make_action("code_review_easy",  {"errors": ["missing colon"]}))
        assert len(env._episode_scores) == 2
        env.reset()
        assert env._episode_scores == []

    def test_step_count_increments(self):
        env = MetaEnvironment()
        env.reset()
        assert env.state.step_count == 0
        env.step(make_action("email_triage_easy", {"classification": "spam"}))
        assert env.state.step_count == 1
        env.step(make_action("code_review_easy",  {"errors": ["colon"]}))
        assert env.state.step_count == 2

    def test_full_episode_12_tasks(self):
        """Run all 12 tasks in one episode and verify average is computed."""
        env = MetaEnvironment()
        env.reset()
        scores = []
        for task_id in TASK_IDS:
            obs = env.step(make_action(task_id, CORRECT_PAYLOADS[task_id]))
            scores.append(obs.score)
        assert len(env._episode_scores) == 12
        expected_avg = round(sum(scores) / 12, 3)
        last_meta = obs.metadata or {}
        if "episode_avg_score" in last_meta:
            assert abs(last_meta["episode_avg_score"] - expected_avg) < 1e-6


# ══════════════════════════════════════════════════════════════════════════════
# 6. GRADER QUALITY TESTS
# ══════════════════════════════════════════════════════════════════════════════

class TestGraderQuality:

    def test_email_easy_perfect_score_on_correct(self):
        env = MetaEnvironment()
        env.reset()
        # Force a known context by probing first
        agent_ctx, grader_ctx, _ = env._load_context("email_triage_easy")
        env._current_agent_context  = agent_ctx
        env._current_grader_context = grader_ctx
        env._current_task_id = "email_triage_easy"
        correct_label = grader_ctx["email"]["label"]
        obs = env.step(make_action("email_triage_easy", {"classification": correct_label}))
        assert obs.score == 1.0

    def test_email_easy_zero_on_wrong_label(self):
        env = MetaEnvironment()
        env.reset()
        agent_ctx, grader_ctx, _ = env._load_context("email_triage_easy")
        env._current_agent_context  = agent_ctx
        env._current_grader_context = grader_ctx
        env._current_task_id = "email_triage_easy"
        correct_label = grader_ctx["email"]["label"]
        wrong_labels  = [l for l in ["spam", "important", "newsletter"] if l != correct_label]
        obs = env.step(make_action("email_triage_easy", {"classification": wrong_labels[0]}))
        assert obs.score == 0.0

    def test_email_medium_perfect_order(self):
        env = MetaEnvironment()
        env.reset()
        obs = env.step(make_action("email_triage_medium", CORRECT_PAYLOADS["email_triage_medium"]))
        assert obs.score == 1.0

    def test_code_hard_perfect_score(self):
        env = MetaEnvironment()
        env.reset()
        obs = env.step(make_action("code_review_hard", CORRECT_PAYLOADS["code_review_hard"]))
        assert obs.score == 1.0

    def test_content_mod_hard_perfect_score(self):
        env = MetaEnvironment()
        env.reset()
        obs = env.step(make_action("content_moderation_hard", CORRECT_PAYLOADS["content_moderation_hard"]))
        assert obs.score == 1.0

    def test_data_hard_outlier_detection(self):
        env = MetaEnvironment()
        env.reset()
        obs = env.step(make_action("data_cleaning_hard", CORRECT_PAYLOADS["data_cleaning_hard"]))
        assert obs.score >= 0.67, f"Expected at least 0.67, got {obs.score}"
        assert obs.partial_credits.get("outliers_correct") is True

    def test_partial_credit_for_partial_answer(self):
        env = MetaEnvironment()
        env.reset()
        # Only find 2 of 4 bugs
        partial_payload = {
            "bugs": [
                {"location": "find_max", "issue": "max_val initialized to 0, negative list fails", "fix": "use float('-inf')"},
                {"location": "divide",   "issue": "zero division", "fix": "check b == 0"},
            ]
        }
        obs = env.step(make_action("code_review_medium", partial_payload))
        assert 0.0 < obs.score < 1.0, f"Partial answer should give partial credit, got {obs.score}"
