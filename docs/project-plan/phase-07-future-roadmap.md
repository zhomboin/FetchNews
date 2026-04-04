# FetchNews Phase 07 路线、进度与下一步

## 目标

在现有内部闭环基础上，接入真实发布平台和真实来源连接器，形成“可提交、可回写、可重试、可观测”的外部真实能力闭环。

## 合并状态

截至 2026-04-04，Phase 07 Task 1 到 Task 5 已经合并到主线。当前文档用于描述“已完成的首轮能力”和“下一轮加固重点”。

## 进度快照

| Task | 内容 | 状态 |
| --- | --- | --- |
| Task 1 | 数据契约和配置基线 | 已完成 |
| Task 2 | 首个真实发布平台闭环 | 已完成 |
| Task 3 | 其余平台适配骨架与 ops 失败归因 | 已完成 |
| Task 4 | 真实来源连接器和增量抓取 | 已完成 |
| Task 5 | API、ops 面板和前端映射 | 已完成 |

## 已完成内容

### Task 1：数据契约和配置基线

- `Settings` 增加真实平台接入配置。
- `publish_jobs` 增加 `dispatch_key`、`failure_category`、`last_provider_status`。
- `sources` 增加 `incremental_cursor`、`last_success_at`。
- schema、响应结构和迁移已同步。

### Task 2：首个真实发布平台闭环

- `telegram` 真实发布器骨架已接入默认 registry。
- 发布回调接口已打通。
- 发布失败分类已落到服务层。
- 重试保留 `dispatch_key`，支持幂等重发。

### Task 3：其余平台适配骨架与 ops 治理

- `wechat`、`x` 增加占位真实发布器。
- ops 汇总从按原始错误信息聚合升级为按 `failure_category` 聚合。
- 平台指标增加最近失败类别字段，便于 drill-down。

### Task 4：真实来源连接器和增量抓取

- 新增 `GitHubReleasesConnector`。
- 新增 `HuggingFacePapersConnector`。
- 新增 `PapersWithCodeConnector`。
- 连接器支持返回 `next_cursor`。
- 采集成功后回写 `incremental_cursor` 与 `last_success_at`。
- 原始快照统一进入 `raw_items.payload.snapshot`。

### Task 5：API、ops 面板和前端映射

- `/ops/summary` 已暴露 `last_failure_category`。
- `/sources` 已暴露 `incremental_cursor`、`last_success_at`。
- `web/src/lib/api.ts` 已补齐前端字段映射。
- ops dashboard、ops detail、ingestion 页面已展示 Phase 07 的平台和来源健康状态。

## 当前验收状态

### 已满足

- 至少 1 个真实发布平台闭环：
  - `telegram` 已具备提交、回调、结果写回和幂等重试骨架。
- 至少 3 类真实来源连接器进入 `raw_items`：
  - `GitHub Releases`
  - `Hugging Face Papers`
  - `Papers with Code`
- 发布失败后可幂等重试且不重复提交：
  - 后端测试已覆盖。
- 平台失败归因进入 ops 汇总：
  - 已完成。
- API 与前端已能消费并展示平台失败分类和来源同步状态：
  - 已完成。

### 尚未满足

- 更完整的外部认证刷新、平台限流和告警治理。
- 把 `wechat / x` 从占位真实发布器升级为真实 API 实现。
- 对真实连接器补更强的异常恢复和生产流量保护。

## 当前建议

1. 先评估哪些真实平台和真实来源已经具备进入小规模生产流量的条件。
2. 优先加固限流、认证和异常恢复，再扩大真实接入范围。
3. 完成后再评估 Phase 08 的真实 LLM provider 接入。

## 下一轮加固重点

1. `telegram` 真实发布 MVP：
   - 从骨架提交升级到真实平台请求
   - 保留 callback / 轮询 / 幂等重试闭环
2. 真实来源连接器生产边界：
   - GitHub token、分页和缓存头
   - Hugging Face HTML 结构变化时的保守回退
   - Papers with Code 分页与异常恢复
3. 平台与来源级限流、重试和 ops 告警：
   - 平台级调度窗口
   - 来源级失败告警
   - 更明确的 Runbook 和小流量验收标准