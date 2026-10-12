from agent_reliability.domain.models import StepKind

from agent_reliability.fault.engine import FaultEngine

from agent_reliability.fault.models import (
    FaultPhase,
    FaultPolicy,
    FaultTarget,
    FaultType,
)


def test_probability_one_injects_until_max_injections() -> None:
    policy = FaultPolicy(
        policy_id="p1",
        target_kind=StepKind.TOOL_CALL,
        target_name="search",
        fault_type=FaultType.TIMEOUT,
        phase=FaultPhase.BEFORE_CALL,
        probability=1.0,
        max_injections=2,
        seed=7,
    )

    engine = FaultEngine([policy])

    target = FaultTarget(
        kind=StepKind.TOOL_CALL,
        name="search",
    )

    assert engine.decide(
        target,
        FaultPhase.BEFORE_CALL,
    ) is not None

    assert engine.decide(
        target,
        FaultPhase.BEFORE_CALL,
    ) is not None

    assert engine.decide(
        target,
        FaultPhase.BEFORE_CALL,
    ) is None


def test_same_seed_produces_same_sequence() -> None:
    policy_a = FaultPolicy(
        policy_id="a",
        target_kind=StepKind.LLM_CALL,
        fault_type=FaultType.RATE_LIMIT,
        probability=0.5,
        max_injections=100,
        seed=123,
    )

    policy_b = policy_a.model_copy(
        update={"policy_id": "b"}
    )

    target = FaultTarget(
        kind=StepKind.LLM_CALL,
        name="provider",
    )

    engine_a = FaultEngine([policy_a])
    engine_b = FaultEngine([policy_b])

    seq_a = [
        engine_a.decide(
            target,
            FaultPhase.BEFORE_CALL,
        ) is not None
        for _ in range(20)
    ]

    seq_b = [
        engine_b.decide(
            target,
            FaultPhase.BEFORE_CALL,
        ) is not None
        for _ in range(20)
    ]

    assert seq_a == seq_b


def test_target_name_must_match_when_policy_specifies_one() -> None:
    policy = FaultPolicy(
        policy_id="p",
        target_kind=StepKind.TOOL_CALL,
        target_name="search",
        fault_type=FaultType.TIMEOUT,
        probability=1.0,
        max_injections=1,
        seed=1,
    )

    engine = FaultEngine([policy])

    target = FaultTarget(
        kind=StepKind.TOOL_CALL,
        name="create_order",
    )

    assert engine.decide(
        target,
        FaultPhase.BEFORE_CALL,
    ) is None
def test_phase_mismatch_does_not_consume_injection_quota() -> None:
    policy = FaultPolicy(
        policy_id="phase-test",
        target_kind=StepKind.TOOL_CALL,
        target_name="search",
        fault_type=FaultType.TIMEOUT,
        phase=FaultPhase.BEFORE_CALL,
        probability=1.0,
        max_injections=1,
        seed=42,
    )

    engine = FaultEngine([policy])

    target = FaultTarget(
        kind=StepKind.TOOL_CALL,
        name="search",
    )

    # 第一次：阶段不匹配，不应该注入
    first = engine.decide(
        target,
        FaultPhase.AFTER_SUCCESS,
    )

    assert first is None

    # 第二次：阶段匹配，应该仍有一次注入机会
    second = engine.decide(
        target,
        FaultPhase.BEFORE_CALL,
    )

    assert second is not None
    assert second.fault_type is FaultType.TIMEOUT
    assert second.policy_id == "phase-test"

    # 第三次：唯一一次注入机会已经消耗
    third = engine.decide(
        target,
        FaultPhase.BEFORE_CALL,
    )

    assert third is None