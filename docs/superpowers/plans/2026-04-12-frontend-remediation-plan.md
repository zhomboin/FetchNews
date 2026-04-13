# 前端整改实施清单

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**目标：** 在不改变现有业务主链路的前提下，完成前端控制台的结构化整改，统一视觉与交互基线，补齐审核与编辑场景中的关键可用性缺口，并为后续持续迭代建立可维护的共享组件层。

**架构：** 本轮不重写前端，而是在现有 `React + Vite + TypeScript` 结构上进行收敛式整改。优先把 [web/src/styles.css](/D:/Code/Project/FetchNews/web/src/styles.css) 中已经稳定的暖白金属视觉语言提炼为共享样式和通用控制台组件，再逐页修正 `stories`、`articles`、`ops`、`ingestion` 的信息层级和操作节奏。`preview-dashboard` 不再视为独立功能页，而是作为总览组件和视觉基线的来源。

**技术栈：** React 18、TypeScript、React Router、TanStack Query、Zustand、CSS

---

## 文件边界

### 现有核心文件

- `web/src/main.tsx`
  - 控制台 Shell、主路由、左侧导航、登录态切换。
- `web/src/styles.css`
  - 当前承载全局 token、布局、组件样式和页面样式，体量已过大。
- `web/src/features/preview/preview-dashboard.tsx`
  - 当前视觉样板页，适合作为总览组件抽取源头。
- `web/src/features/ops/ops-dashboard-page.tsx`
  - 真实总览页，已接入动态数据和详情下钻。
- `web/src/features/ops/ops-detail-page.tsx`
  - 已有详情页入口，需要与总览的状态语义保持一致。
- `web/src/features/ingestion/ingestion-runs-page.tsx`
  - 来源治理、手动触发、批次运行历史页面。
- `web/src/features/stories/stories-page.tsx`
  - 审核队列与标准化检查页，已有基础筛选与单条审核。
- `web/src/features/articles/articles-page.tsx`
  - 三栏编辑工作台入口。
- `web/src/features/articles/article-strategy-rail.tsx`
  - 编辑工作台左栏，负责策略、范围、模板和重建动作。
- `web/src/features/articles/article-composer.tsx`
  - 编辑工作台中栏，负责 block 编辑。
- `web/src/features/articles/article-history-panel.tsx`
  - 编辑工作台右栏，负责历史、版本、平台变体与发布动作。
- `web/src/features/articles/article-history-detail-page.tsx`
  - 修订历史的详情页。
- `web/src/lib/api.ts`
  - 通用 API 映射与页面数据契约边界。
- `web/src/lib/editorial-api.ts`
  - 编辑工作台相关 API。

### 建议新增文件

- `web/src/components/console/page-header.tsx`
  - 统一页面标题、说明文案、健康状态区。
- `web/src/components/console/metric-grid.tsx`
  - 统一指标卡容器与指标卡单元。
- `web/src/components/console/panel.tsx`
  - 统一带标题的控制台面板骨架。
- `web/src/components/console/empty-state.tsx`
  - 统一空态、错误态、加载态容器。
- `web/src/components/console/status-pill.tsx`
  - 统一状态标签语义和映射。
- `web/src/components/console/detail-link.tsx`
  - 统一详情跳转入口。
- `web/src/components/console/index.ts`
  - 统一导出。
- `web/src/styles/tokens.css`
  - 颜色、圆角、阴影、字体、间距 token。
- `web/src/styles/shell.css`
  - 控制台整体布局与导航。
- `web/src/styles/components.css`
  - 共享组件样式。
- `web/src/styles/features.css`
  - 仍保留页面级样式，但只放 feature 特有规则。
- `web/src/features/stories/stories-page.test.tsx`
  - 审核队列交互与筛选测试。
- `web/src/features/ops/ops-dashboard-page.test.tsx`
  - 总览指标与详情链接测试。
- `web/src/features/ingestion/ingestion-runs-page.test.tsx`
  - 来源治理与手动触发交互测试。

## 当前阶段范围

本阶段只处理前端界面整改，不改后端接口契约，不新增后端业务流程。范围聚焦于：

- 文案、编码与导航基线纠偏
- 共享视觉与组件基线收敛
- 总览与监控页统一
- 审核队列的决策交互增强
- 编辑工作台可用性整改
- 列表页一致性与响应式补齐

