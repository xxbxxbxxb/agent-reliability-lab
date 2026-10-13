from uuid import uuid4

from agent_reliability.domain.models import (
    Failure,
    FailureKind,
    StepKind,
)
from agent_reliability.fault.models import (
    FaultDecision,
    FaultType,
)


class ReliabilityExecutionError(Exception):
    pass


class OperationTimeoutError(ReliabilityExecutionError):
    pass


class InjectedFaultError(ReliabilityExecutionError):
    def __init__(self, decision: FaultDecision) -> None:
        self.decision = decision
        super().__init__(decision.fault_type.value)


def classify_exception(
    exc: BaseException,
    run_id: str,
    step_id: str,
    step_kind: StepKind,
) -> Failure:

    kind = (
        FailureKind.PROVIDER
        if step_kind is StepKind.LLM_CALL
        else FailureKind.TOOL
    )

    retry_after_s = None
    injected = False

    if isinstance(exc, OperationTimeoutError):
        kind = FailureKind.TIMEOUT

    elif isinstance(exc, InjectedFaultError):
        injected = True
        retry_after_s = exc.decision.retry_after_s

        kind = {
            FaultType.TIMEOUT: FailureKind.TIMEOUT,
            FaultType.RATE_LIMIT: FailureKind.RATE_LIMIT,
            FaultType.UNAVAILABLE: FailureKind.PROVIDER,
            FaultType.MALFORMED_OUTPUT: FailureKind.PROTOCOL,
            FaultType.EMPTY_RESPONSE: FailureKind.PROTOCOL,
            FaultType.TOOL_CRASH: FailureKind.TOOL,
            FaultType.RESPONSE_LOST_AFTER_SUCCESS: FailureKind.SIDE_EFFECT,
        }[exc.decision.fault_type]

    return Failure(
        failure_id=str(uuid4()),
        run_id=run_id,
        step_id=step_id,
        kind=kind,
        message=str(exc),
        retry_after_s=retry_after_s,
        injected=injected,
    )