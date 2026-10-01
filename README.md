# Agent Reliability Lab

一个面向工具调用型 Agent 的可靠性 Runtime 与评测实验室。项目的目标不是再实现一个聊天 Agent，而是把一次 Agent 执行变成可观测、可注入故障、可恢复、可复盘的工程闭环。

## 当前状态

- Phase 1A / Task 1：工程骨架与测试体系，已完成。
- Phase 1A / Task 2：领域模型与 TraceSink，代码已拉取并能通过当前 5 个测试，但仍处于 Review Changes Requested 状态。
- 当前已验证：`python -m pytest -q` → `5 passed`。
- 当前已知 Review 问题记录在 [学习进度台账](docs/learning-progress.md) 中；测试通过不等于 Task 2 已验收。

## 工程结构

```text
src/agent_reliability/
├── domain/       # Run、Step、TraceEvent、Failure 等业务概念
├── runtime/      # Runtime 依赖的 Port 和未来的执行编排
└── tracing/      # TraceSink 的具体适配器

tests/unit/       # 单元测试
docs/             # 架构、跟写进度和验收模板
.github/workflows/ci.yml
```

当前的边界和数据流见 [架构说明](docs/architecture.md)。

## 开发环境

```bash
python -m pip install -e ".[dev]"
python -m pytest -q
python -m pytest --cov=agent_reliability --cov-report=term-missing
python -m ruff check .
python -m mypy src
```

GitHub Actions 会在 Python 3.11 和 3.12 上安装项目、运行测试、生成覆盖率报告，并执行 Ruff 与 mypy。质量命令是工程门禁；它们不会替代 Task 的领域 Review。

## 可靠性闭环

最终要形成下面的闭环：

```text
用户任务
   ↓
Runtime 创建 Run
   ↓
执行一个或多个 Step
   ├── LLM 调用
   ├── 工具调用
   ├── Memory 读取
   └── Checkpoint / Recovery
   ↓
TraceSink 记录时序事实
   ↓
Fault Injection → Failure 分类 → Recovery / Retry / Degrade / Abort
   ↓
指标、Replay 和评测报告
```

当前仓库只完成了这条链路最前面的领域词汇和内存 Trace 适配器，Runtime 行为会在后续 Task 中逐步加入。

## 首批可靠性场景

| 场景 | 需要证明的行为 | 计划指标 |
| --- | --- | --- |
| Provider timeout | 分类为 timeout，并按策略重试或终止 | 恢复成功率、重试次数 |
| Tool side-effect ambiguity | 不因重复重试造成重复副作用 | 重复副作用率 |
| Response lost after success | 能区分执行结果未知与执行失败 | 误恢复率、幂等命中率 |
| Recovery itself fails | 记录完整因果链并进入 degrade/abort | 失败闭环完整率 |

可靠性评测必须同时保留一个没有 Runtime 保护的 baseline，比较成功率、恢复成功率、延迟、重试次数、重复副作用率和 Trace 完整性。

## 跟写规则

本项目是学习项目。参考实现只用于理解和 Review，不计入你的个人进度。一个 Task 只有在以下证据都存在时才能推进：

1. 你本人完成实现；
2. 你本人运行了测试并保留结果；
3. Review 问题已经解决；
4. 你能独立解释设计取舍并完成一个小变式。

唯一进度来源是 [学习进度台账](docs/learning-progress.md)。后续 Task 使用 [验收模板](docs/task-acceptance-template.md)，不再只依赖聊天记录。

## 推荐路线

1. 完成 Task 2 的字段修正、补充测试并通过 Review。
2. 实现 Run/Step 生命周期和事件发射。
3. 加入确定性的故障注入、恢复和幂等控制。
4. 用最小 ReAct/工具调用场景做端到端评测。
5. 再接入持久化 Trace、OpenTelemetry、Dashboard 或分布式 Worker。

在本地可靠性闭环和评测完成前，不提前引入 PostgreSQL、Redis、Kubernetes 等基础设施。
