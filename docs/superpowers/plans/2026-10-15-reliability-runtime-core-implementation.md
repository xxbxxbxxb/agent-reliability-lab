# Reliability Runtime Core (M1) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 打通 Native Agent 的真实可靠执行闭环，使用实际业务状态证明“提交成功但响应丢失”可以安全恢复，并提供四组对照 CLI 和可复核 JSON 报告。

**Architecture:** 在现有 src/agent_reliability 中演进，不更换包名或重建仓库。Runtime 管生命周期，Executor 组合 Policy、FaultSource、AttemptRunner 与 IdempotencyStore，业务 SUT 和评测器负责实际效果判分。策略决策、单次执行边界、业务结果和观测输出分别维护。

**Tech Stack:** Python >=3.11、asyncio、Pydantic >=2.8,<3；沿用现有 pytest >=8.3,<9、pytest-asyncio >=0.24,<1、pytest-cov >=5,<7、Ruff >=0.6,<1、mypy >=1.11,<2；M1 不新增运行时依赖。

**Spec:** `docs/superpowers/specs/2026-10-15-reliability-runtime-core-design.md`；总体边界见同目录 `2026-10-15-agent-reliability-lab-mature-v1-design.md`。

状态：PLAN_READY_FOR_USER_REVIEW；本文件的命令和测试是待执行步骤，不是通过记录。设计已批准，计划执行方式尚待用户选择。

## Global Constraints

- 独立 agent-reliability-lab；ResearchFlow 独立并作为首个外部 SUT；先 Native，再 LangGraph。
- 保留 Python 3.11/3.12 及 Windows 开发路径；不使用 Python 3.12 才支持的 type 语法。
- 本阶段仅保证同进程的内存去重和受控异步调用语义。跨进程幂等与恢复在 M2 完成。
- 保留 ReliabilityRuntime.run、ExecutionContext.step、现有公共模型和已验收行为。
- excution/errors.py 提供兼容转发；正式实现位于 execution/。
- Operation 输入和可录制输出限定为 JSON 可序列化值；digest 使用 canonical JSON 与 SHA-256。
- max_attempts 是总尝试上限，包含主调用、重试和 fallback；cache hit 不算上游调用。
- 调用前注入失败也消耗一次尝试机会，避免故障导致无限循环；upstream_calls 单独统计实际 dispatch。
- Retry-After 取 max(backoff, server delay)，预算不足直接终止，不能截短服务端要求后提前调用。
- 调用后非幂等副作用结果未知，拒绝自动重发；已完成结果不得因交付或观测失败而删除。
- 取消不重试；不保证通过取消本机 Task 撤销远程副作用；已关闭 Attempt 的晚到结果不得提交。
- 并发同 key 至少 20 个请求验证唯一 owner；测试用 Event/Barrier 协调，不用任意 sleep 猜顺序。
- 模拟 Provider/业务状态明确标 simulated；未知成本 null；报告数字来自实际执行。
- 产品实现台账与用户学习进度分开；不自动升级 docs/learning-progress.md。
- 本阶段不引入 PostgreSQL、Redis、HTTP/SSE 服务、Dashboard、Checkpoint、Replay、OTel Backend 或 Kubernetes。
- 新增关键代码注释使用中英双语；不为了每一行都加注释而淹没控制流程。

## Review Focus

1. 并发等待者取消不能取消 owner，也不能删除其他 owner 的 reservation；Task 3、6 验证。
2. 工具已返回但结果存储失败不能再次执行业务；Task 5 验证 unknown/commit-failed 且调用次数为 1。
3. Retry-After 大于 max_delay_s、无效 HTTP-date、极大 attempt_number 不得提前重试或指数溢出；Task 2 验证。
4. 用户异常携带敏感字符串、观测 Sink 故障不能污染业务结果或报告；Task 1、5 验证。
5. 并发调度变化、参数摘要变化、输入 NaN/Infinity 不能静默改变故障计划或命中错误缓存；Task 1、3、4 验证。

## 文件职责及公共契约

