# 工程与运维基线

本文档总结当前仓库已经具备的工程与运维补齐能力。

## 本轮基线包含的内容

### Alembic 迁移

已实现：

- Alembic 配置与环境文件
- 对应当前 SQLAlchemy 模型集的首个 schema migration
- 显式区分 `SQLite` 测试引导与 PostgreSQL 迁移流程

关键文件：

- [alembic.ini](/D:/Code/Project/FetchNews/alembic.ini)
- [alembic/env.py](/D:/Code/Project/FetchNews/alembic/env.py)
- [alembic/versions/20260401_0001_initial_schema.py](/D:/Code/Project/FetchNews/alembic/versions/20260401_0001_initial_schema.py)
- [fetchnews/db/session.py](/D:/Code/Project/FetchNews/fetchnews/db/session.py)

本轮 SQL 边界：

- 手动 SQL 仅限 PostgreSQL 角色、数据库与 schema 权限初始化
- 业务表结构统一通过 Alembic 创建，不手工粘贴 DDL 到 `psql`
- 具体 SQL 见 [docs/postgresql-local-setup.md](/D:/Code/Project/FetchNews/docs/postgresql-local-setup.md)

### PostgreSQL 正式化

已实现：

- 宿主机 PostgreSQL 作为推荐本地数据库路径
- Compose 不再默认拉起 PostgreSQL 容器
- 显式支持 `APP_DATABASE_BOOTSTRAP_MODE`
- 为 Compose 流程提供 `migrate` 服务

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
- 通过环境变量引导创建管理员账号
- 对关键写操作持久化审计日志

当前角色：

- `viewer`：只读 API 访问
- `editor`：审核、生成、发布和手动运维操作
- `admin`：完整权限，当前用于 bootstrap 登录

关键文件：

- [fetchnews/core/security.py](/D:/Code/Project/FetchNews/fetchnews/core/security.py)
- [fetchnews/core/audit.py](/D:/Code/Project/FetchNews/fetchnews/core/audit.py)
- [fetchnews/main.py](/D:/Code/Project/FetchNews/fetchnews/main.py)
- [fetchnews/models.py](/D:/Code/Project/FetchNews/fetchnews/models.py)

### 告警与监控

已实现：

- ops summary 中的告警
- 最近失败分组
- 平台指标
- 栏目审核指标
- 建议列表
- 前端 ops 告警卡片与 drill-down 支持

关键文件：

- [fetchnews/ops/service.py](/D:/Code/Project/FetchNews/fetchnews/ops/service.py)
- [web/src/features/ops/ops-dashboard-page.tsx](/D:/Code/Project/FetchNews/web/src/features/ops/ops-dashboard-page.tsx)

### 前端测试基线

已实现：

- `Vitest` 测试运行器
- `Testing Library` 测试环境
- API 鉴权头测试
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
- 长生命周期 PostgreSQL 环境的分阶段迁移策略

## 文档语言约束

- 工程与运维说明统一使用中文撰写
- 保留英文工具名时需配合中文语义说明