# FetchNews 当前状态

## 概览

截至 2026-04-06，主线已经具备从来源采集、标准化、聚类、草稿生成、人工审核，到发布回写和 ops 观测的完整内部闭环。

主线已完成 Phase 07 首轮 Task 1-5 和加固与生产就绪 Task 1-5，重点补齐了 `telegram` 真实发布 MVP、真实来源连接器加固、平台冷却窗口限流、来源重试和 source 告警。

## 已完成

- 后端与前端基础骨架
- 来源采集、标准化、聚类与 story 审核
- 日报、周报、月报草稿生成与平台短帖变体
- 审核工作台、块级编辑、版本恢复与混合重建
- 发布任务、执行、轮询、结果回写与失败重试
- 来源治理、栏目势能、平台互动反馈与 ops 汇总
- PostgreSQL、Alembic、登录、权限、审计与基础测试基线

## Phase 07 首轮已完成范围

### Task 1：数据契约和配置基线

- 新增真实平台接入配置字段
- 为 `publish_jobs` 增加 `dispatch_key`、`failure_category`、`last_provider_status`
- 为 `sources` 增加 `incremental_cursor`、`last_success_at`
- 完成对应 schema、响应结构和迁移

### Task 2：首个真实发布平台闭环

- 打通 `telegram` 发布骨架
- 打通 `/publish-jobs/callback/{platform}` 回调写回
- 发布失败分类进入服务层
- 幂等重试保留 `dispatch_key`

### Task 3：其余平台适配骨架与 ops 失败归因

- 为 `wechat`、`x` 增加占位真实发布器
- ops 从原始报错文案聚合升级为按 `failure_category` 聚合
- 平台指标增加 `last_failure_category`

### Task 4：真实来源连接器与增量抓取

- 新增 `GitHubReleasesConnector`
- 新增 `HuggingFacePapersConnector`
- 新增 `PapersWithCodeConnector`
- 支持 `next_cursor`
- 回写 `incremental_cursor` 与 `last_success_at`
- 原始快照进入 `raw_items.payload.snapshot`

### Task 5：API、ops 面板与前端映射

- `/ops/summary` 暴露平台最近失败类别
- `/sources` 暴露来源同步游标和最近成功时间
- 前端 `api.ts` 已完成字段映射
- ops dashboard、ops detail、ingestion 页面已展示健康状态

## Phase 07 加固与生产就绪已完成范围

### Task 1：同步主线并建立执行基线

- 基于主线建立隔离 worktree
- 跑通主线全量回归
- 同步主线状态文档

### Task 2：`telegram` 真实发布 MVP

- 真实调用 `sendMessage`
- 真实写回 `message_id`
- 提交异常收口为失败任务
- callback、轮询、重试继续保留闭环

### Task 3：真实来源连接器认证、分页与异常恢复

- GitHub 支持认证头
- Hugging Face 支持锚点回退
- Papers with Code 优先使用 API `next`
- 成功时推进 cursor
- 无新 cursor 时保留旧值

### Task 4：调度限流、重试和 ops 告警

- 平台冷却窗口限流
- 来源最小重试
- source 重复失败告警
- 配置项支持：
  - `APP_PUBLISH_RATE_LIMIT_WINDOW_SECONDS`
  - `APP_SOURCE_RETRY_ATTEMPTS`
  - `APP_SOURCE_FAILURE_ALERT_THRESHOLD`

### Task 5：文档、Runbook 与小流量验收

- 启动指南同步真实平台与真实来源要求
- 工程运维基线同步限流、重试与告警
- 内容来源文档同步当前推荐小流量来源组合
- 路线和状态文档同步加固完成状态

## 当前推荐运行方式

当前建议采用小流量、单平台、少来源的受控运行方式：

1. 真实发布平台仅启用 `telegram`
2. 真实来源仅启用：
   - `github-openai-releases`
   - `hf-daily`
   - `paperswithcode-latest`
3. 保持冷却窗口和重试参数为默认值
4. 先观察 24 小时，再决定是否扩大范围

## 待实现

1. 更完整的真实平台限流、认证刷新与告警治理
2. `wechat / x` 的真实 API 实现
3. 真实 LLM provider、embedding 去重与召回
4. 更完整的编辑协作治理与审计 UI
5. 生产化部署、监控、备份与 Runbook 收尾

## 备注

- 当前状态文档描述的是主线已完成到哪里
- 若后续存在新的开发分支，以主线状态为基准，再单独标注分支增量
