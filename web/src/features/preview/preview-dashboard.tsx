import React from "react";

import { DetailLink, MetricGrid, PageHeader, PanelHeader, StatusPill } from "../../components/console";

type PreviewDashboardProps = {
  health: string;
  currentPath: string;
};

type PreviewMetric = {
  label: string;
  value: string;
  note: string;
};

type PreviewAlert = {
  category: string;
  title: string;
  summary: string;
  suggestion: string;
  count: string;
  tone: "approved" | "pending" | "failed";
};

type PreviewSectionMetric = {
  key: string;
  label: string;
  reviewed: number;
  pending: number;
  flagged: number;
  total: number;
  momentum: string;
  note: string;
  tone: "calm" | "watch";
};

type PreviewRecommendation = {
  title: string;
  category: string;
  summary: string;
  suggestion: string;
  count: number;
  tone: "calm" | "watch";
};

type PreviewFailureGroup = {
  category: string;
  reason: string;
  count: number;
  targets: string[];
  suggestion: string;
  tone: "calm" | "watch";
};

type PreviewPlatformMetric = {
  platform: string;
  successRate: number;
  totalJobs: number;
  publishedJobs: number;
  failedJobs: number;
  scheduledJobs: number;
  note: string;
  tone: "calm" | "watch";
};

type PreviewRecentJob = {
  platform: string;
  articleId: number;
  updatedAt: string;
  status: "scheduled" | "published" | "failed";
  note: string;
};

type PreviewRecentArticle = {
  title: string;
  periodType: string;
  storyCount: number;
  updatedAt: string;
  status: "ready" | "scheduled" | "published" | "failed" | "draft";
  variantCount: number;
};

const VIEW_LABEL_BY_PATH: Record<string, string> = {
  "/": "总览样板",
  "/preview": "总览样板",
  "/stories": "审核样板",
  "/articles": "草稿样板",
  "/publishing": "发布样板",
};

const METRICS: PreviewMetric[] = [
  { label: "今日采集", value: "184", note: "12 条高优先级信号" },
  { label: "已审核故事", value: "49", note: "仍有 11 条待人工确认" },
  { label: "发布成功率", value: "92%", note: "平台重试窗口整体稳定" },
  { label: "互动点击", value: "1,286", note: "内容回写继续偏向模型与工具链栏目" },
];

const ALERTS: PreviewAlert[] = [
  {
    category: "来源",
    title: "X allowlist 触发限流窗口",
    summary: "已切回节流队列，16:08 重新尝试。",
    suggestion: "优先保留 GitHub / 官方博客来源，避免短时间内补抓同一批帐号。",
    count: "2",
    tone: "pending",
  },
  {
    category: "发布",
    title: "微信回写仍缺 1 条 provider 状态",
    summary: "当前批次已完成发布，但 provider 结果还未完全回填。",
    suggestion: "继续轮询 1 次，如果仍缺失则转人工核对外部 ID。",
    count: "1",
    tone: "approved",
  },
];

const SECTION_METRICS: PreviewSectionMetric[] = [
  {
    key: "models",
    label: "模型与平台",
    reviewed: 12,
    pending: 4,
    flagged: 1,
    total: 17,
    momentum: "高热",
    note: "CTR 11%，头条稿件已形成稳定转化。",
    tone: "watch",
  },
  {
    key: "open_source",
    label: "开源生态",
    reviewed: 9,
    pending: 2,
    flagged: 0,
    total: 11,
    momentum: "上升",
    note: "适合继续作为次级栏目承接社区热度。",
    tone: "calm",
  },
];

const RECOMMENDATIONS: PreviewRecommendation[] = [
  {
    title: "优先清理模型与平台栏目积压",
    category: "栏目",
    summary: "当前高分 story 集中在同一栏目，已经开始挤占发布窗口。",
    suggestion: "优先完成 4 条待审核 story，再决定是否扩展到周报。",
    count: 4,
    tone: "watch",
  },
  {
    title: "把 Telegram 变体改为速览摘要型",
    category: "平台",
    summary: "Telegram 当前互动低于微信和 X，更适合承接列表化摘要。",
    suggestion: "下一个批次使用更紧凑的段落模板，并降低 CTA 密度。",
    count: 2,
    tone: "calm",
  },
];

