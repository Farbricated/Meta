"""
models.py — Meta Multi-Agent Environment v3.0
Proper typed Pydantic models per agent with discriminated union.
No more JSON-string-in-message workaround.
"""

from __future__ import annotations
from typing import Any, Dict, List, Literal, Optional, Union
from pydantic import Field
from openenv.core.env_server.types import Action, Observation


# ── Per-agent payload models ───────────────────────────────────────────────────

class EmailTriageEasyPayload(Action):
    agent: Literal["email_triage"] = "email_triage"
    task_id: Literal["email_triage_easy"] = "email_triage_easy"
    classification: str = Field(
        ...,
        description="One of: 'spam', 'important', 'newsletter'",
    )


class EmailTriageMediumPayload(Action):
    agent: Literal["email_triage"] = "email_triage"
    task_id: Literal["email_triage_medium"] = "email_triage_medium"
    order: List[str] = Field(
        ...,
        description="All 10 email IDs ordered most-to-least urgent",
        min_length=10,
        max_length=10,
    )


class EmailTriageHardPayload(Action):
    agent: Literal["email_triage"] = "email_triage"
    task_id: Literal["email_triage_hard"] = "email_triage_hard"
    reply: str = Field(
        ...,
        description="Full professional reply text to the customer complaint",
        min_length=50,
    )


class CodeReviewEasyPayload(Action):
    agent: Literal["code_review"] = "code_review"
    task_id: Literal["code_review_easy"] = "code_review_easy"
    errors: List[str] = Field(
        ...,
        description="List of syntax error descriptions found in the code",
    )


class BugReport(Action):
    location: str = Field(..., description="Function name where the bug occurs")
    issue: str = Field(..., description="Description of the bug")
    fix: str = Field(..., description="Suggested fix")


class CodeReviewMediumPayload(Action):
    agent: Literal["code_review"] = "code_review"
    task_id: Literal["code_review_medium"] = "code_review_medium"
    bugs: List[BugReport] = Field(
        ...,
        description="All logical bugs found, one per function",
    )


class VulnerabilityReport(Action):
    type: str = Field(..., description="Vulnerability type e.g. sql_injection, xss")
    location: str = Field(..., description="Function name where vulnerability exists")
    severity: str = Field(default="high", description="critical | high | medium | low")
    fix: str = Field(..., description="Recommended fix")


class CodeReviewHardPayload(Action):
    agent: Literal["code_review"] = "code_review"
    task_id: Literal["code_review_hard"] = "code_review_hard"
    vulnerabilities: List[VulnerabilityReport] = Field(
        ...,
        description="All security vulnerabilities found",
    )


class DataCleaningEasyPayload(Action):
    agent: Literal["data_cleaning"] = "data_cleaning"
    task_id: Literal["data_cleaning_easy"] = "data_cleaning_easy"
    missing: List[str] = Field(
        ...,
        description="Missing values described as 'field (row N)'",
    )
    duplicates: List[int] = Field(
        ...,
        description="Row IDs that are duplicates",
    )


class DataCleaningMediumPayload(Action):
    agent: Literal["data_cleaning"] = "data_cleaning"
    task_id: Literal["data_cleaning_medium"] = "data_cleaning_medium"
    issues: Dict[str, str] = Field(
        ...,
        description="Field name → description of data quality issue",
    )
    cleaned_data: List[Dict[str, Any]] = Field(
        ...,
        description="The fully cleaned dataset rows",
    )


class DataCleaningHardPayload(Action):
    agent: Literal["data_cleaning"] = "data_cleaning"
    task_id: Literal["data_cleaning_hard"] = "data_cleaning_hard"
    outliers: List[int] = Field(..., description="Row IDs identified as outliers")
    missing: List[int] = Field(..., description="Row IDs with missing values")
    cleaned_data: List[Dict[str, Any]] = Field(
        ...,
        description="Cleaned dataset with outliers removed and missing values imputed",
    )


class ContentModerationEasyPayload(Action):
    agent: Literal["content_moderation"] = "content_moderation"
    task_id: Literal["content_moderation_easy"] = "content_moderation_easy"
    classifications: List[Dict[str, str]] = Field(
        ...,
        description="List of {id, label} where label is 'safe' or 'harmful'",
    )


class ContentModerationMediumPayload(Action):
    agent: Literal["content_moderation"] = "content_moderation"
    task_id: Literal["content_moderation_medium"] = "content_moderation_medium"
    classifications: List[Dict[str, str]] = Field(
        ...,
        description="List of {id, label, reason} for each post",
    )


class ContentModerationHardPayload(Action):
    agent: Literal["content_moderation"] = "content_moderation"
    task_id: Literal["content_moderation_hard"] = "content_moderation_hard"
    decisions: List[Dict[str, str]] = Field(
        ...,
        description="List of {id, context_a_label, context_b_label} for each case",
    )