| 文件 | 创建/修改及职责 |
| --- | --- |
| domain/models.py | 修改：兼容字段、Attempt/AttemptStatus，Failure/Recovery 关联 |
| execution/models.py、ports.py、validation.py | 创建：操作模型、Callable/Validator 契约、canonical digest/校验 |
| execution/errors.py；excution/errors.py | 正式 typed errors/分类；旧路径兼容转发 |
| runtime/clock.py、events.py | 创建：Clock/Deadline、运行事实缓冲及 best-effort export |
| runtime/context.py、runtime.py；tracing/memory.py | 修改：注入依赖、稳定身份、状态快照及取消 |
| recovery/models.py、engine.py、retry_after.py | 修改/创建：总预算策略、退避、Retry-After 解析 |
| idempotency/models.py、store.py | 创建：reservation 状态、owner token、并发结果等待 |
| fault/models.py、engine.py、schedule.py、injector.py | 修改/创建：策略快照、冻结实验调度、实际扰动执行 |
| execution/attempt.py、executor.py | 创建：单次时间边界与执行编排；避免一个文件承担全部职责 |
| examples/tools.py、minimal_react.py | 创建：实际写入的模拟业务工具和 Native action/observation SUT |
| evaluation/models.py、scenarios.py、benchmark.py | 创建：结果/manifest、固定场景、四组实验和状态判分 |
| cli.py、__main__.py | 创建：标准库 argparse 入口和人类可读/JSON 输出 |
| tests/unit、tests/integration、tests/support.py | 下列 Task 的行为验证；support 只放可控时钟/操作测试替身 |
| README.md、docs/architecture.md、docs/status/product-progress.md、.github/workflows/ci.yml | 更新运行方式、边界、真实验收证据和回归命令 |

每个新增包补 __init__.py。以下签名中的 JsonValue 使用 pydantic.JsonValue；Operation、ResultValidator、FaultSource、IdempotencyStore、Clock、Sleeper 是 Protocol/类型别名。未列出的私有辅助函数由实现者按清晰度选择，不增加通用框架抽象。

## Task 1：建立基线、兼容契约与可信运行事实

**Files:** 修改 domain/models.py、runtime/context.py、runtime/runtime.py、runtime/ports.py、tracing/memory.py、excution/errors.py；创建 execution/{__init__,models,ports,validation,errors}.py、runtime/events.py；测试 test_execution_contracts.py、test_event_recorder.py，保留旧测试。

**Interfaces:**
- OperationSafety = read_only/idempotent/non_idempotent；OperationSpec 为冻结 Pydantic 模型：namespace、operation_id、kind、name、input: JsonValue、tool_version="1"、safety=read_only、timeout_s=5.0、retry_policy: RetryPolicy、max_fallbacks=1。
- OperationContext 为冻结执行视图：run_id/task_id/step_id/operation_id/attempt_id、attempt_number、input、idempotency_key、owner_token、remaining_s；不得持有可修改的其他 Attempt 结果。
- Operation.__call__(context: OperationContext) -> Awaitable[JsonValue]；OperationBinding(name: str, call: Operation)；ResultValidator.__call__(value: JsonValue) -> JsonValue。
- canonical_digest(spec: OperationSpec) -> str：摘要包含 namespace/name/kind/tool_version/input，不含 attempt/provider/timeout/retry 配置；operation_key(spec: OperationSpec, task_id: str) -> str 为 namespace/task_id/operation_id 的无歧义编码；均位于 execution/validation.py。validate_json(value: JsonValue) -> JsonValue 只验证 JSON 合法性，业务 Schema/非空要求由调用者传入 ResultValidator 执行。
- Attempt 含 attempt_id/run_id/step_id/operation_id/number/provider/status/generation/started_at/ended_at；现有 Failure、RecoveryAttempt 新增可选 attempt_id，旧构造可用。
- EventRecorder(sink: TraceSink, *, id_factory: Callable[[], str])；emit(event: TraceEvent) -> Awaitable[None]，先保存深拷贝运行事实再尝试导出，events 与 export_error_count 可读。TraceEvent 新增 sequence/attempt_id/schema_version 的兼容默认值。
- execution/errors.py 保留现有三种错误与 classify_exception 签名，补充 DeadlineExceededError、ProtocolValidationError、ProviderUnavailableError、StoreCommitError、OutcomeUnknownError、IdempotencyConflictError、StaleOwnerError；ProviderRateLimitError(retry_after_s: float | None=None) 携带重试建议，ToolExecutionError(*, outcome: str="unknown") 明确 not_sent/committed/unknown。分类只信任已定义类型，未知错误标 STATE 且 attributes.retryable=False，不保存原始异常全文。

