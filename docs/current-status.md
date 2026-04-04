# FetchNews 当前状态

## 概览

截至 2026-04-04，项目已经具备从来源采集、标准化、聚类、草稿生成、人工审核，到发布回写和 ops 观测的完整内部闭环。

Phase 07 的首轮实现已经合并到主线，已完成 Task 1 到 Task 5。当前重点从“真实外部能力骨架接入”转入“Phase 07 加固与生产就绪”。

## 已完成

- 后端与前端基础骨架。
- 来源采集、标准化、聚类与 story 审核。
- 日报、周报、月报草稿生成与平台短帖变体。
- 审核工作台、块级编辑、版本恢复与混合重建。
- 发布任务、执行、轮询、结果回写与失败重试。
- 来源治理、栏目势能、平台互动反馈与 ops 汇总。
- PostgreSQL、Alembic、登录、权限、审计与基础测试基线。

## Phase 07 首轮已合并范围

### Task 1：数据契约和配置基线

- 新增真实平台接入配置字段。
- 为 `publish_jobs` 增加 `dispatch_key`、`failure_category`、`last_provider_status`。
- 为 `sources` 增加 `incremental_cursor`、`last_success_at`。
- 完成对应 schema 和迁移。

### Task 2：首个真实发布平台闭环

- 打通 `telegram` 真实发布器骨架。
- 打通 `/publish-jobs/callback/{platform}` 回调写回。
- 发布失败分类进入服务层。
- 幂等重试保留 `dispatch_key`，避免重复提交判断只依赖进程内状态。

### Task 3：其余平台适配骨架与 ops 失败归因

- 为 `wechat`、`x` 增加占位真实发布器。
- 统一默认 publisher registry 选择逻辑。
- ops 从“原始报错文案聚合”升级为“按 `failure_category` 聚合”。
- 平台指标增加 `last_failure_category`。

### Task 4：真实来源连接器和增量抓取

- 新增 `GitHubReleasesConnector`、`HuggingFacePapersConnector`、`PapersWithCodeConnector`。
- 连接器支持返回 `items + next_cursor`。
- 采集服务支持按 `slug -> platform -> kind` 解析连接器。
- 成功采集后回写 `sources.incremental_cursor`、`sources.last_success_at`。
- 原始快照统一写入 `raw_items.payload.snapshot`。

### Task 5：API、ops 面板和前端映射

- `/ops/summary` 暴露平台最近失败类别。
- `/sources` 暴露来源同步游标和最近成功时间。
- 前端 `api.ts` 完成 Phase 07 新字段的 snake_case 到 camelCase 映射。
- ops dashboard、ops detail、ingestion 页面已展示平台失败类别、provider 状态和来源同步状态。

## 进行中

- Phase 06 余项收尾：编辑工作台 diff 可视化细节、历史详情页与前端测试环境收敛。
- Phase 07 加固与生产就绪：`telegram` 真实发布 MVP、真实来源连接器认证 / 分页 / 异常恢复、平台与来源限流、ops 告警细化。

## 待实现

1. 更完整的真实平台限流、认证刷新与告警治理。
2. 真实 LLM provider、embedding 去重与召回。
3. 更完整的编辑协作治理和审计 UI。
4. 生产化部署、监控、备份与 Runbook。

## 备注

- 当前状态文档描述的是“主线已经实现到哪里”。
- 若某条开发分支领先于主线，以该分支代码和测试结果为准。