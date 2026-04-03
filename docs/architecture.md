# FetchNews 系统架构

## 1. 目标与范围

`FetchNews` 的 V1 目标不是做一个全自动媒体矩阵，而是构建一条稳定、可审核、可重试的 AI 资讯生产线。

V1 交付重点：

- 定时抓取高价值 AI 来源
- 原始事件入库
- 标准化、去重、聚类与评分
- 生成中文日报、周报、月报与多平台短帖
- 经过人工审核后再进入发布链路

V1 暂不追求：

- 面向外部用户的公开内容门户
- 复杂的多组织权限系统
- 高度自动化的无人值守媒体矩阵

## 2. 整体技术架构

当前采用“模块化单体后端 + React SPA 前端”的架构：

- 后端：`FastAPI` 提供 REST API、任务编排入口和平台集成
- 前端：`React SPA` 提供内部审核与运营控制台
- 异步任务：`Celery + Redis`
- 数据库：`PostgreSQL`

这样设计的原因：

- 当前复杂度集中在采集、处理、生成、审核和发布流程，而不是 SEO
- 审核台是典型内部后台，更适合 SPA
- 单仓模块化更利于快速迭代，避免过早拆成微服务

## 3. 分层结构

### 3.1 来源采集层

职责：

- 定时或手动触发来源抓取
- 支持 API、RSS、HTML 抓取以及有限的动态页面抓取
- 统一写入 `raw_items`

输入：

- 来源目录配置
- 白名单、凭证和启用状态

输出：

- 原始资讯事件
- 采集批次记录

### 3.2 标准化与富化层

职责：

- 提取统一字段：标题、作者、链接、发布时间、摘要、正文、标签
- 规整 URL、清洗追踪参数、识别语言
- 提取关键词与基础主题信号

输出：

- `normalized_items`

### 3.3 聚类与排序层

职责：

- 将同一事件的多来源内容聚合成 `stories`
- 结合来源可信度、时效、热度和治理反馈进行评分
- 形成后续内容生成与审核的核心事件列表

聚类信号包括：

- canonical URL
- 标题近似度
- 来源之间的交叉引用
- 后续可扩展的 embedding 相似度

### 3.4 内容生成层

职责：

- 为每个 `story` 生成中文摘要、亮点和风险说明
- 基于已审核 `stories` 生成日报、周报、月报草稿
- 为 `wechat`、`x`、`telegram` 生成平台变体
- 将来源治理、栏目势能和平台反馈注入排序与文案策略

### 3.5 审核与发布层

职责：

- 审核 `story` 与文章草稿
- 编辑标题、摘要、正文与平台变体
- 创建发布任务、回写结果、失败重试与互动反馈

### 3.6 运维与治理层

职责：

- 汇总采集、审核、发布与失败诊断指标
- 输出来源治理反馈、栏目势能、平台表现
- 形成运营建议与告警

## 4. 前端架构

前端采用 `React SPA + Vite + TypeScript`，核心定位是“内部审核控制台”，不是公开内容站。

页面能力覆盖：

- 运维首页
- 采集监控
- story 审核
- 草稿中心
- 发布队列与回写
- drill-down 详情页

当前视觉方向已经固定：

- 风格名：`暖白金属极简`
- 主题策略：`浅色优先`
- 气质关键词：`企业秩序感`、`可信`、`克制`、`轻未来感`

参考文档：

- [docs/frontend-style.md](/D:/Code/Project/FetchNews/docs/frontend-style.md)

## 5. 核心数据流

```text
来源配置
  -> 采集任务
  -> raw_items
  -> normalized_items
  -> stories
  -> article_drafts + post_variants
  -> 人工审核
  -> publish_jobs
  -> 平台执行与结果回写
  -> 治理反馈与排序优化
```

## 6. 核心数据模型

### `sources`

- 来源定义
- 平台类型
- 优先级
- 白名单规则
- 抓取配置

### `ingest_runs`

- 每次采集批次记录
- 采集成功数、失败数、错误详情

### `raw_items`

- 原始抓取结果
- 原始标题、正文、链接、作者、时间、负载

### `normalized_items`

- 标准化标题
- canonical URL
- 标签、关键词、语言、摘要

### `stories`

- 聚类后的事件实体
- 聚合来源链接
- 亮点、风险标记、评分、审核状态

### `article_drafts`

- 日报、周报、月报草稿
- 标题、摘要、正文、状态、生成说明

### `post_variants`

- 多平台短帖版本
- 平台、内容、更新时间

### `publish_jobs`

- 发布平台、时间、状态、重试次数、外部任务 ID、效果指标

### `audit_logs`

- 登录、审核、生成、发布、回写等关键动作的审计记录

## 7. 推荐目录结构

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
    components/
    features/
    lib/
```

职责边界：

- `fetchnews/` 负责 API、模型、任务、采集和内容处理
- `web/` 负责内部控制台
- `web/src/features/` 按业务域拆分，例如 `stories`、`articles`、`ops`

## 8. 前后端职责边界

### 后端职责

- 采集、标准化、聚类、生成、发布与运维汇总
- 统一权限、审计、幂等与状态管理
- 暴露 REST API，作为业务真相来源

### 前端职责

- 审核、预览、筛选、编辑与发布操作
- 展示指标、告警、日志与 drill-down 明细
- 消费 API，不承载业务真相

## 9. 核心 API 边界

当前保留的关键接口：

- `POST /ingest/run`
- `GET /ingest/runs`
- `GET /stories`
- `POST /stories/{id}/approve`
- `POST /articles/generate/daily`
- `POST /articles/generate/weekly`
- `POST /articles/generate/monthly`
- `GET /articles`
- `GET /articles/{id}`
- `GET /articles/{id}/variants`
- `POST /articles/{id}/publish`
- `GET /publish-jobs`
- `POST /publish-jobs/{id}/retry`
- `GET /ops/summary`

## 10. 部署建议

本地开发推荐：

- 宿主机 PostgreSQL
- `docker compose run --rm migrate`
- `docker compose up api worker beat web redis`

V1 不急于上 Kubernetes，先保证本地与生产环境保持近似形态即可。

## 11. 风控原则

- 白名单优先
- 一手来源优先于二手转载
- 对“传闻”“未证实”“二次转载”单独打标
- 发布失败必须支持幂等重试
- 所有文章段落都必须能回溯到 `story` 与来源链路

## 12. 文档约束

- 项目内所有自有文档统一使用中文撰写
- 允许保留必要的英文技术名词，但必须处于中文语境中
- 新增架构、计划、规范、状态、启动与设计文档时必须遵守该约束