- [ ] Step 1：执行时先按 using-git-worktrees 检查隔离环境；建立 .venv 并 `python -m pip install -e ".[dev]"`；运行当前 pytest、Ruff、mypy，记录实际版本和输出。修复与本计划有关的基线故障后才继续，不能把环境缺 pytest 当测试失败。
- [ ] Step 2：编写以下失败测试；旧路径兼容测试在迁移前应失败于 execution 不存在，其他测试必须失败于具体新行为。

```python
def test_digest_is_stable_but_changes_with_business_input():
    assert digest_same_input_different_dict_order == original_digest
    assert digest_changed_payload != original_digest

def test_legacy_error_import_preserves_exception_identity():
    assert legacy.OperationTimeoutError is current.OperationTimeoutError

async def test_events_are_snapshots_and_export_failure_is_observable():
    assert recorder.events[0].attributes == {"value": "before"}
    assert recorder.export_error_count == 1
```

另测 NaN/Infinity、非字符串字典 key、无效 ID/timeout 在调用前拒绝；Failure.message 使用安全错误码/类型，不收集用户异常原始文本；记录器不输出 input 全文，按允许字段导出且屏蔽凭据键。未知异常归为 STATE、retryable=False；CancelledError 不进入普通分类。
- [ ] Step 3：`python -m pytest tests/unit/test_execution_contracts.py tests/unit/test_event_recorder.py -q`，确认新断言的预期失败。
- [ ] Step 4：实现上述契约、深拷贝、错误分类及兼容转发；Runtime 仅增加可选 id_factory 注入，默认行为保持不变；Clock 在 Task 2 引入。
- [ ] Step 5：运行新测试和既有生命周期测试，`python -m ruff check .`、`python -m mypy src`，期望所有检查通过。
- [ ] Step 6：提交 `refactor: establish reliable execution contracts and event snapshots`。

## Task 2：统一时间预算、Retry-After 与恢复策略

**Files:** 创建 runtime/clock.py、recovery/retry_after.py、tests/unit/test_deadline.py、tests/unit/test_retry_after.py；修改 recovery/models.py、engine.py、runtime/context.py、runtime/runtime.py、test_recovery_engine.py；创建 tests/support.py 与 tests/__init__.py。

**Interfaces:**
- Clock.monotonic() -> float、Clock.utcnow() -> datetime；SystemClock 提供实际实现；Sleeper = Callable[[float], Awaitable[None]]。
- Deadline.after(seconds: float, clock: Clock) -> Deadline；remaining_s() -> float；require_remaining() -> float，耗尽时抛 DeadlineExceededError。
- ReliabilityRuntime(..., clock: Clock | None=None)；run(agent_id, task_id, metadata=None, *, timeout_s: float=30.0)；ExecutionContext.deadline 为本 Run 的共享预算，旧调用不变。
- parse_retry_after(value: str | None, *, now: datetime) -> float | None；RecoveryEngine.decide(failure, attempt_number) 原签名保持；构造可注入独立 rng: Random | None，policy 增加 jitter="none"/"full"，默认 none 保留旧精确延迟测试。
- tests.support.ManualClock(start: float=0.0)、RecordingSleeper(clock)，后者 records: list[float]，每次 await 推进该时钟并让出一次执行权，不与 asyncio 的真实事件循环时钟混用。

- [ ] Step 1：新增具名测试及以下精确断言，包含 attempt_number=0 报 ValueError、极大尝试号不溢出。

```python
def test_retry_after_is_not_capped_to_local_backoff_max():
    assert decision.delay_s == 3.0  # local max_delay_s=2.0, server=3.0

def test_retry_after_http_date_and_invalid_values():
    assert parsed_future_date == 3.0
    assert parsed_invalid is None
    assert parsed_negative is None

def test_deadline_does_not_reset_after_wait():
    assert budget.remaining_s() == 0.0  # start 2s; clock advanced 3s
```

- [ ] Step 2：运行新增测试确认失败；保留已有 max_attempts=3、base_delay_s=0.5 时第二次决定为 1.0 的测试。
- [ ] Step 3：实现 Decimal/有限数解析与 UTC HTTP-date 差值；过去日期返回 0；指数计算先限制指数再计算，服务端 delay 不受本地 backoff cap 截断。clock 与 sleep 分开注入；策略对象在 Engine 内快照。
- [ ] Step 4：运行 deadline、retry_after、recovery 和 lifecycle 测试；相同 jitter seed 独立实例序列相同，FaultEngine 的 RNG 不受影响。
- [ ] Step 5：提交 `feat: add shared deadlines and bounded recovery timing`。