不纳入本阶段的内容：

- 新的后端审核状态机
- 新的发布平台能力
- LLM provider 与 embedding 功能
- 生产部署或监控栈变更

## 补充自查结论

除 [docs/frontend-review.md](/D:/Code/Project/FetchNews/docs/frontend-review.md) 外，基于当前代码又发现以下问题，已纳入本计划：

- 文案语言混用严重。
  - `main.tsx` 导航、`ops-dashboard-page.tsx`、`ops-detail-page.tsx`、`ingestion-runs-page.tsx`、`article-*` 多处仍为英文界面，不符合面向中文编辑团队的控制台定位。
- 存在疑似编码损坏。
  - `features/auth/login-page.tsx` 与 `lib/api.ts` 中部分中文文案已显示为 `???`，这不是风格问题，而是直接影响可用性和可信度的缺陷。
- 存在 SPA 路由连续性问题。
  - `article-history-panel.tsx`、`article-history-detail-page.tsx` 等处仍使用内部 `href` 跳转，容易触发整页刷新，破坏单页应用体验。
- `preview-dashboard.tsx` 与真实总览页割裂。
  - 当前样板页定义了一套视觉结构，但主路由未真正把它纳入产品化路径，导致“样板”和“真实页面”长期并行。
- `styles.css` 规模过大。
  - 当前文件约 2285 行，已经同时承担 token、布局、共享组件和页面特有样式，后续继续扩展会显著提高回归风险。
- 焦点态和可访问性不一致。
  - 当前主要给 `input`、`textarea`、`select` 定义了 focus 样式，但按钮、链接、chip 类交互控件缺少系统性的 `:focus-visible` 策略。
- 登录页仍保留默认凭证预填。
  - `login-page.tsx` 默认写入 `admin / admin-secret`，即使仅用于开发，也不适合作为长期界面默认行为。

### Task 0：修正文案、编码与路由基线

**Files:**
- Modify: `web/src/main.tsx`
- Modify: `web/src/features/auth/login-page.tsx`
- Modify: `web/src/features/ingestion/ingestion-runs-page.tsx`
- Modify: `web/src/features/ops/ops-dashboard-page.tsx`
- Modify: `web/src/features/ops/ops-detail-page.tsx`
- Modify: `web/src/features/articles/article-strategy-rail.tsx`
- Modify: `web/src/features/articles/article-composer.tsx`
- Modify: `web/src/features/articles/article-history-panel.tsx`
- Modify: `web/src/features/articles/article-history-detail-page.tsx`
- Modify: `web/src/lib/api.ts`
- Modify: `web/src/features/auth/login-page.test.tsx`
- Modify: `web/src/features/articles/articles-page.test.tsx`

- [ ] 清理前端界面中的英文导航、英文模块标题和英文操作文案，统一回到中文控制台语境。
- [ ] 修复 `login-page.tsx` 与 `api.ts` 中已经出现的乱码或 `???` 文案，确保文本文件继续保持 UTF-8 无 BOM。
- [ ] 移除登录页默认预填的 `admin / admin-secret`，改成空值或更安全的开发辅助方式。
- [ ] 将内部页面间跳转从 `href="/..."` 收敛为 `Link` 或编程式导航，避免整页刷新。
- [ ] 明确 `preview-dashboard.tsx` 的产品定位：要么纳入真实路由作为视觉回归页，要么只作为共享组件来源，避免继续漂浮为孤立样板。
- [ ] 更新对应测试快照和断言，确保中文文案、导航和路由行为一致。
- [ ] 提交一个只做“文案、编码与路由基线纠偏”的独立 commit。

验证命令：

```bash
npm.cmd run test:run
npm.cmd run build
```

### Task 1：收敛前端样式与共享控制台组件

**Files:**
- Create: `web/src/components/console/page-header.tsx`
- Create: `web/src/components/console/metric-grid.tsx`
- Create: `web/src/components/console/panel.tsx`
- Create: `web/src/components/console/empty-state.tsx`
- Create: `web/src/components/console/status-pill.tsx`
- Create: `web/src/components/console/detail-link.tsx`
- Create: `web/src/components/console/index.ts`
- Create: `web/src/styles/tokens.css`
- Create: `web/src/styles/shell.css`
- Create: `web/src/styles/components.css`
- Create: `web/src/styles/features.css`
- Modify: `web/src/styles.css`
- Modify: `web/src/main.tsx`
- Test: `web/src/lib/api.test.ts`

