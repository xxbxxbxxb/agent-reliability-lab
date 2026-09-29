from typing import Protocol

from agent_reliability.domain.models import TraceEvent


class TraceSink(Protocol):
    async def emit(self, event: TraceEvent) -> None: ...