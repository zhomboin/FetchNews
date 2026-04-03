# 编辑工作台 Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将当前草稿中心升级为支持模板配额、段落级锁定、混合重建、版本对比/恢复与平台模板选择的三栏编辑工作台。

**Architecture:** 以现有 `ArticleDraft` 为顶层稿件对象，新增模板、版本、内容块和人工干预日志四类模型，后端负责块级组装与版本快照，前端负责三栏编辑与审阅交互。生成链路继续以 `stories` 为唯一内容来源，但通过 `DigestTemplate`、`ArticleBlock` 和 `ArticleRevision` 将自动生成与人工编辑分层，确保混合重建不会覆盖锁定内容。

**Tech Stack:** FastAPI、SQLAlchemy 2.x、Alembic、PostgreSQL、React 18、Vite、TypeScript、TanStack Query、Vitest、pytest。

---

## 文件结构与职责

### 后端新增文件

- `D:/Code/Project/FetchNews/fetchnews/pipeline/editorial_templates.py`
  - 模板校验、归一化、默认模板选择。
- `D:/Code/Project/FetchNews/fetchnews/pipeline/editorial_blocks.py`
  - 正文块/平台块生成、块组装、块级重建。
- `D:/Code/Project/FetchNews/fetchnews/pipeline/editorial_revisions.py`
  - revision 快照、diff、恢复、人工动作记录。
- `D:/Code/Project/FetchNews/tests/test_editorial_workbench.py`
  - 编辑工作台主链路测试。

### 后端修改文件

- `D:/Code/Project/FetchNews/fetchnews/models.py`
  - 新增 `DigestTemplate`、`ArticleRevision`、`ArticleBlock`、`EditorialAction`。
- `D:/Code/Project/FetchNews/fetchnews/schemas.py`
  - 新增模板、块、版本、重建、人工动作的请求/响应 schema。
- `D:/Code/Project/FetchNews/fetchnews/main.py`
  - 暴露模板、块、revision、restore、rebuild API。
- `D:/Code/Project/FetchNews/fetchnews/pipeline/article_service.py`
  - 将稿件生成流程改为“基线稿 + 块级组装 + revision 持久化”。
- `D:/Code/Project/FetchNews/fetchnews/pipeline/generation.py`
  - 将 weekly/monthly 模板与平台模板的内容生成改为块级输入/输出。
- `D:/Code/Project/FetchNews/fetchnews/core/audit.py`
  - 记录编辑工作台相关审计事件。
- `D:/Code/Project/FetchNews/alembic/versions/<new_revision>.py`
  - 新增编辑工作台结构迁移和旧稿件回填。
- `D:/Code/Project/FetchNews/tests/test_api.py`
  - API 入口集成测试补充。

### 前端新增文件

- `D:/Code/Project/FetchNews/web/src/features/articles/article-strategy-rail.tsx`
  - 左栏：模板、栏目配额、平台模板、重建控制。
- `D:/Code/Project/FetchNews/web/src/features/articles/article-composer.tsx`
  - 中栏：段落块列表、编辑、锁定、排序。
- `D:/Code/Project/FetchNews/web/src/features/articles/article-history-panel.tsx`
  - 右栏：revision、diff、restore、平台块。
- `D:/Code/Project/FetchNews/web/src/features/articles/article-editor-types.ts`
  - 编辑工作台本地视图类型。
- `D:/Code/Project/FetchNews/web/src/features/articles/articles-page.test.tsx`
  - 编辑工作台交互测试。

### 前端修改文件

- `D:/Code/Project/FetchNews/web/src/features/articles/articles-page.tsx`
  - 将现有草稿中心演进为三栏工作台壳层。
- `D:/Code/Project/FetchNews/web/src/lib/api.ts`
  - 增加模板、块、revision、restore、rebuild 的 DTO 映射。
- `D:/Code/Project/FetchNews/web/src/styles.css`
  - 增加编辑工作台三栏布局与块级控件样式。
- `D:/Code/Project/FetchNews/web/src/main.tsx`
  - 如需调整路由保护或页面装载逻辑，在这里接线。

## 约束与边界

- 不重写已有 `Story`、`PublishJob` 主流程；编辑工作台只替换草稿编辑层。
- `ArticleDraft.body` 和 `PostVariant.content` 继续保留，作为后端由块组装后的发布真相。
- 混合重建默认只作用于未锁定块；全量覆盖必须是显式危险操作。
- 恢复历史版本必须创建新 revision，不允许直接覆写旧 revision。
- 所有文档、注释、UI 文案继续统一使用中文。
- 先完成后端块级能力，再上前端三栏交互，避免 UI 先行失去数据真相。

## 实施顺序

1. 数据模型与迁移基线。
2. 模板与块级生成服务。
3. 混合重建、revision、restore、审计。
4. 三栏工作台 UI 与交互。
5. 发布链路与块级编辑联动验证。

