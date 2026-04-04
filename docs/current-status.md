# FetchNews 当前状态

## 概览

当前项目已经具备从资讯采集到草稿生成、审核、发布、反馈和运维观察的完整内部闭环。后续工作重点是把真实外部平台接入、把智能能力做深、把编辑协作和生产化部署补齐。

## 已完成

- 后端与前端基础骨架。
- 来源采集、标准化、聚类与 story 审核。
- 日报 / 周报 / 月报草稿生成与平台短帖变体。
- 审核工作台、块级编辑、版本恢复、混合重建。
- 发布任务、执行、轮询、结果回写与失败重试。
- 来源治理、栏目势能、平台互动反馈与文案策略联动。
- 运维面板、失败诊断、栏目监控与 drill-down。
- PostgreSQL、Alembic、登录、权限、审计、前端测试基线。

## 进行中

- 编辑工作台的细粒度 diff 可视化。
- 编辑历史明细页与人工干预回放。
- 平台文案策略继续按历史反馈细化。
- 前端 Vitest 挂起问题的环境收敛。

## 后续待实现

1. 真实发布器和真实来源连接器。
2. 真实 LLM provider 和 embedding 去重 / 召回。
3. 更完整的编辑协作治理与审计 UI。
4. 更完善的告警、监控、备份和 Runbook。
5. 生产化部署、CI 与迁移规范收敛。

## 阶段参考

- 详细计划入口：[docs/project-plan/README.md](/D:/Code/Project/FetchNews/docs/project-plan/README.md)
- 后续阶段拆分：[docs/project-plan/phase-07-future-roadmap.md](/D:/Code/Project/FetchNews/docs/project-plan/phase-07-future-roadmap.md)

## 备注

- 当前状态文档用于描述“代码已经实现到哪里”。
- 阶段计划用于描述“下一步要往哪里走”。
- 两者不一致时，以当前状态文档和代码为准，但应尽快同步计划文档。