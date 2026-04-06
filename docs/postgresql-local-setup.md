# 本地 PostgreSQL 配置说明

本文档说明当前项目如何在本地使用 `PostgreSQL`、在哪里配置、需要手工执行哪些初始化 `SQL`，以及它和 `Alembic`、应用初始化之间的边界。

## 1. PostgreSQL 在哪里配置

当前实际生效的数据库配置项是：

- `APP_DATABASE_URL`

常见位置：

- 项目根目录的 `.env`
- `docker-compose.yml` 中传入的环境变量
- 本地手动启动命令中覆盖的环境变量

推荐的本地 `.env` 写法：

```env
APP_DATABASE_URL=postgresql+psycopg://fetchnews:fetchnews@localhost:5432/fetchnews
APP_DATABASE_BOOTSTRAP_MODE=skip
```

含义：

- 使用宿主机本地 `PostgreSQL`。
- 应用不再自行创建 `schema`，而是交给 Alembic。

## 2. Compose 里如何连接宿主机 PostgreSQL

当前 `docker compose` 已调整为连接宿主机数据库，不再默认启动 PostgreSQL 容器。

容器内推荐使用：

```env
APP_DATABASE_URL=postgresql+psycopg://fetchnews:fetchnews@host.docker.internal:5432/fetchnews
```

这表示：

- `api`、`worker`、`beat` 都会连接宿主机 PostgreSQL。
- `redis` 仍然可以由 Compose 启动。
- 启动前需要确认宿主机 PostgreSQL 已经运行。

## 3. 本轮必须手工执行的初始化 SQL

### 3.1 全新本地 PostgreSQL

如果本地 PostgreSQL 还没有准备好，先在 `psql` 中执行：

```sql
CREATE USER fetchnews WITH PASSWORD 'fetchnews';
CREATE DATABASE fetchnews OWNER fetchnews;
GRANT ALL PRIVILEGES ON DATABASE fetchnews TO fetchnews;
\connect fetchnews
GRANT ALL ON SCHEMA public TO fetchnews;
ALTER SCHEMA public OWNER TO fetchnews;
```

这些 `SQL` 的作用：

- 创建数据库用户 `fetchnews`。
- 创建数据库 `fetchnews`。
- 将数据库所有权交给该用户。
- 将 `public` `schema` 权限和所有权交给该用户。

### 3.2 用户和数据库已经存在时

如果角色和数据库已经存在，只需要更新它们：

```sql
ALTER USER fetchnews WITH PASSWORD 'fetchnews';
ALTER DATABASE fetchnews OWNER TO fetchnews;
\connect fetchnews
GRANT ALL ON SCHEMA public TO fetchnews;
ALTER SCHEMA public OWNER TO fetchnews;
```

## 4. 哪些内容不应该手工写 SQL

本轮不需要手动执行建表 `SQL`。

原因：

- 业务表结构统一由 Alembic 创建。
- 迁移命令是：

```bash
alembic upgrade head
```

因此，手工 `SQL` 仅限：

- 角色创建。
- 数据库创建。
- `schema` 权限与所有权配置。

业务表、索引以及后续 `schema` 变更都应该进入 Alembic migration。

## 5. Bootstrap Admin 是否需要手工 SQL

不需要。

当前管理员账户由应用启动阶段根据环境变量自动补齐，相关变量包括：

- `APP_BOOTSTRAP_ADMIN_USERNAME`
- `APP_BOOTSTRAP_ADMIN_PASSWORD`
- `APP_BOOTSTRAP_ADMIN_DISPLAY_NAME`

也就是说：

- 数据库角色和库需要你手工准备。
- 应用表结构由 Alembic 创建。
- 管理员账户由应用初始化逻辑自动创建或更新。

## 6. 推荐启动顺序

### 使用 Compose

```bash
docker compose run --rm migrate
docker compose up api worker beat web redis
```

### 手动启动

```bash
alembic upgrade head
uvicorn fetchnews.main:app --host 0.0.0.0 --port 8000 --reload
celery -A fetchnews.tasks.worker.celery_app worker --loglevel=info
celery -A fetchnews.tasks.worker.celery_app beat --loglevel=info
cd web
npm run dev -- --host 0.0.0.0
```

## 7. 如何验证 PostgreSQL 已正确接入

执行迁移后，可以在 `psql` 中检查：

```sql
\dt
SELECT version_num FROM alembic_version;
SELECT username, role, is_active FROM users ORDER BY id;
```

预期结果：

- 能看到业务表。
- `alembic_version` 有当前版本号。
- `users` 表中有 bootstrap 管理员账户。

## 8. 当前为什么仍然保留 SQLite

当前项目依然支持 `SQLite` 作为测试或临时路径，但本地正式开发推荐 `PostgreSQL`，原因是：

- 当前工作流已经涉及 Alembic、鉴权、审计和更接近生产的 `schema` 演进。
- 后续还会引入更复杂的编辑历史、模板和发布记录。
- `PostgreSQL` 才是当前仓库的主路径。

## 9. 文档约束

- `PostgreSQL` 配置文档统一使用中文。
- 可以保留 `SQL`、环境变量和工具命令原文，但说明必须使用中文。

## 10. 2026-04-03 编辑工作台迁移说明

本轮新增了两条 Alembic migration：

- `20260403_0002_editorial_workbench.py`
- `20260403_0003_article_draft_templates.py`

它们负责创建和扩展以下结构：

- `digest_templates`
- `article_revisions`
- `article_blocks`
- `editorial_actions`
- `article_drafts.template_id`
- `article_drafts.active_revision_id`

这一轮**不需要新增手工 SQL**。仍然只需要完成：

1. `PostgreSQL` 角色、数据库、`schema` 权限初始化。
2. 执行 `alembic upgrade head`。

也就是说，编辑工作台相关表和字段全部由 Alembic 创建，不要手工在 `psql` 里补 `DDL`。