### Task 1：编辑工作台数据模型与迁移基线

**Files:**
- Create: `D:/Code/Project/FetchNews/tests/test_editorial_workbench.py`
- Modify: `D:/Code/Project/FetchNews/fetchnews/models.py`
- Modify: `D:/Code/Project/FetchNews/fetchnews/schemas.py`
- Modify: `D:/Code/Project/FetchNews/alembic/versions/20260401_0001_initial_schema.py`
- Create: `D:/Code/Project/FetchNews/alembic/versions/20260403_0002_editorial_workbench.py`

- [ ] **Step 1: 写失败测试，固定模型与 API 最小契约**

```python
def test_generate_article_creates_initial_revision_with_blocks(client):
    response = client.post('/articles/generate/weekly', json={'target_date': '2026-04-03'})
    assert response.status_code == 200
    payload = response.json()
    assert payload['active_revision_id'] is not None
    assert payload['block_count'] > 0
```

- [ ] **Step 2: 运行测试确认失败**

Run: `python -m pytest tests/test_editorial_workbench.py::test_generate_article_creates_initial_revision_with_blocks -v`
Expected: FAIL，提示缺少 revision/block 字段或模型未定义。

- [ ] **Step 3: 新增模型和 schema**

```python
class DigestTemplate(Base):
    __tablename__ = 'digest_templates'
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    period_type = Column(String(20), nullable=False)
    section_quotas = Column(JSON, nullable=False, default=dict)
```

```python
class ArticleRevision(Base):
    __tablename__ = 'article_revisions'
    id = Column(Integer, primary_key=True)
    article_id = Column(Integer, ForeignKey('article_drafts.id'), nullable=False)
    version_number = Column(Integer, nullable=False)
    change_type = Column(String(30), nullable=False)
    snapshot = Column(JSON, nullable=False, default=dict)
```

- [ ] **Step 4: 编写 Alembic 迁移**

```python
def upgrade() -> None:
    op.create_table('digest_templates', ...)
    op.create_table('article_revisions', ...)
    op.create_table('article_blocks', ...)
    op.create_table('editorial_actions', ...)
```

- [ ] **Step 5: 运行最小测试与迁移验证**

Run: `python -m pytest tests/test_editorial_workbench.py::test_generate_article_creates_initial_revision_with_blocks -v`
Expected: PASS

Run: `python -m pytest tests/test_api.py -k article -v`
Expected: PASS

- [ ] **Step 6: 提交**

```bash
git add tests/test_editorial_workbench.py fetchnews/models.py fetchnews/schemas.py alembic/versions
git commit -m "feat: add editorial workbench schema"
```

### Task 2：模板层与块级基线稿生成

**Files:**
- Create: `D:/Code/Project/FetchNews/fetchnews/pipeline/editorial_templates.py`
- Create: `D:/Code/Project/FetchNews/fetchnews/pipeline/editorial_blocks.py`
- Modify: `D:/Code/Project/FetchNews/fetchnews/pipeline/article_service.py`
- Modify: `D:/Code/Project/FetchNews/fetchnews/pipeline/generation.py`
- Modify: `D:/Code/Project/FetchNews/fetchnews/main.py`
- Test: `D:/Code/Project/FetchNews/tests/test_editorial_workbench.py`

- [ ] **Step 1: 写失败测试，固定模板配额和块生成行为**

```python
def test_weekly_template_allocates_sections_and_blocks(client):
    payload = client.post('/articles/generate', json={
        'period_type': 'weekly',
        'target_date': '2026-04-03',
        'template_id': 1,
    }).json()
    assert payload['section_plan'][0]['sectionKey'] == 'research'
    assert any(block['blockType'] == 'story_paragraph' for block in payload['blocks'])
```

- [ ] **Step 2: 运行测试确认失败**

Run: `python -m pytest tests/test_editorial_workbench.py::test_weekly_template_allocates_sections_and_blocks -v`
Expected: FAIL，提示缺少统一生成入口、模板字段或块数据。

- [ ] **Step 3: 实现模板服务与默认模板回退**

```python
def resolve_digest_template(session, period_type: str, template_id: int | None) -> DigestTemplate:
    ...
```

- [ ] **Step 4: 实现块级组装与稿件组装**

```python
def build_article_blocks(stories, template, platform_templates):
    return [
        {'block_type': 'title', 'content': '...'},
        {'block_type': 'section_heading', 'section_key': 'research', 'content': '研究进展'},
    ]
```

- [ ] **Step 5: 暴露统一生成接口**

Run: `python -m pytest tests/test_editorial_workbench.py -k template -v`
Expected: PASS

- [ ] **Step 6: 回归现有 digest 流程**

Run: `python -m pytest tests/test_api.py -k "generate or periodic" -v`
Expected: PASS