## Task 3：并发幂等存储与 owner 生命周期

**Files:** 创建 idempotency/{__init__,models,store}.py、tests/unit/test_idempotency_store.py；错误类型在 execution/errors.py，引用执行契约时避免循环导入。

**Interfaces:**
- ReservationStatus = new/in_progress/completed/unknown；Reservation(key, digest, status, owner_token: str | None, result: JsonValue | None)。store 内区分“结果为合法 null”和“无结果”，不能用 result is None 判完成。
- IdempotencyStore.reserve(key: str, digest: str) -> Awaitable[Reservation]。
- complete(key: str, owner_token: str, result: JsonValue)、release(key: str, owner_token: str)、mark_unknown(key: str, owner_token: str) -> Awaitable[None]。
- wait(key: str, digest: str, timeout_s: float) -> Awaitable[Reservation]；InMemoryIdempotencyStore 兑现同一签名；错误包括 IdempotencyConflictError、StaleOwnerError、OutcomeUnknownError。

- [ ] Step 1：写失败测试：20 次并发 reserve 的 NEW 数为 1，其余 IN_PROGRESS；complete 后全部返回深拷贝且状态 COMPLETED；合法 JSON null 可以缓存。
- [ ] Step 2：增加 test_cancelled_waiter_does_not_cancel_owner、test_wrong_owner_cannot_complete_or_release、test_same_key_different_digest_rejects、test_unknown_is_never_new；用 Event 控制 owner 完成及 waiter 取消。运行测试确认失败于缺实现。
- [ ] Step 3：实现短锁状态转换与每记录 Event 通知；锁不覆盖业务 await；等待者的 wait_for 只作用于自己，release 后等待者重新 reserve 竞争唯一 owner；UNKNOWN 不自动过期变 NEW。
- [ ] Step 4：运行该测试文件；完整结果修改不会污染后续 cache hit，取消一个 waiter 后 owner 仍能 complete，其余 waiter 都收到结果。
- [ ] Step 5：提交 `feat: implement owner-safe in-memory idempotency`。

## Task 4：实际故障注入和冻结实验调度

**Files:** 修改 fault/models.py、engine.py；创建 fault/schedule.py、injector.py、tests/unit/test_fault_schedule.py、test_fault_injector.py；修改 runtime/context.py、runtime/runtime.py。

**Interfaces:**
- FaultSource.decide(target: FaultTarget, phase: FaultPhase, *, operation_id: str="", attempt_number: int=1) -> FaultDecision | None；旧两位置参数调用仍有效。
- ScheduledFault(operation_id, attempt_number, phase, decision) 为冻结记录；FrozenFaultSchedule(entries: tuple[ScheduledFault,...]) 按显式键查询；记录配置 hash，不依赖并发消费顺序。
- FaultInjector.before(decision: FaultDecision | None, context: OperationContext) -> Awaitable[None]；transform_result(decision, value: JsonValue) -> JsonValue；after_commit(decision) -> None。
- FaultSource 定义在 fault/schedule.py。timeout 注入使用有界异步延迟（smoke 场景20ms，对照单次预算5ms）触发真实 Attempt timeout，确保 raw 组也能结束；Task6另用未完成Event验证真实取消。rate_limit/unavailable/tool_crash 使用 typed error；malformed/empty 返回损坏结果供业务 Validator 发现；response_lost 仅 after_commit 抛错。非法 fault/phase 组合在配置时拒绝。
- ReliabilityRuntime(..., fault_factory: Callable[[], FaultSource] | None=None)；每个 run 生成独立 ctx.fault_source，默认无故障。

- [ ] Step 1：写 test_schedule_is_independent_of_task_interleaving、test_engine_snapshots_mutable_policy、test_invalid_fault_phase_rejects；assert 正反调用顺序得到同一 operation→decision 映射，非匹配不消耗 RNG/配额。
- [ ] Step 2：写 Injector 测试，assert malformed/empty 经真实 Validator 得到协议失败；response_lost 错误只在 after_commit 出现；运行新增测试确认预期失败。
- [ ] Step 3：实现显式调度键、配置快照、各拦截点行为；FaultDecision 增加需要的兼容可选元数据，不能返回尚未使用的“故障类型字符串”就视为已执行扰动。
- [ ] Step 4：运行全部 fault 测试及旧顺序 seed 测试；真实 timeout 的完整验证留给 Task 6 的 AttemptRunner。
- [ ] Step 5：提交 `feat: execute faults with reproducible schedules`。

