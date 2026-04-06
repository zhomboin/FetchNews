# Phase 07 外部真实能力接入 Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在现有内部闭环之上，打通“至少 1 个真实发布平台 + 至少 3 类真实来源连接器 + ops 可观测 + 幂等重试”的 Phase 07 验收闭环。

**Architecture:** 继续沿用现有 `publishing/`、`sources/`、`tasks/`、`ops/` 模块边界，不先做大重构。发布侧保持“调度 -> 提交 -> 轮询 / 回调 -> 结果回写”链路，采集侧保持“连接器抓取 -> `raw_items` 入库 -> pipeline 标准化 / 聚类”链路，优先通过少量模型字段扩展、配置层增强和错误分类补齐真实能力。Phase 07 不追求一次性打齐所有平台；先落 1 个真实发布平台作为生产闭环，其余平台以可替换适配器形式接上骨架。

**Tech Stack:** FastAPI、SQLAlchemy 2.x、Alembic、Celery、Redis、httpx、feedparser、selectolax、React SPA、pytest、Vitest。

---

## 文件结构与职责

### 后端新增文件

- `D:/Code/Project/FetchNews/fetchnews/publishing/platform_errors.py`
  - 平台发布错误分类、可重试判定、ops 失败归因映射。
- `D:/Code/Project/FetchNews/fetchnews/publishing/real_publishers.py`
  - 真实平台发布器适配层，优先放 1 个真实平台实现和其余平台占位适配器。
- `D:/Code/Project/FetchNews/fetchnews/sources/real_connectors.py`
  - GitHub、Hugging Face、Papers with Code 等真实连接器实现。
- `D:/Code/Project/FetchNews/tests/test_real_publishing.py`
  - 发布器真实适配流程测试。
- `D:/Code/Project/FetchNews/tests/test_real_connectors.py`
  - 真实来源连接器、增量抓取、异常恢复测试。

### 后端修改文件

- `D:/Code/Project/FetchNews/fetchnews/settings.py`
  - 新增平台凭证、回调签名、限流窗口、连接器认证配置。
- `D:/Code/Project/FetchNews/fetchnews/models.py`
  - 为 `publish_jobs`、`sources`、`ingest_runs` 增补真实外部接入需要的状态字段。
- `D:/Code/Project/FetchNews/fetchnews/schemas.py`
  - 新增发布状态详情、失败分类、来源同步状态等响应结构。
- `D:/Code/Project/FetchNews/fetchnews/publishing/connectors.py`
  - 保留协议定义，扩展真实发布器提交 / 轮询 / 回调契约。
- `D:/Code/Project/FetchNews/fetchnews/publishing/service.py`
  - 幂等提交、错误分类、平台限流、回调 / 轮询结果回写。
- `D:/Code/Project/FetchNews/fetchnews/sources/connectors.py`
  - 默认连接器注册改为“mock + real connector”并存。
- `D:/Code/Project/FetchNews/fetchnews/sources/service.py`
  - 增量抓取游标、原始快照、失败归因、来源级统计。
- `D:/Code/Project/FetchNews/fetchnews/sources/catalog.py`
  - 补齐 Phase 07 目标来源及其配置骨架。
- `D:/Code/Project/FetchNews/fetchnews/ops/service.py`
  - 暴露平台成功率、失败归因、来源抓取稳定性。
- `D:/Code/Project/FetchNews/fetchnews/tasks/worker.py`
  - 注册回调轮询、限流调度、连接器批次执行策略。
- `D:/Code/Project/FetchNews/fetchnews/main.py`
  - 暴露真实发布结果回调、来源状态 / 手动重试接口。
- `D:/Code/Project/FetchNews/tests/test_api.py`
  - 扩充真实发布与真实连接器的 API 级回归。
- `D:/Code/Project/FetchNews/tests/test_platform_ops.py`
  - 扩充 ops 指标和告警断言。
- `D:/Code/Project/FetchNews/alembic/versions/<new_revision>.py`
  - Phase 07 所需迁移。

### 前端修改文件

- `D:/Code/Project/FetchNews/web/src/lib/api.ts`
  - 映射发布失败分类、来源同步状态、ops 平台指标字段。
- `D:/Code/Project/FetchNews/web/src/features/ops/ops-dashboard-page.tsx`
  - 展示平台成功率、失败归因、连接器稳定性。
- `D:/Code/Project/FetchNews/web/src/features/ops/ops-detail-page.tsx`
  - 增加来源 / 平台 drill-down。
