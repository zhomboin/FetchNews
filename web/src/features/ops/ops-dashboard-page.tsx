import React from "react";
import { useQuery } from "@tanstack/react-query";

import { ArticleDraftRecord, PublishJobRecord, fetchArticleDrafts, fetchOpsSummary, fetchPublishJobs } from "../../lib/api";

const OPS_SUMMARY_QUERY_KEY = ["opsSummary"] as const;
const PUBLISH_JOBS_QUERY_KEY = ["publishJobs"] as const;
const ARTICLES_QUERY_KEY = ["articles"] as const;
const REFRESH_INTERVAL_MS = 30_000;

type OpsDashboardPageProps = {
  health: string;
  mode: "overview" | "publishing";
};

type OpsMetric = {
  label: string;
  value: string;
  note: string;
};

function formatDateTime(value: string): string {
  return new Intl.DateTimeFormat("zh-CN", {
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(value));
}

function formatPlatform(platform: string): string {
  if (platform === "wechat") {
    return "WeChat";
  }
  if (platform === "telegram") {
    return "Telegram";
  }
  return platform.toUpperCase();
}

function formatPublishStatus(status: string): string {
  if (status === "scheduled") {
    return "待回写";
  }
  if (status === "published") {
    return "已发布";
  }
  if (status === "failed") {
    return "失败";
  }
  return status;
}

function formatArticleStatus(status: string): string {
  if (status === "ready") {
    return "待发布";
  }
  if (status === "scheduled") {
    return "已排期";
  }
  if (status === "published") {
    return "已发布";
  }
  if (status === "failed") {
    return "发布失败";
  }
  return "草稿";
}

function buildMetrics(summary: Awaited<ReturnType<typeof fetchOpsSummary>> | undefined): OpsMetric[] {
  if (summary === undefined) {
    return [
      { label: "累计入库", value: "--", note: "等待后端指标" },
      { label: "已审核 stories", value: "--", note: "等待后端指标" },
      { label: "发布成功率", value: "--", note: "等待后端指标" },
      { label: "到期任务", value: "--", note: "等待后端指标" },
    ];
  }

  return [
    {
      label: "累计入库",
      value: `${summary.itemsIngestedTotal}`,
      note: `${summary.ingestRunsTotal} 次采集运行，异常 ${summary.ingestRunsFailed} 次`,
    },
    {
      label: "已审核 stories",
      value: `${summary.storiesApproved}`,
      note: `总量 ${summary.storiesTotal}，待审核 ${summary.storiesPending}`,
    },
    {
      label: "发布成功率",
      value: `${Math.round(summary.publishSuccessRate * 100)}%`,
      note: `成功 ${summary.publishJobsPublished}，失败 ${summary.publishJobsFailed}`,
    },
    {
      label: "到期任务",
      value: `${summary.duePublishJobs}`,
      note: `排队 ${summary.publishJobsScheduled}，文章失败 ${summary.articlesFailed}`,
    },
  ];
}

function pickRecentJobs(jobs: PublishJobRecord[]): PublishJobRecord[] {
  return [...jobs]
    .sort((left, right) => new Date(right.updatedAt).getTime() - new Date(left.updatedAt).getTime())
    .slice(0, 6);
}

function pickRecentArticles(articles: ArticleDraftRecord[]): ArticleDraftRecord[] {
  return [...articles]
    .sort((left, right) => new Date(right.updatedAt).getTime() - new Date(left.updatedAt).getTime())
    .slice(0, 5);
}

/**
 * Real operations dashboard for ingestion and publishing health.
 */
export function OpsDashboardPage({ health, mode }: OpsDashboardPageProps): React.JSX.Element {
  const summaryQuery = useQuery({
    queryKey: OPS_SUMMARY_QUERY_KEY,
    queryFn: fetchOpsSummary,
    refetchInterval: REFRESH_INTERVAL_MS,
  });
  const publishJobsQuery = useQuery({
    queryKey: PUBLISH_JOBS_QUERY_KEY,
    queryFn: fetchPublishJobs,
    refetchInterval: REFRESH_INTERVAL_MS,
  });
  const articlesQuery = useQuery({
    queryKey: ARTICLES_QUERY_KEY,
    queryFn: fetchArticleDrafts,
    refetchInterval: REFRESH_INTERVAL_MS,
  });

  const summary = summaryQuery.data;
  const metrics = buildMetrics(summary);
  const recentJobs = pickRecentJobs(publishJobsQuery.data ?? []);
  const recentArticles = pickRecentArticles(articlesQuery.data ?? []);
  const title = mode === "publishing" ? "发布运维面板" : "运营总览面板";
  const lead =
    mode === "publishing"
      ? "集中查看发布成功率、失败任务和最近一次回写结果，确认多平台分发链路是否稳定。"
      : "将采集、审核、草稿与发布指标收拢到同一面板，用来判断当天 AI 资讯流水线是否健康。";

  return (
    <div className="preview-page ops-dashboard-page">
      <section className="intro-band">
        <div className="intro-copy">
          <p className="eyebrow">Operations Console</p>
          <h1>{title}</h1>
          <p className="lede">{lead}</p>
        </div>

        <div className="intro-meta">
          <div className="signal-pill">
            <span className="signal-dot-live" />
            <strong>{health}</strong>
          </div>
          <div className="meta-chip">
            <span>刷新频率</span>
            <strong>30 秒</strong>
          </div>
        </div>
      </section>

      <section className="metric-strip" aria-label="运维指标概览">
        {metrics.map((metric) => (
          <article key={metric.label} className="metric-cell">
            <p>{metric.label}</p>
            <strong>{metric.value}</strong>
            <span>{metric.note}</span>
          </article>
        ))}
      </section>

      <section className="ops-grid">
        <article className="panel ops-health-panel">
          <header className="section-title">
            <div>
              <p>Pipeline Health</p>
              <h2>主链路健康度</h2>
            </div>
            <span>{summaryQuery.isFetching ? "正在刷新" : "稳定读取中"}</span>
          </header>

          <div className="runway ops-runway">
            <div className="runway-step">
              <div className="runway-node">
                <span>1</span>
              </div>
              <div className="runway-copy">
                <strong>采集</strong>
                <p>{summary?.ingestRunsTotal ?? 0}</p>
                <span>累计运行，异常 {summary?.ingestRunsFailed ?? 0}</span>
              </div>
            </div>
            <div className="runway-step">
              <div className="runway-node">
                <span>2</span>
              </div>
              <div className="runway-copy">
                <strong>审核</strong>
                <p>{summary?.storiesApproved ?? 0}</p>
                <span>待审核 {summary?.storiesPending ?? 0}</span>
              </div>
            </div>
            <div className="runway-step">
              <div className="runway-node">
                <span>3</span>
              </div>
              <div className="runway-copy">
                <strong>发布</strong>
                <p>{summary?.publishJobsPublished ?? 0}</p>
                <span>排队 {summary?.publishJobsScheduled ?? 0}</span>
              </div>
            </div>
          </div>

          <div className="risk-overview-grid ops-risk-grid">
            <div className="risk-stat" data-tone={(summary?.articlesFailed ?? 0) > 0 ? "watch" : "calm"}>
              <p>文章失败</p>
              <strong>{summary?.articlesFailed ?? 0}</strong>
              <span>如果这里持续增长，优先检查发布任务失败原因。</span>
            </div>
            <div className="risk-stat" data-tone={(summary?.duePublishJobs ?? 0) > 0 ? "watch" : "calm"}>
              <p>到期未完成</p>
              <strong>{summary?.duePublishJobs ?? 0}</strong>
              <span>到期任务积压说明 dispatch 或 poll 链路需要关注。</span>
            </div>
            <div className="risk-stat" data-tone="default">
              <p>短帖总任务</p>
              <strong>{summary?.publishJobsTotal ?? 0}</strong>
              <span>用于判断当天分发负载是否异常放大。</span>
            </div>
          </div>
        </article>

        <article className="panel ops-jobs-panel">
          <header className="section-title">
            <div>
              <p>Recent Publish Jobs</p>
              <h2>最近发布任务</h2>
            </div>
            <span>{recentJobs.length} 条</span>
          </header>

          <div className="publish-job-list">
            {publishJobsQuery.isLoading ? <div className="empty-state">正在加载发布任务...</div> : null}
            {publishJobsQuery.isError ? <div className="empty-state">发布任务加载失败，请确认 /publish-jobs 接口可用。</div> : null}
            {!publishJobsQuery.isLoading && !publishJobsQuery.isError && recentJobs.length === 0 ? (
              <div className="empty-state">当前还没有发布任务。</div>
            ) : null}
            {recentJobs.map((job) => (
              <article key={job.id} className="publish-job-row">
                <div className="publish-job-copy">
                  <div>
                    <strong>{formatPlatform(job.platform)}</strong>
                    <p>{formatDateTime(job.scheduledFor)}</p>
                  </div>
                  <div className="publish-job-meta">
                    <span className={`status-pill status-${job.status}`}>{formatPublishStatus(job.status)}</span>
                    <span>重试 {job.retries}</span>
                  </div>
                </div>
                <div className="publish-job-note-stack">
                  <span className="publish-job-note">最近更新：{formatDateTime(job.updatedAt)}</span>
                  {job.providerJobId ? <span className="publish-job-note">Provider Job：{job.providerJobId}</span> : null}
                  {job.externalId ? <span className="publish-job-note">外部 ID：{job.externalId}</span> : null}
                  {job.errorMessage ? <span className="publish-job-error">{job.errorMessage}</span> : null}
                </div>
              </article>
            ))}
          </div>
        </article>

        <article className="panel ops-articles-panel">
          <header className="section-title">
            <div>
              <p>Recent Drafts</p>
              <h2>最新草稿状态</h2>
            </div>
            <span>{recentArticles.length} 条</span>
          </header>

          <div className="ops-article-list">
            {articlesQuery.isLoading ? <div className="empty-state">正在加载草稿...</div> : null}
            {articlesQuery.isError ? <div className="empty-state">草稿加载失败，请确认 /articles 接口可用。</div> : null}
            {!articlesQuery.isLoading && !articlesQuery.isError && recentArticles.length === 0 ? (
              <div className="empty-state">当前还没有日报草稿。</div>
            ) : null}
            {recentArticles.map((article) => (
              <article key={article.id} className="ops-article-row">
                <div>
                  <strong>{article.title}</strong>
                  <p>{article.summary}</p>
                </div>
                <div className="ops-article-meta">
                  <span className={`status-pill status-${article.status}`}>{formatArticleStatus(article.status)}</span>
                  <span>{formatDateTime(article.updatedAt)}</span>
                </div>
              </article>
            ))}
          </div>
        </article>
      </section>
    </div>
  );
}