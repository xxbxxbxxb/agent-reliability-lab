# M1：可靠执行 Runtime 闭环设计

日期：2026-10-15

状态：DRAFT_FOR_USER_REVIEW；等待本书面设计评审后再写实施计划

总体设计：`2026-10-15-agent-reliability-lab-mature-v1-design.md`

基线：`main@f66aead6f3591faee8cd3f6ef9205cb58bf2177a`

## 1. 目标与成功标准

把现有 Run/Step、FaultEngine、RecoveryEngine 组合成真正执行异步 LLM/Tool 操作的 Runtime。第一份交付是离线可运行的 Native Agent 和故障对照实验，而非继续只增加模型类。

核心验收：一个会写入模拟业务记录的 Tool 成功后丢失返回；普通重试产生重复记录；可靠执行复用同一稳定身份并读取已完成结果，只产生一次业务提交。结论来自实际执行次数、业务记录和 Trace 的一致结果，不预填报告数字。

本阶段仅保证同进程的内存去重和受控异步调用语义。跨进程幂等与恢复在 M2 完成，不用内存示例为其背书。

## 2. 范围与明确边界

包含：保留现有领域模型/API；execution 命名兼容迁移；Operation/Attempt 模型；输入与输出校验；Timeout/总 Deadline；有界 Retry/Retry-After/Fallback；取消；内存 reservation/结果/冲突检测；真实故障执行；Failure 与 RecoveryAttempt 关联；Native SUT；四组对照 CLI 与 JSON 报告。

不包含：数据库、Redis、长任务 HTTP API、Web UI、Checkpoint、Replay、OTel Exporter、完整 HTTP/SSE Proxy、LangGraph、Kubernetes。此处是子项目边界，不是放弃总体设计中的后续交付。

异步操作需遵守取消协议；阻塞 Python、CPU 密集计算、拒绝退出的本机子进程不作为可被本阶段协程 timeout 强制停止的对象。不能以本机 Task 取消推断远程工具没有提交。

## 3. 现有代码如何演进

- `domain/models.py` 保留 Run/Step/Failure 等公共名字，增加必要版本、状态和 Attempt 关联；新增字段提供兼容默认值。
- `runtime/context.py` 保留 `async with ctx.step(kind, name)`，并提供 Executor 使用的稳定身份入口；调用者处理 Step 异常后仍可令 Run 成功。
- `runtime/runtime.py` 注入 ID factory/Clock 等必要依赖，继续处理 Run 成功、失败与取消。
- `fault/engine.py` 保留现有匹配、seed 和 max_injections 行为；构造时快照策略；新增可冻结的实验调度入口，不改掉现有确定性测试所验证的契约。
- `recovery/engine.py` 保持为可测试的决策组件；安全性与预算否决留在 Executor，不能只靠 FailureKind 决定任意副作用可重试。
- `execution/` 成为正式目录；`excution/errors.py` 转发旧公共名字，不立即使已有跟写代码导入失败。
- `tracing/memory.py` 仍可用于离线运行；记录事件快照，避免之后修改可变对象改变历史事实。
- `docs/learning-progress.md` 不把 AI 实现标为用户个人已掌握；新增 `docs/status/product-progress.md` 记录产品完成证据。

## 4. 核心契约

| 契约 | 职责 |
| --- | --- |
| OperationSpec | operation_id、kind、name、规范化 input、安全类别、单次 timeout、重试策略、fallback 列表 |
| OperationContext | run/step/operation/attempt ID、稳定幂等 key、remaining deadline、当前 owner token |
| Operation Callable | 接收 OperationContext，返回待校验结果；不私自增加未声明的 retry |
| Result Validator | 对真实结果进行 Schema/空输出检查；可报告协议失败 |
| Attempt | 一次上游调用/注入尝试；started/ended、Provider、结果/错误、generation |
| Clock/Sleeper | monotonic/UTC 时间与可取消等待；测试中注入虚拟时钟，真实 timeout 另做集成验证 |
| IdempotencyStore | 原子 reserve/complete/mark_unknown/release；任何写回校验 owner token |
| RecoveryEngine | 根据 Failure、尝试号和 Policy 提出 retry/fallback/abort |
| ReliableOperationExecutor | 组合上述契约，统一执行、安全检查、预算、取消和结果提交 |
| Scenario/Grader | 冻结故障与初始状态；从实际业务状态判分，所有对照组共用 |