- `D:/Code/Project/FetchNews/web/src/features/ingestion/ingestion-runs-page.tsx`
  - 增加来源错误分类、增量状态、手动重试入口。

## 约束与切分

- Phase 07 不要同时把 `wechat / x / telegram` 三个平台都做到真实生产强度。验收只要求 1 个真实发布平台打通，其余平台先提供可替换适配层即可。
- 真实来源优先顺序固定为：GitHub、官方博客 RSS、arXiv、Hugging Face、Papers with Code。先确保 3 类稳定进入 `raw_items`，再补其余。
- 凭证管理先走 `Settings` + 环境变量，不引入单独的 secrets 服务。
- 幂等真相继续落在 `publish_jobs`；不要把是否已经发过的判断只放在进程内缓存。
- `raw_items` 仍然是采集真相，真实连接器只能增强 `payload` 快照，不能绕过原始事件层。
- 文档、测试、迁移同步更新，避免“代码支持真实接入，文档仍然写 mock”。

## 实施顺序

1. 先补数据契约和配置层，让真实接入有落库位置。
2. 先落 1 个真实发布平台闭环，再补其余平台适配骨架。
3. 再落 3 类真实来源连接器与增量抓取。
4. 最后补 ops 可观测、告警和前端展示。

### Task 1：打 Phase 07 数据契约和配置基线

**Files:**
- Create: `D:/Code/Project/FetchNews/tests/test_real_publishing.py`
- Modify: `D:/Code/Project/FetchNews/fetchnews/settings.py`
- Modify: `D:/Code/Project/FetchNews/fetchnews/models.py`
- Modify: `D:/Code/Project/FetchNews/fetchnews/schemas.py`
- Create: `D:/Code/Project/FetchNews/alembic/versions/<new_revision>.py`

- [ ] **Step 1: 写失败测试，固定真实发布与真实采集的最小字段契约**

```python
def test_publish_job_persists_failure_category_and_dispatch_key() -> None:
    ...
    assert job.dispatch_key is not None
    assert job.failure_category == "rate_limit"
```

```python
def test_source_persists_incremental_cursor_and_last_success_at() -> None:
    ...
    assert source.config["cursor"] == "next-page-token"
```

- [ ] **Step 2: 运行测试确认失败**

Run: `python -m pytest tests/test_real_publishing.py -v`
Expected: FAIL，提示字段或 schema 未定义。

- [ ] **Step 3: 扩展配置层**

```python
class Settings(BaseSettings):
    publish_real_platform: str | None = Field(default=None)
    telegram_bot_token: str | None = Field(default=None)
    x_bearer_token: str | None = Field(default=None)
    wechat_app_id: str | None = Field(default=None)
```

- [ ] **Step 4: 扩展模型和迁移**

```python
class PublishJob(Base):
    dispatch_key = mapped_column(String(160), nullable=True, index=True)
    failure_category = mapped_column(String(60), nullable=True, index=True)
    last_provider_status = mapped_column(String(80), nullable=True)
```

```python
def upgrade() -> None:
    op.add_column("publish_jobs", sa.Column("dispatch_key", sa.String(length=160), nullable=True))
    op.add_column("publish_jobs", sa.Column("failure_category", sa.String(length=60), nullable=True))
```

- [ ] **Step 5: 运行最小验证**

Run: `python -m pytest tests/test_real_publishing.py -v`
Expected: PASS

Run: `python -m pytest tests/test_api.py -k "publish or ingest" -v`
Expected: PASS

- [ ] **Step 6: 提交**

```bash
git add fetchnews/settings.py fetchnews/models.py fetchnews/schemas.py tests/test_real_publishing.py alembic/versions
git commit -m "feat: add phase 07 publish and source contract fields"
```

### Task 2：落 1 个真实发布平台闭环

**Files:**
- Create: `D:/Code/Project/FetchNews/fetchnews/publishing/platform_errors.py`
- Create: `D:/Code/Project/FetchNews/fetchnews/publishing/real_publishers.py`
- Modify: `D:/Code/Project/FetchNews/fetchnews/publishing/connectors.py`
- Modify: `D:/Code/Project/FetchNews/fetchnews/publishing/service.py`
- Modify: `D:/Code/Project/FetchNews/fetchnews/main.py`
- Modify: `D:/Code/Project/FetchNews/fetchnews/tasks/worker.py`
- Test: `D:/Code/Project/FetchNews/tests/test_real_publishing.py`
- Test: `D:/Code/Project/FetchNews/tests/test_api.py`

- [ ] **Step 1: 写失败测试，固定真实发布提交流程和幂等重试行为**

