import React from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import {
  ArticleDraftRecord,
  PostVariantRecord,
  PublishJobRecord,
  StoryRecord,
  fetchArticleDrafts,
  fetchArticleVariants,
  fetchPublishJobs,
  fetchStories,
  generateDailyArticle,
  publishArticle,
  retryPublishJob,
  writePublishJobResult,
} from "../../lib/api";

const ARTICLES_QUERY_KEY = ["articles"] as const;
const STORIES_QUERY_KEY = ["stories"] as const;
const PUBLISH_JOBS_QUERY_KEY = ["publishJobs"] as const;
const ARTICLE_VARIANTS_QUERY_KEY = (articleId: number | null) => ["articleVariants", articleId] as const;
const ARTICLE_REFRESH_INTERVAL_MS = 30_000;
const PUBLISH_PLATFORMS = ["wechat", "x", "telegram"] as const;
const MANUAL_FAILURE_MESSAGE = "人工审核标记失败，等待重试";

type ArticlesPageProps = {
  health: string;
};

type ArticleMetrics = {
  totalArticles: number;
  readyArticles: number;
  publishedArticles: number;
  totalStories: number;
  totalVariants: number;
};

type ScopeMode = "all-approved" | "custom";

function getTodayDateInput(): string {
  const now = new Date();
  const year = now.getFullYear();
  const month = `${now.getMonth() + 1}`.padStart(2, "0");
  const day = `${now.getDate()}`.padStart(2, "0");
  return `${year}-${month}-${day}`;
}

function getDefaultScheduleInput(): string {
  const next = new Date();
  next.setMinutes(next.getMinutes() + 30);
  const year = next.getFullYear();
  const month = `${next.getMonth() + 1}`.padStart(2, "0");
  const day = `${next.getDate()}`.padStart(2, "0");
  const hour = `${next.getHours()}`.padStart(2, "0");
  const minute = `${next.getMinutes()}`.padStart(2, "0");
  return `${year}-${month}-${day}T${hour}:${minute}`;
}

function formatDate(value: string): string {
  return new Intl.DateTimeFormat("zh-CN", {
    month: "2-digit",
    day: "2-digit",
  }).format(new Date(value));
}

