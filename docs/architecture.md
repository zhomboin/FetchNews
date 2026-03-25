# FetchNews 系统架构

## 1. 目标与范围

`FetchNews` 的 V1 目标不是做一个全自动媒体矩阵，而是做一条稳定、可审阅、可重试的 AI 资讯生产线。

V1 交付重点：

- 定时抓取高价值 AI 来源
- 原始事件入库
- 标准化、去重、聚类与打分
- 生成中文日报长文和多平台短帖
- 人工审核后进入发布队列

V1 暂不追求：

- 公开内容门户
- 多角色权限系统
- 复杂外部用户前台

## 2. 整体技术架构

V1 采用“模块化单体后端 + React SPA 前端”的结构：

- 后端：`FastAPI` 提供 REST API、工作流编排入口和平台集成
- 前端：`React SPA` 提供内部审核与运营控制台
- 异步任务：`Celery + Redis`
- 数据库：`PostgreSQL`

这样设计的原因：

- 审核台是内部系统，交互复杂，更适合 SPA
- 当前核心复杂度在采集、处理、生成与发布，而不是 SEO
- 保持单仓模块化，避免过早拆成微服务

## 3. 分层架构

### 3.1 Source Ingestion

职责：

- 定时或手动触发来源抓取
- 支持 API、RSS、HTML 抓取和有限的动态页面抓取
- 将结果写入 `raw_items`

输入：

- 来源配置
- 凭证和白名单

输出：

- 原始资讯事件

### 3.2 Normalize & Enrich

职责：

- 提取统一字段：标题、作者、URL、发布时间、正文、标签
- 规范化 URL
- 做语言识别、必要翻译和关键词提取
- 补充基础热度和可信度信号

输出：

- `normalized_items`

### 3.3 Ranking & Clustering

职责：

- 将同一事件的多来源内容聚合为一个 `story`
- 根据来源可信度、时效、热度和相关度计算分数
- 形成可审核的聚类结果

聚类优先规则：

- 相同 canonical URL
- 高相似标题
- 白名单来源的交叉引用

### 3.4 Content Generation

职责：

- 为每个 `story` 生成中文摘要、亮点和风险说明
- 基于当日 `stories` 生成长文草稿
- 派生 X、微博、即刻、Telegram 等短帖版本

要求：

- 每个聚合事件都必须保留来源引用
- 长文和短帖都必须能回溯到对应 `story`

### 3.5 Review & Publishing

职责：

- 审核 `story` 和文章草稿
- 编辑标题、排序、删除和驳回
- 写入发布队列并记录发布结果

### 3.6 Frontend Console

职责：

- 展示今日采集概览、审核队列、草稿、日志和发布队列
- 提供审核、编辑、预览、发布和重试操作
- 仅通过 REST API 与后端通信

## 4. 核心数据流

```text
React SPA
  -> FastAPI REST API
  -> source config / manual actions
  -> ingestion workers
  -> raw_items
  -> normalized_items
  -> clustered stories
  -> article_drafts + post_variants
  -> review / approval
  -> publish_jobs
  -> platform delivery
```

## 5. 核心数据模型

### sources

- 来源定义
- 平台类型
- 优先级
- 白名单规则
- 抓取配置

### raw_items

- 原始抓取内容
- 第三方平台元数据
- 原文快照或正文

### normalized_items

- 规范化标题
- canonical URL
- 作者、语言、标签
- 标准化摘要

### stories

- 聚类后的事件实体
- 主标题、摘要、亮点、来源链路
- 分数、风险标记、审核状态

### article_drafts

- 每日文章草稿
- 标题、导语、正文、摘要
- 草稿状态

### post_variants

- 不同平台的短内容版本
- 平台、文案和状态

### publish_jobs

- 发布计划
- 平台、时间、状态、重试次数、外部 ID

### audit_logs

- 抓取、生成、审核和发布的审计记录

## 6. 推荐目录结构