```python
def test_dispatch_due_publish_jobs_reuses_dispatch_key_on_retry() -> None:
    result = dispatch_due_publish_jobs(session, registry)
    assert result.jobs_dispatched == 1
    assert job.provider_job_id == "provider-123"
```

```python
def test_publish_callback_marks_job_published_without_duplicate_submit(client) -> None:
    response = client.post("/publish-jobs/callback/telegram", json={...})
    assert response.status_code == 200
```

- [ ] **Step 2: 运行测试确认失败**

Run: `python -m pytest tests/test_real_publishing.py -k "dispatch or callback" -v`
Expected: FAIL，提示缺少真实发布器或回调接口。

- [ ] **Step 3: 扩展发布协议**

```python
class PublisherConnector(Protocol):
    def submit(...)
    def poll(...)
    def handle_callback(self, payload: dict[str, object]) -> PublishPollResult | None:
        ...
```

- [ ] **Step 4: 实现 1 个真实发布平台和错误分类**

```python
class RealTelegramPublisher:
    def submit(...):
        response = httpx.post(...)
        ...
```

```python
def classify_publish_error(status_code: int, body: str) -> str:
    if status_code == 429:
        return "rate_limit"
```

- [ ] **Step 5: 在服务层补幂等、限流和回写**

Run: `python -m pytest tests/test_real_publishing.py -v`
Expected: PASS

Run: `python -m pytest tests/test_api.py -k "publish_dispatch or publish_job_result_writeback" -v`
Expected: PASS

- [ ] **Step 6: 提交**

```bash
git add fetchnews/publishing fetchnews/main.py fetchnews/tasks/worker.py tests/test_real_publishing.py tests/test_api.py
git commit -m "feat: add first real publishing platform"
```

### Task 3：补齐其余平台适配骨架与轮询 / 回调治理

**Files:**
- Modify: `D:/Code/Project/FetchNews/fetchnews/publishing/real_publishers.py`
- Modify: `D:/Code/Project/FetchNews/fetchnews/publishing/service.py`
- Modify: `D:/Code/Project/FetchNews/fetchnews/ops/service.py`
- Modify: `D:/Code/Project/FetchNews/tests/test_platform_ops.py`
- Test: `D:/Code/Project/FetchNews/tests/test_real_publishing.py`

- [ ] **Step 1: 写失败测试，固定平台失败归因和 ops 聚合**

```python
def test_ops_summary_groups_publish_failures_by_platform_and_category() -> None:
    summary = build_ops_summary(session)
    assert summary.recent_failure_groups[0].category == "publish"
```

- [ ] **Step 2: 运行测试确认失败**

Run: `python -m pytest tests/test_platform_ops.py -k publish -v`
Expected: FAIL，提示缺少失败分类或平台指标字段。

- [ ] **Step 3: 为 `wechat / x` 增加占位真实适配器和统一注册逻辑**

```python
def build_default_publisher_registry(settings: Settings | None = None) -> PublisherRegistry:
    return {"telegram": telegram, "x": x_connector, "wechat": wechat_connector}
```

- [ ] **Step 4: 增强 ops 指标输出**

Run: `python -m pytest tests/test_platform_ops.py -v`
Expected: PASS

Run: `python -m pytest tests/test_real_publishing.py -k "rate_limit or moderation or auth" -v`
Expected: PASS

- [ ] **Step 5: 提交**

```bash
git add fetchnews/publishing/real_publishers.py fetchnews/publishing/service.py fetchnews/ops/service.py tests/test_platform_ops.py tests/test_real_publishing.py
git commit -m "feat: classify platform failures and ops metrics"
```

### Task 4：落 3 类真实来源连接器和增量抓取

**Files:**
- Create: `D:/Code/Project/FetchNews/fetchnews/sources/real_connectors.py`
- Modify: `D:/Code/Project/FetchNews/fetchnews/sources/connectors.py`
- Modify: `D:/Code/Project/FetchNews/fetchnews/sources/service.py`
- Modify: `D:/Code/Project/FetchNews/fetchnews/sources/catalog.py`
- Create: `D:/Code/Project/FetchNews/tests/test_real_connectors.py`
- Modify: `D:/Code/Project/FetchNews/tests/test_ingestion.py`

- [ ] **Step 1: 写失败测试，固定 GitHub / Hugging Face / Papers with Code 的抓取和增量行为**

```python
def test_github_connector_stores_page_cursor_and_raw_snapshot() -> None:
    items = connector.fetch(source)
    assert items[0].metadata["snapshot"] is not None
```