function formatDateTime(value: string): string {
  return new Intl.DateTimeFormat("zh-CN", {
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(value));
}

function summarizeArticles(articles: ArticleDraftRecord[]): ArticleMetrics {
  return {
    totalArticles: articles.length,
    readyArticles: articles.filter((article) => article.status === "ready" || article.status === "scheduled").length,
    publishedArticles: articles.filter((article) => article.status === "published").length,
    totalStories: articles.reduce((sum, article) => sum + article.storyCount, 0),
    totalVariants: articles.reduce((sum, article) => sum + article.variantCount, 0),
  };
}

function pickVariant(variants: PostVariantRecord[], platform: string): PostVariantRecord | undefined {
  return variants.find((variant) => variant.platform === platform);
}

function formatStoryStatus(status: StoryRecord["status"]): string {
  if (status === "approved") {
    return "已审核";
  }
  return "待审核";
}

function formatArticleStatus(status: string): string {
  if (status === "draft") {
    return "草稿";
  }
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
  return status;
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

function formatPlatform(platform: string): string {
  if (platform === "wechat") {
    return "WeChat";
  }
  if (platform === "telegram") {
    return "Telegram";
  }
  return platform.toUpperCase();
}

function toUtcIsoString(value: string): string | null {
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return null;
  }
  return parsed.toISOString();
}

/**
 * Phase 04/05 draft center for digest generation, review, publish writeback, and retry handling.
 */
export function ArticlesPage({ health }: ArticlesPageProps): React.JSX.Element {
  const queryClient = useQueryClient();
  const [targetDate, setTargetDate] = React.useState(getTodayDateInput());
  const [scopeMode, setScopeMode] = React.useState<ScopeMode>("all-approved");
  const [selectedStoryIds, setSelectedStoryIds] = React.useState<number[]>([]);
  const [generationNote, setGenerationNote] = React.useState("");
  const [selectedArticleId, setSelectedArticleId] = React.useState<number | null>(null);
  const [selectedPlatforms, setSelectedPlatforms] = React.useState<string[]>([...PUBLISH_PLATFORMS]);
  const [scheduledFor, setScheduledFor] = React.useState(getDefaultScheduleInput());

  const articlesQuery = useQuery({
    queryKey: ARTICLES_QUERY_KEY,
    queryFn: fetchArticleDrafts,
    refetchInterval: ARTICLE_REFRESH_INTERVAL_MS,
  });
  const storiesQuery = useQuery({
    queryKey: STORIES_QUERY_KEY,
    queryFn: fetchStories,
    refetchInterval: ARTICLE_REFRESH_INTERVAL_MS,
  });
  const publishJobsQuery = useQuery({
    queryKey: PUBLISH_JOBS_QUERY_KEY,
    queryFn: fetchPublishJobs,
    refetchInterval: ARTICLE_REFRESH_INTERVAL_MS,
  });

  function invalidateArticleWorkspace(articleId: number | null = selectedArticleId): void {
    void queryClient.invalidateQueries({ queryKey: ARTICLES_QUERY_KEY });
    void queryClient.invalidateQueries({ queryKey: PUBLISH_JOBS_QUERY_KEY });
    if (articleId !== null) {
      void queryClient.invalidateQueries({ queryKey: ARTICLE_VARIANTS_QUERY_KEY(articleId) });
    }
  }

  const generateMutation = useMutation({
    mutationFn: () =>
      generateDailyArticle({
        targetDate,
        storyIds: scopeMode === "custom" ? selectedStoryIds : undefined,
        generationNote: generationNote.trim() || undefined,
      }),
    onSuccess: (article) => {
      setSelectedArticleId(article.id);
      invalidateArticleWorkspace(article.id);
    },
  });

  const publishMutation = useMutation({
    mutationFn: (articleId: number) => {
      const scheduledIso = toUtcIsoString(scheduledFor);
      if (scheduledIso === null) {
        throw new Error("invalid_schedule");
      }
      return publishArticle(articleId, {
        platforms: selectedPlatforms,
        scheduledFor: scheduledIso,
      });
    },
    onSuccess: () => {
      invalidateArticleWorkspace();
    },
  });

  const markPublishedMutation = useMutation({
    mutationFn: (jobId: number) => writePublishJobResult(jobId, { status: "published" }),
    onSuccess: () => {
      invalidateArticleWorkspace();
    },
  });

  const markFailedMutation = useMutation({
    mutationFn: (jobId: number) =>
      writePublishJobResult(jobId, {
        status: "failed",
        errorMessage: MANUAL_FAILURE_MESSAGE,
      }),
    onSuccess: () => {
      invalidateArticleWorkspace();
    },
  });

  const retryMutation = useMutation({
    mutationFn: (jobId: number) => retryPublishJob(jobId),
    onSuccess: () => {
      invalidateArticleWorkspace();
    },
  });

  const articles = articlesQuery.data ?? [];
  const allStories = storiesQuery.data ?? [];
  const approvedStories = allStories.filter((story) => story.status === "approved");
  const metrics = summarizeArticles(articles);

  React.useEffect(() => {
    if (scopeMode === "custom" && selectedStoryIds.length === 0 && approvedStories.length > 0) {
      setSelectedStoryIds(approvedStories.map((story) => story.id));
    }
  }, [approvedStories, scopeMode, selectedStoryIds.length]);

  React.useEffect(() => {
    if (articles.length === 0) {
      if (selectedArticleId !== null) {
        setSelectedArticleId(null);
      }
      return;
    }

    const articleStillExists = articles.some((article) => article.id === selectedArticleId);
    if (!articleStillExists) {
      setSelectedArticleId(articles[0].id);
    }
  }, [articles, selectedArticleId]);

  const selectedArticle = articles.find((article) => article.id === selectedArticleId) ?? null;
  const variantsQuery = useQuery({
    queryKey: ARTICLE_VARIANTS_QUERY_KEY(selectedArticleId),
    queryFn: () => fetchArticleVariants(selectedArticleId ?? 0),
    enabled: selectedArticleId !== null,
    refetchInterval: ARTICLE_REFRESH_INTERVAL_MS,
  });

  const variants = variantsQuery.data ?? [];
  const wechatVariant = pickVariant(variants, "wechat");
  const xVariant = pickVariant(variants, "x");
  const telegramVariant = pickVariant(variants, "telegram");

  const selectedArticleStories = selectedArticle
    ? allStories.filter((story) => selectedArticle.storyIds.includes(story.id))
    : [];
  const articlePublishJobs = (publishJobsQuery.data ?? [])
    .filter((job) => job.articleId === selectedArticleId)
    .sort((left, right) => new Date(right.scheduledFor).getTime() - new Date(left.scheduledFor).getTime());
  const hasAllSelectedVariants = selectedArticle
    ? selectedPlatforms.every(
        (platform) =>
          selectedArticle.variantCount >= selectedPlatforms.length &&
          variants.some((variant) => variant.platform === platform),
      )
    : false;
  const canGenerate =
    scopeMode === "all-approved" ? approvedStories.length > 0 : selectedStoryIds.length > 0;
  const canPublish =
    selectedArticle !== null &&
    selectedPlatforms.length > 0 &&
    toUtcIsoString(scheduledFor) !== null &&
    hasAllSelectedVariants;
  const isJobActionPending =
    markPublishedMutation.isPending || markFailedMutation.isPending || retryMutation.isPending;

  function toggleSelectedStory(storyId: number): void {
    setSelectedStoryIds((current) =>
      current.includes(storyId) ? current.filter((id) => id !== storyId) : [...current, storyId],
    );
  }

  function togglePlatform(platform: string): void {
    setSelectedPlatforms((current) =>
      current.includes(platform) ? current.filter((item) => item !== platform) : [...current, platform],
    );
  }

  function renderPublishJobActions(job: PublishJobRecord): React.JSX.Element {
    if (job.status === "scheduled") {
      return (
        <div className="publish-job-actions">
          <button
            type="button"
            className="button-secondary"
            onClick={() => markFailedMutation.mutate(job.id)}
            disabled={isJobActionPending}
          >
            标记失败
          </button>
          <button
            type="button"
            className="button-primary"
            onClick={() => markPublishedMutation.mutate(job.id)}
            disabled={isJobActionPending}
          >
            标记已发布
          </button>
        </div>
      );
    }

    if (job.status === "failed") {
      return (
        <div className="publish-job-actions">
          <button
            type="button"
            className="button-secondary"
            onClick={() => retryMutation.mutate(job.id)}
            disabled={isJobActionPending}
          >
            重新入队
          </button>
        </div>
      );
    }

    return (
      <div className="publish-job-actions publish-job-actions-readonly">
        <span>结果已回写，无需额外操作。</span>
      </div>
    );
  }

  return (
    <div className="page-stack">
      <section className="hero-panel">
        <div>
          <p className="eyebrow">Daily Digest Studio</p>
          <h1>日报草稿中心</h1>
          <p className="lede">
            基于已审核 stories 控制日报生成范围与说明，并在同一工作台完成发布前审核、结果回写、失败重试和状态追踪。
          </p>
        </div>

        <div className="hero-meta">
          <div className="signal-pill">
            <span className="signal-dot-live" />
            <strong>{health}</strong>
          </div>
          <div className="meta-chip">
            <span>当前阶段</span>
            <strong>Phase 04 + Phase 05</strong>
          </div>
        </div>
      </section>

      <section className="stats-grid" aria-label="日报草稿摘要">
        <article className="metric-cell">
          <p>草稿数量</p>
          <strong>{metrics.totalArticles}</strong>
          <span>当前库内可审核的日报草稿</span>
        </article>
        <article className="metric-cell">
          <p>待发布草稿</p>
          <strong>{metrics.readyArticles}</strong>
          <span>处于 ready 或 scheduled 状态的日报</span>
        </article>
        <article className="metric-cell">
          <p>已发布草稿</p>
          <strong>{metrics.publishedArticles}</strong>
          <span>所有发布任务都已完成回写的日报</span>
        </article>
        <article className="metric-cell">
          <p>短帖变体</p>
          <strong>{metrics.totalVariants}</strong>
          <span>已生成的各平台短帖版本总数</span>
        </article>
      </section>

      <section className="panel article-control-panel">
        <header className="section-title ingestion-head">
          <div>
            <p>Digest Controls</p>
            <h2>按日期重建与生成控制</h2>
          </div>
          <span>{articlesQuery.isFetching || storiesQuery.isFetching ? "正在刷新" : "30 秒自动刷新"}</span>
        </header>

        <div className="article-generator-grid">
          <label className="field-shell article-date-field">
            <span>目标日期</span>
            <input type="date" value={targetDate} onChange={(event) => setTargetDate(event.target.value)} />
          </label>

          <div className="filter-group">
            <p className="filter-caption">story 范围</p>
            <div className="filter-chip-row">
              <button
                type="button"
                className={`filter-chip ${scopeMode === "all-approved" ? "active" : ""}`}
                onClick={() => setScopeMode("all-approved")}
              >
                全部已审核
              </button>
              <button
                type="button"
                className={`filter-chip ${scopeMode === "custom" ? "active" : ""}`}
                onClick={() => setScopeMode("custom")}
              >
                自定义范围
              </button>
            </div>
          </div>
        </div>

        {scopeMode === "custom" ? (
          <div className="story-scope-panel">
            <div className="story-scope-head">
              <strong>选择参与本次日报的 stories</strong>
              <span>
                {selectedStoryIds.length} / {approvedStories.length} 条
              </span>
            </div>

            <div className="story-scope-list">
              {approvedStories.map((story) => (
                <button
                  key={story.id}
                  type="button"
                  className={`story-scope-chip ${selectedStoryIds.includes(story.id) ? "selected" : ""}`}
                  onClick={() => toggleSelectedStory(story.id)}
                >
                  <span>{story.clusterTitle}</span>
                  <strong>{formatStoryStatus(story.status)}</strong>
                </button>
              ))}
            </div>
          </div>
        ) : null}

        <label className="field-shell article-note-field">
          <span>生成说明</span>
          <textarea
            value={generationNote}
            onChange={(event) => setGenerationNote(event.target.value)}
            placeholder="例如：优先突出 agent 工作流与评测方向，淡化泛社区热帖。"
            rows={4}
          />
        </label>

        <div className="action-row">
          <button type="button" className="button-secondary" onClick={() => setGenerationNote("")}>清空说明</button>
          <button
            type="button"
            className="button-primary"
            onClick={() => generateMutation.mutate()}
            disabled={!canGenerate || generateMutation.isPending}
          >
            {generateMutation.isPending ? "生成中..." : "按日期生成或重建日报"}
          </button>
        </div>

        <div className="action-status">
          <span>
            {scopeMode === "all-approved"
              ? `将使用全部 ${approvedStories.length} 条已审核 stories 参与生成。`
              : `将使用 ${selectedStoryIds.length} 条 stories 参与生成。`}
          </span>
          {generateMutation.isSuccess ? <strong>已生成草稿 #{generateMutation.data.id}</strong> : null}
          {generateMutation.isError ? <strong>日报生成失败，请检查 story 选择与后端日志。</strong> : null}
        </div>
      </section>

      <section className="article-layout">
        <article className="panel article-list-panel">
          <header className="section-title">
            <div>
              <p>Draft Ledger</p>
              <h2>草稿列表</h2>
            </div>
            <span>{articles.length} 条</span>
          </header>

          {articlesQuery.isLoading ? <div className="empty-state">正在加载日报草稿...</div> : null}
          {articlesQuery.isError ? <div className="empty-state">日报草稿加载失败，请确认 /articles 接口可用。</div> : null}
          {!articlesQuery.isLoading && !articlesQuery.isError && articles.length === 0 ? (
            <div className="empty-state">当前还没有日报草稿。先生成一篇日报。</div>
          ) : null}

          {!articlesQuery.isLoading && !articlesQuery.isError && articles.length > 0 ? (
            <div className="article-list">
              {articles.map((article) => (
                <button
                  key={article.id}
                  type="button"
                  className={`article-row ${article.id === selectedArticleId ? "selected" : ""}`}
                  onClick={() => setSelectedArticleId(article.id)}
                >
                  <div className="article-row-topline">
                    <p>{formatDate(article.targetDate)}</p>
                    <span className={`status-pill status-${article.status}`}>{formatArticleStatus(article.status)}</span>
                  </div>
                  <h3>{article.title}</h3>
                  <p>{article.summary}</p>
                  <div className="article-row-meta">
                    <span>{article.storyCount} 条 stories</span>
                    <span>{article.variantCount} 个变体</span>
                    <span>{formatDateTime(article.updatedAt)}</span>
                  </div>
                </button>
              ))}
            </div>
          ) : null}
        </article>

        <article className="panel article-detail-panel">
          <header className="section-title">
            <div>
              <p>Draft Review</p>
              <h2>草稿详情与发布前审核</h2>
            </div>
            <span>{selectedArticle ? `草稿 #${selectedArticle.id}` : "未选择草稿"}</span>
          </header>

          {!selectedArticle ? <div className="empty-state">选择左侧草稿后查看正文、短帖和发布审核信息。</div> : null}

          {selectedArticle ? (
            <div className="article-detail-stack">
              <section className="article-hero-card">
                <div className="article-hero-copy">
                  <p>{selectedArticle.targetDate}</p>
                  <h3>{selectedArticle.title}</h3>
                  <span>{selectedArticle.summary}</span>
                </div>
                <div className="article-hero-meta">
                  <div>
                    <strong>{selectedArticle.storyCount}</strong>
                    <span>stories</span>
                  </div>
                  <div>
                    <strong>{selectedArticle.variantCount}</strong>
                    <span>variants</span>
                  </div>
                  <div>
                    <strong>{formatArticleStatus(selectedArticle.status)}</strong>
                    <span>article status</span>
                  </div>
                </div>
              </section>

              <section className="article-body-panel">
                <header className="subsection-head">
                  <strong>生成说明</strong>
                  <span>{selectedArticle.generationNote ? "已配置" : "未配置"}</span>
                </header>
                <p className="article-note-copy">{selectedArticle.generationNote ?? "当前草稿未记录额外生成说明。"}</p>
              </section>

              <section className="article-body-panel">
                <header className="subsection-head">
                  <strong>纳入范围</strong>
                  <span>{selectedArticleStories.length} 条 stories</span>
                </header>
                <div className="story-scope-list compact">
                  {selectedArticleStories.map((story) => (
                    <div key={story.id} className="story-scope-chip selected static">
                      <span>{story.clusterTitle}</span>
                      <strong>{story.score.toFixed(1)}</strong>
                    </div>
                  ))}
                </div>
              </section>

              <section className="article-body-panel">
                <header className="subsection-head">
                  <strong>长文正文</strong>
                  <span>{formatDateTime(selectedArticle.updatedAt)}</span>
                </header>
                <pre className="article-body-pre">{selectedArticle.body}</pre>
              </section>

              <section className="variant-grid">
                <article className="variant-card">
                  <header className="subsection-head">
                    <strong>WeChat</strong>
                    <span>{wechatVariant ? formatDateTime(wechatVariant.updatedAt) : "未生成"}</span>
                  </header>
                  <p>{wechatVariant?.content ?? "当前还没有 WeChat 版本。"}</p>
                </article>
                <article className="variant-card">
                  <header className="subsection-head">
                    <strong>X</strong>
                    <span>{xVariant ? formatDateTime(xVariant.updatedAt) : "未生成"}</span>
                  </header>
                  <p>{xVariant?.content ?? "当前还没有 X 版本。"}</p>
                </article>
                <article className="variant-card">
                  <header className="subsection-head">
                    <strong>Telegram</strong>
                    <span>{telegramVariant ? formatDateTime(telegramVariant.updatedAt) : "未生成"}</span>
                  </header>
                  <p>{telegramVariant?.content ?? "当前还没有 Telegram 版本。"}</p>
                </article>
              </section>

              <section className="article-body-panel publish-review-panel">
                <header className="subsection-head">
                  <strong>发布前审核</strong>
                  <span>{articlePublishJobs.length} 条发布任务</span>
                </header>

                <div className="publish-checklist-grid">
                  <div className="risk-stat" data-tone={selectedArticle.storyCount > 0 ? "calm" : "watch"}>
                    <p>内容范围</p>
                    <strong>{selectedArticle.storyCount > 0 ? "已覆盖" : "缺失"}</strong>
                    <span>
                      {selectedArticle.storyCount > 0
                        ? `${selectedArticle.storyCount} 条 stories 已纳入本稿。`
                        : "当前草稿没有故事输入。"}
                    </span>
                  </div>
                  <div className="risk-stat" data-tone={hasAllSelectedVariants ? "calm" : "watch"}>
                    <p>平台变体</p>
                    <strong>{hasAllSelectedVariants ? "可发布" : "待补齐"}</strong>
                    <span>
                      {hasAllSelectedVariants
                        ? "所选平台均存在可用变体。"
                        : "请先确认所选平台的变体已生成。"}
                    </span>
                  </div>
                  <div className="risk-stat" data-tone={selectedArticle.status === "failed" ? "watch" : "default"}>
                    <p>草稿状态</p>
                    <strong>{formatArticleStatus(selectedArticle.status)}</strong>
                    <span>状态会跟随发布任务回写自动变化，无需手工同步。</span>
                  </div>
                </div>

                <div className="publish-control-stack">
                  <div className="filter-group">
                    <p className="filter-caption">发布平台</p>
                    <div className="filter-chip-row">
                      {PUBLISH_PLATFORMS.map((platform) => (
                        <button
                          key={platform}
                          type="button"
                          className={`filter-chip ${selectedPlatforms.includes(platform) ? "active" : ""}`}
                          onClick={() => togglePlatform(platform)}
                        >
                          {formatPlatform(platform)}
                        </button>
                      ))}
                    </div>
                  </div>

                  <label className="field-shell article-date-field">
                    <span>计划发布时间</span>
                    <input type="datetime-local" value={scheduledFor} onChange={(event) => setScheduledFor(event.target.value)} />
                  </label>
                </div>

                <div className="action-row">
                  <button
                    type="button"
                    className="button-primary"
                    onClick={() => {
                      if (selectedArticle !== null) {
                        publishMutation.mutate(selectedArticle.id);
                      }
                    }}
                    disabled={!canPublish || publishMutation.isPending}
                  >
                    {publishMutation.isPending ? "创建中..." : "创建发布任务"}
                  </button>
                </div>

                <div className="action-status">
                  <span>先在本页确认正文、平台短帖和发布时间，再创建发布任务。</span>
                  {publishMutation.isSuccess ? <strong>已写入 {publishMutation.data.length} 条发布任务。</strong> : null}
                  {publishMutation.isError ? <strong>发布任务创建失败，请检查时间和平台选择。</strong> : null}
                  {markPublishedMutation.isSuccess ? <strong>发布成功结果已回写。</strong> : null}
                  {markFailedMutation.isSuccess ? <strong>失败结果已回写，可直接重试。</strong> : null}
                  {retryMutation.isSuccess ? <strong>失败任务已重新入队。</strong> : null}
                </div>

                <div className="publish-job-list">
                  {articlePublishJobs.length === 0 ? (
                    <div className="empty-state">当前草稿还没有发布任务。</div>
                  ) : (
                    articlePublishJobs.map((job) => (
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
                          {job.externalId ? <span className="publish-job-note">外部 ID：{job.externalId}</span> : null}
                          {job.errorMessage ? <span className="publish-job-error">{job.errorMessage}</span> : null}
                        </div>

                        {renderPublishJobActions(job)}
                      </article>
                    ))
                  )}
                </div>
              </section>

              {variantsQuery.isLoading ? <div className="empty-state">正在加载短帖变体...</div> : null}
              {variantsQuery.isError ? <div className="empty-state">短帖变体加载失败，请确认 /articles/:articleId/variants 接口可用。</div> : null}
            </div>
          ) : null}
        </article>
      </section>
    </div>
  );
}