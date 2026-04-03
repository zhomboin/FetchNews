# FetchNews 编辑工作台设计

## 目标

将当前草稿中心扩展为完整的编辑工作台，支持：

- 更细的周报 / 月报栏目配额模板
- 更强的平台文案策略，通过可选模板控制 `wechat`、`x`、`telegram`
- 段落级锁定、混合重建、版本对比、恢复与人工干预历史

该设计在不破坏现有采集、story、草稿、发布与运维链路的前提下，替换当前过于粗粒度的草稿编辑层。

## 用户确认过的关键决策

本设计基于以下已确认选择：

- 工作台结构：`B. 三栏编排工作台`
- 重建策略：`混合模式`
- 编辑粒度：`段落级`
- 周报 / 月报配额策略：`模板策略`
- 平台文案控制方式：`可选模板`

## 推荐方案

不要继续拉伸当前“整篇字符串草稿”模型，而是引入聚焦的编辑模型：

- 用 digest template 管理周报 / 月报栏目配额
- 用块级内容模型管理标题、摘要、导语、栏目块和 CTA
- 用 revision 快照管理生成、编辑、重建、恢复和模板切换历史
- 用 editorial action 记录人工干预动作

这是当前最能承载“段落级锁定 + 混合重建 + 版本恢复”的方案，同时复杂度仍然可控。

## 工作台布局

后台采用三栏结构：

### 左栏：策略区

职责：

- 选择 digest template
- 预览栏目配额和栏目顺序
- 选择 `wechat`、`x`、`telegram` 平台模板
- 配置重建策略
- 触发重建

左栏只负责生成策略，不直接承载正文编辑。

### 中栏：段落编排区

职责：

- 编辑内容块
- 锁定 / 解锁内容块
- 调整块顺序
- 查看栏目结构
- 在重建前识别 stale reference

中栏是正文内容的唯一主编辑面。

### 右栏：历史与渠道区

职责：

- 查看 revision 历史
- 查看 revision diff
- 从历史版本恢复并生成新版本
- 预览和编辑平台专属块
- 查看发布前状态

右栏负责可追溯性和渠道内容，不承载主正文编排。

## 数据模型

### 保留的现有模型

以下模型继续保留，作为系统主骨架：

- `Story`
- `ArticleDraft`
- `PostVariant`
- `PublishJob`
- `AuditLog`

`ArticleDraft` 仍是草稿顶层记录和发布目标。

### 新增模型

#### `DigestTemplate`

用途：

- 存储周报 / 月报可复用模板

建议字段：

- `id`
- `name`
- `period_type`
- `description`
- `section_quotas`
- `section_order`
- `default_platform_templates`
- `is_default`
- `created_at`
- `updated_at`

`section_quotas` 建议以 JSON 存储，例如：

```json
{
  "research": 0.35,
  "open_source": 0.25,
  "product": 0.20,
  "signals": 0.20
}
```

#### `ArticleRevision`

用途：

- 为每一个有意义的草稿状态建立版本

建议字段：

- `id`
- `article_id`
- `version_number`
- `change_type`
- `change_note`
- `template_id`
- `snapshot`
- `created_by_user_id`
- `created_at`

`snapshot` 用来保存块状态与平台模板选择，以便可靠恢复。

#### `ArticleBlock`

用途：

- 取代单体 `body` 文本，支持段落级编辑

建议字段：

- `id`
- `article_id`
- `revision_id`
- `block_key`
- `block_type`
- `section_key`
- `platform_scope`
- `story_id`
- `title`
- `content`
- `sort_order`
- `is_locked`
- `is_manual`
- `metadata`
- `created_at`
- `updated_at`

支持的块类型至少包括：

- `title`
- `summary`
- `intro`
- `section_heading`
- `story_paragraph`
- `section_wrapup`
- `cta`
- `platform_hook`
- `platform_body`
- `platform_cta`

#### `EditorialAction`

用途：

- 记录细粒度人工干预动作

建议字段：

- `id`
- `article_id`
- `revision_id`
- `actor_user_id`
- `action_type`
- `target_type`
- `target_id`
- `detail`
- `created_at`

典型动作：

- `lock_block`
- `unlock_block`
- `edit_block`
- `move_block`
- `switch_digest_template`
- `switch_platform_template`
- `rebuild_article`
- `restore_revision`

## 生成与重建流程

### 1. 基线生成

生成草稿时：

1. 确定目标 `period_type`
2. 确定所选或默认 digest template
3. 排序候选 stories
4. 应用栏目配额和栏目顺序
5. 生成正文 blocks
6. 根据平台模板生成平台 blocks
7. 创建 `ArticleRevision(version 1)` 或新的重建版本

### 2. 人工编辑

编辑不再直接改整篇 `body` 字符串，而是修改 `ArticleBlock`：

- 改写内容
- 锁定或解锁内容块
- 调整块顺序
- 标记人工覆盖

后端负责将 blocks 重新组装为：

- `ArticleDraft.body`
- `PostVariant.content`

### 3. 混合重建

混合重建规则：

- 已锁定正文块保留
- 未锁定正文块重生成
- 已锁定平台块保留
- 未锁定平台块重生成
- 栏目配额仅对未锁定内容组重新分配
- 如果锁定块引用的 story 已被移除，则保留块内容，但打上 `stale_reference`

同时提供一个显式危险操作：

- `force_full_rebuild`

该操作忽略锁定，但仍然创建新 revision，而不是覆盖历史。

### 4. 恢复

恢复版本时，不直接覆盖历史，而是：

