# Phase 07 加固与生产就绪 Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在已合并的 Phase 07 Task 1-5 基础上，把“真实外部能力接入骨架”加固成可以承接小规模真实流量的后半段实现。

**Architecture:** 继续沿用现有 `publishing/`、`sources/`、`tasks/`、`ops/` 模块边界，不做目录重构。优先补真实发布和真实来源的生产边界，包括认证、限流、异常恢复、回调校验和可观测，再决定是否进入 Phase 08 的真实 LLM provider 接入。

**Tech Stack:** FastAPI、SQLAlchemy 2.x、Alembic、Celery、Redis、httpx、selectolax、pytest、React SPA、Vitest。

---

## 前置条件

- 本地 `master` 目前还没有同步到已合并的 Phase 07 PR；执行本计划前，先把本地主线更新到合并后的最新提交。
- 当前主工作区有用户自己的文档改动未提交：
  - `D:/Code/Project/FetchNews/docs/engineering-ops-baseline.md`
  - `D:/Code/Project/FetchNews/docs/postgresql-local-setup.md`
  - `D:/Code/Project/FetchNews/docs/superpowers/plans/2026-04-04-phase-07-external-capabilities.md`
- 后续实现应在新的隔离 worktree 中进行，不直接在脏工作区上开发。

## 文件结构与职责

### 需要重点修改的后端文件

- `D:/Code/Project/FetchNews/fetchnews/settings.py`
  - 真实平台和真实来源的认证、限流、超时、callback 配置。
- `D:/Code/Project/FetchNews/fetchnews/main.py`
  - callback 校验、手动验证接口、ops 健康暴露。
- `D:/Code/Project/FetchNews/fetchnews/publishing/real_publishers.py`
  - `telegram` 真实发布 MVP、`wechat / x` 继续保留骨架。
- `D:/Code/Project/FetchNews/fetchnews/publishing/service.py`
  - 发布幂等、调度限流、轮询超时、失败归因和重试策略。
- `D:/Code/Project/FetchNews/fetchnews/sources/real_connectors.py`
  - GitHub / Hugging Face / Papers with Code 的认证、增量和异常恢复。
- `D:/Code/Project/FetchNews/fetchnews/sources/service.py`
  - 连接器批次执行、cursor 推进、失败回退和来源级指标。
- `D:/Code/Project/FetchNews/fetchnews/ops/service.py`
  - 平台与来源的失败归因、成功率、告警阈值。
- `D:/Code/Project/FetchNews/fetchnews/tasks/worker.py`
  - 发布轮询、来源抓取和限流任务编排。
- `D:/Code/Project/FetchNews/alembic/versions/<new_revision>.py`
  - 如果新增来源 / 平台限流状态表或字段，需要对应迁移。

### 需要重点修改的测试文件

- `D:/Code/Project/FetchNews/tests/test_real_publishing.py`
- `D:/Code/Project/FetchNews/tests/test_real_connectors.py`
- `D:/Code/Project/FetchNews/tests/test_ingestion.py`
- `D:/Code/Project/FetchNews/tests/test_platform_ops.py`
- `D:/Code/Project/FetchNews/tests/test_api.py`

### 需要同步的文档文件

- `D:/Code/Project/FetchNews/docs/current-status.md`
- `D:/Code/Project/FetchNews/docs/implementation-roadmap.md`
- `D:/Code/Project/FetchNews/docs/project-plan/phase-07-future-roadmap.md`
- `D:/Code/Project/FetchNews/docs/getting-started.md`
- `D:/Code/Project/FetchNews/docs/engineering-ops-baseline.md`
- `D:/Code/Project/FetchNews/docs/content-sources.md`

## 任务切分

### Task 1: 同步主线并建立新的执行基线

**Files:**
- Modify: `D:/Code/Project/FetchNews/docs/current-status.md`
- Modify: `D:/Code/Project/FetchNews/docs/implementation-roadmap.md`
- Modify: `D:/Code/Project/FetchNews/docs/project-plan/phase-07-future-roadmap.md`

- [ ] **Step 1: 拉取已合并主线到新的隔离 worktree**

Run: `git fetch origin && git worktree add .worktrees/phase-07-hardening origin/master`
Expected: 新 worktree 基于已合并 Phase 07 的主线创建成功。

- [ ] **Step 2: 运行全量测试，记录当前基线**

Run: `python -m pytest`
Expected: 全量通过，作为后续加固的回归基线。

