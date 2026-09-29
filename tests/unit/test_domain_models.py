from agent_reliability.domain.models import(
    Failure,
    FailureKind,
    Run,
    RunStatus,
    Step,
    StepKind,
    TraceEvent,
)
from agent_reliability.tracing.memory import InMemoryTraceSink

def test_run_starts_pending() ->None:
    run = Run(
        run_id = "run-1",
        agent_id = "react",
        task_id = "task-1"
    )
    assert run.status is RunStatus.PENDING
    
def test_failure_is_attached_to_step() ->None:
    step = Step(
        step_id = "step-1",
        run_id = "run-1",
        kind = StepKind.TOOL_CALL,
        name ="create_order",
    )
    
    failure = Failure(
        failure_id = "failure-1",
        run_id = "run-1",
        step_id = step.step_id,
        kind = FailureKind.TIMEOUT,
        message = "tool timed out",
        
    )
    assert failure.step_id == "step-1"

async def test_in_memory_trace_sink_preserves_event_order() ->None:
    sink = InMemoryTraceSink()
    first = TraceEvent(
        event_id = "e1",
        run_id = "r1",
        event_type = "run.started",
    )
    second = TraceEvent(
        event_id ="e2",
        run_id = "r1",
        event_type = "run.succeeded",
    )
    await sink.emit(first)
    await sink.emit(second)
    
    assert [event.event_type for event in sink.events] == [
        "run.started",
        "run.succeeded",
    ]
    