- [ ] **Step 7: 提交**

```bash
git add fetchnews/pipeline/editorial_templates.py fetchnews/pipeline/editorial_blocks.py fetchnews/pipeline/article_service.py fetchnews/pipeline/generation.py fetchnews/main.py tests/test_editorial_workbench.py
git commit -m "feat: add digest templates and block generation"
```

### Task 3：混合重建、块编辑与审计

**Files:**
- Create: `D:/Code/Project/FetchNews/fetchnews/pipeline/editorial_revisions.py`
- Modify: `D:/Code/Project/FetchNews/fetchnews/core/audit.py`
- Modify: `D:/Code/Project/FetchNews/fetchnews/main.py`
- Modify: `D:/Code/Project/FetchNews/fetchnews/schemas.py`
- Modify: `D:/Code/Project/FetchNews/fetchnews/pipeline/article_service.py`
- Test: `D:/Code/Project/FetchNews/tests/test_editorial_workbench.py`
- Test: `D:/Code/Project/FetchNews/tests/test_api.py`

- [ ] **Step 1: 写失败测试，固定锁定与混合重建规则**

```python
def test_rebuild_preserves_locked_blocks_and_regenerates_unlocked_blocks(client):
    rebuild = client.post('/articles/1/rebuild', json={'mode': 'mixed'})
    assert rebuild.status_code == 200
    assert rebuild.json()['preservedLockedBlocks'] > 0
    assert rebuild.json()['regeneratedBlocks'] > 0
```

- [ ] **Step 2: 运行测试确认失败**

Run: `python -m pytest tests/test_editorial_workbench.py::test_rebuild_preserves_locked_blocks_and_regenerates_unlocked_blocks -v`
Expected: FAIL，提示缺少 `/articles/{id}/rebuild` 或锁定逻辑。

- [ ] **Step 3: 实现块编辑、锁定、排序接口**

```python
@router.patch('/articles/{article_id}/blocks/{block_id}')
def update_article_block(...):
    ...
```

- [ ] **Step 4: 实现混合重建与审计动作**

```python
def rebuild_article(article, mode='mixed'):
    if block.is_locked and mode == 'mixed':
        preserve(block)
```

- [ ] **Step 5: 回归 restore / publish 兼容性**

Run: `python -m pytest tests/test_editorial_workbench.py -k rebuild -v`
Expected: PASS

Run: `python -m pytest tests/test_api.py -k "publish or restore" -v`
Expected: PASS

- [ ] **Step 6: 提交**

```bash
git add fetchnews/pipeline/editorial_revisions.py fetchnews/core/audit.py fetchnews/main.py fetchnews/schemas.py fetchnews/pipeline/article_service.py tests/test_editorial_workbench.py tests/test_api.py
git commit -m "feat: add mixed rebuild and editorial audit"
```

### Task 4：Revision、Diff、恢复与人工动作查询

**Files:**
- Modify: `D:/Code/Project/FetchNews/fetchnews/pipeline/editorial_revisions.py`
- Modify: `D:/Code/Project/FetchNews/fetchnews/main.py`
- Modify: `D:/Code/Project/FetchNews/fetchnews/schemas.py`
- Test: `D:/Code/Project/FetchNews/tests/test_editorial_workbench.py`
- Test: `D:/Code/Project/FetchNews/tests/test_api.py`

- [ ] **Step 1: 写失败测试，固定 revision diff 与 restore 行为**

```python
def test_restore_revision_creates_new_revision_instead_of_mutating_history(client):
    restored = client.post('/articles/1/revisions/2/restore')
    assert restored.status_code == 200
    assert restored.json()['versionNumber'] == 3
```

- [ ] **Step 2: 运行测试确认失败**

Run: `python -m pytest tests/test_editorial_workbench.py::test_restore_revision_creates_new_revision_instead_of_mutating_history -v`
Expected: FAIL，提示缺少 revision API 或版本号未递增。

- [ ] **Step 3: 实现 revision 列表、详情、diff、restore**

```python
def build_revision_diff(previous_snapshot, current_snapshot):
    return {'changedBlocks': [...], 'platformChanges': [...]} 
```

- [ ] **Step 4: 实现人工动作查询接口**

Run: `python -m pytest tests/test_editorial_workbench.py -k revision -v`
Expected: PASS

Run: `python -m pytest tests/test_api.py -k editorial -v`
Expected: PASS

- [ ] **Step 5: 提交**

```bash
git add fetchnews/pipeline/editorial_revisions.py fetchnews/main.py fetchnews/schemas.py tests/test_editorial_workbench.py tests/test_api.py
git commit -m "feat: add revision history and restore flow"
```

### Task 5：三栏编辑工作台 UI

