"""
Tests for all 4 Digital Yodha environments.
Run: pytest tests/test_envs.py -v
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import pytest
from models import Action
from environments.email_triage.env import EmailTriageEnv
from environments.code_review.env import CodeReviewEnv
from environments.data_cleaning.env import DataCleaningEnv
from environments.content_moderation.env import ContentModerationEnv


# ─── Email Triage ─────────────────────────────────────────────────────────────

class TestEmailTriage:
    def setup_method(self):
        self.env = EmailTriageEnv()

    def test_reset_easy(self):
        obs = self.env.reset("email_triage_easy")
        assert obs.agent == "email_triage"
        assert obs.difficulty == "easy"
        assert "email" in obs.context

    def test_step_easy_correct(self):
        obs = self.env.reset("email_triage_easy")
        correct_label = obs.context["email"]["label"]
        action = Action(agent="email_triage", task_id="email_triage_easy", payload={"classification": correct_label})
        result = self.env.step(action)
        assert result.reward.score == 1.0
        assert result.done is True

    def test_step_easy_wrong(self):
        obs = self.env.reset("email_triage_easy")
        correct_label = obs.context["email"]["label"]
        wrong = {"spam": "important", "important": "spam", "newsletter": "spam"}[correct_label]
        action = Action(agent="email_triage", task_id="email_triage_easy", payload={"classification": wrong})
        result = self.env.step(action)
        assert result.reward.score == 0.0

    def test_reset_medium(self):
        obs = self.env.reset("email_triage_medium")
        assert obs.difficulty == "medium"
        assert len(obs.context["emails"]) == 10

    def test_step_medium_perfect(self):
        self.env.reset("email_triage_medium")
        perfect_order = ["m1", "m5", "m3", "m6", "m10", "m8", "m2", "m4", "m7", "m9"]
        action = Action(agent="email_triage", task_id="email_triage_medium", payload={"order": perfect_order})
        result = self.env.step(action)
        assert result.reward.score == 1.0

    def test_reset_hard(self):
        obs = self.env.reset("email_triage_hard")
        assert obs.difficulty == "hard"
        assert "email" in obs.context

    def test_step_hard_partial(self):
        self.env.reset("email_triage_hard")
        partial_reply = "I understand your frustration and sincerely apologize. We will process a full refund and send a replacement within 24 hours."
        action = Action(agent="email_triage", task_id="email_triage_hard", payload={"reply": partial_reply})
        result = self.env.step(action)
        assert result.reward.score > 0.0
        assert result.reward.score <= 1.0

    def test_state(self):
        self.env.reset("email_triage_easy")
        state = self.env.state()
        assert "task_id" in state
        assert "done" in state


# ─── Code Review ──────────────────────────────────────────────────────────────

class TestCodeReview:
    def setup_method(self):
        self.env = CodeReviewEnv()

    def test_reset_easy(self):
        obs = self.env.reset("code_review_easy")
        assert obs.agent == "code_review"
        assert "code" in obs.context

    def test_step_easy_correct(self):
        self.env.reset("code_review_easy")
        action = Action(agent="code_review", task_id="code_review_easy", payload={"errors": ["missing colon after for loop"]})
        result = self.env.step(action)
        assert result.reward.score == 1.0

    def test_step_easy_wrong(self):
        self.env.reset("code_review_easy")
        action = Action(agent="code_review", task_id="code_review_easy", payload={"errors": ["wrong indentation"]})
        result = self.env.step(action)
        assert result.reward.score == 0.0

    def test_reset_medium(self):
        obs = self.env.reset("code_review_medium")
        assert obs.difficulty == "medium"

    def test_step_medium_all_bugs(self):
        self.env.reset("code_review_medium")
        action = Action(agent="code_review", task_id="code_review_medium", payload={
            "bugs": [
                {"location": "find_max", "issue": "max_val initialized to 0, fails for all-negative lists", "fix": "Initialize to None or float('-inf')"},
                {"location": "get_user", "issue": "uses assignment = instead of comparison ==", "fix": "Change = to =="},
                {"location": "divide", "issue": "no zero division guard", "fix": "Check if b == 0 before dividing"},
            ]
        })
        result = self.env.step(action)
        assert result.reward.score == 1.0

    def test_reset_hard(self):
        obs = self.env.reset("code_review_hard")
        assert obs.difficulty == "hard"

    def test_step_hard_all_vulns(self):
        self.env.reset("code_review_hard")
        action = Action(agent="code_review", task_id="code_review_hard", payload={
            "vulnerabilities": [
                {"type": "sql_injection", "location": "get_user_by_name", "fix": "Use parameterized queries"},
                {"type": "xss", "location": "render_comment", "fix": "Sanitize or escape HTML"},
                {"type": "sql_injection", "location": "login", "fix": "Use parameterized queries"},
            ]
        })
        result = self.env.step(action)
        assert result.reward.score == 1.0


# ─── Data Cleaning ────────────────────────────────────────────────────────────

class TestDataCleaning:
    def setup_method(self):
        self.env = DataCleaningEnv()

    def test_reset_easy(self):
        obs = self.env.reset("data_cleaning_easy")
        assert obs.agent == "data_cleaning"
        assert "data" in obs.context

    def test_step_easy_perfect(self):
        self.env.reset("data_cleaning_easy")
        action = Action(agent="data_cleaning", task_id="data_cleaning_easy", payload={
            "missing": ["age (row 2)", "name (row 4)", "email (row 5)"],
            "duplicates": [1, 3]
        })
        result = self.env.step(action)
        assert result.reward.score == 1.0

    def test_step_easy_partial(self):
        self.env.reset("data_cleaning_easy")
        action = Action(agent="data_cleaning", task_id="data_cleaning_easy", payload={
            "missing": ["age (row 2)"],
            "duplicates": [1, 3]
        })
        result = self.env.step(action)
        assert 0.0 < result.reward.score < 1.0

    def test_reset_medium(self):
        obs = self.env.reset("data_cleaning_medium")
        assert obs.difficulty == "medium"

    def test_reset_hard(self):
        obs = self.env.reset("data_cleaning_hard")
        assert obs.difficulty == "hard"

    def test_step_hard_outliers(self):
        self.env.reset("data_cleaning_hard")
        action = Action(agent="data_cleaning", task_id="data_cleaning_hard", payload={
            "outliers": [4, 8],
            "missing": [6],
            "cleaned_data": [
                {"id": 1, "value": 10.5}, {"id": 2, "value": 11.2},
                {"id": 3, "value": 10.8}, {"id": 4, "value": 10.8},
                {"id": 5, "value": 10.1}, {"id": 6, "value": 10.8},
                {"id": 7, "value": 11.5}, {"id": 8, "value": 10.8},
                {"id": 9, "value": 10.9}, {"id": 10, "value": 11.0},
            ]
        })
        result = self.env.step(action)
        assert result.reward.score == 1.0


# ─── Content Moderation ───────────────────────────────────────────────────────

class TestContentModeration:
    def setup_method(self):
        self.env = ContentModerationEnv()

    def test_reset_easy(self):
        obs = self.env.reset("content_moderation_easy")
        assert obs.agent == "content_moderation"
        assert "posts" in obs.context

    def test_step_easy_perfect(self):
        self.env.reset("content_moderation_easy")
        action = Action(agent="content_moderation", task_id="content_moderation_easy", payload={
            "classifications": [
                {"id": "c1", "label": "harmful"},
                {"id": "c2", "label": "safe"},
                {"id": "c3", "label": "harmful"},
                {"id": "c4", "label": "safe"},
                {"id": "c5", "label": "harmful"},
            ]
        })
        result = self.env.step(action)
        assert result.reward.score == 1.0

    def test_step_easy_partial(self):
        self.env.reset("content_moderation_easy")
        action = Action(agent="content_moderation", task_id="content_moderation_easy", payload={
            "classifications": [
                {"id": "c1", "label": "safe"},  # wrong
                {"id": "c2", "label": "safe"},
                {"id": "c3", "label": "harmful"},
                {"id": "c4", "label": "safe"},
                {"id": "c5", "label": "harmful"},
            ]
        })
        result = self.env.step(action)
        assert result.reward.score == 0.8

    def test_reset_hard(self):
        obs = self.env.reset("content_moderation_hard")
        assert obs.difficulty == "hard"
        assert "cases" in obs.context

    def test_step_hard_perfect(self):
        self.env.reset("content_moderation_hard")
        action = Action(agent="content_moderation", task_id="content_moderation_hard", payload={
            "decisions": [
                {"id": "h1", "context_a_label": "safe", "context_b_label": "harmful"},
                {"id": "h2", "context_a_label": "safe", "context_b_label": "harmful"},
            ]
        })
        result = self.env.step(action)
        assert result.reward.score == 1.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
