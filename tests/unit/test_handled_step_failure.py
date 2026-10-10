
from agent_reliability.domain.models import (
    RunStatus,
    StepKind,
)
from agent_reliability.runtime.runtime import ReliabilityRuntime
from agent_reliability.tracing.memory import InMemoryTraceSink


async def test_handled_step_failure_allows_run_success() -> None:
    sink = InMemoryTraceSink()

    runtime = ReliabilityRuntime(
        trace_sink=sink,
    )

    async with runtime.run(
        agent_id="react",
        task_id="handled-failure",
    ) as ctx:

        try:
            async with ctx.step(
                StepKind.TOOL_CALL,
                "search",
            ) as step:

                raise RuntimeError("search failed")

        except RuntimeError:
            pass

    assert ctx.run.status is RunStatus.SUCCEEDED

    assert step.started_at is not None
    assert step.ended_at is not None

    event_types = [
        event.event_type
        for event in sink.events
    ]

    assert event_types == [
        "run.started",
        "step.started",
        "step.failed",
        "run.succeeded",
    ]
    step_failed_event = next(
        event
        for event in sink.events
        if event.event_type =="step.failed"
    )
    assert step_failed_event.step_id == step.step_id
    
    assert step_failed_event.run_id == ctx.run.run_id