```text
docs/
tests/
fetchnews/
  api/
    routes/
  core/
  db/
  models/
  pipeline/
  publishing/
  sources/
    connectors/
    catalog.py
  tasks/
  main.py
web/
  src/
    app/
    components/
    features/
    lib/
  public/
  package.json
```

目录职责：

- `fetchnews/` 负责 API、任务、数据模型、抓取和内容处理
- `web/` 负责内部审核控制台
- `web/src/features/` 按业务域拆分，如 `stories`、`articles`、`publish-jobs`

## 7. 前后端职责边界

### 后端职责

- 抓取、标准化、聚类、内容生成和发布编排
- 暴露 REST API
- 统一权限、审计和幂等控制

### 前端职责

- 审核与运营交互
- 列表筛选、预览、表单提交、发布操作
- 只消费 API，不内嵌业务真相

### 为什么不选 Next.js

- 当前不是 SEO 驱动的公开内容站
- 审核台更接近后台系统，SPA 更直接
- 避免同时维护 React 服务端渲染逻辑和 Python 工作流系统

## 8. 前端体验与视觉基线

当前正式确认的后台视觉方向：

- 风格名：`暖白金属极简`
- 主题模式：`浅色优先`
- 气质：`企业秩序感 + 轻未来感`

页面应统一服务于以下后台场景：

- 内容审核
- 统计图表
- 日报草稿预览
- 系统日志与发布排程

设计原则：

- 先保证信息效率，再表达 AI 气质
- AI 感通过细网格、轨迹线、金属高光和状态提示体现
- 不使用赛博朋克霓虹、重玻璃拟态和夸张装饰
- 图表、日志、审核卡片都应采用统一控制台语言

参考与规范：

- [docs/frontend-style.md](/D:/Code/Project/FetchNews/docs/frontend-style.md)
- [docs/assets/fetchnews-warm-metal-preview.png](/D:/Code/Project/FetchNews/docs/assets/fetchnews-warm-metal-preview.png)

## 9. API 边界

保留以下核心接口：

- `POST /ingest/run`
- `GET /stories`
- `POST /stories/{id}/approve`
- `POST /articles/generate/daily`
- `GET /articles/{id}`
- `POST /articles/{id}/publish`
- `GET /publish-jobs`

推荐补充的前端接口：

- `GET /dashboard/summary`
- `GET /articles/{id}/variants`
- `POST /publish-jobs/{id}/retry`

## 10. 后端实现建议

### 应用层

- `FastAPI` 仅提供 API
- 用 Pydantic schema 明确请求和响应契约
- 本地前后端通过 CORS 对接

### 数据层

- 使用 `SQLAlchemy 2.x`
- 正式环境按 `PostgreSQL` 设计

### 异步任务

- 使用 `Celery + Redis`
- 任务分为：抓取、处理、生成、发布

### 内容生成层

- 抽象 LLM provider 接口
- 支持 fallback 模板生成
- 输出必须附来源引用上下文

## 11. 前端实现建议

推荐技术栈：

- `React 18`
- `Vite`
- `TypeScript`
- `React Router`
- `TanStack Query`
- `Zustand`
- `Tailwind CSS`

页面范围：

- 仪表盘
- 审核队列
- 日报草稿编辑与预览
- 平台短帖预览
- 发布队列与失败重试

约束：

- 不做公开门户
- 不做服务端渲染
- 所有页面默认按内部运营场景设计

## 12. 部署建议

开发环境使用 `Docker Compose`：

- `api`
- `worker`
- `beat`
- `web`
- `postgres`
- `redis`

生产环境 V1 保持同构部署即可，不急于迁移 `Kubernetes`。

## 13. 风控原则

- 白名单优先
- 不以中文转载站为唯一来源
- 对“传闻”“未证实”“二次转载”单独打标
- 发布失败必须幂等重试
- 所有文章段落都必须能回溯到 `story` 与来源链路

## 14. 结论

当前正式选型：

- 后端：`FastAPI + SQLAlchemy + PostgreSQL + Celery + Redis`
- 前端：`React SPA + Vite + TypeScript`
- 视觉基线：`暖白金属极简，浅色优先，企业秩序感 + 轻未来感`