# FetchNews 总体计划

## 总体目标

构建一套面向中文 AI 从业者的资讯生产与分发系统。系统需要持续抓取高价值来源，完成标准化、聚类、草稿生成、多平台派发、人工审核和发布结果回流，并将反馈反向作用于排序、栏目策略和平台文案策略。

## 当前阶段状态

- `阶段 00`：已完成
- `阶段 01`：已完成
- `阶段 02`：基础完成
- `阶段 03`：基础完成
- `阶段 04`：基础完成
- `阶段 05`：基础完成
- `阶段 06`：进行中

详细实现快照：

- [../current-status.md](/D:/Code/Project/FetchNews/docs/current-status.md)

## 阶段拆分

### 阶段 00：文档与决策基线

目标：

- 建立架构、协作规则、风格基线与计划入口

状态：

- 已完成

文档：

- [phase-00-docs-and-decisions.md](/D:/Code/Project/FetchNews/docs/project-plan/phase-00-docs-and-decisions.md)

### 阶段 01：基础骨架

目标：

- 后端骨架
- 前端 SPA 骨架
- 本地编排与验证基线

状态：

- 已完成

文档：

- [phase-01-foundation.md](/D:/Code/Project/FetchNews/docs/project-plan/phase-01-foundation.md)

### 阶段 02：来源采集

目标：

- 来源目录
- 原始事件入库
- 调度与监控

状态：

- 基础完成

文档：

- [phase-02-ingestion.md](/D:/Code/Project/FetchNews/docs/project-plan/phase-02-ingestion.md)

### 阶段 03：标准化与聚类

目标：

- 标准化
- 去重
- 聚类
- 评分
- story 审核

状态：

- 基础完成

文档：

- [phase-03-normalize-and-cluster.md](/D:/Code/Project/FetchNews/docs/project-plan/phase-03-normalize-and-cluster.md)

### 阶段 04：内容生成

目标：

- 日报 / 周报 / 月报草稿
- 平台短帖变体
- 基于栏目组织输出

状态：

- 基础完成

文档：

- [phase-04-content-generation.md](/D:/Code/Project/FetchNews/docs/project-plan/phase-04-content-generation.md)

### 阶段 05：审核与发布

目标：

- 后台审核流程
- 发布任务
- 结果回写、重试与反馈

状态：

- 基础完成

说明：

- 工作流已在内部原型中跑通，但真实平台集成仍待补齐

文档：

- [phase-05-review-and-publishing.md](/D:/Code/Project/FetchNews/docs/project-plan/phase-05-review-and-publishing.md)

### 阶段 06：优化、运维与治理

目标：

- 来源治理
- 栏目势能
- 平台反馈回路
- 运维诊断与持续优化
- 编辑工作台、人工干预与编辑历史能力

状态：

- 进行中

当前已完成：

- ops 仪表盘
- 失败分组
- 平台指标
- 栏目势能
- 来源治理反馈
- 来源互动反馈回流排序
- 周报 / 月报栏目混排
- 互动驱动的平台文案策略
- 周报 / 月报的栏目与平台联合变体优化
- 编辑工作台设计 spec

文档：

- [phase-06-optimization-and-operations.md](/D:/Code/Project/FetchNews/docs/project-plan/phase-06-optimization-and-operations.md)

## 当前里程碑

已达成：

- 里程碑 A：前后端骨架可本地运行
- 里程碑 B：采集、入库与监控可本地运行
- 里程碑 C：story 聚类与草稿生成可本地运行
- 里程碑 D：审核、发布编排与反馈回路可本地运行
- 里程碑 E：工程与运维基线已建立

仍待完成：

- 里程碑 F：真实来源与真实平台集成达到可生产试运行
- 里程碑 G：LLM 与向量能力进入主工作流
- 里程碑 H：编辑工作台、编辑历史与人工干预能力完整可用
- 里程碑 I：部署、安全、迁移与监控达到生产可用水平

## 下一步优先级

推荐顺序：

1. 真实发布器
2. 更稳健的真实采集连接器
3. LLM 与 embedding 集成
4. 完整编辑工作台实现
5. 数据库迁移与部署加固
6. 登录、权限、告警与审计继续补齐