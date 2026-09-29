from __future__ import annotations
from datetime import datetime,timezone
from enum import StrEnum
from typing import Any
from pydantic import BaseModel,Field

def utc_now() ->datetime:
    return datetime.now(timezone.utc)

class RunStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"
    
class StepKind(StrEnum):
    LLM_CALL = "llm_call"
    TOOL_CALL = "tool_call"
    MEMORY_READ ="memory_read"
    CHECKPOINT = "checkpoint"
    RECOVERY = "recovery"

class FailureKind(StrEnum):
    PROVIDER = "provider"
    TOOL = "tool"
    PROTOCOL  = "protocol"
    TIMEOUT = "timeout"
    RATE_LIMIT = "rate_limit"
    SIDE_EFFECT = "side_effect"
    STATE = "state"

class Run(BaseModel):
    run_id: str
    agent_id: str
    task_id: str
    status:RunStatus = RunStatus.PENDING
    stared_at: datetime | None=None
    
class Step(BaseModel):
    step_id: str
    run_id: str
    kind: StepKind
    name: str
    started_at: datetime | None = None
    ended_at: datetime | None = None
    
class TraceEvent(BaseModel):
    event_id:str
    run_id: str
    step_id: str |None = None
    event_type: str
    occured_at: datetime = Field(default_factory=utc_now)
    attributes: dict[str,Any] = Field(default_factory=dict)

class Failure(BaseModel):
    failure_id: str
    run_id: str
    step_id: str
    kind: FailureKind
    message: str
    retry_after_s: float | None = None
    injected: bool = False
    attributes: dict[str, Any] = Field(default_factory=dict)


class RecoveryAttempt(BaseModel):
    recovery_id: str
    run_id: str
    step_id: str
    failure_id: str
    action: str
    attempt_number: int
    succeeded: bool | None = None
    delay_s: float = 0.0
    attributes: dict[str, Any] = Field(default_factory=dict)