- [ ] 盘点 `styles.css` 中已经跨页面复用的 token、面板、指标卡、按钮、状态标签、详情链接、空状态和布局规则。
- [ ] 把全局 token 与控制台壳层样式拆出到 `tokens.css` 和 `shell.css`，保持现有视觉方向不变。
- [ ] 把共享组件样式拆到 `components.css`，将页面特有样式留在 `features.css`。
- [ ] 新建 `console` 组件目录，把页面标题、指标卡、面板、状态标签、详情入口、空状态收敛为复用组件。
- [ ] 为按钮、链接、筛选 chip、切换按钮统一补上 `:focus-visible` 策略，避免只给表单控件定义焦点态。
- [ ] 修改 `main.tsx`，让导航壳层优先消费共享组件和统一样式入口，避免继续在页面中复制 hero / metric / panel 结构。
- [ ] 运行前端现有测试，确保 API 映射与壳层入口未被破坏。
- [ ] 提交一个只做“样式收敛 + 共享组件抽取”的独立 commit。

验证命令：

```bash
npm.cmd run test:run
npm.cmd run build
```

### Task 2：把预览样板升级为真实总览组件基线

**Files:**
- Modify: `web/src/features/preview/preview-dashboard.tsx`
- Modify: `web/src/features/ops/ops-dashboard-page.tsx`
- Modify: `web/src/features/ops/ops-detail-page.tsx`
- Modify: `web/src/components/console/page-header.tsx`
- Modify: `web/src/components/console/metric-grid.tsx`
- Modify: `web/src/components/console/panel.tsx`
- Test: `web/src/features/ops/ops-dashboard-page.test.tsx`

- [ ] 将 `preview-dashboard.tsx` 中已验证有效的视觉区块，拆成可接收动态数据的总览组件，而不是继续保留为纯静态样板。
- [ ] 整理 `ops-dashboard-page.tsx` 中已经存在的真实总览模块，改为直接使用共享总览组件。
- [ ] 校准总览页与详情页的语义一致性，统一状态文字、状态标签和详情跳转按钮样式。
- [ ] 保留 `preview-dashboard.tsx` 作为视觉回归页或内部展示页，但不再让它单独定义另一套结构。
- [ ] 为 `ops-dashboard-page` 增加测试，覆盖指标渲染、告警卡展示和详情跳转入口。
- [ ] 提交一个只做“总览页与预览基线统一”的独立 commit。

验证命令：

```bash
npm.cmd run test:run
npm.cmd run build
```

### Task 3：增强审核队列的决策交互

**Files:**
- Modify: `web/src/features/stories/stories-page.tsx`
- Modify: `web/src/lib/api.ts`
- Modify: `web/src/styles/features.css`
- Create: `web/src/features/stories/stories-page.test.tsx`

- [ ] 重新梳理 `stories-page.tsx` 的信息层级，把“筛选区、风险总览、story 列表、normalized items”做更明确的主次拆分。
- [ ] 在现有单条批准基础上，预留更清晰的决策位，包括拒绝、复核标记、批量操作入口的 UI 占位和状态反馈。
- [ ] 增强 source links、risk flags、sections 的呈现方式，让审核员能更快判断 story 是否可进入草稿链路。
- [ ] 统一列表页中的筛选、排序、空态、错误态呈现方式，避免 stories 页面继续形成私有交互风格。
- [ ] 为 stories 页面新增测试，覆盖筛选、审核操作反馈、空态和错误态。
- [ ] 提交一个只做“审核页决策交互整改”的独立 commit。

验证命令：

```bash
npm.cmd run test:run -- stories-page
npm.cmd run build
```

### Task 4：整改三栏编辑工作台的可用性