1. 复制目标 revision 的 snapshot
2. 创建一个新的 `restore` revision
3. 将该新版本设为当前有效版本

这样可以保持版本链可追溯。

## 模板策略

### 栏目模板（Digest Template）

周报和月报使用模板控制：

- 栏目配额
- 默认栏目顺序
- 默认平台模板
- 可选编辑说明

日报可以继续使用“排序优先”策略，不必套用完整配额体系。

### 平台模板

编辑只选择模板，不开放完全自由编排策略。

首批模板建议：

- `wechat`
  - `editorial_summary`
  - `actionable_roundup`
- `x`
  - `tracking_hook`
  - `headline_push`
- `telegram`
  - `quick_bulletin`
  - `discussion_brief`

模板决定结构、开头风格和 CTA 风格，但仍消费同一批编辑内容块。

## API 设计

### 模板接口

- `GET /templates/digests`
- `POST /templates/digests`
- `PATCH /templates/digests/{id}`

### 草稿生成接口

- `POST /articles/generate`
  - 支持 `period_type`、`target_date`、`story_ids`、`template_id`、`generation_note`
- `POST /articles/{id}/rebuild`
  - 支持重建模式和可选块范围

### 块编辑接口

- `GET /articles/{id}/blocks`
- `PATCH /articles/{id}/blocks/{block_id}`
- `POST /articles/{id}/blocks/reorder`

### 版本接口

- `GET /articles/{id}/revisions`
- `GET /articles/{id}/revisions/{revision_id}`
- `POST /articles/{id}/revisions/{revision_id}/restore`

### 人工干预与审计接口

- `GET /articles/{id}/editorial-actions`

## 前端设计

当前 `/articles` 页面不再只是草稿中心，而是演进为完整编辑工作台。

建议 UI 结构：

- 左栏：策略配置与重建控制
- 中栏：块级正文编辑器
- 右栏：版本历史、diff 与平台块

关键交互：

- 点击块进行编辑
- 行内锁定 / 解锁
- 调整块顺序
- 切换 digest template 并预览配额影响
- 切换各平台模板
- 查看 revision diff
- 恢复历史版本

界面必须延续当前“暖白金属极简”视觉基线。

## 错误处理

### 重建安全

当重建遇到已移除 story 所对应的锁定块时：

- 保留锁定内容
- 将块标记为 stale
- 在工作台显示警告
- 发布前要求人工确认

### 模板安全

如果栏目配额和不规范：

- 后端自动归一化
- 在响应中返回归一化结果
- 记录一条编辑动作日志

### 版本安全

如果恢复失败，例如：

- revision 不存在
- revision 与 article 不匹配
- snapshot 非法

则必须保证当前 active revision 不被破坏。

## 测试策略

### 后端测试

需要覆盖：

- digest template 校验与默认选择
- 周报 / 月报栏目配额分配
- 基于已审核 stories 生成 blocks
- 混合重建保留锁定块
- 全量重建替换锁定块
- restore 流程创建新 revision，而不是篡改旧版本
- 从 blocks 组装文章正文与平台变体
- editorial action 日志写入

### 前端测试

需要覆盖：

- 模板选择与配额预览
- 块锁定 / 解锁
- 块编辑与保存
- revision 列表与恢复动作
- 平台模板切换
- 混合重建确认流程

### 集成测试

至少覆盖：

1. 用某个模板生成周报
2. 锁定标题和导语
3. 手工修改一个段落
4. 重建草稿
5. 确认锁定块被保留、未锁定块发生变化
6. 恢复一个历史 revision
7. 基于恢复后的当前版本发布

## 风险

### 迁移复杂度

当前 `ArticleDraft.body` 过于粗粒度。迁移到块模型时需要：

- 新表
- 旧草稿回填策略
- 过渡期 API 兼容方案

### 界面密度

工作台容易过载。界面必须保持三栏分工明确，并对高级操作做渐进展示。

### 内容漂移

锁定块可能随 story 排序变化而失去语义新鲜度，因此必须在发布前暴露 stale reference。

### 恢复误用

编辑可能误把恢复当成 destructive rollback。系统必须始终采用“从历史版本创建新版本”的策略。

## 分阶段实施建议

### 阶段 A：数据模型与迁移

- 新增 `DigestTemplate`
- 新增 `ArticleRevision`
- 新增 `ArticleBlock`
- 新增 `EditorialAction`
- 编写 Alembic migration
- 为现有草稿回填初始 revision 结构

### 阶段 B：模板引擎

- 实现周报 / 月报模板选择
- 实现栏目配额分配
- 暴露模板 CRUD 接口
- 保持日报兼容

### 阶段 C：块级编辑与混合重建

- 生成 blocks
- 编辑、锁定 blocks
- 重建未锁定块
- 从 blocks 组装正文和平台变体

### 阶段 D：版本历史与恢复

- 增加 revision 列表接口
- 增加 revision 详情与 diff
- 增加 restore 流程
- 增加人工干预日志浏览能力

### 阶段 E：工作台界面集成

- 将 `/articles` 演进为三栏工作台
- 加入模板策略栏
- 加入段落编辑器
- 加入 revision 与平台栏

## 推荐落地顺序

1. 数据模型与迁移
2. 周报 / 月报模板策略
3. 块级草稿组装
4. 混合重建
5. revision diff 与 restore
6. 完整工作台 UI

这个顺序能尽早交付可用能力，同时控制迁移风险。

## 文档语言约束

- 设计 spec 统一使用中文撰写
- 保留必要的英文模型名和接口名，但解释必须为中文