# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.

"""
Data models for the Meta Multi-Agent Environment.

Covers 4 real-world agents:
  1. Email Triage
  2. Code Review
  3. Data Cleaning
  4. Content Moderation
"""

from typing import Any, Dict, List, Optional
from openenv.core.env_server.types import Action, Observation
from pydantic import Field


# ─── SHARED ───────────────────────────────────────────────────────────────────

class MetaAction(Action):
    """Universal action for the Meta multi-agent environment."""

    agent: str = Field(..., description="Agent name: email_triage | code_review | data_cleaning | content_moderation")
    task_id: str = Field(..., description="Task ID e.g. email_triage_easy")
    payload: Dict[str, Any] = Field(default_factory=dict, description="Task-specific action payload")


class MetaObservation(Observation):
    """Universal observation from the Meta multi-agent environment."""

    agent: str = Field(default="", description="Agent that produced this observation")
    task_id: str = Field(default="", description="Current task ID")
    difficulty: str = Field(default="", description="Task difficulty: easy | medium | hard")
    context: Dict[str, Any] = Field(default_factory=dict, description="Task context data shown to agent")
    instructions: str = Field(default="", description="What the agent needs to do")
    feedback: str = Field(default="", description="Feedback from last action")
    score: float = Field(default=0.0, description="Score from last action (0.0 to 1.0)")
