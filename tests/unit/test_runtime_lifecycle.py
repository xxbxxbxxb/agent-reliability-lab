import asyncio

import pytest

from agent_reliability.domain.models import RunStatus, StepKind
from agent_reliability.runtime.runtime import ReliabilityRuntime
from agent_reliability.tracing.memory import InMemoryTraceSink


# 测试 1：Run 和 Step 正常执行
async def test_successful_run_emits_ordered_lifecycle_events() -> None:
    sink = InMemoryTraceSink()
    runtime = ReliabilityRuntime(trace_sink=sink)

    async with runtime.run(agent_id="react", task_id="t1") as ctx:
        assert ctx.run.status is RunStatus.RUNNING

        async with ctx.step(StepKind.TOOL_CALL, "search") as step:
            assert step.started_at is not None
            assert step.ended_at is None

    assert ctx.run.status is RunStatus.SUCCEEDED
    assert ctx.run.ended_at is not None
    assert step.ended_at is not None

    assert [event.event_type for event in sink.events] == [
        "run.started",
        "step.started",
        "step.finished",
        "run.succeeded",
    ]


# 测试 2：Run 执行失败
async def test_failed_run_never_emits_run_succeeded() -> None:
    sink = InMemoryTraceSink()
    runtime = ReliabilityRuntime(trace_sink=sink)

    with pytest.raises(RuntimeError, match="boom"):
        async with runtime.run(agent_id="react", task_id="t2") as ctx:
            raise RuntimeError("boom")

    assert ctx.run.status is RunStatus.FAILED
    assert ctx.run.started_at is not None
    assert ctx.run.ended_at is not None

    event_types = [event.event_type for event in sink.events]

    assert event_types == [
        "run.started",
        "run.failed",
    ]

    assert "run.succeeded" not in event_types


# 测试 3：Run 被取消
async def test_cancelled_run_uses_cancelled_terminal_state() -> None:
    sink = InMemoryTraceSink()
    runtime = ReliabilityRuntime(trace_sink=sink)

    with pytest.raises(asyncio.CancelledError):
        async with runtime.run(agent_id="react", task_id="t3") as ctx:
            raise asyncio.CancelledError()

    assert ctx.run.status is RunStatus.CANCELLED
    assert ctx.run.ended_at is not None

    assert [event.event_type for event in sink.events] == [
        "run.started",
        "run.cancelled",
    ]


# 测试 4：Step 失败时，生命周期和 Trace 必须一致
async def test_failed_step_has_consistent_lifecycle() -> None:
    sink = InMemoryTraceSink()
    runtime = ReliabilityRuntime(trace_sink=sink)

    with pytest.raises(RuntimeError, match="tool failed"):
        async with runtime.run(
            agent_id="react",
            task_id="t4",
        ) as ctx:

            async with ctx.step(
                StepKind.TOOL_CALL,
                "search",
            ) as step:
                raise RuntimeError("tool failed")

    # Step 必须属于当前 Run
    assert step.run_id == ctx.run.run_id

    # Step 失败也必须记录完整的生命周期时间
    assert step.started_at is not None
    assert step.ended_at is not None
    assert step.ended_at >= step.started_at

    # 异常传播至 Run，整个 Run 最终也应失败
    assert ctx.run.status is RunStatus.FAILED

    # 验证严格的事件顺序
    event_types = [event.event_type for event in sink.events]

    assert event_types == [
        "run.started",
        "step.started",
        "step.failed",
        "run.failed",
    ]

    # Step 事件必须指向正确的 Step
    step_failed_event = sink.events[2]

    assert step_failed_event.run_id == ctx.run.run_id
    assert step_failed_event.step_id == step.step_id
    assert step_failed_event.attributes["error_type"] == "RuntimeError"

    # 失败的执行不能被记录为成功
    assert "step.finished" not in event_types
    assert "run.succeeded" not in event_types