## Task 5：Executor 组合与经典副作用恢复闭环

**Files:** 创建 execution/attempt.py、executor.py、tests/unit/test_operation_executor.py、tests/integration/test_canonical_side_effect_recovery.py；修改 runtime/context.py 与 errors/models 所需字段。

**Interfaces:**
- AttemptRunner(clock: Clock).run(context: OperationContext, operation: Operation, *, timeout_s: float) -> Awaitable[JsonValue]；只负责一次尝试协程的结果/timeout，不自带重试。Executor 传入的 operation 闭包包含 before fault、实际 dispatch、transform、validate，确保注入延迟也在同一时间边界内；dispatch 计数只在 before fault 通过后增加。
- ReliableOperationExecutor(store: IdempotencyStore, *, clock: Clock | None=None, sleeper: Sleeper=asyncio.sleep, max_concurrency: int=20)。execute(ctx: ExecutionContext, spec: OperationSpec, bindings: tuple[OperationBinding,...], *, validate: ResultValidator=validate_json) -> Awaitable[JsonValue]。
- bindings[0] 是主操作，其余为有序 fallback；空列表/重复名称在任何调用前拒绝。ctx 提供 deadline、fault_source、event recorder。每个 execute 建一个 Step；多个 Attempt 共享 Step 和 operation_id。
- Executor 依次检查预算/owner→before fault→调用→transform→validate→complete→after_commit；所有对外返回来自已经验证的结果。RecoveryEngine 只建议动作，Executor 审核安全性/总预算。
- 同 key 完成命中不新建物理 Attempt，发 idempotency.hit；IN_PROGRESS 仅等待剩余预算；释放通知后重新竞争；UNKNOWN 抛 OutcomeUnknownError。max_attempts 包括 before-call 故障，实际 dispatch 另计。

- [ ] Step 1：编写 test_response_lost_after_success_is_recovered_once，用真实 list.append 作为本地副作用，冻结 attempt 1 AFTER_SUCCESS 丢回复。断言 result 正确、len(rows)==1、upstream dispatch==1、fault/Failure/Recovery/idempotency.hit 可通过同一 Step 关联。
- [ ] Step 2：编写 test_unhandled_failure_aborts_run、test_handled_operation_failure_allows_run_success、test_invalid_result_never_completes、test_unknown_exception_never_retries；运行确认新执行路径尚不存在而失败。
- [ ] Step 3：实现上述 execute 与 Step/Attempt 事件；fallback 共享 attempts/deadline，参数摘要跨尝试不变；补 RecoveryAttempt 的成功/失败结尾，保留主/备用 Failure 全链。
- [ ] Step 4：补充 test_commit_failure_does_not_repeat_tool 和 test_broken_trace_sink_does_not_repeat_committed_effect：在实际 Tool 成功之后让 complete 抛 StoreCommitError，assert calls==1 且 Run 失败/结果未知，不伪报成功；仅 export 坏时业务仍成功且 export_error_count>0。
- [ ] Step 5：运行 Executor、canonical 与全部旧测试，期望存储故障和导出故障呈现上述不同结果；必要修复属于本任务同一验证循环。
- [ ] Step 6：提交 `feat: compose reliable executor and side-effect recovery`，在提交说明记录核心场景实际结果，不将它扩展为跨进程保证。

## Task 6：取消、晚到结果与总预算的对抗验收

**Files:** 修改 execution/attempt.py、executor.py、runtime/context.py、runtime/runtime.py；创建 tests/integration/test_execution_boundaries.py；扩展 test_operation_executor.py。

**Interfaces:** 使用 Task 1–5 已定义签名；不增加第二套 executor 或框架。Attempt generation 在开始时创建，关闭后失效；提交前检查 generation、task.cancelling()、deadline。Step 取消产生明确终止事实；旧 Step 非取消异常事件不变。

