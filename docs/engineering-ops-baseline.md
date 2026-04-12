# 工程与运维基线

本文档总结当前仓库已经具备的工程与运维能力，以及仍需继续补齐的部分。

## 本轮基线包含的内容

### Alembic 迁移

已实现：

- Alembic 配置与环境文件
- 对应当前 SQLAlchemy 模型集的 schema migration
- 显式区分 `SQLite` 测试引导与 `PostgreSQL` 迁移流程

关键文件：

- [alembic.ini](/D:/Code/Project/FetchNews/alembic.ini)
- [alembic/env.py](/D:/Code/Project/FetchNews/alembic/env.py)
- [alembic/versions/20260401_0001_initial_schema.py](/D:/Code/Project/FetchNews/alembic/versions/20260401_0001_initial_schema.py)
- [alembic/versions/20260403_0002_editorial_workbench.py](/D:/Code/Project/FetchNews/alembic/versions/20260403_0002_editorial_workbench.py)
- [alembic/versions/20260403_0003_article_draft_templates.py](/D:/Code/Project/FetchNews/alembic/versions/20260403_0003_article_draft_templates.py)
- [alembic/versions/20260404_0004_phase07_contract_fields.py](/D:/Code/Project/FetchNews/alembic/versions/20260404_0004_phase07_contract_fields.py)
- [fetchnews/db/session.py](/D:/Code/Project/FetchNews/fetchnews/db/session.py)

本轮 SQL 边界：

- 手动 SQL 仅限 `PostgreSQL` 角色、数据库和 `schema` 权限初始化
- 业务表结构统一通过 Alembic 创建，不手工粘贴 DDL 到 `psql`
- 具体 SQL 见 [docs/postgresql-local-setup.md](/D:/Code/Project/FetchNews/docs/postgresql-local-setup.md)

### PostgreSQL 正式化

已实现：

- 宿主机 `PostgreSQL` 作为推荐本地数据库路径
- `docker compose` 不再默认拉起 `PostgreSQL` 容器
- 显式支持 `APP_DATABASE_BOOTSTRAP_MODE`
- Compose 流程提供 `migrate` 服务

关键文件：

- [docker-compose.yml](/D:/Code/Project/FetchNews/docker-compose.yml)
- [.env.example](/D:/Code/Project/FetchNews/.env.example)
- [docs/postgresql-local-setup.md](/D:/Code/Project/FetchNews/docs/postgresql-local-setup.md)

### 登录、权限与审计

已实现：

- 鉴权开关接口：`GET /auth/config`
- 登录接口：`POST /auth/login`
- 当前用户接口：`GET /auth/me`
- 受保护 API 的角色权限控制
- 通过环境变量引导创建 bootstrap 管理员账户
- 关键写操作审计日志
- callback 写回的审计事件 `publish.callback`

当前角色：

- `viewer`：只读 API 访问
- `editor`：审核、生成、发布和手动运维操作
- `admin`：完整权限，当前主要用于 bootstrap 登录

关键文件：

- [fetchnews/core/security.py](/D:/Code/Project/FetchNews/fetchnews/core/security.py)
- [fetchnews/core/audit.py](/D:/Code/Project/FetchNews/fetchnews/core/audit.py)
- [fetchnews/main.py](/D:/Code/Project/FetchNews/fetchnews/main.py)
- [fetchnews/models.py](/D:/Code/Project/FetchNews/fetchnews/models.py)

### Phase 07 配置基线

已实现：

- `APP_PUBLISH_REAL_PLATFORM`
- `APP_PUBLISH_CALLBACK_SECRET`
- `APP_GITHUB_TOKEN`
- `APP_TELEGRAM_BOT_TOKEN`
- `APP_TELEGRAM_CHAT_ID`
- `APP_X_BEARER_TOKEN`
- `APP_WECHAT_APP_ID`
- `APP_PUBLISH_RATE_LIMIT_WINDOW_SECONDS`
- `APP_SOURCE_RETRY_ATTEMPTS`
- `APP_SOURCE_FAILURE_ALERT_THRESHOLD`

约束：

- `development` / `test` 环境默认 callback secret 为 `fetchnews-dev-callback-secret`
- 非 `development/test` 环境必须显式设置 `APP_PUBLISH_CALLBACK_SECRET`
- 如果未设置，应用在启动阶段直接失败
- 如果启用 `github-openai-releases` 等 GitHub API 来源，必须显式设置 `APP_GITHUB_TOKEN`

### 发布基线

已实现：

- `telegram` 真实发布 MVP
- `dispatch_key` 幂等键
- callback 写回与轮询收敛
- 发布失败分类 `failure_category`
- 平台 `rate_limit` 失败后的冷却回避窗口
- 失败后按任务粒度重试

