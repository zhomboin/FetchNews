# FetchNews

`FetchNews` 是一个面向中文 AI 从业者的资讯聚合、内容审核与多平台分发系统。

## 当前状态

仓库已经不再只是规划文档，而是具备可运行的内部原型，当前主链路已经打通：

- 定时或手动抓取白名单来源
- 原始事件入库
- 标准化、去重、聚类与评分
- 生成日报、周报、月报草稿
- 生成 `wechat`、`x`、`telegram` 平台变体
- 在 React 管理后台完成 story 与草稿审核
- 创建发布任务、轮询结果、失败重试与效果回写
- 通过登录、角色权限与审计日志保护后台
- 将来源治理、栏目势能与平台互动反馈反向注入排序与文案策略

当前阶段状态：

- `Phase 00` 到 `Phase 05`：基础实现已完成
- `Phase 06`：持续优化中

详细实现快照见：

- [docs/current-status.md](/D:/Code/Project/FetchNews/docs/current-status.md)

## 已实现能力

### 后端

- `FastAPI` 应用与 REST API
- `SQLAlchemy` 数据模型与持久化层
- `Celery + Redis` 任务队列与调度
- 来源目录、采集批次与原始事件存储
- 标准化与 story 聚类流水线
- 日报 / 周报 / 月报生成
- 发布任务编排、结果回写、重试与效果记录
- 登录配置、当前用户解析与路由保护
- 关键写操作的审计日志
- 运维汇总、告警、诊断与治理反馈回路

### 前端

- `React SPA + Vite + TypeScript` 内部审核控制台
- 登录页与受保护路由
- 采集监控页
- story 审核与筛选页
- 草稿中心与发布前审核流程
- 运维仪表盘、告警面板与 drill-down 详情页
- 基于 `Vitest` 和 Testing Library 的前端测试基线

### 数据与部署

- Alembic 迁移基线
- PostgreSQL 优先的本地开发路径
- 连接宿主机 PostgreSQL 的 Docker Compose 工作流
- `SQLite` 与 `PostgreSQL` 的显式数据库初始化模式

## 关键文档

- 当前实现状态：[docs/current-status.md](/D:/Code/Project/FetchNews/docs/current-status.md)
- 系统架构：[docs/architecture.md](/D:/Code/Project/FetchNews/docs/architecture.md)
- 实施路线：[docs/implementation-roadmap.md](/D:/Code/Project/FetchNews/docs/implementation-roadmap.md)
- 总体计划：[docs/project-plan/00-master-plan.md](/D:/Code/Project/FetchNews/docs/project-plan/00-master-plan.md)
- 计划索引：[docs/project-plan/README.md](/D:/Code/Project/FetchNews/docs/project-plan/README.md)
- 启动指南：[docs/getting-started.md](/D:/Code/Project/FetchNews/docs/getting-started.md)
- 本地 PostgreSQL 配置：[docs/postgresql-local-setup.md](/D:/Code/Project/FetchNews/docs/postgresql-local-setup.md)
- 工程与运维基线：[docs/engineering-ops-baseline.md](/D:/Code/Project/FetchNews/docs/engineering-ops-baseline.md)
- 前端风格规范：[docs/frontend-style.md](/D:/Code/Project/FetchNews/docs/frontend-style.md)
- TypeScript 规范：[docs/typescript-style.md](/D:/Code/Project/FetchNews/docs/typescript-style.md)
- 内容来源清单：[docs/content-sources.md](/D:/Code/Project/FetchNews/docs/content-sources.md)
- 编辑工作台设计稿：[docs/superpowers/specs/2026-04-03-editorial-workbench-design.md](/D:/Code/Project/FetchNews/docs/superpowers/specs/2026-04-03-editorial-workbench-design.md)

## 本地启动

当宿主机 PostgreSQL 已经启动时，推荐这样启动：

```bash
docker compose run --rm migrate
docker compose up api worker beat web redis
```

然后访问：

- API：[http://localhost:8000](http://localhost:8000)
- 管理后台：[http://localhost:5173](http://localhost:5173)
- 采集页面：[http://localhost:5173/ingestion](http://localhost:5173/ingestion)

本地默认管理员账号由环境变量控制：

- 用户名：`APP_BOOTSTRAP_ADMIN_USERNAME`
- 密码：`APP_BOOTSTRAP_ADMIN_PASSWORD`

更多说明见：

- [docs/getting-started.md](/D:/Code/Project/FetchNews/docs/getting-started.md)

## 验证命令

后端测试：

```bash
python -m pytest
```

前端测试：

```bash
cd web
npm run test:run
```

前端构建：

```bash
cd web
npm run build
```

## 当前高优先级后续工作

- 接入真实外部来源连接器
- 接入真实平台发布器
- 接入真实 LLM provider，用于摘要与长文生成
- 引入 `pgvector` / embedding 相似度与召回
- 增强审计日志查看与外部告警能力
- 落地更完整的编辑历史、人工干预与编辑工作台

## 文档约束

- 项目内所有自有文档统一使用中文撰写
- 允许保留必要的英文技术名词，但必须置于中文语境中
- 本约束适用于根目录文档、`docs/` 下文档、计划文档与设计 spec
- 第三方依赖自带文档、`node_modules` 与工具缓存目录不在此约束内

## 编码约定

- 所有文本文件统一使用 `UTF-8`、无 `BOM`
- 所有文本文件统一使用 `LF` 换行
- 由 [`.editorconfig`](/D:/Code/Project/FetchNews/.editorconfig) 与 [`.gitattributes`](/D:/Code/Project/FetchNews/.gitattributes) 约束