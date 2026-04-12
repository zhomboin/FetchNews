# 后端待修复问题清单

本文档记录 2026-04-11 对后端与环境配置的审查结果，以及对应的处理状态。

## 处理优先级与状态

### 已处理

- [x] #1 docker-compose 未提供 postgres 服务
- [x] #2 `settings.py` 默认值与 `.env.example` 不一致
- [x] #3 生产环境对默认密钥缺少强制校验
- [x] #4 `.env.example` 中含有未被 `Settings` 读取的变量
- [x] #5 "平台冷却窗口限流"文档与实现不符
- [x] #6 `retry_publish_job` 清空 `provider_payload` 丢失历史快照
- [x] #7 `_sync_article_status` 一旦有失败即把文章整体标为 FAILED
- [x] #10 占位真实发布器在日志中打印 `using placeholder real publisher for {platform}`
- [x] #12 HF 连接器在合成 `published_at` 时同时写入 `fetched_at` 与 `published_at_is_synthetic`
- [x] #13 `_filter_records_by_id` 在 cursor 未命中时回退为"全部当新条目"
- [x] #16 `/auth/login` 增加内存级 `LoginRateLimiter`（按 `(username, client_ip)` 滑动窗口）
- [x] #18 `AppState` 在 `drop_all` 前校验 DB URL 必须是 sqlite 或带 `test` 标记

### 待处理（按优先级）

#### P2

- [x] **#8** 回调端点 `/publish-jobs/callback/{platform}` 增加内存级 IP 滑动窗口限频，并在 `ops/summary` 输出 `security` 告警。
- [x] **#9** `RealTelegramPublisher` 增加 `submit_async` 异步提交入口，保留当前同步提交路径供现有调度链路使用。
- [x] **#11** `sources/service.py::_sync_sources` 改为保留原有 `source.config` 动态字段并用解析后的配置覆盖静态键。

- [x] **#14** `_fetch_with_retries` 在 429/403 重试前读取 `Retry-After` 并退避，其他错误走指数退避。
- [x] **#15** `GitHubReleasesConnector` 为 GitHub API 请求补齐 `Accept: application/vnd.github+json` 头。
- [x] **#17** 自实现 token 格式在 `security.py` 注释中明确标注为“非标准 JWT”，避免客户端误按标准 JWT 解码。

- [x] **#19** `docs/getting-started.md` 明确说明：Postgres + `bootstrap_mode=skip/auto->skip` 时，首次启动前必须先执行 `alembic upgrade head`。
- [x] **#21** `test_real_connectors.py` 增加 `httpx.MockTransport` 覆盖真实 HTTP 分支与 GitHub 请求头断言。

- [ ] **#22** `fetchnews/api/` 只含空 `__init__.py`，`main.py` ~860 行单文件堆所有路由。
  - 建议：随 Phase 08+ 拆分路由。

## 引用

- 本清单对应审查记录：`docs/current-status.md`（2026-04-11 条目）。
- 生产化部署相关修复收敛到 Phase 10。
