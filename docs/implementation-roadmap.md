# FetchNews 实施路线

## Phase 0: 仓库基础

目标：
- 建立项目说明、协作约定、架构文档和环境模板
- 形成统一的目录与模块边界

当前状态：
- 已完成

详细计划：
- [phase-00-docs-and-decisions.md](/D:/Code/Project/FetchNews/docs/project-plan/phase-00-docs-and-decisions.md)

## Phase 1: 应用骨架

目标：
- 建立 `fetchnews/` 包结构
- FastAPI 应用入口
- 配置管理
- 数据库连接和初始化
- 建立 `web/` React SPA 骨架
- 建立前后端 API 通信基础

交付物：
- `fetchnews/main.py`
- `fetchnews/core/`
- `fetchnews/db/`
- `fetchnews/models/`
- `web/src/`

详细计划：
- [phase-01-foundation.md](/D:/Code/Project/FetchNews/docs/project-plan/phase-01-foundation.md)

## Phase 2: 来源采集

目标：
- 建立来源目录和连接器注册表
- 接入 GitHub、arXiv、RSS、X 白名单来源
- 原始抓取结果入库

交付物：
- `sources`
- `raw_items`
- 手动触发采集 API

详细计划：
- [phase-02-ingestion.md](/D:/Code/Project/FetchNews/docs/project-plan/phase-02-ingestion.md)

## Phase 3: 标准化与聚类

目标：
- URL 归一化
- 标题相似度聚类
- 事件评分
- story 生成

交付物：
- `normalized_items`
- `stories`
- `GET /stories`

详细计划：
- [phase-03-normalize-and-cluster.md](/D:/Code/Project/FetchNews/docs/project-plan/phase-03-normalize-and-cluster.md)

## Phase 4: 内容生成

目标：
- 单条 story 摘要
- 中文日报生成
- 短帖派生

交付物：
- `article_drafts`
- `post_variants`
- `POST /articles/generate/daily`

详细计划：
- [phase-04-content-generation.md](/D:/Code/Project/FetchNews/docs/project-plan/phase-04-content-generation.md)

## Phase 5: 审核与发布

目标：
- React SPA 审核后台
- story 审核
- 发布队列
- 发布任务状态查询

交付物：
- `POST /stories/{id}/approve`
- `POST /articles/{id}/publish`
- `GET /publish-jobs`
- React 审核页面

详细计划：
- [phase-05-review-and-publishing.md](/D:/Code/Project/FetchNews/docs/project-plan/phase-05-review-and-publishing.md)

## Phase 6: 质量优化

目标：
- 来源权重优化
- 风险标签
- 失败重试
- 周报/月报扩展

交付物：
- 更稳定的聚类和排序
- 更成熟的运营能力

详细计划：
- [phase-06-optimization-and-operations.md](/D:/Code/Project/FetchNews/docs/project-plan/phase-06-optimization-and-operations.md)

## 计划总入口

- [项目计划目录](/D:/Code/Project/FetchNews/docs/project-plan/README.md)
- [总体项目计划](/D:/Code/Project/FetchNews/docs/project-plan/00-master-plan.md)
