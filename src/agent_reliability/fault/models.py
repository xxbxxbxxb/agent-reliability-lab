from enum import StrEnum

from pydantic import BaseModel, Field

from agent_reliability.domain.models import StepKind


class FaultType(StrEnum):
    TIMEOUT = "timeout"
    RATE_LIMIT = "rate_limit"
    UNAVAILABLE = "unavailable"
    MALFORMED_OUTPUT = "malformed_output"
    EMPTY_RESPONSE = "empty_response"
    TOOL_CRASH = "tool_crash"
    RESPONSE_LOST_AFTER_SUCCESS = "response_lost_after_success"


class FaultPhase(StrEnum):
    BEFORE_CALL = "before_call"
    AFTER_SUCCESS = "after_success"


class FaultPolicy(BaseModel):
    policy_id: str
    target_kind: StepKind
    target_name: str | None = None
    fault_type: FaultType
    phase: FaultPhase = FaultPhase.BEFORE_CALL
    probability: float = Field(ge=0.0, le=1.0)
    max_injections: int = Field(ge=1)
    seed: int
    retry_after_s: float | None = Field(default=None, ge=0.0)


class FaultTarget(BaseModel):
    kind: StepKind
    name: str


class FaultDecision(BaseModel):
    policy_id: str
    fault_type: FaultType
    phase: FaultPhase
    retry_after_s: float | None = None