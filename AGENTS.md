# AGENTS.md

## 项目目标

`FetchNews` 是一个面向中文 AI 从业者的资讯聚合与内容分发系统。目标是从 GitHub、论文源、官方博客、X 及社区平台定时抓取高价值 AI 信息，完成标准化、去重、聚类、摘要与长文/短帖生成，并在人工审核后分发到不同平台。

当前仓库仍处于早期阶段：
- 已有 `pyproject.toml`
- 已有围绕来源目录、聚类、日报生成和 API 流程的测试草稿
- 已有总体计划文档与分阶段计划文档
- 业务代码尚未落地完成

## 当前推荐技术栈

- 后端：`FastAPI`
- ORM / 数据库：`SQLAlchemy 2.x` + `PostgreSQL`
- 队列与定时：`Celery` + `Redis`
- 抓取：`httpx`、`feedparser`、`selectolax`
- 内容生成：LLM 接口抽象层，支持后续接 OpenAI 或其他模型提供方
- 前端：`React SPA`，推荐 `React 18 + Vite + TypeScript`
- 状态与请求：`TanStack Query` + `Zustand`
- 样式：`Tailwind CSS`
- 后台：V1 做内部审核控制台，不做公开前台站点

## 代码组织约定

实现时请优先采用以下目录结构：

```text
fetchnews/
  api/
  core/
  db/
  models/
  pipeline/
  publishing/
  sources/
  tasks/
  main.py
tests/
docs/
web/
```

模块职责边界：
- `api/`: FastAPI 路由与请求/响应模型装配
- `core/`: 配置、日志、时间、通用工具
- `db/`: Engine、Session、初始化与种子数据
- `models/`: SQLAlchemy 数据模型
- `pipeline/`: 标准化、打分、聚类、摘要、文章生成
- `publishing/`: 各平台发布器与任务封装
- `sources/`: 各资讯来源连接器、白名单、抓取注册表
- `tasks/`: Celery 任务入口
- `web/`: React SPA 审核控制台

推荐的 `web/` 结构：

```text
web/
  src/
    app/
    components/
    features/
    lib/
```

## 开发原则

- 先保留 `raw_items`，再做标准化与聚类；不要跳过原始事件层。
- 长文与短帖都必须从同一批 `stories` 生成，避免内容资产分叉。
- 每条聚合事件必须保留来源链接、抓取时间和风险标记。
- 发布动作与内容生成必须解耦，发布失败要可重试且幂等。
- 白名单优先，不做无限制全网抓取。
- 前端只消费 API，不直接承载业务真相。

## 文件编码约定

- 仓库内所有文本文件统一使用 `UTF-8`，不带 BOM。
- 统一使用 `LF` 作为换行符。
- 新增或修改文档、Python、前端源码、JSON、YAML、TOML 时，必须保持该编码约定。
- 优先遵循 [`.editorconfig`](/D:/Code/Project/FetchNews/.editorconfig) 和 [`.gitattributes`](/D:/Code/Project/FetchNews/.gitattributes) 中的规则。
## 测试与验证

- 新增行为优先补测试。
- 至少覆盖：
  - 来源目录和优先级
  - 标准化与聚类
  - 日报生成
  - 审核与发布 API
- 在声称完成前，至少运行：

```bash
python -m pytest
```

如果实现 React SPA，至少补充关键页面渲染、状态流或 API 集成测试。

## 文档入口

- 架构说明：[docs/architecture.md](/D:/Code/Project/FetchNews/docs/architecture.md)
- 来源清单：[docs/content-sources.md](/D:/Code/Project/FetchNews/docs/content-sources.md)
- 实施路线：[docs/implementation-roadmap.md](/D:/Code/Project/FetchNews/docs/implementation-roadmap.md)
- 计划目录：[docs/project-plan/README.md](/D:/Code/Project/FetchNews/docs/project-plan/README.md)
- 总计划：[docs/project-plan/00-master-plan.md](/D:/Code/Project/FetchNews/docs/project-plan/00-master-plan.md)

## 协作说明

- 在实现前先读 `docs/architecture.md`
- 在开发当前阶段前先读对应的 `docs/project-plan/phase-*.md`
- 若要扩展来源，先更新 `docs/content-sources.md`
- 若要修改阶段目标，先同步 `docs/implementation-roadmap.md` 和 `docs/project-plan/`