class CrossAgentChainPayload(Action):
    agent: Literal["cross_agent"] = "cross_agent"
    task_id: Literal["cross_agent_chain"] = "cross_agent_chain"
    email_classification: str = Field(
        ...,
        description="One of: 'spam', 'important', 'newsletter'",
    )
    bugs: List[Dict[str, str]] = Field(
        ...,
        description="Bugs found in the attached code snippet",
    )


class CrossAgentEmailDataPayload(Action):
    agent: Literal["cross_agent"] = "cross_agent"
    task_id: Literal["cross_agent_email_data"] = "cross_agent_email_data"
    email_priority: str = Field(
        ...,
        description="Priority of the email: 'critical', 'high', 'medium', 'low'",
    )
    data_issues: Dict[str, str] = Field(
        ...,
        description="Data quality issues found in the attachment",
    )
    cleaned_data: List[Dict[str, Any]] = Field(
        ...,
        description="Cleaned version of the attachment data",
    )


class CrossAgentCodeEmailPayload(Action):
    agent: Literal["cross_agent"] = "cross_agent"
    task_id: Literal["cross_agent_code_email"] = "cross_agent_code_email"
    vulnerability_type: str = Field(
        ...,
        description="Type of the primary security vulnerability found",
    )
    vulnerability_location: str = Field(
        ...,
        description="Function name where the vulnerability exists",
    )
    disclosure_email: str = Field(
        ...,
        description="Professional security disclosure email to the development team",
        min_length=80,
    )


class CrossAgentModEscalationPayload(Action):
    agent: Literal["cross_agent"] = "cross_agent"
    task_id: Literal["cross_agent_mod_escalation"] = "cross_agent_mod_escalation"
    content_label: str = Field(
        ...,
        description="'safe' or 'harmful'",
    )
    escalate: bool = Field(
        ...,
        description="Whether to escalate to human review",
    )
    moderation_notice: str = Field(
        ...,
        description="User-facing moderation notice (if harmful), or empty string if safe",
    )


class TicketTriageEasyPayload(Action):
    agent: Literal["ticket_triage"] = "ticket_triage"
    task_id: Literal["ticket_triage_easy"] = "ticket_triage_easy"
    priority: str = Field(
        ...,
        description="One of: 'critical', 'high', 'medium', 'low'",
    )
    category: str = Field(
        ...,
        description="One of: 'bug', 'feature_request', 'question', 'billing'",
    )


class TicketTriageMediumPayload(Action):
    agent: Literal["ticket_triage"] = "ticket_triage"
    task_id: Literal["ticket_triage_medium"] = "ticket_triage_medium"
    order: List[str] = Field(
        ...,
        description="All 8 ticket IDs ordered by priority (highest first)",
    )
    assignments: Dict[str, str] = Field(
        ...,
        description="ticket_id → team assignment: 'backend', 'frontend', 'devops', 'billing'",
    )


class TicketTriageHardPayload(Action):
    agent: Literal["ticket_triage"] = "ticket_triage"
    task_id: Literal["ticket_triage_hard"] = "ticket_triage_hard"
    root_cause: str = Field(
        ...,
        description="Root cause analysis of the linked incident tickets",
    )
    resolution_steps: List[str] = Field(
        ...,
        description="Ordered list of steps to resolve the incident",
    )
    affected_services: List[str] = Field(
        ...,
        description="List of services impacted by the incident",
    )
    severity: str = Field(
        ...,
        description="Incident severity: 'P1', 'P2', 'P3', 'P4'",
    )


# ── Unified MetaAction — wraps everything in the JSON-message format ──────────
# We keep backward compat with the OpenEnv spec (message: str) but now
# also expose typed endpoints per task via /step/{task_id}

class MetaAction(Action):
    """
    Universal action for all Meta agents.
    Pack your typed action as a JSON string in the `message` field.

    Format:
        {
          "agent": "email_triage",
          "task_id": "email_triage_easy",
          "payload": { "classification": "spam" }
        }

    Agents: email_triage | code_review | data_cleaning |
            content_moderation | cross_agent | ticket_triage
    """
    message: str = Field(
        ...,
        description=(
            'JSON: {"agent": "<agent>", "task_id": "<task_id>", "payload": {...}}. '
            "See GET /tasks for all task IDs and payload schemas."
        ),
        min_length=2,
    )


# ── Observation ───────────────────────────────────────────────────────────────

class MetaObservation(Observation):
    """
    Observation returned after each step.
    Contains task context, grader feedback, and score (0.0–1.0).
    """
    agent: str = Field(default="", description="Agent that produced this observation")
    task_id: str = Field(default="", description="Current task identifier")
    difficulty: str = Field(default="", description="easy | medium | hard")
    context: Dict[str, Any] = Field(
        default_factory=dict,
        description="Task data presented to the agent",
    )
    instructions: str = Field(
        default="",
        description="What the agent must do and the exact payload format required",
    )
    feedback: str = Field(
        default="",
        description="Grader feedback explaining the score and what was missed",
    )
    score: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Grader score: 0.0 = complete failure, 1.0 = perfect",
    )
    partial_credits: Dict[str, Any] = Field(
        default_factory=dict,
        description="Per-criterion boolean breakdown of what was and wasn't correct",
    )