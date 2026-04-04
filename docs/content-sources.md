# FetchNews 内容来源清单

## 目标

只接入对中文 AI 从业者真正有价值、且能够稳定获取的一手或高质量二手来源。优先保证质量、可追溯性和可治理性，不追求无限制全网覆盖。

## 当前已实现来源

### P0

#### GitHub

- `github-trending`
  - 状态：已实现
  - 说明：基于 HTML 抓取趋势仓库。
- `github-openai-releases`
  - 状态：已实现
  - 说明：Phase 07 新增，面向真实 release/tag 更新。

#### arXiv / 论文源

- `arxiv-cs-ai`
  - 状态：已实现
  - 说明：基于 RSS。

#### 官方博客 / RSS

- `openai-blog`
  - 状态：已实现
  - 说明：基于 RSS。

#### X

- `x-allowlist`
  - 状态：占位实现
  - 说明：当前仅支持白名单静态条目，不是实时 API 抓取。

### P1

#### 聚合与社区来源

- `hf-daily`
  - 状态：已实现
  - 说明：Phase 07 新增，支持真实连接器骨架和增量游标。
- `paperswithcode-latest`
  - 状态：已实现
  - 说明：Phase 07 新增，支持真实连接器骨架和增量游标。
- `reddit-ml`
  - 状态：规划中

## 当前采集能力

- 连接器可按 `slug -> platform -> kind` 选择。
- 真实连接器可返回 `items + next_cursor`。
- 成功采集后回写 `sources.incremental_cursor` 和 `sources.last_success_at`。
- 原始快照统一落到 `raw_items.payload.snapshot`。

## 下一批优先接入

1. 扩展更多 GitHub 指定组织和 release 源。
2. 扩展更多官方博客 RSS。
3. 把 `x-allowlist` 从占位实现升级到真实 API 接入。
4. 视质量和治理成本，再补 Reddit、Hacker News 等聚合来源。

## 来源治理原则

- 一手来源优先于转载。
- 组织白名单优先于关键词泛抓。
- 官方博客优先于社区转述。
- 同一事件至少保留 1 个原始来源链接。
- 中文媒体主要用于补背景，不作为唯一事实依据。