- [ ] Step 1：新增以下集成测试并确认失败于相应缺失边界：test_real_async_timeout_closes_attempt；test_cancel_provider_propagates；test_cancel_backoff_starts_no_new_attempt；test_cancel_reservation_waiter_preserves_owner。
- [ ] Step 2：补 test_late_result_is_not_committed（操作捕获取消后返回旧值，仍须拒绝提交）、test_non_idempotent_unknown_never_retries（调用后失败而无已完成记录）、test_concurrency_slot_is_released；用 Event 协调，不用依赖精确耗时的断言。
- [ ] Step 3：实现统一时间边界及 finally 清理；单次 timeout=min(spec timeout, remaining run budget)，等待并发槽也使用剩余预算；取消后不再 sleep/retry/fallback。副作用可能发生时转 UNKNOWN，已完成记录保留。对不退出的任意代码不宣称能够强杀。
- [ ] Step 4：补参数化预算测试：max_attempts=3 时主/备总机会<=3，max_fallbacks=1 不二次切换；server delay=3、remaining=2 时第二次调用不存在；不可安全重发的工具不能 fallback；主/备都失败仍保留两项 Failure。
- [ ] Step 5：运行所有集成测试及全套测试，期望调用次数、取消状态、UNKNOWN 和预算断言全部通过。
- [ ] Step 6：提交 `fix: enforce cancellation fencing and shared retry budgets`。

## Task 7：Native ReAct SUT、四组基准与状态判分

**Files:** 创建 examples/{__init__,tools,minimal_react}.py、evaluation/{__init__,models,scenarios,benchmark}.py、tests/unit/test_minimal_react.py、test_benchmark_grading.py、tests/integration/test_four_arm_comparison.py。

**Interfaces:**
- AgentAction 为 tool(name, arguments)/finish(answer) 的区分联合；ScriptedProvider.next_action(history: tuple[JsonValue,...]) -> Awaitable[AgentAction]；脚本只决定动作，工具实际由 Executor 执行。
- ToolRegistry 保存注册名、参数验证器、OperationBinding 及安全语义；不接受任意代码/路径。MinimalReactAgent.run(ctx: ExecutionContext, task: TaskCase, *, max_turns: int=8) -> Awaitable[JsonValue]，每轮决策也经过 LLM_CALL 执行边界。
- TaskCase(case_id, scenario_id, input, expected_rows, expected_answer, schedule, expectations) 为冻结配置；ExpectedOutcome(task_success: bool, effect_count: int, outcome: str) 给出各 ProtectionMode 的验收预期，expectations 为其映射且构造后保持深拷贝。BusinessState 提供 append/query 快照，不由 Agent 的“成功”回答充当判分依据。
- ProtectionMode = raw/timeout_only/naive_retry/reliable_runtime；run_case(case: TaskCase, mode: ProtectionMode, *, seed: int) -> Awaitable[CaseResult]；run_benchmark(profile: str, seed: int) -> Awaitable[BenchmarkReport]。
- 各组使用同一可组合执行管线和 FaultSource：raw 无保护但仍观测；timeout_only 只有单次 timeout；naive_retry 有限 retry 无去重/结果未知保护；reliable_runtime 全策略。所有组状态独立重置，错误策略只允许在模拟内置业务上使用。
- CaseResult 包括 task_success、outcome、upstream_calls、retry/fallback/cache hits、effect_count、expected_effects、duplicate_count、fault exposures、latency_s、events、safety_pass；BenchmarkReport 含 schema_version、runtime/SUT/dataset/config hash、seed、simulated=true、cost=null、逐 case 结果及聚合。所有统计读取执行结果，expectations 只用于独立验收比对，不用于填充观测结果。

- [ ] Step 1：写 Native 成功/未知 Tool/参数错误/超过8轮/空最终回答测试；assert 实际工具记录与结构化结果均符合预期。
- [ ] Step 2：运行 test_minimal_react.py，确认新 SUT 尚不存在而失败。
- [ ] Step 3：实现 TaskCase/ToolRegistry/Native loop，用 operation_id=任务内稳定的 decision:index 与 tool:index；namespace 独立于 Run，所有对照组采用同一逻辑寻址。
- [ ] Step 4：写 canonical 四组实测断言：response-lost 下 raw 和 timeout_only 任务失败且真实提交1次；naive_retry 成功且提交2次；reliable_runtime 成功且提交1次。断言来自真实执行状态，不能从 mode 名直接填统计值；改变 Tool 数据后 Grader 必须失败。
- [ ] Step 5：运行 test_benchmark_grading.py 和 test_four_arm_comparison.py，确认缺少测量/判分路径的预期失败。
- [ ] Step 6：实现10个具名 smoke case：normal、response-lost、429、503、real-timeout、malformed、empty、tool-crash、unknown-outcome、fallback；相同 schedule/状态/版本四组配对。Tool-crash case 在实际注册 Tool 内抛 ToolExecutionError，并记录提交是否发生。所有组外层都有实验级1秒超时防止错误策略挂死，它不计为 raw 组的 Operation 保护。未知结果作为合法业务报告而非 benchmark 进程崩溃；配置错误单独报错。p95 使用 nearest-rank 且带样本量，不比较非确定性时延是否字节相同。
- [ ] Step 7：运行 Native、Grader、四组集成与全套测试；固定 seed 重跑时比较业务结果/故障映射/计数，排除时间和随机 ID。
- [ ] Step 8：提交 `feat: demonstrate native agent reliability with measured comparisons`。

