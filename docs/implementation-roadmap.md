# FetchNews 实施路线图

## 目标

将系统从“内部闭环可运行”推进到“真实外部能力接入、可观测、可扩展”，同时避免把来源接入、内容智能、协作治理和生产化部署混在同一轮里实现。

## 当前阶段

- Phase 00 - Phase 06：基础能力已具备
- Phase 07 主线基线：Task 1-5 已合并到主线
- Phase 07 加固与生产就绪：当前分支已完成 Task 1-5
- Phase 08 - Phase 10：后续阶段

## Phase 07 当前进度

### 主线已合并

1. 数据契约和配置基线
2. `telegram` 真实发布骨架与 callback 闭环
3. `wechat / x` 占位真实发布器和 ops 失败归因
4. 真实来源连接器与增量抓取
5. API、ops 页面和 ingestion 页面接入健康字段

### 当前分支已加固完成

1. `telegram` 真实发布 MVP
2. 真实来源连接器认证、分页与回退
3. 平台冷却窗口限流
4. 来源最小重试
5. source 重复失败告警
6. 小流量运行 Runbook

## 推荐推进顺序

1. 先完成 Phase 07 加固收尾并观察小流量运行结果
2. 再进入 Phase 08，接真实 LLM provider 和 embedding 能力
3. 然后完成 Phase 09 的编辑协作治理
4. 最后收敛到 Phase 10 的生产化部署与运维

## 路线分层

### 层 1：当前已跑通的内部闭环

- 采集
- 标准化
- 聚类
- 草稿生成
- 审核
- 发布
- 结果回写
- ops 观测

### 层 2：当前已接上的真实外部能力

- `telegram` 真实发布 MVP
- `GitHub Releases / Hugging Face / Papers with Code` 真实来源连接器
- 幂等重试与失败归因
- 平台与来源级 ops 信号
- 前端健康状态展示

### 层 3：后续能力

- `wechat / x` 真实 API 接入
- 更强的限流和认证刷新
- 真实 LLM provider
- embedding 去重和召回
- 编辑协作治理
- 生产环境部署和监控

## 当前建议

当前不建议直接进入 Phase 08。更稳妥的顺序是：

1. 先用 `telegram + github-openai-releases` 做小流量运行
2. 观察 24 小时后，再加入 `hf-daily` 与 `paperswithcode-latest`
3. 稳定后再评估是否进入真实 LLM provider 接入

## 约束

- 每个阶段都必须能独立验收
- 涉及模型字段或表结构变化时，先有迁移，再有实现和文档
- 真实外部接入优先做小范围闭环，不一次性全量打开