```python
def test_ingest_run_records_completed_with_errors_per_source_category(client) -> None:
    response = client.post("/ingest/run", json={"source_slugs": [...]})
    assert response.json()["errors"][0]["source_slug"] == "hf-daily"
```

- [ ] **Step 2: 运行测试确认失败**

Run: `python -m pytest tests/test_real_connectors.py -v`
Expected: FAIL，提示缺少真实连接器实现。

- [ ] **Step 3: 实现真实连接器和注册逻辑**

```python
class GitHubReleasesConnector:
    def fetch(self, source: Source) -> list[RawIngestedItem]:
        ...
```

```python
class PapersWithCodeConnector:
    def fetch(self, source: Source) -> list[RawIngestedItem]:
        ...
```

- [ ] **Step 4: 在采集服务层补游标、快照和异常恢复**

Run: `python -m pytest tests/test_real_connectors.py tests/test_ingestion.py -v`
Expected: PASS

- [ ] **Step 5: 提交**

```bash
git add fetchnews/sources tests/test_ingestion.py tests/test_real_connectors.py
git commit -m "feat: add real source connectors and incremental ingest"
```

### Task 5：补 API、ops 面板和前端映射

**Files:**
- Modify: `D:/Code/Project/FetchNews/fetchnews/main.py`
- Modify: `D:/Code/Project/FetchNews/fetchnews/ops/service.py`
- Modify: `D:/Code/Project/FetchNews/web/src/lib/api.ts`
- Modify: `D:/Code/Project/FetchNews/web/src/features/ops/ops-dashboard-page.tsx`
- Modify: `D:/Code/Project/FetchNews/web/src/features/ops/ops-detail-page.tsx`
- Modify: `D:/Code/Project/FetchNews/web/src/features/ingestion/ingestion-runs-page.tsx`
- Modify: `D:/Code/Project/FetchNews/web/src/lib/api.test.ts`
- Modify: `D:/Code/Project/FetchNews/tests/test_api.py`

- [ ] **Step 1: 写失败测试，固定前后端显示字段**

```python
def test_ops_summary_exposes_platform_failure_categories(client) -> None:
    summary = client.get("/ops/summary").json()
    assert "failure_category" in summary["publish_platform_metrics"][0]
```

```ts
it("maps publish failure categories and source sync state", () => {
  expect(mapped.failureCategory).toBe("rate_limit");
});
```

- [ ] **Step 2: 运行测试确认失败**

Run: `python -m pytest tests/test_api.py -k "ops_summary" -v`
Expected: FAIL

Run: `cd web; npm.cmd run test:run -- src/lib/api.test.ts`
Expected: FAIL

- [ ] **Step 3: 接线 API 和前端视图模型**

- [ ] **Step 4: 回归构建和主链路**

Run: `python -m pytest tests/test_api.py tests/test_platform_ops.py -v`
Expected: PASS

Run: `npm.cmd run build`
Expected: BUILD SUCCESS

- [ ] **Step 5: 提交**

```bash
git add fetchnews/main.py fetchnews/ops/service.py web/src/lib/api.ts web/src/features/ops web/src/features/ingestion tests/test_api.py web/src/lib/api.test.ts
git commit -m "feat: surface phase 07 platform and source health in ops"
```

## 总体验证

按 Phase 07 实现完成后，统一执行：

```bash
python -m pytest
npm.cmd run build
```

期望结果：
- 至少 1 个真实发布平台从 `/articles/{id}/publish` 到结果回写闭环通过测试。
- 至少 3 类真实来源连接器稳定进入 `raw_items`。
- 发布失败后重试不产生重复发布记录。
- ops 汇总能看到平台成功率和失败归因。

## 文档同步要求

实现过程中同步更新以下文档：

- `D:/Code/Project/FetchNews/docs/current-status.md`
- `D:/Code/Project/FetchNews/docs/implementation-roadmap.md`
- `D:/Code/Project/FetchNews/docs/project-plan/phase-07-future-roadmap.md`
- `D:/Code/Project/FetchNews/docs/content-sources.md`

## 执行备注

- 当前 Phase 06 仍在进行中，Phase 07 更适合作为独立分支推进，不要在同一批次里夹带 Phase 09 的 diff / 协作治理改动。
- 如果真实平台选择受外部凭证限制，优先做 `telegram` 作为第一个真实发布平台；`wechat / x` 先完成适配骨架与错误分类。
- 这份计划已经按当前仓库现有模块落位，不需要先做目录级重构。