const FAILURE_GROUPS: PreviewFailureGroup[] = [
  {
    category: "采集",
    reason: "RSS feed 字段缺失",
    count: 2,
    targets: ["official-blog-rss", "labs-feed"],
    suggestion: "转入 HTML fallback 解析，并补记 author 缺省策略。",
    tone: "watch",
  },
  {
    category: "发布",
    reason: "provider callback 延迟",
    count: 1,
    targets: ["wechat"],
    suggestion: "继续轮询，若超过窗口则转人工核对。",
    tone: "calm",
  },
];

const PLATFORM_METRICS: PreviewPlatformMetric[] = [
  {
    platform: "微信",
    successRate: 0.94,
    totalJobs: 16,
    publishedJobs: 15,
    failedJobs: 1,
    scheduledJobs: 0,
    note: "长文导读依旧是主力入口。",
    tone: "calm",
  },
  {
    platform: "X",
    successRate: 0.88,
    totalJobs: 17,
    publishedJobs: 15,
    failedJobs: 1,
    scheduledJobs: 1,
    note: "讨论型钩子表现稳定，但来源核对压力更高。",
    tone: "watch",
  },
];

const RECENT_JOBS: PreviewRecentJob[] = [
  {
    platform: "微信",
    articleId: 204,
    updatedAt: "04/13 16:22",
    status: "published",
    note: "已写回 842 曝光 / 97 点击",
  },
  {
    platform: "Telegram",
    articleId: 204,
    updatedAt: "04/13 16:18",
    status: "scheduled",
    note: "18:35 窗口待执行",
  },
];

const RECENT_ARTICLES: PreviewRecentArticle[] = [
  {
    title: "AI 资讯日报 2026-04-13",
    periodType: "日报",
    storyCount: 7,
    updatedAt: "04/13 16:11",
    status: "ready",
    variantCount: 3,
  },
  {
    title: "AI 周报 2026-W15",
    periodType: "周报",
    storyCount: 15,
    updatedAt: "04/13 15:48",
    status: "scheduled",
    variantCount: 3,
  },
];

function formatStatus(status: PreviewRecentJob["status"] | PreviewRecentArticle["status"]): string {
  if (status === "scheduled") return "待发布";
  if (status === "published") return "已发布";
  if (status === "failed") return "失败";
  if (status === "ready") return "就绪";
  return "草稿";
}

