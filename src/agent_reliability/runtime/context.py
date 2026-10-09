from __future__ import annotations

from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import AsyncIterator
from uuid import uuid4

from agent_reliability.domain.models import (
    Run,
    Step,
    StepKind,
    TraceEvent,
    utc_now,
)
from agent_reliability.runtime.ports import TraceSink


@dataclass
class ExecutionContext:
    run: Run
    trace_sink: TraceSink

    @asynccontextmanager
    async def step(
        self,
        kind: StepKind,
        name: str,
    ) -> AsyncIterator[Step]:

        step = Step(
            step_id=str(uuid4()),
            run_id=self.run.run_id,
            kind=kind,
            name=name,
            started_at=utc_now(),
        )

        await self.trace_sink.emit(
            TraceEvent(
                event_id=str(uuid4()),
                run_id=self.run.run_id,
                step_id=step.step_id,
                event_type="step.started",
                attributes={
                    "kind": kind.value,
                    "name": name,
                },
            )
        )

        try:
            yield step

        except BaseException as exc:
            step.ended_at = utc_now()

            await self.trace_sink.emit(
                TraceEvent(
                    event_id=str(uuid4()),
                    run_id=self.run.run_id,
                    step_id=step.step_id,
                    event_type="step.failed",
                    attributes={
                        "error_type": type(exc).__name__,
                        "message": str(exc),
                    },
                )
            )

            raise

        else:
            step.ended_at = utc_now()

            await self.trace_sink.emit(
                TraceEvent(
                    event_id=str(uuid4()),
                    run_id=self.run.run_id,
                    step_id=step.step_id,
                    event_type="step.finished",
                )
            )