- [ ] **Step 3: 更新状态文档，把“Phase 07 Task 1-5 已合并”写进主线**

```md
## 当前阶段

- Phase 07 Task 1-5 已合并到主线
- 下一步进入 Phase 07 加固与生产就绪
```

- [ ] **Step 4: 提交**

```bash
git add docs/current-status.md docs/implementation-roadmap.md docs/project-plan/phase-07-future-roadmap.md
git commit -m "docs: mark phase 07 baseline merged on main"
```

### Task 2: 把 Telegram 从骨架提升到真实发布 MVP

**Files:**
- Modify: `D:/Code/Project/FetchNews/fetchnews/settings.py`
- Modify: `D:/Code/Project/FetchNews/fetchnews/main.py`
- Modify: `D:/Code/Project/FetchNews/fetchnews/publishing/real_publishers.py`
- Modify: `D:/Code/Project/FetchNews/fetchnews/publishing/service.py`
- Modify: `D:/Code/Project/FetchNews/tests/test_real_publishing.py`
- Modify: `D:/Code/Project/FetchNews/tests/test_api.py`

- [ ] **Step 1: 写失败测试，固定真实 Telegram 发布成功、失败和超时路径**

```python
def test_real_telegram_submit_uses_bot_token_and_returns_provider_job_id() -> None:
    submission = publisher.submit(job, article, variant)
    assert submission.provider_job_id.startswith("telegram-")
```

```python
def test_real_telegram_callback_updates_provider_payload_and_audit_log() -> None:
    response = client.post("/publish-jobs/callback/telegram", json=payload, headers=headers)
    assert response.status_code == 200
```

- [ ] **Step 2: 运行测试确认失败**

Run: `python -m pytest tests/test_real_publishing.py -k "telegram" -v`
Expected: FAIL，提示真实 Telegram 提交逻辑仍是骨架。

- [ ] **Step 3: 实现 Telegram 真实提交 MVP**

```python
class RealTelegramPublisher:
    def submit(self, job, article, variant):
        response = httpx.post(
            f"{self.api_base_url}/bot{self.bot_token}/sendMessage",
            json={"chat_id": self.default_chat_id, "text": variant.content},
            timeout=self.request_timeout_seconds,
        )
```

- [ ] **Step 4: 在服务层补真实 provider 响应写回和失败分类**

Run: `python -m pytest tests/test_real_publishing.py -v`
Expected: PASS

- [ ] **Step 5: 提交**

```bash
git add fetchnews/settings.py fetchnews/main.py fetchnews/publishing/real_publishers.py fetchnews/publishing/service.py tests/test_real_publishing.py tests/test_api.py
git commit -m "feat: add telegram real publishing mvp"
```

### Task 3: 加固真实来源连接器的认证、分页与异常恢复

**Files:**
- Modify: `D:/Code/Project/FetchNews/fetchnews/settings.py`
- Modify: `D:/Code/Project/FetchNews/fetchnews/sources/real_connectors.py`
- Modify: `D:/Code/Project/FetchNews/fetchnews/sources/service.py`
- Modify: `D:/Code/Project/FetchNews/fetchnews/sources/catalog.py`
- Modify: `D:/Code/Project/FetchNews/tests/test_real_connectors.py`
- Modify: `D:/Code/Project/FetchNews/tests/test_ingestion.py`

- [ ] **Step 1: 写失败测试，固定 GitHub 认证头、Papers with Code 分页和 Hugging Face 解析回退**

```python
def test_github_releases_connector_uses_token_when_configured(monkeypatch) -> None:
    ...
    assert headers["Authorization"].startswith("Bearer ")
```

```python
def test_huggingface_connector_recovers_when_expected_cards_missing(monkeypatch) -> None:
    result = connector.fetch(source)
    assert result.items == []
```

- [ ] **Step 2: 运行测试确认失败**

Run: `python -m pytest tests/test_real_connectors.py -v`
Expected: FAIL

- [ ] **Step 3: 实现来源侧生产边界**

```python
response = httpx.get(
    url,
    headers={
        "User-Agent": "FetchNews/0.1",
        "Authorization": f"Bearer {token}",
        "If-None-Match": etag,
    },
)
```

- [ ] **Step 4: 在采集服务层补 cursor 推进保护和失败不覆盖旧 cursor**

Run: `python -m pytest tests/test_real_connectors.py tests/test_ingestion.py -v`
Expected: PASS

- [ ] **Step 5: 提交**

