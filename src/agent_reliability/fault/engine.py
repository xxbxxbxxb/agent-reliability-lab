from dataclasses import dataclass
from random import Random

from agent_reliability.fault.models import (
    FaultDecision,
    FaultPhase,
    FaultPolicy,
    FaultTarget,
)


@dataclass
class _PolicyState:
    policy: FaultPolicy
    rng: Random
    injections: int = 0


class FaultEngine:
    def __init__(self, policies: list[FaultPolicy]) -> None:
        self._states = [
            _PolicyState(
                policy=p,
                rng=Random(p.seed),
            )
            for p in policies
        ]

    def decide(
        self,
        target: FaultTarget,
        phase: FaultPhase,
    ) -> FaultDecision | None:

        for state in self._states:
            policy = state.policy

            if policy.phase != phase:
                continue

            if policy.target_kind != target.kind:
                continue

            if (
                policy.target_name is not None
                and policy.target_name != target.name
            ):
                continue

            if state.injections >= policy.max_injections:
                continue

            if state.rng.random() >= policy.probability:
                continue

            state.injections += 1

            return FaultDecision(
                policy_id=policy.policy_id,
                fault_type=policy.fault_type,
                phase=policy.phase,
                retry_after_s=policy.retry_after_s,
            )

        return None