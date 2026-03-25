# FetchNews

一个面向中文 AI 从业者的资讯聚合、内容生成与多平台分发工作流。

## 项目目标

系统每天定时从高价值 AI 资讯来源抓取内容，完成清洗、去重、聚类、摘要与文章生成，并在人工审核后生成：
- 一篇可发布的中文日报/周报长文
- 针对不同平台的短帖版本
- 可追溯的来源与发布记录

## 当前状态

当前仓库已经有：
- Python 项目基础配置 `[pyproject.toml](/D:/Code/Project/FetchNews/pyproject.toml)`
- 核心行为测试草稿
- 架构文档、来源文档和实施路线文档
- 总计划文档和分阶段计划文档

当前仓库还没有：
- 业务实现代码
- 数据模型与 API
- 实际抓取器、React SPA 审核后台和发布队列

## 设计原则

- 原始数据先落库，再做标准化和聚类
- 长文与短帖从同一批结构化事件生成
- 内容生成与发布解耦
- 人工审核优先于全自动发布
- 白名单来源优先于泛抓取

## 技术栈

- 后端：Python 3.11+、FastAPI、SQLAlchemy 2.x、PostgreSQL、Redis、Celery
- 抓取：httpx / feedparser / selectolax
- 前端：React 18、Vite、TypeScript、React Router、TanStack Query、Zustand、Tailwind CSS

## 技术架构结论

当前架构已经收敛为：
- `fetchnews/`：后端 API、采集、处理、生成、发布
- `web/`：内部审核与运营 React SPA
- 前后端通过 REST API 通信
- 使用 `Docker Compose` 管理 `api`、`worker`、`beat`、`web`、`postgres`、`redis`

## 文档

- 协作约定：[AGENTS.md](/D:/Code/Project/FetchNews/AGENTS.md)
- 系统架构：[docs/architecture.md](/D:/Code/Project/FetchNews/docs/architecture.md)
- 来源清单：[docs/content-sources.md](/D:/Code/Project/FetchNews/docs/content-sources.md)
- 实施路线：[docs/implementation-roadmap.md](/D:/Code/Project/FetchNews/docs/implementation-roadmap.md)
- 项目计划目录：[docs/project-plan/README.md](/D:/Code/Project/FetchNews/docs/project-plan/README.md)
- 总体项目计划：[docs/project-plan/00-master-plan.md](/D:/Code/Project/FetchNews/docs/project-plan/00-master-plan.md)

## 文件编码约定

- 所有文本文件统一使用 `UTF-8`，不带 BOM
- 统一使用 `LF` 作为换行符
- 仓库通过 [`.editorconfig`](/D:/Code/Project/FetchNews/.editorconfig) 和 [`.gitattributes`](/D:/Code/Project/FetchNews/.gitattributes) 约束编码与换行
- 新增脚本、配置、前端源码和文档时，都必须遵守该约定
## 本地开发

安装依赖：

```bash
python -m pip install -e .[dev]
```

运行测试：

```bash
python -m pytest
```

环境变量模板见：

- [.env.example](/D:/Code/Project/FetchNews/.env.example)

## 推荐的后续开发顺序

1. 先阅读总体计划与当前阶段文档
2. 建立 `fetchnews/` 包结构与 FastAPI 应用入口
3. 建立 `web/` React SPA 骨架与 API 通信基础
4. 实现数据库模型、Session 管理和种子来源
5. 接入 GitHub、arXiv、RSS、X 白名单来源
6. 实现标准化、去重、聚类与摘要生成
7. 实现审核后台与发布队列
