# FetchNews 总体项目计划

## 1. 总体目标

建设一套面向中文 AI 从业者的资讯生产与分发系统，能够每天从高价值来源自动抓取信息，经过标准化、聚类和摘要后，生成可审阅的中文日报与多平台短帖，并在人工审核后完成定时发布。

## 2. 业务目标

核心业务目标：
- 提高 AI 资讯采集效率
- 减少重复搬运和低价值噪声
- 形成稳定的每日内容生产流程
- 支持多平台分发而不丢失来源可追溯性

V1 成功标准：
- 每天稳定产出 1 篇可审阅日报草稿
- P0 来源抓取成功率达到可持续运行水平
- 同一事件能有效聚类，减少重复稿件
- 审核台能完成 story 审核、文章预览和发布触发
- 发布记录、失败重试和审计链路可查询

## 3. 技术目标

- 后端采用模块化单体，避免过早微服务化
- 前端采用 React SPA 审核控制台
- 数据层以 PostgreSQL 为中心，Redis 承担队列与缓存职责
- 所有核心流水线均可通过异步任务调度
- 前后端通过稳定 REST API 解耦

## 4. 阶段拆分

### Phase 00: 文档与决策基线
目标：建立统一的项目说明、架构决策、来源范围和计划入口。
文档： [phase-00-docs-and-decisions.md](/D:/Code/Project/FetchNews/docs/project-plan/phase-00-docs-and-decisions.md)

### Phase 01: 应用骨架
目标：建立 `fetchnews/` 后端骨架与 `web/` React SPA 骨架，打通最小开发链路。
文档： [phase-01-foundation.md](/D:/Code/Project/FetchNews/docs/project-plan/phase-01-foundation.md)

### Phase 02: 来源接入
目标：接入 GitHub、arXiv、RSS、X 白名单来源，并完成原始内容入库。
文档： [phase-02-ingestion.md](/D:/Code/Project/FetchNews/docs/project-plan/phase-02-ingestion.md)

### Phase 03: 标准化与聚类
目标：将原始内容转为统一 schema，并完成去重、聚类和评分。
文档： [phase-03-normalize-and-cluster.md](/D:/Code/Project/FetchNews/docs/project-plan/phase-03-normalize-and-cluster.md)

### Phase 04: 内容生成
目标：为 story 生成摘要，并生成日报长文和多平台短帖。
文档： [phase-04-content-generation.md](/D:/Code/Project/FetchNews/docs/project-plan/phase-04-content-generation.md)

### Phase 05: 审核与发布
目标：完成 React SPA 审核台、发布队列和平台分发。
文档： [phase-05-review-and-publishing.md](/D:/Code/Project/FetchNews/docs/project-plan/phase-05-review-and-publishing.md)

### Phase 06: 质量优化与运营能力
目标：提升稳定性、来源质量、排序效果和周报月报能力。
文档： [phase-06-optimization-and-operations.md](/D:/Code/Project/FetchNews/docs/project-plan/phase-06-optimization-and-operations.md)

## 5. 阶段依赖关系

推荐顺序：
1. Phase 00
2. Phase 01
3. Phase 02
4. Phase 03
5. Phase 04
6. Phase 05
7. Phase 06

关键依赖：
- Phase 02 依赖 Phase 01 的基础工程与数据库
- Phase 03 依赖 Phase 02 的原始数据入库
- Phase 04 依赖 Phase 03 的 `stories`
- Phase 05 同时依赖 Phase 01 的前端骨架和 Phase 04 的文章资产
- Phase 06 建立在前五个阶段可运行的基础上

## 6. 里程碑定义

- 里程碑 A：仓库与前后端骨架可本地启动
- 里程碑 B：P0 来源能够抓取并入库
- 里程碑 C：story 聚类与日报草稿自动生成
- 里程碑 D：审核台支持人工审核与发布触发
- 里程碑 E：系统具备稳定运行和优化基础

## 7. 当前状态

已完成：
- 基础说明文档
- 架构选型
- 来源清单
- 分阶段计划拆分

未完成：
- 业务代码
- API 与数据库模型
- React SPA 审核台
- 抓取器、生成器和发布器实现