关于"平台冷却窗口限流"的准确语义：

- 它**不是**按秒主动节流的令牌桶
- 实际行为：一旦某个平台最近一次失败被 `classify_publish_failure` 归类为
  `rate_limit`，在 `APP_PUBLISH_RATE_LIMIT_WINDOW_SECONDS` 时间内，
  `dispatch_due_publish_jobs` 会跳过该平台上的新任务，并将这些被跳过的任务
  的 `last_provider_status` 标记为 `rate_limited`
- 如果从未发生 `rate_limit` 分类的失败，成功任务之间不会有任何节流
- 实现入口：`fetchnews/publishing/service.py::_platform_rate_limit_window_open`

当前边界：

- `wechat / x` 仍是适配器骨架，不是可直接上线的真实平台集成
- 平台限流当前为服务内失败回避窗口，不是分布式令牌桶

关键文件：

- [fetchnews/publishing/real_publishers.py](/D:/Code/Project/FetchNews/fetchnews/publishing/real_publishers.py)
- [fetchnews/publishing/service.py](/D:/Code/Project/FetchNews/fetchnews/publishing/service.py)
- [fetchnews/publishing/platform_errors.py](/D:/Code/Project/FetchNews/fetchnews/publishing/platform_errors.py)

### 来源采集基线

已实现：

- `GitHub Releases`
- `Hugging Face Papers`
- `Papers with Code`
- 真实连接器增量游标
- 来源最小重试
- 失败时不覆盖旧 `incremental_cursor`
- 原始快照统一进入 `raw_items.payload.snapshot`

当前边界：

- `GitHub` 当前支持 Bearer token，请求级认证仍较轻量
- `Hugging Face` 仍依赖 HTML 解析，需要继续观察结构变化
- `Papers with Code` 当前已优先使用 API `next`，但还未做更重的生产保护

关键文件：

- [fetchnews/sources/real_connectors.py](/D:/Code/Project/FetchNews/fetchnews/sources/real_connectors.py)
- [fetchnews/sources/service.py](/D:/Code/Project/FetchNews/fetchnews/sources/service.py)
- [fetchnews/sources/catalog.py](/D:/Code/Project/FetchNews/fetchnews/sources/catalog.py)

### 告警与监控

已实现：

- `ops summary` 中的告警摘要
- 最近失败分组
- 平台指标
- 栏目审核指标
- source 重复失败告警
- 建议列表
- 前端 `ops` 仪表盘的 drill-down 展示

关键文件：

- [fetchnews/ops/service.py](/D:/Code/Project/FetchNews/fetchnews/ops/service.py)
- [web/src/features/ops/ops-dashboard-page.tsx](/D:/Code/Project/FetchNews/web/src/features/ops/ops-dashboard-page.tsx)

### 前端测试基线

已实现：

- `Vitest` 测试运行器
- `Testing Library` 测试环境
- API 映射测试
- 登录表单提交流程测试

命令：

```bash
cd web
npm run test:run
```

关键文件：

- [web/package.json](/D:/Code/Project/FetchNews/web/package.json)
- [web/vite.config.ts](/D:/Code/Project/FetchNews/web/vite.config.ts)
- [web/src/lib/api.test.ts](/D:/Code/Project/FetchNews/web/src/lib/api.test.ts)
- [web/src/features/auth/login-page.test.tsx](/D:/Code/Project/FetchNews/web/src/features/auth/login-page.test.tsx)

## 小流量运行准则

建议当前只在小流量条件下开放真实能力：

1. 真实发布平台仅启用 `telegram`
2. 真实来源仅启用：
   - `github-openai-releases`
   - `hf-daily`
   - `paperswithcode-latest`
3. 保持来源重试次数为 `2`
4. 保持平台 `rate_limit` 失败冷却窗口为 `300` 秒
5. 每次扩大范围前至少观察 24 小时

## 仍待补齐的能力

尚未完全完成：

- 用户管理 UI 与密码重置流程
- 审计日志查看 UI 与导出接口
- 邮件、Webhook、Slack 等外部告警通道
- `Prometheus / Grafana` 或 `Sentry` 等生产监控栈
- 更完整的真实平台限流、认证刷新与告警治理
- `wechat / x` 的真实 API 实现
- 分布式 worker 场景下更强的限流状态共享

## 2026-04-06 Phase 07 加固增量

本轮新增的工程与运维能力：

- `telegram` 真实发布 MVP
- 真实来源连接器认证头、分页与保守回退
- 发布平台 `rate_limit` 失败冷却回避窗口
- 来源最小重试
- source 重复失败告警
- 小流量验收 Runbook

## 文档语言约束

- 工程与运维说明统一使用中文撰写
- 保留英文工具名时，需要放在中文语义中解释清楚
