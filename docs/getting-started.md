# 启动与验证

本文档说明当前阶段如何在本地启动 `FetchNews`，以及如何验证已经落地的功能是否正常工作。

## 当前阶段可验证的能力

当前可以实际验证的内容包括：
- 后端 API 可启动并响应健康检查
- 来源目录可通过 `/sources` 返回
- 手动触发采集可通过 `POST /ingest/run` 执行
- 采集批次可通过 `/ingest/runs` 和 `/ingest/runs/{id}` 查询
- `Celery beat` 已具备默认采集调度配置
- React SPA 可展示采集运行列表，并可从前端手动触发采集

当前还不属于“完整验证范围”的内容：
- 真实的标准化、去重、聚类与评分
- 生产级 LLM 总结生成
- 真实的平台发布链路
- 完整的 X 平台正式接入

## 推荐启动方式

当前阶段推荐优先使用 `Docker Compose`。原因很简单：
- 启动步骤最少
- 前后端与队列进程一起拉起
- 不需要你先手工准备 PostgreSQL
- 对当前 Phase 02 验证最直接

### 方式一：Docker Compose 启动

在项目根目录执行：

```bash
docker compose up api worker beat web redis
```

启动成功后，默认地址如下：
- 后端 API：[http://localhost:8000](http://localhost:8000)
- 前端审核台：[http://localhost:5173](http://localhost:5173)
- 采集运行页：[http://localhost:5173/ingestion](http://localhost:5173/ingestion)
- Redis：`localhost:6379`

说明：
- 当前 `docker-compose.yml` 默认用 `SQLite` 作为本地快速验证数据库。
- 这只是当前阶段的低成本本地方案，不改变正式架构以 `PostgreSQL` 为目标的设计。

### 方式二：本地手动启动

如果你不想用容器，也可以手动启动。

1. 安装后端依赖：

```bash
python -m pip install -e .[dev]
```

2. 安装前端依赖：

```bash
cd web
npm install
cd ..
```

3. 在项目根目录创建 `.env`，可以先参考这个最小版本：

```env
APP_NAME=FetchNews
APP_ENVIRONMENT=development
APP_HOST=0.0.0.0
APP_PORT=8000
APP_DATABASE_URL=sqlite:///./fetchnews.db
APP_REDIS_URL=redis://localhost:6379/0
APP_CORS_ORIGINS=["http://localhost:5173"]
APP_INGEST_INTERVAL_SECONDS=1800
VITE_API_BASE=http://localhost:8000
```

4. 启动 Redis。

如果本机已经有 Redis，可直接使用；否则建议还是回到 `Docker Compose`。

5. 启动后端 API：

```bash
uvicorn fetchnews.main:app --host 0.0.0.0 --port 8000 --reload
```

6. 启动 Celery Worker：

```bash
celery -A fetchnews.tasks.worker.celery_app worker --loglevel=info
```

7. 启动 Celery Beat：

```bash
celery -A fetchnews.tasks.worker.celery_app beat --loglevel=info
```

8. 启动前端：

```bash
cd web
npm run dev -- --host 0.0.0.0
```

## 如何验证当前功能

建议按下面的顺序验证，能最快确认当前阶段是否正常。

### 1. 验证后端是否启动成功

访问：
- [http://localhost:8000/healthz](http://localhost:8000/healthz)

期望返回：

```json
{"status":"ok","service":"FetchNews"}
```

### 2. 验证来源目录是否可用

访问：
- [http://localhost:8000/sources](http://localhost:8000/sources)

当前应能看到这些默认来源中的一部分：
- `github-trending`
- `arxiv-cs-ai`
- `openai-blog`
- `x-allowlist`
- `hf-daily`
- `reddit-ml`

### 3. 手动触发一次采集

可以直接调用接口：

```bash
curl -X POST http://localhost:8000/ingest/run ^
  -H "Content-Type: application/json" ^
  -d "{\"source_slugs\":[\"github-trending\",\"arxiv-cs-ai\",\"openai-blog\"]}"
```

如果你在 PowerShell 中执行，也可以使用：

```powershell
Invoke-RestMethod -Method Post -Uri http://localhost:8000/ingest/run -ContentType 'application/json' -Body '{"source_slugs":["github-trending","arxiv-cs-ai","openai-blog"]}'
```

期望现象：
- 返回一个新的采集批次
- `status` 为 `completed` 或 `completed_with_errors`
- `items_ingested` 大于等于 `0`
- 如果某个来源失败，错误会出现在 `errors` 字段中，但不会阻断整个批次

说明：
- `x-allowlist` 当前仍是占位接入，默认情况下没有配置 `static_items` 会报错，这是现阶段的预期行为，不算异常设计。

### 4. 查询采集批次结果

访问：
- [http://localhost:8000/ingest/runs](http://localhost:8000/ingest/runs)

如果想查看单个批次详情：
- [http://localhost:8000/ingest/runs/1](http://localhost:8000/ingest/runs/1)

你应该能看到：
- `source_slugs`
- `status`
- `sources_total`
- `sources_succeeded`
- `sources_failed`
- `items_ingested`
- `errors`
- `started_at`
- `finished_at`

### 5. 验证前端采集页

打开：
- [http://localhost:5173/ingestion](http://localhost:5173/ingestion)

当前前端可以验证这些行为：
- 页面能正常加载采集批次列表
- 页面能从 `/sources` 拉取来源目录
- 默认会勾选 `P0` 来源
- 点击“立即采集”后，会调用 `POST /ingest/run`
- 新批次创建成功后，页面会自动刷新列表

如果页面顶部健康状态显示后端未连接，优先检查：
- `VITE_API_BASE` 是否指向 `http://localhost:8000`
- 后端 API 是否真的已经启动
- 浏览器控制台是否有跨域错误

### 6. 验证定时调度是否存在

当前 `Celery beat` 已经注册默认任务：
- `ingest-default-sources`

默认周期来自：
- `APP_INGEST_INTERVAL_SECONDS`

当前默认值是：
- `1800` 秒

如果你启动了 `beat`，可以直接看日志确认是否开始调度 `fetchnews.ingest.run`。

## 自动化验证命令

在声称当前功能可用之前，至少执行：

```bash
python -m pytest
```

如果你改了前端，还要执行：

```bash
cd web
npm.cmd run build
```

## 当前阶段的预期限制

这些限制是当前阶段已知且合理的：
- `docker-compose.yml` 目前没有把 PostgreSQL 拉起来，本地快速验证使用的是 `SQLite`
- `X` 来源仍是占位实现，不是正式接入
- 采集成功不代表后续标准化、聚类和内容生成已经完整实现
- 当前审核台重点是“看见和触发采集”，不是完整运营后台

## 建议的验证节奏

如果你只是想快速判断“项目现在是不是活的”，最短路径是：

1. 执行 `docker compose up api worker beat web redis`
2. 打开 [http://localhost:8000/healthz](http://localhost:8000/healthz)
3. 打开 [http://localhost:5173/ingestion](http://localhost:5173/ingestion)
4. 点击一次“立即采集”
5. 确认列表中出现新的采集批次

如果这五步都成立，说明当前阶段的主链路已经跑通。

## PostgreSQL Note

The Docker Compose quick-start path now assumes PostgreSQL is already running on the host machine. For manual setup details, hostnames, and initialization SQL, see:

- [docs/postgresql-local-setup.md](/D:/Code/Project/FetchNews/docs/postgresql-local-setup.md)