```bash
git add fetchnews/settings.py fetchnews/sources/real_connectors.py fetchnews/sources/service.py fetchnews/sources/catalog.py tests/test_real_connectors.py tests/test_ingestion.py
git commit -m "feat: harden real source connectors"
```

### Task 4: 发布与采集调度补限流、重试和 ops 告警

**Files:**
- Modify: `D:/Code/Project/FetchNews/fetchnews/settings.py`
- Modify: `D:/Code/Project/FetchNews/fetchnews/publishing/service.py`
- Modify: `D:/Code/Project/FetchNews/fetchnews/sources/service.py`
- Modify: `D:/Code/Project/FetchNews/fetchnews/tasks/worker.py`
- Modify: `D:/Code/Project/FetchNews/fetchnews/ops/service.py`
- Modify: `D:/Code/Project/FetchNews/tests/test_platform_ops.py`
- Modify: `D:/Code/Project/FetchNews/tests/test_api.py`

- [ ] **Step 1: 写失败测试，固定平台限流和来源失败告警行为**

```python
def test_dispatch_due_publish_jobs_skips_platform_when_rate_limit_window_open() -> None:
    result = dispatch_due_publish_jobs(session, registry)
    assert result.jobs_dispatched == 0
```

```python
def test_ops_summary_emits_alert_for_repeated_source_failures() -> None:
    summary = build_ops_summary(session)
    assert any(alert["category"] == "source" for alert in summary["alerts"])
```

- [ ] **Step 2: 运行测试确认失败**

Run: `python -m pytest tests/test_platform_ops.py -v`
Expected: FAIL

- [ ] **Step 3: 实现平台级和来源级限流、重试与告警**

```python
if platform_window_open(job.platform, now):
    continue

if source_recent_failures[source.slug] >= settings.source_failure_alert_threshold:
    alerts.append(...)
```

- [ ] **Step 4: 回归 ops 与 API**

Run: `python -m pytest tests/test_platform_ops.py tests/test_api.py -v`
Expected: PASS

- [ ] **Step 5: 提交**

```bash
git add fetchnews/settings.py fetchnews/publishing/service.py fetchnews/sources/service.py fetchnews/tasks/worker.py fetchnews/ops/service.py tests/test_platform_ops.py tests/test_api.py
git commit -m "feat: add phase 07 rate limits and alerts"
```

### Task 5: 文档、Runbook 和小流量验收

**Files:**
- Modify: `D:/Code/Project/FetchNews/docs/getting-started.md`
- Modify: `D:/Code/Project/FetchNews/docs/engineering-ops-baseline.md`
- Modify: `D:/Code/Project/FetchNews/docs/content-sources.md`
- Modify: `D:/Code/Project/FetchNews/docs/current-status.md`
- Modify: `D:/Code/Project/FetchNews/docs/implementation-roadmap.md`
- Modify: `D:/Code/Project/FetchNews/docs/project-plan/phase-07-future-roadmap.md`

- [ ] **Step 1: 补“真实平台最小上线条件”和“来源异常恢复说明”**

```md
## 真实平台最小上线条件

- 已配置 callback secret
- 已配置平台认证
- 已验证幂等重试和限流
```

- [ ] **Step 2: 补小流量验收清单**

```md
1. 仅开启 `telegram`
2. 仅开启 `github-openai-releases`
3. 连续运行 24 小时观察成功率和 failure_category
```

- [ ] **Step 3: 运行最终验证**

Run: `python -m pytest`
Expected: PASS

Run: `npm.cmd run build`
Expected: SUCCESS

- [ ] **Step 4: 提交**

```bash
git add docs/getting-started.md docs/engineering-ops-baseline.md docs/content-sources.md docs/current-status.md docs/implementation-roadmap.md docs/project-plan/phase-07-future-roadmap.md
git commit -m "docs: add phase 07 hardening runbook"
```

## 完成判定

满足以下条件后，再进入 Phase 08：

- `telegram` 可以在受控环境下完成真实提交、回调、轮询、结果回写和幂等重试。
- 3 类真实来源连接器具备认证、增量、异常恢复和来源级健康指标。
- 发布与采集都有明确的限流和告警行为。
- 主线文档已经说明生产与开发环境差异。

## 执行后建议

完成本计划后，再单独写下一份计划：

- `Phase 08 真实 LLM provider 与 embedding 召回`

不要把 Phase 08 的模型接入和本计划混在同一个实现批次里。