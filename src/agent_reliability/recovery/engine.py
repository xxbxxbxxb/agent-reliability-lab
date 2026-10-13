from agent_reliability.domain.models import Failure

from agent_reliability.recovery.models import (
    RecoveryAction,
    RecoveryDecision,
    RetryPolicy,
)


class RecoveryEngine:
    def __init__(self, policy: RetryPolicy) -> None:
        self._policy = policy

    def decide(
        self,
        failure: Failure,
        attempt_number: int,
    ) -> RecoveryDecision:

        if failure.kind not in self._policy.retryable_failure_kinds:
            if failure.kind in self._policy.fallback_failure_kinds:
                return RecoveryDecision(
                    action=RecoveryAction.FALLBACK
                )

            return RecoveryDecision(
                action=RecoveryAction.ABORT
            )

        if attempt_number >= self._policy.max_attempts:
            if failure.kind in self._policy.fallback_failure_kinds:
                return RecoveryDecision(
                    action=RecoveryAction.FALLBACK
                )

            return RecoveryDecision(
                action=RecoveryAction.ABORT
            )

        backoff = min(
            self._policy.base_delay_s * (2 ** (attempt_number - 1)),
            self._policy.max_delay_s,
        )

        if (
            self._policy.respect_retry_after
            and failure.retry_after_s is not None
        ):
            backoff = max(backoff, failure.retry_after_s)

        return RecoveryDecision(
            action=RecoveryAction.RETRY,
            delay_s=backoff,
        )