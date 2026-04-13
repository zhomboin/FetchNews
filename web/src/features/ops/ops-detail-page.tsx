import React from "react";
import { useQuery } from "@tanstack/react-query";
import { useSearchParams } from "react-router-dom";

import { DetailLink, EmptyState, StatusPill } from "../../components/console";
import {
  ArticleDraftRecord,
  IngestRunRecord,
  PublishJobRecord,
  SourceSpec,
  StoryRecord,
  fetchArticleDrafts,
  fetchIngestRuns,
  fetchOpsSummary,
  fetchPublishJobs,
  fetchSourceSpecs,
  fetchStories,
  formatSectionLabel,
} from "../../lib/api";

const REFRESH_INTERVAL_MS = 30_000;
const OPS_SUMMARY_QUERY_KEY = ["opsSummary", "detail"] as const;
const STORIES_QUERY_KEY = ["stories", "detail"] as const;
const PUBLISH_JOBS_QUERY_KEY = ["publishJobs", "detail"] as const;
const ARTICLES_QUERY_KEY = ["articles", "detail"] as const;
const SOURCE_SPECS_QUERY_KEY = ["sourceSpecs", "detail"] as const;
const INGEST_RUNS_QUERY_KEY = ["ingestRuns", "detail"] as const;

type OpsDetailPageProps = {
  health: string;
};

type DetailKind = "section" | "platform" | "source";

function isDetailKind(value: string | null): value is DetailKind {
  return value === "section" || value === "platform" || value === "source";
}

