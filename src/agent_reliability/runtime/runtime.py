from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from typing import AsyncIterator
from uuid import uuid4

from agent_reliability.domain.models import (
    Run,
    RunStatus,
    TraceEvent,
    utc_now,
)
from agent_reliability.runtime.context import ExecutionContext
from agent_reliability.runtime.ports import TraceSink


class ReliabilityRuntime:

    def __init__(self, trace_sink: TraceSink) -> None:
        self._trace_sink = trace_sink

    @asynccontextmanager
    async def run(
        self,
        agent_id: str,
        task_id: str,
        metadata: dict | None = None,
    ) -> AsyncIterator[ExecutionContext]:

        run = Run(
            run_id=str(uuid4()),
            agent_id=agent_id,
            task_id=task_id,
            metadata=metadata or {},
        )

        run.status = RunStatus.RUNNING
        run.started_at = utc_now()

        await self._trace_sink.emit(
            TraceEvent(
                event_id=str(uuid4()),
                run_id=run.run_id,
                event_type="run.started",
            )
        )

        ctx = ExecutionContext(
            run=run,
            trace_sink=self._trace_sink,
        )

        try:
            yield ctx

        except asyncio.CancelledError:
            run.status = RunStatus.CANCELLED
            run.ended_at = utc_now()

            await self._trace_sink.emit(
                TraceEvent(
                    event_id=str(uuid4()),
                    run_id=run.run_id,
                    event_type="run.cancelled",
                )
            )

            raise

        except BaseException as exc:
            run.status = RunStatus.FAILED
            run.ended_at = utc_now()

            await self._trace_sink.emit(
                TraceEvent(
                    event_id=str(uuid4()),
                    run_id=run.run_id,
                    event_type="run.failed",
                    attributes={
                        "error_type": type(exc).__name__,
                        "message": str(exc),
                    },
                )
            )

            raise

        else:
            run.status = RunStatus.SUCCEEDED
            run.ended_at = utc_now()

            await self._trace_sink.emit(
                TraceEvent(
                    event_id=str(uuid4()),
                    run_id=run.run_id,
                    event_type="run.succeeded",
                )
            )