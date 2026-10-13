from agent_reliability.domain.models import (
    Failure,
    FailureKind,
)

from agent_reliability.recovery.engine import RecoveryEngine

from agent_reliability.recovery.models import (
    RecoveryAction,
    RetryPolicy,
)


def _failure(
    kind: FailureKind,
    retry_after_s: float | None = None,
) -> Failure:
    return Failure(
        failure_id="f1",
        run_id="r1",
        step_id="s1",
        kind=kind,
        message="x",
        retry_after_s=retry_after_s,
    )


def test_retryable_timeout_uses_exponential_backoff() -> None:
    engine = RecoveryEngine(
        RetryPolicy(
            max_attempts=3,
            base_delay_s=0.5,
            max_delay_s=10.0,
        )
    )

    decision = engine.decide(
        _failure(FailureKind.TIMEOUT),
        attempt_number=2,
    )

    assert decision.action is RecoveryAction.RETRY
    assert decision.delay_s == 1.0


def test_retry_after_is_respected_when_larger_than_backoff() -> None:
    engine = RecoveryEngine(
        RetryPolicy(
            max_attempts=3,
            base_delay_s=0.5,
            max_delay_s=10.0,
        )
    )

    decision = engine.decide(
        _failure(
            FailureKind.RATE_LIMIT,
            retry_after_s=3.0,
        ),
        attempt_number=1,
    )

    assert decision.action is RecoveryAction.RETRY
    assert decision.delay_s == 3.0


def test_non_retryable_protocol_failure_aborts_immediately() -> None:
    engine = RecoveryEngine(
        RetryPolicy(max_attempts=5)
    )

    decision = engine.decide(
        _failure(FailureKind.PROTOCOL),
        attempt_number=1,
    )

    assert decision.action is RecoveryAction.ABORT
    assert decision.delay_s == 0.0


def test_configured_protocol_failure_selects_fallback() -> None:
    engine = RecoveryEngine(
        RetryPolicy(
            max_attempts=5,
            fallback_failure_kinds=frozenset({
                FailureKind.PROTOCOL
            }),
        )
    )

    decision = engine.decide(
        _failure(FailureKind.PROTOCOL),
        attempt_number=1,
    )

    assert decision.action is RecoveryAction.FALLBACK
    assert decision.delay_s == 0.0


def test_attempt_at_max_attempts_aborts() -> None:
    engine = RecoveryEngine(
        RetryPolicy(max_attempts=2)
    )

    decision = engine.decide(
        _failure(FailureKind.TIMEOUT),
        attempt_number=2,
    )

    assert decision.action is RecoveryAction.ABORT