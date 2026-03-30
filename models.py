# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.

"""
Data models for the Meta Multi-Agent Environment v2.

The real OpenEnv create_app() validates actions against the Action base class
which requires a `message` field. We use that field to carry a JSON-encoded
payload so all 4 agents share one unified action schema.

Action format (send as JSON string in `message`):
{
  "agent": "email_triage",
  "task_id": "email_triage_easy",
  "payload": { ... task-specific fields ... }
}
"""

from typing import Any, Dict
from openenv.core.env_server.types import Action, Observation
from pydantic import Field


class MetaAction(Action):
    """
    Universal action for all 4 Meta agents.

    Pack your full action as a JSON string in the `message` field.

    Example:
        message = '{"agent": "email_triage", "task_id": "email_triage_easy", "payload": {"classification": "spam"}}'
    """
    message: str = Field(
        ...,
        description=(
            'JSON string: {"agent": "<agent>", "task_id": "<task_id>", "payload": {...}}. '
            "Agents: email_triage | code_review | data_cleaning | content_moderation. "
            "Tasks: <agent>_easy | <agent>_medium | <agent>_hard."
        ),
        min_length=2,
    )


class MetaObservation(Observation):
    """
    Observation returned after each step in the Meta environment.
    Contains task context, grader feedback, and score (0.0 to 1.0).
    """
    agent: str = Field(default="", description="Which agent produced this observation")
    task_id: str = Field(default="", description="Current task identifier")
    difficulty: str = Field(default="", description="Task difficulty: easy | medium | hard")
    context: Dict[str, Any] = Field(default_factory=dict, description="Task data shown to the agent")
    instructions: str = Field(default="", description="What the agent must do and what payload format to use")
    feedback: str = Field(default="", description="Grader feedback explaining the score")
    score: float = Field(default=0.0, ge=0.0, le=1.0, description="Grader score 0.0=fail 1.0=perfect")
    partial_credits: Dict[str, Any] = Field(default_factory=dict, description="Per-criterion score breakdown")
