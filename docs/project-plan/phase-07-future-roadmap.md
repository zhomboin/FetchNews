# FetchNews Phase 07 路线、进度与下一步

## 目标

在现有内部闭环基础上，接入真实发布平台和真实来源连接器，形成“可提交、可回写、可重试、可观测”的外部真实能力闭环，并补齐最小生产边界。

## 状态

截至 2026-04-06：

- Phase 07 主线 Task 1-5 已合并
- Phase 07 加固与生产就绪 Task 1-5 已在当前分支完成

当前文档同时描述“已完成的首轮能力”和“已完成的加固项”。

## 主线 Task 1-5 回顾

| Task | 内容 | 状态 |
| --- | --- | --- |
| Task 1 | 数据契约和配置基线 | 已完成 |
| Task 2 | 首个真实发布平台骨架闭环 | 已完成 |
| Task 3 | 其余平台适配骨架与 ops 失败归因 | 已完成 |
| Task 4 | 真实来源连接器与增量抓取 | 已完成 |
| Task 5 | API、ops 面板与前端映射 | 已完成 |

## 加固与生产就绪 Task 1-5 回顾

| Task | 内容 | 状态 |
| --- | --- | --- |
| Task 1 | 同步主线并建立执行基线 | 已完成 |
| Task 2 | `telegram` 真实发布 MVP | 已完成 |
| Task 3 | 真实来源连接器认证、分页与异常恢复 | 已完成 |
| Task 4 | 平台限流、来源重试和 ops 告警 | 已完成 |
| Task 5 | 文档、Runbook 和小流量验收 | 已完成 |

## 已完成能力

### 发布侧

- `telegram` 真实发布 MVP
- callback secret 校验
- callback 审计事件
- 轮询超时收敛
- 失败分类 `failure_category`
- 平台冷却窗口限流

### 来源侧

- `GitHub Releases`
- `Hugging Face Papers`
- `Papers with Code`
- 认证头、分页游标、锚点回退
- 来源最小重试
- cursor 保守推进
- 原始快照落库

### ops 与前端

- 平台最近失败类别
- source 重复失败告警
- 来源同步状态
- 失败分组与建议项
- 前端 ops 和 ingestion 页面展示健康信号

## 当前验收结论

### 已满足

- 至少 1 个真实发布平台具备受控闭环：
  - `telegram`
- 至少 3 类真实来源连接器能够进入 `raw_items`
  - `GitHub Releases`
  - `Hugging Face Papers`
  - `Papers with Code`
- 发布失败后可幂等重试且不重复提交
- 平台失败分类和 source 告警可以进入 ops 汇总

### 仍未满足

- `wechat / x` 还不是可直接上线的真实 API 实现
- 平台限流当前是服务级冷却窗口，不是分布式限流
- 更完整的认证刷新、外部告警通道和生产监控栈仍未接入

## 真实平台最小上线条件

1. 显式配置 `APP_PUBLISH_CALLBACK_SECRET`
2. 显式配置目标平台凭证
3. 同一轮只启用一个真实发布平台
4. 验证 `dispatch -> callback/poll -> result writeback -> retry`
5. 验证失败后平台冷却窗口生效
6. 验证 ops 中能看到失败分类与 source 告警

## 小流量验收清单

建议按以下步骤执行：

1. 仅启用 `telegram`
2. 仅启用 `github-openai-releases`
3. 保持默认重试次数与冷却窗口
4. 运行 24 小时
5. 观察：
   - 平台失败分类
   - source 告警数
   - `incremental_cursor` 推进
   - callback / poll 收敛情况
6. 稳定后再加入 `hf-daily` 和 `paperswithcode-latest`

## 下一步建议

1. 先在小流量环境验证这条加固分支
2. 稳定后择机合并
3. 再评估下一轮工作：
   - `wechat / x` 真实 API 接入
   - 更强的限流与认证刷新
   - Phase 08 真实 LLM provider 与 embedding