Operation 输入和可录制输出限定为 JSON 可序列化值。digest 使用 canonical JSON 与 SHA-256；key 相同但参数/工具版本不同返回明确 conflict，不能返回旧结果。secret 不进入报告或完整异常文本。

### 4.1 Reservation 结果

- NEW：得到唯一 owner token，可执行。
- IN_PROGRESS：另一 owner 正在执行；有界等待同一结果，不获得第二次执行权。
- COMPLETED：摘要匹配时返回结果快照，不调用底层 Tool。
- UNKNOWN：可能已有副作用但无法确认，不能仅因租约过期自动再次执行。

内存实现用锁保护状态转换；锁不能覆盖整个网络等待。等待者取消只取消自己的等待，不取消其他 owner 的操作，也不删除其他 owner 的 reservation。等待完成使用不传播取消的结果通知。

## 5. 操作执行与失败规则

一个逻辑 Operation 建立一个 Step，每个物理尝试建立 Attempt。 BEFORE_CALL 故障发生在调用前；AFTER_SUCCESS 的 response_lost 发生在真实业务返回、校验和本阶段已完成结果记录之后。重试命中 COMPLETED 时记录 cache hit/recovery success，不伪造第二次底层 Tool 调用。

失败路径均创建 Failure；retry/fallback 创建 RecoveryAttempt 并关联触发 Failure。新尝试成功后结束对应恢复；最终失败同时保留所有前因。没有恢复策略的未知程序异常直接抛出；不能把编程错误装成 Provider 短暂故障。

调用前能证明没有副作用的失败允许释放 reservation；调用发出后失败但无法证明结果的非幂等工具标记 UNKNOWN。已完成结果不会因交付失败被删除。完成结果的存储失败不能重新调用模型来“补偿”。

回退仅适用于声明语义兼容的 Provider 或只读操作。非幂等业务工具的 fallback 默认拒绝，以免另一个工具重复提交。所有 Provider 共用同一个 max_attempts、Deadline 和逻辑 operation_id。

### 5.1 预算与取消

max_attempts 是总物理尝试上限，包含初次、重试和 fallback；max_fallbacks 另行约束 Provider 切换。若一项响应已命中缓存，不增加物理上游调用计数。指数计算有上限保护，attempt_number 必须 >=1。

退避采用 capped exponential；jitter 单独注入随机源；Retry-After 为秒或 HTTP-date，负数/无效值按解析规则忽略并记录。选取 max(backoff, Retry-After)，等待后必须再次检查预算与取消。剩余时间不足则终止，不能为了“完成重试”突破 Deadline。

协程取消传播到调用和退避，不转成可重试异常；释放自己拥有的并发槽。Executor 提交前检查 generation、取消状态和 deadline；即使回调较晚返回，也不能覆盖已经关闭的尝试。对不遵守取消的外部任务，只保证拒绝过期结果及拒绝不安全重发，不保证强制终止远端计算。

## 6. 故障执行

| 故障 | 真实实现/验证方式 |
| --- | --- |
| timeout | 延迟协程触发真实 asyncio 时间边界；直接抛错的版本单独标模拟 |
| rate_limit / unavailable | 构造明确的 typed Provider 错误，记录 Retry-After |
| malformed_output / empty_response | 先产生无效返回，再由结果校验器发现 |
| tool_crash | 调用 Tool 后按控制点产生异常，保留是否已发出/提交的信息 |
| response_lost_after_success | 业务结果实际写入，完成记录可查，再丢失交付 |
| duplicate invocation | 多个并发调用同一 key，验证唯一 owner 与结果共享 |
| cancel during backoff | 由另一 Task 取消，检查不再调用 Provider |

Policy 配置与状态分离；每个 Run 有独立配额及随机状态。实验冻结 schedule，避免任务调度改变命中顺序；非匹配操作不消耗配额/随机量。故障、退避 jitter、ID 生成的随机源不得相互消耗。

