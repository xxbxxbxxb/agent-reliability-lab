from enum import StrEnum

from pydantic import BaseModel, Field

from agent_reliability.domain.models import FailureKind


class RecoveryAction(StrEnum):
    RETRY = "retry"
    ABORT = "abort"
    FALLBACK = "fallback"


class RetryPolicy(BaseModel):
    max_attempts: int = Field(default=3, ge=1)

    base_delay_s: float = Field(default=0.1, ge=0.0)

    max_delay_s: float = Field(default=2.0, ge=0.0)

    retryable_failure_kinds: frozenset[FailureKind] = frozenset({
        FailureKind.TIMEOUT,
        FailureKind.RATE_LIMIT,
        FailureKind.PROVIDER,
        FailureKind.TOOL,
        FailureKind.SIDE_EFFECT,
    })

    fallback_failure_kinds: frozenset[FailureKind] = frozenset()

    respect_retry_after: bool = True


class RecoveryDecision(BaseModel):
    action: RecoveryAction
    delay_s: float = 0.0