export function PreviewDashboard({ health, currentPath }: PreviewDashboardProps): React.JSX.Element {
  const currentLabel = VIEW_LABEL_BY_PATH[currentPath] ?? VIEW_LABEL_BY_PATH["/"];

  return (
    <div className="preview-page ops-dashboard-page">
      <PageHeader
        className="intro-band"
        eyebrow="总览样板"
        title="暖白金属控制台总览"
        lead="这个样板页不再维护独立的信息结构，而是直接复用真实运营总览的版面语言，用静态样本验证层级、节奏和视觉基线。"
        health={health}
        metaLabel="当前预览"
        metaValue={currentLabel}
      />

      <MetricGrid ariaLabel="核心概览指标" items={METRICS} variant="strip" />

      <section className="ops-alert-strip" aria-label="预览告警">
        {ALERTS.map((alert) => (
          <article key={alert.title} className="ops-alert-card" data-tone={alert.tone === "approved" ? "calm" : "watch"}>
            <div className="ops-alert-head">
              <div>
                <p>{alert.category}</p>
                <strong>{alert.title}</strong>
              </div>
              <StatusPill status={alert.tone}>{alert.count}</StatusPill>
            </div>
            <span>{alert.summary}</span>
            <p className="failure-suggestion">{alert.suggestion}</p>
          </article>
        ))}
      </section>

      <section className="ops-grid">
        <article className="panel ops-health-panel">
          <PanelHeader kicker="流程健康度" title="核心工作流状态" meta="静态样板快照" />

          <div className="runway ops-runway">
            <div className="runway-step">
              <div className="runway-node">
                <span>1</span>
              </div>
              <div className="runway-copy">
                <strong>采集</strong>
                <p>18</p>
                <span>2 个来源进入降速保护</span>
              </div>
            </div>
            <div className="runway-step">
              <div className="runway-node">
                <span>2</span>
              </div>
              <div className="runway-copy">
                <strong>审核</strong>
                <p>49</p>
                <span>11 条 story 仍待编辑确认</span>
              </div>
            </div>
            <div className="runway-step">
              <div className="runway-node">
                <span>3</span>
              </div>
              <div className="runway-copy">
                <strong>发布</strong>
                <p>30</p>
                <span>2 个平台窗口仍待执行</span>
              </div>
            </div>
          </div>

          <div className="risk-overview-grid ops-risk-grid">
            <div className="risk-stat" data-tone="watch">
              <p>失败草稿</p>
              <strong>2</strong>
              <span>需要编辑台人工检查平台回写和变体状态。</span>
            </div>
            <div className="risk-stat" data-tone="watch">
              <p>到期未完成</p>
              <strong>1</strong>
              <span>一个 Telegram 批次还没有进入 provider 终态。</span>
            </div>
            <div className="risk-stat" data-tone="calm">
              <p>行动队列</p>
              <strong>2</strong>
              <span>当前建议动作已经足够支撑下一轮编辑决策。</span>
            </div>
          </div>
        </article>

        <div className="ops-side-stack">
          <article className="panel ops-section-panel">
            <PanelHeader kicker="栏目审核" title="按栏目查看编辑负载" meta={`${SECTION_METRICS.length} 个栏目`} />
            <div className="source-governance-grid section-metric-list">
              {SECTION_METRICS.map((metric) => (
                <article key={metric.key} className="source-governance-card" data-tone={metric.tone}>
                  <div className="source-governance-head">
                    <div>
                      <p>{metric.key}</p>
                      <strong>{metric.label}</strong>
                    </div>
                    <StatusPill status="pending">{metric.total}</StatusPill>
                  </div>
                  <div className="platform-metric-grid compact-gap">
                    <div>
                      <span>已审核</span>
                      <strong>{metric.reviewed}</strong>
                    </div>
                    <div>
                      <span>待审核</span>
                      <strong>{metric.pending}</strong>
                    </div>
                    <div>
                      <span>需复核</span>
                      <strong>{metric.flagged}</strong>
                    </div>
                    <div>
                      <span>总数</span>
                      <strong>{metric.total}</strong>
                    </div>
                  </div>
                  <p className="platform-metric-note">{`${metric.momentum} · ${metric.note}`}</p>
                  <div className="panel-link-row">
                    <DetailLink>打开栏目详情</DetailLink>
                  </div>
                </article>
              ))}
            </div>
          </article>

          <article className="panel ops-recommendation-panel">
            <PanelHeader kicker="反馈闭环" title="建议的下一步动作" meta={`${RECOMMENDATIONS.length} 条建议`} />
            <div className="failure-group-list recommendation-list">
              {RECOMMENDATIONS.map((recommendation) => (
                <article key={recommendation.title} className="failure-group-card recommendation-card" data-tone={recommendation.tone}>
                  <div className="failure-group-head">
                    <div>
                      <p>{recommendation.category}</p>
                      <strong>{recommendation.title}</strong>
                    </div>
                    <StatusPill status="pending">{recommendation.count}</StatusPill>
                  </div>
                  <p className="source-governance-note">{recommendation.summary}</p>
                  <p className="failure-suggestion">{recommendation.suggestion}</p>
                  <div className="panel-link-row">
                    <DetailLink>打开建议详情</DetailLink>
                  </div>
                </article>
              ))}
            </div>
          </article>
        </div>
      </section>

      <section className="ops-grid">
        <article className="panel ops-diagnostics-panel">
          <PanelHeader kicker="失败诊断" title="最近的失败分组" meta={`${FAILURE_GROUPS.length} 个分组`} />
          <div className="failure-group-list">
            {FAILURE_GROUPS.map((group) => (
              <article key={group.reason} className="failure-group-card" data-tone={group.tone}>
                <div className="failure-group-head">
                  <div>
                    <p>{group.category}</p>
                    <strong>{group.reason}</strong>
                  </div>
                  <StatusPill status="failed">{group.count}</StatusPill>
                </div>
                <div className="failure-chip-list">
                  {group.targets.map((target) => (
                    <span key={target} className="failure-target-chip">
                      {target}
                    </span>
                  ))}
                </div>
                <p className="failure-suggestion">{group.suggestion}</p>
                <div className="panel-link-row">
                  <DetailLink>打开失败详情</DetailLink>
                </div>
              </article>
            ))}
          </div>
        </article>

        <article className="panel ops-platform-panel">
          <PanelHeader kicker="平台表现" title="按渠道查看发布表现" meta={`${PLATFORM_METRICS.length} 个平台`} />
          <div className="platform-metric-list">
            {PLATFORM_METRICS.map((metric) => (
              <article key={metric.platform} className="platform-metric-card" data-tone={metric.tone}>
                <div className="platform-metric-head">
                  <strong>{metric.platform}</strong>
                  <span>{Math.round(metric.successRate * 100)}%</span>
                </div>
                <div className="platform-metric-grid">
                  <div>
                    <span>任务总数</span>
                    <strong>{metric.totalJobs}</strong>
                  </div>
                  <div>
                    <span>已发布</span>
                    <strong>{metric.publishedJobs}</strong>
                  </div>
                  <div>
                    <span>失败</span>
                    <strong>{metric.failedJobs}</strong>
                  </div>
                  <div>
                    <span>待执行</span>
                    <strong>{metric.scheduledJobs}</strong>
                  </div>
                </div>
                <p className="platform-metric-note">{metric.note}</p>
                <div className="panel-link-row">
                  <DetailLink>{metric.failedJobs > 0 ? "打开失败任务" : "打开平台详情"}</DetailLink>
                </div>
              </article>
            ))}
          </div>
        </article>
      </section>

      <section className="ops-grid">
        <article className="panel ops-jobs-panel">
          <PanelHeader kicker="最近任务" title="最近的发布活动" meta={`${RECENT_JOBS.length} 条任务`} />
          <div className="ops-article-list">
            {RECENT_JOBS.map((job) => (
              <article key={`${job.platform}-${job.articleId}`} className="ops-article-row">
                <div>
                  <strong>{job.platform}</strong>
                  <p>{`稿件 #${job.articleId} · ${job.updatedAt}`}</p>
                </div>
                <div className="ops-article-meta">
                  <StatusPill status={job.status}>{formatStatus(job.status)}</StatusPill>
                  <span>{job.note}</span>
                  <DetailLink soft>详情</DetailLink>
                </div>
              </article>
            ))}
          </div>
        </article>

        <article className="panel ops-articles-panel">
          <PanelHeader kicker="最近草稿" title="最近的稿件更新" meta={`${RECENT_ARTICLES.length} 篇草稿`} />
          <div className="ops-article-list">
            {RECENT_ARTICLES.map((article) => (
              <article key={article.title} className="ops-article-row">
                <div>
                  <strong>{article.title}</strong>
                  <p>{`${article.periodType} · ${article.storyCount} 条 story · 更新于 ${article.updatedAt}`}</p>
                </div>
                <div className="ops-article-meta">
                  <StatusPill status={article.status}>{formatStatus(article.status)}</StatusPill>
                  <span>{`${article.variantCount} 个变体`}</span>
                </div>
              </article>
            ))}
          </div>
        </article>
      </section>
    </div>
  );
}