## 7. Native SUT 与命令行体验

Native Agent 使用 action/observation 循环：读取任务 → Provider 选择注册 Tool → Executor 执行 → Tool 结果返回给 Provider → 结构化最终答案。限制最大轮数及总预算，未知 Tool/参数不合法时明确失败。

ScriptedProvider 提供无 Key、无网络的确定性基准；其行为不冒充真实大模型推理。真实 HTTP Provider 在后续 HTTP Adapter 阶段提供，两者最终共用同一执行契约。

内置模拟业务 Tool 实际维护业务记录并提供查询接口，Grader 从记录检查 task_correct、commit_count 和 payload。四组保护配置分别为 raw、timeout_only、naive_retry、reliable_runtime，统一测量事件。

规划中的命令（本阶段实施完成前尚不可运行）：

```bash
python -m agent_reliability demo --scenario response-lost --compare --seed 42
python -m agent_reliability benchmark --profile smoke --seed 42 --output report.json
```

终端展示每组的任务结果、物理调用、恢复、业务提交、重复写入、耗时；JSON 同时输出配置、版本、故障暴露和逐任务数据。未知成本为 null。脚本 Provider 和模拟业务状态标记 simulated。

## 8. 验收场景

1. 正常流程：运行 Native Agent，真实 Tool 被调用并产生预期业务记录，Run/Step/Attempt 终止事件完整。
2. 经典丢回复：raw 失败，naive_retry 按设定产生重复提交，可靠组成功且恰好一次提交；所有结果从实际状态计算。
3. 并发同 key：至少 20 个并发请求只有一个 owner 执行业务，其余返回相同结果；独立取消等待者不干扰 owner。
4. 相同 key 不同参数：立即 conflict，不执行第二次，也不返回错误缓存结果。
5. Retry/Retry-After/Deadline：退避计算正确，服务端要求不被截短，总预算不足无额外调用。
6. Fallback：主/备均计入同一总预算；明确记录切换，两个 Provider 均失败时保留因果链。
7. 取消：在 Provider、等待 reservation、退避三个位置取消，无新 Attempt；Run 为 cancelled，owner 状态合法。
8. 不确定副作用：发出非幂等工具后结果未知，不再次自动执行；错误报告含 outcome_unknown。
9. 结果/日志边界：观测收集异常不能使已完成结果被删除；必要状态写入失败不能伪报成功或触发整个业务重复。
10. 状态隔离与晚到结果：不同 Run 不共享故障配额/数据；已关闭 Attempt 的晚到结果不能覆盖结果。
11. 输出校验：malformed/empty 经实际验证器被拒绝；不把无效回答计为任务成功。
12. 兼容与回归：旧 execution 拼写导入可用，现有生命周期测试保留；局部失败被处理后 Run 可成功。

时间计算使用可注入时钟做确定性验证，同时至少一项真实异步耗时/取消集成验证。并发测试使用 Barrier/Event 控制顺序，不靠任意 sleep 猜调度。

## 9. 工程验证与交付

实施计划需先建立隔离环境，安装现有开发依赖，重跑当前基线，再按失败测试→最小实现→验证推进。验证命令包括 pytest、Ruff、mypy、两条 CLI 以及 JSON 结果与实际业务状态的一致性检查。既有 CI 的绿色记录不能代替本次验证。

交付包含：可评审分支代码、CLI 示例、实际生成的报告、产品实现台账、架构更新和 Windows 安装命令。产品台账逐项记录代码提交、验证命令、结果和适用边界；用户学习台账不因此升级。

当前本文件只定义行为、边界与验收，不包含未经评审的逐文件实施步骤，也没有任何“已实现/已测试通过”的新功能声明。

## 10. 自审结论

本切片围绕一个完整 Native 执行业务闭环；数据库/平台/框架边界已排除，范围足以形成独立实施计划。幂等键、请求冲突、并发 owner、调用后不确定结果、Fallback 预算和取消均有明确规则。实现期不必重新询问已明确的 Python 版本、Native 优先或学习台账边界；如发现影响这些契约的未知条件，记录具体证据再修订设计。