**Files:**
- Modify: `web/src/features/articles/articles-page.tsx`
- Modify: `web/src/features/articles/article-strategy-rail.tsx`
- Modify: `web/src/features/articles/article-composer.tsx`
- Modify: `web/src/features/articles/article-history-panel.tsx`
- Modify: `web/src/features/articles/article-history-detail-page.tsx`
- Modify: `web/src/features/articles/article-editor-types.ts`
- Modify: `web/src/lib/editorial-api.ts`
- Modify: `web/src/styles/features.css`
- Modify: `web/src/features/articles/articles-page.test.tsx`

- [ ] 重新定义三栏工作台的视觉主次，明确“策略与范围”“正文编辑”“历史与发布”三栏的阅读入口和操作节奏。
- [ ] 降低中栏与右栏操作互相干扰的程度，突出当前选中文稿、待保存 block、锁定 block、重建范围和恢复版本。
- [ ] 强化版本历史与 diff 的可读性，避免用户在当前历史面板中难以判断“改了什么、何时可恢复”。
- [ ] 重新组织发布编排区和平台反馈区，把“创建发布任务、执行、轮询、手工纠正、反馈写回”整理为更清晰的顺序。
- [ ] 为文章页补更多测试，优先覆盖 block 编辑、版本恢复、重建操作和发布区状态变化。
- [ ] 提交一个只做“编辑工作台可用性整改”的独立 commit。

验证命令：

```bash
npm.cmd run test:run -- articles-page
npm.cmd run build
```

### Task 5：统一 ingestion / ops / publishing 的列表页体验

**Files:**
- Modify: `web/src/features/ingestion/ingestion-runs-page.tsx`
- Modify: `web/src/features/ops/ops-dashboard-page.tsx`
- Modify: `web/src/features/ops/ops-detail-page.tsx`
- Modify: `web/src/styles/features.css`
- Create: `web/src/features/ingestion/ingestion-runs-page.test.tsx`
- Modify: `web/src/components/console/status-pill.tsx`
- Modify: `web/src/components/console/empty-state.tsx`

- [ ] 把 ingestion、ops、publishing 相关列表中的状态标签、时间信息、错误信息、chip 和详情入口统一成同一套语义。
- [ ] 优先修正 ingestion 页中的来源治理卡、手动触发区和批次历史区的视觉密度，让其更接近“运营控制台”而不是功能拼盘。
- [ ] 校准 ops detail 和 ops dashboard 的 drill-down 体验，确保用户从总览点击进入详情后仍能保持上下文连续。
- [ ] 补齐共享空态、错误态、加载态的细节，让页面在无数据和接口异常时也保持一致观感。
- [ ] 为 ingestion 和 ops 总览增加基础交互测试。
- [ ] 提交一个只做“列表页一致性整改”的独立 commit。

验证命令：

```bash
npm.cmd run test:run
npm.cmd run build
```

### Task 6：补齐响应式与视觉细节收尾

**Files:**
- Modify: `web/src/styles/features.css`
- Modify: `web/src/styles/components.css`
- Modify: `web/src/features/auth/login-page.tsx`
- Modify: `web/src/features/auth/login-page.test.tsx`
- Modify: `web/src/main.tsx`

- [ ] 针对 1400px、980px、620px 三个关键断点，逐页检查导航、指标卡、列表行、三栏工作台和详情页的布局退化情况。
- [ ] 优先修正窄屏下的三栏工作台、ops 卡片网格、长链接、按钮排布和 chip 换行问题。
- [ ] 收尾登录页视觉细节，补上更符合规范的输入框和按钮质感，并增加显示/隐藏密码交互。
- [ ] 做一轮统一的 hover、focus、disabled、saving、loading 微交互检查，确保动效克制且语义清晰。
- [ ] 提交一个只做“响应式与细节收尾”的独立 commit。

验证命令：

```bash
npm.cmd run test:run
npm.cmd run build
```

## 最终验收

- [ ] `web/` 构建通过。
- [ ] 前端测试通过，至少覆盖 `stories`、`articles`、`ingestion`、`ops` 的关键交互。
- [ ] 总览页、审核页、编辑工作台、ingestion 页、ops 详情页在视觉语言上明显统一。
- [ ] 页面不再依赖单个超大 `styles.css` 继续堆叠特性。
- [ ] 新增文档与注释继续遵守中文约束。

最终验证命令：

```bash
npm.cmd run test:run
npm.cmd run build
python -m pytest
```