## Task 8：CLI、CI 和可复核交付

**Files:** 创建 cli.py、__main__.py、tests/integration/test_cli.py、docs/status/product-progress.md；修改 README.md、docs/architecture.md、.github/workflows/ci.yml；产品版本按现有0.1.0兼容演进记录，不提前发布到包索引。

**Interfaces:** cli.main(argv: Sequence[str] | None=None) -> int；两个命令与批准设计一致：`demo --scenario response-lost --compare --seed 42`、`benchmark --profile smoke --seed 42 --output report.json`。CLI 默认终端表；指定 JSON 输出时 UTF-8 写完整 BenchmarkReport。非法参数/路径错误非0退出；实验中的预期失败通过完整报告表达，进程退出0；`--check` 比较独立 expectations 和可靠组 safety_pass，硬门禁失败返回1。unknown-outcome 的安全拒绝和 raw 的预期失败不等于回归，不能简单要求所有 task_success=True。

- [ ] Step 1：写 subprocess CLI 失败测试：assert 两条有效命令 exit_code==0、报告能由 BenchmarkReport 校验、四组行齐全、JSON cost is None、simulated is True；无效 profile 退出非0；增加 --check 可靠组结果被破坏后退出1的测试。用 sys.executable，避免 Windows 引号及解释器不一致。
- [ ] Step 2：运行 test_cli.py，确认新入口缺失造成预期失败。
- [ ] Step 3：实现 argparse 及两条入口；JSON 使用临时文件+原子替换，路径/序列化失败明确退出，不能输出半个成功报告；不打印原始异常敏感文本。
- [ ] Step 4：更新 README 的真实实现状态、venv/Anaconda Windows 与 Linux 命令、模拟边界、核心场景和后续 M2；CI 继续 Linux Python3.11/3.12质量检查，增加 Windows3.11核心与CLI smoke，上传实际 smoke JSON artifact。不更改用户学习台账。
- [ ] Step 5：执行一次完整验收：`python -m pytest -q`、`python -m ruff check .`、`python -m mypy src`、两条 CLI，另运行 `benchmark --profile smoke --seed 42 --check --output artifacts/m1-smoke.json`；检查产物计数与业务状态一致、工作区无密钥。测试完成后在产品台账记录命令、实际结果、提交和未验证项，不预写绿色状态。
- [ ] Step 6：提交 `feat: ship runtime demo and reliability regression CLI`。
- [ ] Step 7：按执行技能完成整分支 Review，修复阻塞问题并重跑受影响验收后形成必要修复提交；提供分支/演示命令/真实报告，M1验收后再细化M2实施计划。

## 自审与执行交接

覆盖关系：Spec§3→Task1/2；§4→Task1/3/5；§5→Task2/5/6；§6→Task4/6；§7→Task7/8；§8十二项验收→Task3/5/6/7/8；§9→Task1基线与Task8交付。五项 Review Focus 都有具名测试。M1 不承担后续平台接口的未验证保证。

计划接口检查：Runtime fault_factory 只在 Task4 引入，Clock 在 Task2 引入；Task5只组合已存在契约；Task7使用同一个Executor/故障管线；Task8不另写统计算法。OperationBinding.name 与 fallback 名称以调用时 tuple 为唯一来源，不保留重复的 Provider 列表配置。

推荐 **Native** 执行：由当前会话按顺序实现8个任务，最后做整分支独立 Review。理由是时间、owner、故障和执行器的接口关联紧密，顺序实现更容易保持一致。也可选择 Subagent-driven，逐任务实施和独立评审；它需要更多上下文与评审轮次。

计划审阅及执行方式确认后，使用对应执行技能；过程中不为已明确的版本/Native优先/学习台账边界重复提问。发现影响批准契约的冲突时，先说明具体证据，再做范围修订。
