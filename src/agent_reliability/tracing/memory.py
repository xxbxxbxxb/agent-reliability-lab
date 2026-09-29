from dataclasses import dataclass, field

from agent_reliability.domain.models import TraceEvent


@dataclass
class InMemoryTraceSink:
    events: list[TraceEvent] = field(default_factory=list)

    async def emit(self, event: TraceEvent) -> None:
        self.events.append(event)