function formatDateTime(value: string | null): string {
  if (value === null) {
    return "运行中";
  }

  return new Intl.DateTimeFormat("zh-CN", {
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(value));
}

function formatPublishStatus(status: string): string {
  if (status === "scheduled") {
    return "待发布";
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
    return "就绪";
  }
  if (status === "scheduled") {
    return "已排程";
  }
  if (status === "published") {
    return "已发布";
  }
  if (status === "failed") {
    return "失败";
  }
  return "草稿";
}

function formatStoryStatus(status: StoryRecord["status"]): string {
  return status === "approved" ? "已审核" : "待审核";
}

function formatRunStatus(status: IngestRunRecord["status"]): string {
  if (status === "running") {
    return "运行中";
  }
  if (status === "completed") {
    return "已完成";
  }
  if (status === "failed") {
    return "失败";
  }
  return status;
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

function formatMomentumTier(momentumTier: string): string {
  if (momentumTier === "hot") {
    return "高热";
  }
  if (momentumTier === "rising") {
    return "上升";
  }
  if (momentumTier === "cooling") {
    return "降温";
  }
  return "平稳";
}

function formatPeriodType(periodType: ArticleDraftRecord["periodType"]): string {
  if (periodType === "weekly") {
    return "周报";
  }
  if (periodType === "monthly") {
    return "月报";
  }
  return "日报";
}

function buildDetailPath(kind: DetailKind, target: string, failedOnly = false): string {
  const searchParams = new URLSearchParams({ kind });
  if (kind === "section") {
    searchParams.set("section", target);
  }
  if (kind === "platform") {
    searchParams.set("platform", target);
  }
  if (kind === "source") {
    searchParams.set("source", target);
  }
  if (failedOnly) {
    searchParams.set("failedOnly", "1");
  }
  return `/ops/details?${searchParams.toString()}`;
}

function readConfigNumber(source: SourceSpec, key: string): number | null {
  const value = source.config[key];
  if (typeof value === "number") {
    return value;
  }
  if (typeof value === "string") {
    const parsed = Number(value);
    return Number.isFinite(parsed) ? parsed : null;
  }
  return null;
}

function countSourceFailures(run: IngestRunRecord, sourceSlug: string): number {
  return run.errors.filter((error) => error.sourceSlug === sourceSlug).length;
}

function pickTarget(searchParams: URLSearchParams, kind: DetailKind | null): string | null {
  if (kind === "section") {
    return searchParams.get("section");
  }
  if (kind === "platform") {
    return searchParams.get("platform");
  }
  if (kind === "source") {
    return searchParams.get("source");
  }
  return null;
}

function getWorkbenchLink(kind: DetailKind | null): string {
  if (kind === "section") {
    return "/stories";
  }
  if (kind === "platform") {
    return "/articles";
  }
  if (kind === "source") {
    return "/ingestion";
  }
  return "/";
}

/**
 * Drill-down detail page for section, platform, and failed source diagnostics.
 */
export function OpsDetailPage({ health }: OpsDetailPageProps): React.JSX.Element {
  const [searchParams] = useSearchParams();
  const kind = isDetailKind(searchParams.get("kind")) ? searchParams.get("kind") : null;
  const detailKind = kind as DetailKind | null;
  const target = pickTarget(searchParams, detailKind);
  const failedOnly = searchParams.get("failedOnly") === "1";

  const opsSummaryQuery = useQuery({
    queryKey: OPS_SUMMARY_QUERY_KEY,
    queryFn: fetchOpsSummary,
    enabled: detailKind === "section" && target !== null,
    refetchInterval: REFRESH_INTERVAL_MS,
  });
  const storiesQuery = useQuery({
    queryKey: STORIES_QUERY_KEY,
    queryFn: fetchStories,
    enabled: detailKind === "section" && target !== null,
    refetchInterval: REFRESH_INTERVAL_MS,
  });
  const publishJobsQuery = useQuery({
    queryKey: PUBLISH_JOBS_QUERY_KEY,
    queryFn: fetchPublishJobs,
    enabled: detailKind === "platform" && target !== null,
    refetchInterval: REFRESH_INTERVAL_MS,
  });
  const articlesQuery = useQuery({
    queryKey: ARTICLES_QUERY_KEY,
    queryFn: fetchArticleDrafts,
    enabled: detailKind === "platform" && target !== null,
    refetchInterval: REFRESH_INTERVAL_MS,
  });
  const sourceSpecsQuery = useQuery({
    queryKey: SOURCE_SPECS_QUERY_KEY,
    queryFn: fetchSourceSpecs,
    enabled: detailKind === "source" && target !== null,
    refetchInterval: REFRESH_INTERVAL_MS,
  });
  const ingestRunsQuery = useQuery({
    queryKey: INGEST_RUNS_QUERY_KEY,
    queryFn: fetchIngestRuns,
    enabled: detailKind === "source" && target !== null,
    refetchInterval: REFRESH_INTERVAL_MS,
  });

  const opsSummary = opsSummaryQuery.data;
  const stories = storiesQuery.data ?? [];
  const publishJobs = publishJobsQuery.data ?? [];
  const articles = articlesQuery.data ?? [];
  const sourceSpecs = sourceSpecsQuery.data ?? [];
  const ingestRuns = ingestRunsQuery.data ?? [];

  const sectionMetric =
    detailKind === "section" && target !== null
      ? opsSummary?.sectionReviewMetrics.find((metric) => metric.section === target) ?? null
      : null;
  const sectionStories =
    detailKind === "section" && target !== null
      ? stories
          .filter((story) => story.sections.includes(target))
          .sort((left, right) => right.score - left.score)
      : [];
  const platformJobs =
    detailKind === "platform" && target !== null
      ? publishJobs
          .filter((job) => job.platform === target)
          .filter((job) => (failedOnly ? job.status === "failed" : true))
          .sort((left, right) => new Date(right.updatedAt).getTime() - new Date(left.updatedAt).getTime())
      : [];
  const platformEngagement = platformJobs.reduce(
    (totals, job) => ({
      impressions: totals.impressions + (job.performanceMetrics.impressions ?? 0),
      opens: totals.opens + (job.performanceMetrics.opens ?? 0),
      clicks: totals.clicks + (job.performanceMetrics.clicks ?? 0),
      interactions: totals.interactions + (job.performanceMetrics.interactions ?? 0),
    }),
    { impressions: 0, opens: 0, clicks: 0, interactions: 0 },
  );
  const relatedArticleIds = new Set(platformJobs.map((job) => job.articleId));
  const platformArticles =
    detailKind === "platform" && target !== null
      ? articles
          .filter((article) => relatedArticleIds.has(article.id))
          .sort((left, right) => new Date(right.updatedAt).getTime() - new Date(left.updatedAt).getTime())
      : [];
  const sourceSpec =
    detailKind === "source" && target !== null ? sourceSpecs.find((source) => source.slug === target) ?? null : null;
  const sourceRuns =
    detailKind === "source" && target !== null
      ? ingestRuns
          .filter((run) => run.sourceSlugs.includes(target))
          .filter((run) => (failedOnly ? countSourceFailures(run, target) > 0 : true))
          .sort((left, right) => new Date(right.startedAt).getTime() - new Date(left.startedAt).getTime())
      : [];
  const sourceFailureRows =
    detailKind === "source" && target !== null
      ? sourceRuns.flatMap((run) =>
          run.errors
            .filter((error) => error.sourceSlug === target)
            .map((error) => ({ runId: run.id, message: error.message, startedAt: run.startedAt })),
        )
      : [];

  const isLoading =
    opsSummaryQuery.isLoading ||
    storiesQuery.isLoading ||
    publishJobsQuery.isLoading ||
    articlesQuery.isLoading ||
    sourceSpecsQuery.isLoading ||
    ingestRunsQuery.isLoading;
  const isError =
    opsSummaryQuery.isError ||
    storiesQuery.isError ||
    publishJobsQuery.isError ||
    articlesQuery.isError ||
    sourceSpecsQuery.isError ||
    ingestRunsQuery.isError;

  const headingTitle =
    detailKind === "section"
      ? `${target ? formatSectionLabel(target) : "栏目"}详情`
      : detailKind === "platform"
        ? `${target ? formatPlatform(target) : "平台"}详情`
        : detailKind === "source"
          ? `${target ?? "来源"}详情`
          : "运营详情";
  const headingLead =
    detailKind === "section"
      ? "查看当前被归入该栏目的 story、审核状态和风险信号，判断它们是否适合进入稿件链路。"
      : detailKind === "platform"
        ? "查看单个平台的发布任务、最近失败原因以及当前关联的稿件，便于快速排查平台侧问题。"
        : detailKind === "source"
          ? "在调整信任分或重新触发采集前，先检查来源治理状态、失败记录和最近运行情况。"
          : "请先从运营总览中选择栏目、平台或来源，再打开对应的下钻详情页。";

  return (
    <div className="page-stack detail-page">
      <section className="hero-panel">
        <div>
          <p className="eyebrow">运营下钻</p>
          <h1>{headingTitle}</h1>
          <p className="lede">{headingLead}</p>
          <div className="detail-breadcrumb-row">
            <DetailLink to={detailKind === "platform" ? "/publishing" : "/"}>
              返回运营总览
            </DetailLink>
            <DetailLink soft to={getWorkbenchLink(detailKind)}>
              打开对应工作台
            </DetailLink>
            {detailKind === "platform" && target !== null ? (
              <DetailLink soft to={buildDetailPath("platform", target, !failedOnly)}>
                {failedOnly ? "查看全部任务" : "仅看失败任务"}
              </DetailLink>
            ) : null}
            {detailKind === "source" && target !== null ? (
              <DetailLink soft to={buildDetailPath("source", target, !failedOnly)}>
                {failedOnly ? "查看全部运行" : "仅看失败运行"}
              </DetailLink>
            ) : null}
          </div>
        </div>

        <div className="hero-meta">
          <div className="signal-pill">
            <span className="signal-dot-live" />
            <strong>{health}</strong>
          </div>
          <div className="meta-chip">
            <span>当前目标</span>
            <strong>{target ?? "尚未选择目标"}</strong>
          </div>
        </div>
      </section>

      {!detailKind || target === null ? (
        <section className="panel">
          <EmptyState>这个详情页需要从运营总览中带入栏目、平台或来源目标。</EmptyState>
        </section>
      ) : null}

      {detailKind === "section" && target !== null ? (
        <>
          <section className="stats-grid" aria-label="栏目详情指标">
            <article className="metric-cell">
              <p>故事数</p>
              <strong>{sectionStories.length}</strong>
              <span>当前归入该栏目的 story 总数。</span>
            </article>
            <article className="metric-cell">
              <p>已审核</p>
              <strong>{sectionStories.filter((story) => story.status === "approved").length}</strong>
              <span>已经可以进入稿件生成链路的 story。</span>
            </article>
            <article className="metric-cell">
              <p>待审核</p>
              <strong>{sectionStories.filter((story) => story.status !== "approved").length}</strong>
              <span>仍等待人工审核的 story。</span>
            </article>
            <article className="metric-cell">
              <p>需复核</p>
              <strong>{sectionStories.filter((story) => story.riskFlags.length > 0).length}</strong>
              <span>至少带有一个风险标记的 story。</span>
            </article>
            <article className="metric-cell">
              <p>栏目势能</p>
              <strong>{formatMomentumTier(sectionMetric?.momentumTier ?? "steady")}</strong>
              <span>
                {sectionMetric
                  ? `${sectionMetric.engagementImpressions} 次曝光带来 ${sectionMetric.engagementClicks} 次点击。`
                  : "当前栏目还没有沉淀发布后的互动数据。"}
              </span>
            </article>
            <article className="metric-cell">
              <p>CTR</p>
              <strong>{sectionMetric ? `${Math.round(sectionMetric.clickThroughRate * 100)}%` : "--"}</strong>
              <span>
                {sectionMetric
                  ? `${sectionMetric.engagementInteractions} 次互动，${sectionMetric.engagementOpens} 次打开。`
                  : "等待发布反馈后再计算栏目转化表现。"}
              </span>
            </article>
          </section>

          <section className="panel detail-panel">
            <header className="section-title">
              <div>
                <p>栏目故事</p>
                <h2>{formatSectionLabel(target)}</h2>
              </div>
              <span>{storiesQuery.isFetching ? "刷新中" : "实时栏目切片"}</span>
            </header>

            {isLoading ? <EmptyState>正在加载栏目详情...</EmptyState> : null}
            {isError ? <EmptyState>栏目详情加载失败，请检查 `stories` 接口后重试。</EmptyState> : null}
            {!isLoading && !isError && sectionStories.length === 0 ? (
              <EmptyState>当前没有 story 命中该栏目。</EmptyState>
            ) : null}

            {!isLoading && !isError && sectionStories.length > 0 ? (
              <div className="detail-card-list">
                {sectionStories.map((story) => (
                  <article key={story.id} className="detail-card" data-tone={story.riskFlags.length > 0 ? "watch" : "calm"}>
                    <div className="detail-card-header">
                      <div>
                        <p className="detail-kicker">{story.storyKey}</p>
                        <h3>{story.clusterTitle}</h3>
                      </div>
                      <div className="detail-card-meta">
                        <StatusPill status={story.status}>{formatStoryStatus(story.status)}</StatusPill>
                        <strong>{story.score.toFixed(1)}</strong>
                      </div>
                    </div>
                    <p className="detail-copy">{story.summary}</p>
                    <div className="detail-chip-row">
                      {story.sections.map((section) => (
                        <span key={`${story.id}-${section}`} className="section-badge section-badge-soft">
                          {formatSectionLabel(section)}
                        </span>
                      ))}
                    </div>
                    {story.riskFlags.length > 0 ? (
                      <div className="detail-chip-row">
                        {story.riskFlags.map((flag) => (
                          <span key={`${story.id}-${flag}`} className="failure-target-chip">
                            {flag}
                          </span>
                        ))}
                      </div>
                    ) : null}
                    <div className="detail-inline-grid">
                      <div>
                        <span>条目数</span>
                        <strong>{story.itemCount}</strong>
                      </div>
                      <div>
                        <span>最近窗口</span>
                        <strong>{formatDateTime(story.lastSeenAt)}</strong>
                      </div>
                    </div>
                    {story.highlights.length > 0 ? (
                      <div className="detail-note-stack">
                        {story.highlights.slice(0, 3).map((highlight) => (
                          <p key={`${story.id}-${highlight}`} className="detail-note">
                            {highlight}
                          </p>
                        ))}
                      </div>
                    ) : null}
                    {story.sourceLinks.length > 0 ? (
                      <div className="detail-chip-row">
                        {story.sourceLinks.slice(0, 3).map((link) => (
                          <DetailLink key={link} href={link} rel="noreferrer" soft target="_blank">
                            来源链接
                          </DetailLink>
                        ))}
                      </div>
                    ) : null}
                  </article>
                ))}
              </div>
            ) : null}
          </section>
        </>
      ) : null}

      {detailKind === "platform" && target !== null ? (
        <>
          <section className="stats-grid" aria-label="平台详情指标">
            <article className="metric-cell">
              <p>任务数</p>
              <strong>{platformJobs.length}</strong>
              <span>当前平台筛选下可见的发布任务。</span>
            </article>
            <article className="metric-cell">
              <p>已发布</p>
              <strong>{platformJobs.filter((job) => job.status === "published").length}</strong>
              <span>已经进入终态并完成发布的任务。</span>
            </article>
            <article className="metric-cell">
              <p>点击</p>
              <strong>{platformEngagement.clicks}</strong>
              <span>当前可见任务累计 {platformEngagement.interactions} 次互动。</span>
            </article>
            <article className="metric-cell">
              <p>关联稿件</p>
              <strong>{platformArticles.length}</strong>
              <span>当前平台累计记录 {platformEngagement.impressions} 次曝光。</span>
            </article>
          </section>

          <section className="ops-grid detail-grid">
            <article className="panel">
              <header className="section-title">
              <div>
                <p>平台任务</p>
                <h2>{formatPlatform(target)}</h2>
              </div>
              <span>{failedOnly ? "仅失败任务" : "全部任务"}</span>
            </header>

              {isLoading ? <EmptyState>正在加载平台详情...</EmptyState> : null}
              {isError ? <EmptyState>平台详情加载失败，请检查发布任务和稿件接口。</EmptyState> : null}
              {!isLoading && !isError && platformJobs.length === 0 ? (
                <EmptyState>当前还没有任务命中这个平台筛选条件。</EmptyState>
              ) : null}

              {!isLoading && !isError && platformJobs.length > 0 ? (
                <div className="publish-job-list">
                  {platformJobs.map((job) => (
                    <article key={job.id} className="publish-job-row">
                      <div className="publish-job-copy">
                        <div>
                          <strong>稿件 #{job.articleId}</strong>
                          <p>{formatDateTime(job.scheduledFor)}</p>
                        </div>
                        <div className="publish-job-meta">
                          <StatusPill status={job.status}>{formatPublishStatus(job.status)}</StatusPill>
                          <span>重试 {job.retries} 次</span>
                        </div>
                      </div>
                      <div className="publish-job-note-stack">
                        <span className="publish-job-note">更新时间：{formatDateTime(job.updatedAt)}</span>
                        {job.providerJobId ? <span className="publish-job-note">提供方任务：{job.providerJobId}</span> : null}
                        {job.dispatchKey ? <span className="publish-job-note">分发键：{job.dispatchKey}</span> : null}
                        {job.lastProviderStatus ? (
                          <span className="publish-job-note">提供方状态：{job.lastProviderStatus}</span>
                        ) : null}
                        {job.externalId ? <span className="publish-job-note">外部 ID：{job.externalId}</span> : null}
                        {job.metricsRecordedAt ? (
                          <span className="publish-job-note">
                            指标：{job.performanceMetrics.impressions ?? 0} 次曝光 · {job.performanceMetrics.clicks ?? 0} 次点击 · {job.performanceMetrics.interactions ?? 0} 次互动
                          </span>
                        ) : null}
                        {job.failureCategory ? (
                          <span className="publish-job-note">失败分类：{job.failureCategory}</span>
                        ) : null}
                        {job.errorMessage ? <span className="publish-job-error">{job.errorMessage}</span> : null}
                      </div>
                    </article>
                  ))}
                </div>
              ) : null}
            </article>

            <article className="panel">
              <header className="section-title">
              <div>
                  <p>关联稿件</p>
                  <h2>{formatPlatform(target)} 的关联稿件</h2>
                </div>
                <span>{platformArticles.length} 篇稿件</span>
              </header>

              {isLoading ? <EmptyState>正在加载关联稿件...</EmptyState> : null}
              {!isLoading && !isError && platformArticles.length === 0 ? (
                <EmptyState>当前没有稿件与这个平台筛选条件关联。</EmptyState>
              ) : null}

              {!isLoading && !isError && platformArticles.length > 0 ? (
                <div className="ops-article-list">
                  {platformArticles.map((article) => {
                    const matchingJobs = platformJobs.filter((job) => job.articleId === article.id);
                    return (
                      <article key={article.id} className="ops-article-row">
                        <div>
                          <strong>{article.title}</strong>
                          <p>
                            {formatPeriodType(article.periodType)} · {article.storyCount} 条 story · 更新于 {formatDateTime(article.updatedAt)}
                          </p>
                        </div>
                        <div className="ops-article-meta">
                          <StatusPill status={article.status}>{formatArticleStatus(article.status)}</StatusPill>
                          <span>{matchingJobs.length} 条关联任务</span>
                        </div>
                      </article>
                    );
                  })}
                </div>
              ) : null}
            </article>
          </section>
        </>
      ) : null}

      {detailKind === "source" && target !== null ? (
        <>
          <section className="stats-grid" aria-label="来源详情指标">
            <article className="metric-cell">
              <p>运行批次</p>
              <strong>{sourceRuns.length}</strong>
              <span>最近包含该来源的采集批次。</span>
            </article>
            <article className="metric-cell">
              <p>失败记录</p>
              <strong>{sourceFailureRows.length}</strong>
              <span>当前可见运行中记录到的来源错误条数。</span>
            </article>
            <article className="metric-cell">
              <p>信任分</p>
              <strong>{sourceSpec?.effectiveTrustScore?.toFixed(1) ?? "--"}</strong>
              <span>治理反馈作用后的有效信任分。</span>
            </article>
            <article className="metric-cell">
              <p>排序倍率</p>
              <strong>{sourceSpec?.effectiveScoreMultiplier?.toFixed(2) ?? "--"}x</strong>
              <span>story 排序阶段实际使用的倍率。</span>
            </article>
            <article className="metric-cell">
              <p>Cursor</p>
              <strong>{sourceSpec?.incrementalCursor ?? "--"}</strong>
              <span>该来源最近一次持久化的增量游标。</span>
            </article>
            <article className="metric-cell">
              <p>最近成功</p>
              <strong>{sourceSpec?.lastSuccessAt ? formatDateTime(sourceSpec.lastSuccessAt) : "--"}</strong>
              <span>该来源最近一次成功写回采集结果的时间。</span>
            </article>
          </section>

          <section className="ops-grid detail-grid">
            <article className="panel">
              <header className="section-title">
              <div>
                <p>来源治理</p>
                <h2>{sourceSpec?.label ?? target}</h2>
              </div>
              <span>{sourceSpec?.priority ?? "未知优先级"}</span>
            </header>

              {isLoading ? <EmptyState>正在加载来源详情...</EmptyState> : null}
              {isError ? <EmptyState>来源详情加载失败，请检查来源目录和采集运行接口。</EmptyState> : null}
              {!isLoading && !isError && sourceSpec === null ? (
                <EmptyState>来源目录里没有与该 slug 匹配的条目。</EmptyState>
              ) : null}

              {!isLoading && !isError && sourceSpec !== null ? (
                <article className="source-governance-card" data-tone={sourceSpec.governanceFlags.length > 0 ? "watch" : "calm"}>
                  <div className="source-governance-head">
                    <div>
                      <p>{sourceSpec.platform}</p>
                      <strong>{sourceSpec.label}</strong>
                    </div>
                    <span className="source-chip">{sourceSpec.priority}</span>
                  </div>
                  <div className="platform-metric-grid compact-gap">
                    <div>
                      <span>基础信任分</span>
                      <strong>{readConfigNumber(sourceSpec, "trust_score")?.toFixed(1) ?? "--"}</strong>
                    </div>
                    <div>
                      <span>有效信任分</span>
                      <strong>{sourceSpec.effectiveTrustScore?.toFixed(1) ?? "--"}</strong>
                    </div>
                    <div>
                      <span>基础倍率</span>
                      <strong>{readConfigNumber(sourceSpec, "score_multiplier")?.toFixed(2) ?? "--"}x</strong>
                    </div>
                    <div>
                      <span>有效倍率</span>
                      <strong>{sourceSpec.effectiveScoreMultiplier?.toFixed(2) ?? "--"}x</strong>
                    </div>
                  </div>
                  <p className="source-governance-note">
                    失败 {sourceSpec.feedbackSignals.failed_ingest_runs ?? 0} · 待审核 {sourceSpec.feedbackSignals.pending_stories ?? 0} · 需复核 {sourceSpec.feedbackSignals.flagged_stories ?? 0}
                  </p>
                  {sourceSpec.incrementalCursor || sourceSpec.lastSuccessAt ? (
                    <p className="source-governance-note">
                      {sourceSpec.incrementalCursor ? `游标 ${sourceSpec.incrementalCursor}` : "游标 --"} ·{" "}
                      {sourceSpec.lastSuccessAt ? `最近成功 ${formatDateTime(sourceSpec.lastSuccessAt)}` : "最近成功 --"}
                    </p>
                  ) : null}
                  {sourceSpec.governanceFlags.length > 0 ? (
                    <div className="failure-chip-list">
                      {sourceSpec.governanceFlags.map((flag) => (
                        <span key={`${sourceSpec.slug}-${flag}`} className="failure-target-chip">
                          {flag}
                        </span>
                      ))}
                    </div>
                  ) : null}
                </article>
              ) : null}
            </article>

            <article className="panel">
              <header className="section-title">
              <div>
                  <p>运行历史</p>
                  <h2>{failedOnly ? "失败运行" : "最近运行"}</h2>
                </div>
                <span>{sourceRuns.length} 次运行</span>
              </header>

              {isLoading ? <EmptyState>正在加载来源运行记录...</EmptyState> : null}
              {!isLoading && !isError && sourceRuns.length === 0 ? (
                <EmptyState>当前没有运行记录命中该来源筛选条件。</EmptyState>
              ) : null}

              {!isLoading && !isError && sourceRuns.length > 0 ? (
                <div className="ingest-run-list">
                  {sourceRuns.map((run) => {
                    const sourceErrors = run.errors.filter((error) => error.sourceSlug === target);
                    return (
                      <article key={run.id} className="ingest-run-row">
                        <div className="run-main">
                          <div className="run-head">
                            <h3>采集批次 #{run.id}</h3>
                            <StatusPill status={run.status}>{formatRunStatus(run.status)}</StatusPill>
                          </div>
                          <div className="source-chip-list">
                            {run.sourceSlugs.map((slug) => (
                              <span key={`${run.id}-${slug}`} className="source-chip">
                                {slug}
                              </span>
                            ))}
                          </div>
                          {sourceErrors.length > 0 ? (
                            <div className="run-errors">
                              {sourceErrors.map((error) => (
                                <p key={`${run.id}-${error.message}`}>{error.message}</p>
                              ))}
                            </div>
                          ) : (
                            <p className="run-note">该批次没有记录到当前来源的专属错误。</p>
                          )}
                        </div>
                        <div className="run-metrics">
                          <div>
                            <span>状态</span>
                            <strong>{formatRunStatus(run.status)}</strong>
                          </div>
                          <div>
                            <span>条目</span>
                            <strong>{run.itemsIngested}</strong>
                          </div>
                          <div>
                            <span>开始时间</span>
                            <strong>{formatDateTime(run.startedAt)}</strong>
                          </div>
                          <div>
                            <span>结束时间</span>
                            <strong>{formatDateTime(run.finishedAt)}</strong>
                          </div>
                        </div>
                      </article>
                    );
                  })}
                </div>
              ) : null}
            </article>
          </section>
        </>
      ) : null}
    </div>
  );
}
