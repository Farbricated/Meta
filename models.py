from pydantic import BaseModel, Field
from typing import Any, Dict, List, Optional


class Observation(BaseModel):
    agent: str
    task_id: str
    difficulty: str
    context: Dict[str, Any]
    instructions: str
    step_count: int = 0


class Action(BaseModel):
    agent: str
    task_id: str
    payload: Dict[str, Any] = Field(
        description="Action payload — content depends on agent and task"
    )


class Reward(BaseModel):
    score: float = Field(ge=0.0, le=1.0)
    partial_credits: Dict[str, float] = {}
    feedback: str = ""
    done: bool = False


class StepResult(BaseModel):
    observation: Observation
    reward: Reward
    done: bool
    info: Dict[str, Any] = {}


class TaskInfo(BaseModel):
    id: str
    name: str
    difficulty: str
    description: str
    agent: str
    action_schema: Dict[str, Any]


class BaselineScore(BaseModel):
    task_id: str
    score: float
    feedback: str
