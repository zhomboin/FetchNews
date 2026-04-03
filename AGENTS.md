# AGENTS.md

## 项目目标

`FetchNews` 是一个面向中文 AI 从业者的资讯聚合、内容审核与多平台分发系统。目标是从 GitHub、论文源、官方博客、X 与社区平台定时抓取高价值 AI 信息，完成标准化、去重、聚类、摘要与长文 / 短帖生成，并在人工审核后分发到不同平台。

当前仓库已经具备：

- 后端与前端基础骨架
- 来源采集、标准化、聚类、草稿生成与发布工作流
- 登录、权限、审计、迁移与基础运维能力
- 架构、路线、阶段计划与专项设计文档

## 当前推荐技术栈

- 后端：`FastAPI`
- ORM / 数据库：`SQLAlchemy 2.x` + `PostgreSQL`
- 队列与定时：`Celery` + `Redis`
- 抓取：`httpx`、`feedparser`、`selectolax`
- 内容生成：抽象 LLM provider，支持后续接入 OpenAI 或其他模型
- 前端：`React SPA`
- 前端推荐组合：`React 18 + Vite + TypeScript + React Router + TanStack Query + Zustand + Tailwind CSS`

## 代码组织约定

推荐目录结构：

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

模块边界：

- `api/`：FastAPI 路由、请求与响应契约
- `core/`：配置、日志、时间与通用工具
- `db/`：engine、session、初始化和种子数据
- `models/`：SQLAlchemy 数据模型
- `pipeline/`：标准化、聚类、摘要和文章生成
- `publishing/`：各平台发布器
- `sources/`：来源连接器、白名单和来源目录
- `tasks/`：Celery 任务入口
- `web/`：React SPA 内部审核控制台

## 开发原则

- 先落 `raw_items`，再做标准化与聚类，不跳过原始事件层
- 长文和短帖必须从同一批 `stories` 派生
- 每条聚合事件都要保留来源链接、抓取时间和风险标记
- 发布动作与内容生成必须解耦，失败任务必须可幂等重试
- 白名单优先，不做无限制全网抓取
- 前端只消费 API，不承载业务真相

## 前端风格基线

当前前端风格已经确认，后续页面实现必须遵守：

- 风格名：`暖白金属极简`
- 主题策略：`浅色优先`
- 气质关键词：`企业秩序感`、`可信`、`克制`、`轻未来感`

具体约束：

- 主色调使用暖白、钛灰、浅香槟金和低饱和信号色
- 禁用赛博朋克霓虹、重玻璃拟态、强紫蓝发光和过度装饰
- 审核、草稿、图表、日志和发布模块应呈现统一控制台语言
- AI 主题通过细节表达，不通过炫技表达

实现和评审前先对照：

- [docs/frontend-style.md](/D:/Code/Project/FetchNews/docs/frontend-style.md)
- [docs/assets/fetchnews-warm-metal-preview.png](/D:/Code/Project/FetchNews/docs/assets/fetchnews-warm-metal-preview.png)
- [.impeccable.md](/D:/Code/Project/FetchNews/.impeccable.md)

## TypeScript 开发约束

前端 TypeScript 代码遵循 Google TypeScript Style Guide 的语法规范基线，并结合本项目做如下约束：

- 组件、类型、接口使用 `UpperCamelCase`
- 变量、函数、方法、参数、普通属性使用 `lowerCamelCase`
- 模块级不可变常量使用 `CONSTANT_CASE`
- 禁止使用 `_` 前缀或后缀命名
- 前端内部状态、视图模型统一使用 `camelCase`
- 后端 `snake_case` 字段只能停留在 API 边界层，由 `web/src/lib/api.ts` 做映射
- 导出的顶层类型、函数、组件在必要时补充有意义的 `/** JSDoc */`
- 不写重复类型信息的注释，不使用 `@override`

实现前端功能前先对照：

- [docs/typescript-style.md](/D:/Code/Project/FetchNews/docs/typescript-style.md)

## 文档语言约束

- 项目内所有自有文档统一使用中文撰写
- 允许保留必要的英文专有名词，但必须放在中文上下文中
- 新增或修改 `README.md`、`AGENTS.md`、`AGENT.md`、`.impeccable.md`、`docs/**/*.md` 时必须遵守该约束
- 第三方依赖自带文档、缓存目录与工具生成的外部说明不在此要求内

## 文件编码约定

- 仓库内所有文本文件统一使用 `UTF-8`，无 `BOM`
- 统一使用 `LF` 作为换行符
- 新增或修改文档、Python、前端源码、JSON、YAML、TOML 时，必须保持该编码约定
- 优先遵循 [`.editorconfig`](/D:/Code/Project/FetchNews/.editorconfig) 和 [`.gitattributes`](/D:/Code/Project/FetchNews/.gitattributes)

## 测试与验证

新增行为优先补测试。至少覆盖：

- 来源目录和优先级
- 标准化与聚类
- 日报生成
- 审核与发布 API

在声称完成前，至少运行：

```bash
python -m pytest
```

如果修改 `web/`，还需要运行：

```bash
npm.cmd run build
```

## 文档入口

- 架构说明：[docs/architecture.md](/D:/Code/Project/FetchNews/docs/architecture.md)
- 前端风格：[docs/frontend-style.md](/D:/Code/Project/FetchNews/docs/frontend-style.md)
- 来源清单：[docs/content-sources.md](/D:/Code/Project/FetchNews/docs/content-sources.md)
- 实施路线：[docs/implementation-roadmap.md](/D:/Code/Project/FetchNews/docs/implementation-roadmap.md)
- 计划目录：[docs/project-plan/README.md](/D:/Code/Project/FetchNews/docs/project-plan/README.md)
- 总体计划：[docs/project-plan/00-master-plan.md](/D:/Code/Project/FetchNews/docs/project-plan/00-master-plan.md)
- 编辑工作台设计：[docs/superpowers/specs/2026-04-03-editorial-workbench-design.md](/D:/Code/Project/FetchNews/docs/superpowers/specs/2026-04-03-editorial-workbench-design.md)

## 协作说明

- 开发前先读 [docs/architecture.md](/D:/Code/Project/FetchNews/docs/architecture.md)
- 实现前端页面前先读 [docs/frontend-style.md](/D:/Code/Project/FetchNews/docs/frontend-style.md)
- 进入某个阶段前先读对应的 `docs/project-plan/phase-*.md`
- 扩展来源前先更新 [docs/content-sources.md](/D:/Code/Project/FetchNews/docs/content-sources.md)
- 进入编辑工作台相关实现前先读 [docs/superpowers/specs/2026-04-03-editorial-workbench-design.md](/D:/Code/Project/FetchNews/docs/superpowers/specs/2026-04-03-editorial-workbench-design.md)