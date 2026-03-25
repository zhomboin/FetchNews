# FetchNews

面向中文 AI 从业者的资讯聚合、内容审核与多平台分发工作流。

## 项目目标

系统每天定时从高价值 AI 来源抓取最新信息，完成清洗、去重、聚类、打分、摘要与文章生成，并在人工审核后输出：

- 一篇可发布的中文日报或周报长文
- 适配不同平台的短帖版本
- 可追溯的来源、审核与发布记录

## 当前状态

当前仓库已经具备：

- 后端 Phase 01 骨架：`FastAPI`、基础模型、API 路由和任务入口
- 前端 Phase 01 骨架：`React SPA + Vite + TypeScript`
- 架构文档、来源清单、实施路线与分阶段计划
- 基础测试与本地开发编排

## 技术栈

- 后端：`Python 3.11+`、`FastAPI`、`SQLAlchemy 2.x`、`PostgreSQL`、`Redis`、`Celery`
- 抓取：`httpx`、`feedparser`、`selectolax`
- 前端：`React 18`、`Vite`、`TypeScript`、`React Router`、`TanStack Query`、`Zustand`、`Tailwind CSS`

## 当前前端风格基线

内部审核后台的视觉风格已经固定为：

- `暖白金属极简`
- `浅色优先`
- `企业秩序感 + 轻未来感`

这套风格用于统一承载：

- 内容审核队列
- 日报草稿预览
- 统计图表
- 系统日志与发布排程

风格要求：

- 以暖白、钛灰、浅香槟金为主，不使用赛博霓虹和重紫色 AI 风格
- 优先强调信息层级、可读性和审核效率，不做营销站式大装饰
- AI 感来自细节，如轨迹线、微弱高光、控制台式状态提示，而不是大量发光特效
- 图表、日志、审核卡片都应保持统一的控制台语义

设计规范见：

- [docs/frontend-style.md](/D:/Code/Project/FetchNews/docs/frontend-style.md)
- [docs/assets/fetchnews-warm-metal-preview.png](/D:/Code/Project/FetchNews/docs/assets/fetchnews-warm-metal-preview.png)

## 文档

- 协作约定：[AGENTS.md](/D:/Code/Project/FetchNews/AGENTS.md)
- 系统架构：[docs/architecture.md](/D:/Code/Project/FetchNews/docs/architecture.md)
- 前端风格：[docs/frontend-style.md](/D:/Code/Project/FetchNews/docs/frontend-style.md)
- 来源清单：[docs/content-sources.md](/D:/Code/Project/FetchNews/docs/content-sources.md)
- 实施路线：[docs/implementation-roadmap.md](/D:/Code/Project/FetchNews/docs/implementation-roadmap.md)
- 项目计划目录：[docs/project-plan/README.md](/D:/Code/Project/FetchNews/docs/project-plan/README.md)
- 总体项目计划：[docs/project-plan/00-master-plan.md](/D:/Code/Project/FetchNews/docs/project-plan/00-master-plan.md)

## 文件编码约定

- 所有文本文件统一使用 `UTF-8`，无 `BOM`
- 统一使用 `LF` 作为换行符
- 通过 [`.editorconfig`](/D:/Code/Project/FetchNews/.editorconfig) 和 [`.gitattributes`](/D:/Code/Project/FetchNews/.gitattributes) 约束编码与换行

## 本地开发

安装依赖：

```bash
python -m pip install -e .[dev]
```

运行测试：

```bash
python -m pytest
```

环境变量模板：

- [.env.example](/D:/Code/Project/FetchNews/.env.example)

## 推荐的后续开发顺序

1. 先阅读整体计划与当前阶段文档。
2. 完善 `fetchnews/` 的数据库、来源注册和异步任务。
3. 在 `web/` 中按已确认风格继续扩展审核、草稿和发布页面。
4. 接入 GitHub、arXiv、RSS、X 白名单等来源。
5. 实现标准化、聚类、摘要生成与发布工作流。