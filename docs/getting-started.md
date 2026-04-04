# 启动指南

本文档说明如何在本地启动当前的 `FetchNews` 栈，并验证仓库中已经落地的能力。

## 当前可验证的能力

当前仓库已经可以验证以下端到端行为：

- 后端 API 可以正常启动并响应健康检查
- 宿主机 `PostgreSQL` 可作为推荐本地数据库
- Alembic 可以创建并升级当前 schema
- 开启鉴权后，登录可以保护后台控制台
- 白名单来源可以手动或定时触发采集
- `normalized_items`、`stories`、草稿与发布任务都可以查询
- 发布任务支持创建、`dispatch`、`poll`、结果写回、callback 回写与重试
- ops 汇总接口可以返回告警、失败分组以及平台 / 栏目指标

## 推荐的本地依赖

必需服务：

- 宿主机 `PostgreSQL`
- `Redis`，可运行在宿主机或 Compose 中

推荐启动顺序：

```bash
docker compose run --rm migrate
docker compose up api worker beat web redis
```

重要说明：

- Compose 不再默认拉起 `PostgreSQL` 容器
- 应用容器通过 `host.docker.internal` 访问宿主机 `PostgreSQL`
- 在 `api`、`worker`、`beat` 启动前，应先执行 migration

## 环境变量配置

在仓库根目录创建 `.env`，并从 [.env.example](/D:/Code/Project/FetchNews/.worktrees/phase-07-task-1/.env.example) 开始调整。

最小本地开发示例：

```env
APP_DATABASE_URL=postgresql+psycopg://fetchnews:fetchnews@localhost:5432/fetchnews
APP_DATABASE_BOOTSTRAP_MODE=skip
APP_REDIS_URL=redis://localhost:6379/0
APP_AUTH_ENABLED=true
APP_AUTH_SECRET_KEY=change-this-before-exposing-the-console
APP_BOOTSTRAP_ADMIN_USERNAME=admin
APP_BOOTSTRAP_ADMIN_PASSWORD=admin-secret
APP_PUBLISH_CALLBACK_SECRET=fetchnews-dev-callback-secret
VITE_API_BASE=http://localhost:8000
```

如果要验证 Phase 07 的真实发布器骨架，还需要补以下变量：

```env
APP_PUBLISH_REAL_PLATFORM=telegram
APP_TELEGRAM_BOT_TOKEN=replace-with-your-telegram-token
```

也可以切换到其他平台骨架：

```env
APP_PUBLISH_REAL_PLATFORM=x
APP_X_BEARER_TOKEN=replace-with-your-x-token
```

```env
APP_PUBLISH_REAL_PLATFORM=wechat
APP_WECHAT_APP_ID=replace-with-your-wechat-app-id
```

关于 callback secret：

- `development` 和 `test` 环境默认使用 `fetchnews-dev-callback-secret`
- 非 `development/test` 环境必须显式设置 `APP_PUBLISH_CALLBACK_SECRET`
- 如果未配置，应用会在启动阶段直接失败，而不是等 callback 时才暴露问题

## 运行迁移前必须执行的 SQL

如果本地 `PostgreSQL` 还没有完成初始化，请先在 `psql` 中执行：

```sql
CREATE USER fetchnews WITH PASSWORD 'fetchnews';
CREATE DATABASE fetchnews OWNER fetchnews;
GRANT ALL PRIVILEGES ON DATABASE fetchnews TO fetchnews;
\connect fetchnews
GRANT ALL ON SCHEMA public TO fetchnews;
ALTER SCHEMA public OWNER TO fetchnews;
```

如果角色和数据库已经存在，则执行更新 SQL：

```sql
ALTER USER fetchnews WITH PASSWORD 'fetchnews';
ALTER DATABASE fetchnews OWNER TO fetchnews;
\connect fetchnews
GRANT ALL ON SCHEMA public TO fetchnews;
ALTER SCHEMA public OWNER TO fetchnews;
```

## 不使用 Compose 的手动启动方式

1. 安装后端依赖

```bash
python -m pip install -e .[dev]
```

2. 安装前端依赖

```bash
cd web
npm install
cd ..
```

3. 如果数据库尚未准备，执行上文的 `PostgreSQL` 初始化 SQL

4. 执行迁移

```bash
alembic upgrade head
```

5. 启动后端 API

```bash
uvicorn fetchnews.main:app --host 0.0.0.0 --port 8000 --reload
```

6. 启动 worker

```bash
celery -A fetchnews.tasks.worker.celery_app worker --loglevel=info
```

7. 启动 beat

```bash
celery -A fetchnews.tasks.worker.celery_app beat --loglevel=info
```

8. 启动前端

```bash
cd web
npm run dev -- --host 0.0.0.0
```

## 验证清单

### 1. 健康检查

打开 [http://localhost:8000/healthz](http://localhost:8000/healthz)。

预期返回：

```json
{"status":"ok","service":"FetchNews"}
```

### 2. 鉴权配置与登录

打开 [http://localhost:8000/auth/config](http://localhost:8000/auth/config)。

当鉴权开启时，预期返回：

```json
{"auth_enabled":true}
```

然后打开 [http://localhost:5173](http://localhost:5173)，使用 bootstrap 管理员账户登录，确认可以进入后台而不是停留在登录页。

### 3. 来源目录

完成登录后，访问 [http://localhost:8000/sources](http://localhost:8000/sources)，或通过前端携带 token 调用。

预期可见已启用来源，例如：

- `github-trending`
- `arxiv-cs-ai`
- `openai-blog`
- `x-allowlist`

### 4. 手动采集

在前端打开 [http://localhost:5173/ingestion](http://localhost:5173/ingestion)，触发一次采集。

预期行为：

- 创建一条新的采集批次
- 列表自动出现新批次
- 某个来源失败不会阻断整批采集，错误能在详情中看到

### 5. story 审核与草稿生成

打开 [http://localhost:5173/stories](http://localhost:5173/stories)，审核通过一个或多个 story；再到 [http://localhost:5173/articles](http://localhost:5173/articles) 生成日报、周报或月报。

预期行为：

- 草稿被创建或重建
- 所选 story 范围被保留
- `wechat`、`x`、`telegram` 平台变体可查看

### 6. 发布与运维验证

在草稿中心创建发布任务，然后返回 [http://localhost:5173](http://localhost:5173) 查看运维首页。

预期行为：

- 发布任务能在草稿中心和 `/publish-jobs` 中看到
- 失败任务可以重试
- ops 面板可以展示告警、失败分组和平台指标

如果要验证 callback 写回，还需要向 `/publish-jobs/callback/{platform}` 发送请求，并带上 header：

```text
X-FetchNews-Callback-Secret: <your secret>
```

开发环境默认值为：

```text
X-FetchNews-Callback-Secret: fetchnews-dev-callback-secret
```

### 7. 审计验证

外部 callback 写回也会进入审计日志，事件名为 `publish.callback`。如果你在本地调试 callback，应该能看到对应的发布任务、平台和 provider 状态被记录下来。

## 验证命令

在声称环境健康前，至少执行：

```bash
python -m pytest
```

```bash
cd web
npm run test:run
```

```bash
cd web
npm run build
```

## 文档语言约束

- 启动与验证文档统一使用中文
- 保留英文命令、环境变量和接口路径，但说明文字必须使用中文