**Files:**
- Create: `D:/Code/Project/FetchNews/web/src/features/articles/article-strategy-rail.tsx`
- Create: `D:/Code/Project/FetchNews/web/src/features/articles/article-composer.tsx`
- Create: `D:/Code/Project/FetchNews/web/src/features/articles/article-history-panel.tsx`
- Create: `D:/Code/Project/FetchNews/web/src/features/articles/article-editor-types.ts`
- Modify: `D:/Code/Project/FetchNews/web/src/features/articles/articles-page.tsx`
- Modify: `D:/Code/Project/FetchNews/web/src/lib/api.ts`
- Modify: `D:/Code/Project/FetchNews/web/src/styles.css`
- Test: `D:/Code/Project/FetchNews/web/src/features/articles/articles-page.test.tsx`

- [ ] **Step 1: 写失败测试，固定三栏渲染与模板/锁定交互**

```tsx
it('renders strategy rail, composer, and history panel', async () => {
  render(<ArticlesPage />);
  expect(await screen.findByText('模板策略')).toBeInTheDocument();
  expect(screen.getByText('段落编排')).toBeInTheDocument();
  expect(screen.getByText('版本历史')).toBeInTheDocument();
});
```

- [ ] **Step 2: 运行测试确认失败**

Run: `cd web; npm run test:run -- articles-page.test.tsx`
Expected: FAIL，提示页面中不存在三栏工作台文案或组件。

- [ ] **Step 3: 实现三栏壳层与 API 映射**

```ts
export interface ArticleBlockViewModel {
  blockId: number;
  blockType: string;
  content: string;
  isLocked: boolean;
}
```

- [ ] **Step 4: 接入块编辑、锁定、模板选择、重建触发**

Run: `cd web; npm run test:run -- articles-page.test.tsx`
Expected: PASS

Run: `npm.cmd run build`
Expected: BUILD SUCCESS

- [ ] **Step 5: 提交**

```bash
git add web/src/features/articles web/src/lib/api.ts web/src/styles.css
git commit -m "feat: add editorial workbench interface"
```

### Task 6：右栏 diff/restore、平台模板与发布前联动

**Files:**
- Modify: `D:/Code/Project/FetchNews/web/src/features/articles/article-history-panel.tsx`
- Modify: `D:/Code/Project/FetchNews/web/src/features/articles/articles-page.tsx`
- Modify: `D:/Code/Project/FetchNews/web/src/lib/api.ts`
- Modify: `D:/Code/Project/FetchNews/web/src/styles.css`
- Test: `D:/Code/Project/FetchNews/web/src/features/articles/articles-page.test.tsx`
- Test: `D:/Code/Project/FetchNews/tests/test_api.py`

- [ ] **Step 1: 写失败测试，固定平台模板与 revision 恢复交互**

```tsx
it('restores a revision and refreshes platform variants', async () => {
  render(<ArticlesPage />);
  await user.click(await screen.findByRole('button', {name: '恢复为当前版本'}));
  expect(await screen.findByText('已基于历史版本创建新版本')).toBeInTheDocument();
});
```

- [ ] **Step 2: 运行测试确认失败**

Run: `cd web; npm run test:run -- articles-page.test.tsx`
Expected: FAIL，提示缺少恢复交互或平台模板区域。

- [ ] **Step 3: 实现右栏 diff/restore 与平台模板联动**

- [ ] **Step 4: 回归发布链路**

Run: `python -m pytest tests/test_api.py -k publish -v`
Expected: PASS

Run: `cd web; npm run test:run`
Expected: PASS

Run: `npm.cmd run build`
Expected: BUILD SUCCESS

- [ ] **Step 5: 提交**

```bash
git add web/src/features/articles web/src/lib/api.ts web/src/styles.css tests/test_api.py
git commit -m "feat: connect revision history with publish workflow"
```

## 总体验证

按阶段实现完成后，统一执行：

```bash
python -m pytest
cd web && npm run test:run
npm.cmd run build
git diff --check
```

期望结果：
- pytest 全部通过
- Vitest 全部通过
- 前端构建通过
- diff check 无空白与行尾问题

## 文档同步要求

实现过程中同步更新以下文档：

- `D:/Code/Project/FetchNews/docs/current-status.md`
- `D:/Code/Project/FetchNews/docs/implementation-roadmap.md`
- `D:/Code/Project/FetchNews/docs/project-plan/phase-06-optimization-and-operations.md`（如阶段定义受影响）
- `D:/Code/Project/FetchNews/docs/superpowers/specs/2026-04-03-editorial-workbench-design.md`（仅在实现偏离 spec 时修订）

## 执行备注

- 当前 harness 虽支持子代理，但本次实现默认在当前会话中执行，除非用户明确要求并行代理。
- 坚持 TDD：先测后改，先后端后前端。
- 每个 task 完成后都做小提交，避免把迁移、模型、前端交互混成一笔。