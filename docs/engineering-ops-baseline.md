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
- Phase 07 callback 写回的审计事件 `publish.callback`

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
- `APP_TELEGRAM_BOT_TOKEN`
- `APP_X_BEARER_TOKEN`
- `APP_WECHAT_APP_ID`

约束：

- `development` / `test` 环境默认 callback secret 为 `fetchnews-dev-callback-secret`
- 非 `development/test` 环境必须显式设置 `APP_PUBLISH_CALLBACK_SECRET`
- 如果未设置，应用在启动阶段直接失败

### 告警与监控

已实现：

- `ops summary` 中的告警摘要
- 最近失败分组
- 平台指标
- 栏目审核指标
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

## 仍待补齐的能力

尚未完全完成：

- 用户管理 UI 与密码重置流程
- 审计日志查看 UI 与导出接口
- 邮件、Webhook、Slack 等外部告警通道
- `Prometheus / Grafana` 或 `Sentry` 等生产监控栈
- 更完整的真实平台限流、认证刷新与告警治理
- `wechat / x` 的真实 API 实现

## 2026-04-03 迁移增量

工程基线已增加编辑工作台相关的数据库演进能力，当前 migration 集包括：

- `20260401_0001_initial_schema.py`
- `20260403_0002_editorial_workbench.py`
- `20260403_0003_article_draft_templates.py`

新增覆盖的结构：

- `digest_templates`
- `article_revisions`
- `article_blocks`
- `editorial_actions`
- `article_drafts.template_id`
- `article_drafts.active_revision_id`

这一轮没有新增需要人工执行的业务 SQL，数据库层面的新增动作继续统一走 Alembic。

## 2026-04-04 Phase 07 增量

本轮新增的工程与运维面能力：

- 发布 callback 入口的 secret 校验
- 发布 callback 的审计落库
- 真实来源连接器的增量游标字段与回写
- 前后端对平台失败类别和来源同步状态的可视化

## 文档语言约束

- 工程与运维说明统一使用中文撰写
- 保留英文工具名时，需要放在中文语义中解释清楚