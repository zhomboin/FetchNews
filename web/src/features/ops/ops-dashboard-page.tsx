import React from "react";
import { useQuery } from "@tanstack/react-query";

import {
  ArticleDraftRecord,
  FailureGroupRecord,
  PublishJobRecord,
  fetchArticleDrafts,
  fetchOpsSummary,
  fetchPublishJobs,
} from "../../lib/api";

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

function formatFailureCategory(category: string): string {
  if (category === "ingest") {
    return "采集";
  }
  if (category === "publish") {
    return "发布";
  }
  return category;
}

function buildMetrics(summary: Awaited<ReturnType<typeof fetchOpsSummary>> | undefined): OpsMetric[] {
  if (summary === undefined) {
    return [
      { label: "累计入库", value: "--", note: "等待后端指标" },
      { label: "已审核 Stories", value: "--", note: "等待后端指标" },
      { label: "发布成功率", value: "--", note: "等待后端指标" },
      { label: "诊断信号", value: "--", note: "等待后端指标" },
    ];
  }

  return [
    {
      label: "累计入库",
      value: `${summary.itemsIngestedTotal}`,
      note: `${summary.ingestRunsTotal} 次采集，异常 ${summary.ingestRunsFailed} 次`,
    },
    {
      label: "已审核 Stories",
      value: `${summary.storiesApproved}`,
      note: `总量 ${summary.storiesTotal}，待审核 ${summary.storiesPending}`,
    },
    {
      label: "发布成功率",
      value: `${Math.round(summary.publishSuccessRate * 100)}%`,
      note: `成功 ${summary.publishJobsPublished}，失败 ${summary.publishJobsFailed}`,
    },
    {
      label: "诊断信号",
      value: `${summary.recentFailureGroups.length}`,
      note: `到期未完成 ${summary.duePublishJobs}，失败草稿 ${summary.articlesFailed}`,
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

function pickFailureGroups(groups: FailureGroupRecord[]): FailureGroupRecord[] {
  return groups.slice(0, 6);
}

function getFailureTone(group: FailureGroupRecord): "watch" | "calm" {
  if (group.category === "publish") {
    return "watch";
  }
  return "calm";
}

/**
 * Real operations dashboard for ingestion, diagnostics, and publishing health.
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
  const failureGroups = pickFailureGroups(summary?.recentFailureGroups ?? []);
  const title = mode === "publishing" ? "发布运维面板" : "运营总览面板";
  const lead =
    mode === "publishing"
      ? "集中查看发布成功率、失败归因、重试建议和最近一次结果回写，确认多平台分发链路是否稳定。"
      : "将采集、审核、草稿、发布和失败诊断汇总到同一控制台，快速判断当日 AI 资讯流水线是否健康。";

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
              <p>草稿失败</p>
              <strong>{summary?.articlesFailed ?? 0}</strong>
              <span>如果这里持续增长，优先检查发布任务失败原因。</span>
            </div>
            <div className="risk-stat" data-tone={(summary?.duePublishJobs ?? 0) > 0 ? "watch" : "calm"}>
              <p>到期未完成</p>
              <strong>{summary?.duePublishJobs ?? 0}</strong>
              <span>到期任务积压通常说明 dispatch 或 poll 链路需要关注。</span>
            </div>
            <div className="risk-stat" data-tone={(summary?.recentFailureGroups.length ?? 0) > 0 ? "watch" : "default"}>
              <p>失败归因</p>
              <strong>{summary?.recentFailureGroups.length ?? 0}</strong>
              <span>按近因聚合失败原因，便于判断是否值得集中重试。</span>
            </div>
          </div>
        </article>

        <div className="ops-side-stack">
          <article className="panel ops-diagnostics-panel">
            <header className="section-title">
              <div>
                <p>Failure Diagnostics</p>
                <h2>最近失败原因</h2>
              </div>
              <span>{failureGroups.length} 组</span>
            </header>

            {failureGroups.length === 0 ? (
              <div className="empty-state">最近没有失败分组，当前运维面板没有需要人工跟进的异常。</div>
            ) : (
              <div className="failure-group-list">
                {failureGroups.map((group) => (
                  <article key={`${group.category}-${group.reason}`} className="failure-group-card" data-tone={getFailureTone(group)}>
                    <div className="failure-group-head">
                      <div>
                        <p>{formatFailureCategory(group.category)}</p>
                        <strong>{group.reason}</strong>
                      </div>
                      <span className="status-pill status-failed">{group.count} 次</span>
                    </div>
                    <div className="failure-chip-list">
                      {group.targets.map((target) => (
                        <span key={`${group.reason}-${target}`} className="failure-target-chip">
                          {target}
                        </span>
                      ))}
                    </div>
                    <p className="failure-suggestion">{group.suggestion}</p>
                  </article>
                ))}
              </div>
            )}
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
        </div>

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
              <div className="empty-state">当前还没有已生成的日报、周报或月报草稿。</div>
            ) : null}
            {recentArticles.map((article) => (
              <article key={article.id} className="ops-article-row">
                <div>
                  <strong>{article.title}</strong>
                  <p>{article.summary}</p>
                </div>
                <div className="ops-article-meta">
                  <span className="period-pill" data-period={article.periodType}>
                    {article.periodType}
                  </span>
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