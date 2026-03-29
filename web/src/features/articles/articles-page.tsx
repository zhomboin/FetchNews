import React from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import {
  ArticleDraftRecord,
  PostVariantRecord,
  fetchArticleDrafts,
  fetchArticleVariants,
  generateDailyArticle,
} from "../../lib/api";

const ARTICLES_QUERY_KEY = ["articles"] as const;
const ARTICLE_VARIANTS_QUERY_KEY = (articleId: number | null) => ["articleVariants", articleId] as const;
const ARTICLE_REFRESH_INTERVAL_MS = 30_000;

type ArticlesPageProps = {
  health: string;
};

type ArticleMetrics = {
  totalArticles: number;
  readyArticles: number;
  totalStories: number;
  totalVariants: number;
};

function getTodayDateInput(): string {
  const now = new Date();
  const year = now.getFullYear();
  const month = `${now.getMonth() + 1}`.padStart(2, "0");
  const day = `${now.getDate()}`.padStart(2, "0");
  return `${year}-${month}-${day}`;
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
    readyArticles: articles.filter((article) => article.status === "ready").length,
    totalStories: articles.reduce((sum, article) => sum + article.storyCount, 0),
    totalVariants: articles.reduce((sum, article) => sum + article.variantCount, 0),
  };
}

function pickVariant(variants: PostVariantRecord[], platform: string): PostVariantRecord | undefined {
  return variants.find((variant) => variant.platform === platform);
}

/**
 * Phase 04 draft center for generating daily digests and reviewing platform variants.
 */
export function ArticlesPage({ health }: ArticlesPageProps): React.JSX.Element {
  const queryClient = useQueryClient();
  const [targetDate, setTargetDate] = React.useState(getTodayDateInput());
  const [selectedArticleId, setSelectedArticleId] = React.useState<number | null>(null);

  const articlesQuery = useQuery({
    queryKey: ARTICLES_QUERY_KEY,
    queryFn: fetchArticleDrafts,
    refetchInterval: ARTICLE_REFRESH_INTERVAL_MS,
  });

  const generateMutation = useMutation({
    mutationFn: (dateValue: string) => generateDailyArticle(dateValue),
    onSuccess: (article) => {
      setSelectedArticleId(article.id);
      void queryClient.invalidateQueries({ queryKey: ARTICLES_QUERY_KEY });
      void queryClient.invalidateQueries({ queryKey: ARTICLE_VARIANTS_QUERY_KEY(article.id) });
    },
  });

  const articles = articlesQuery.data ?? [];

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

  const metrics = summarizeArticles(articles);
  const variants = variantsQuery.data ?? [];
  const wechatVariant = pickVariant(variants, "wechat");
  const xVariant = pickVariant(variants, "x");
  const telegramVariant = pickVariant(variants, "telegram");

  return (
    <div className="page-stack">
      <section className="hero-panel">
        <div>
          <p className="eyebrow">Daily Digest Studio</p>
          <h1>日报草稿中心</h1>
          <p className="lede">
            基于已审核的 stories 生成日报长文与平台短帖，并在同一控制台内预览草稿资产，作为后续发布链路的输入。
          </p>
        </div>

        <div className="hero-meta">
          <div className="signal-pill">
            <span className="signal-dot-live" />
            <strong>{health}</strong>
          </div>
          <div className="meta-chip">
            <span>当前阶段</span>
            <strong>Phase 04 内容生成</strong>
          </div>
        </div>
      </section>

      <section className="stats-grid" aria-label="日报草稿摘要">
        <article className="metric-cell">
          <p>草稿数量</p>
          <strong>{metrics.totalArticles}</strong>
          <span>当前库内可审阅的日报草稿</span>
        </article>
        <article className="metric-cell">
          <p>Ready 草稿</p>
          <strong>{metrics.readyArticles}</strong>
          <span>已生成并可进入发布链路的日报</span>
        </article>
        <article className="metric-cell">
          <p>聚合 stories</p>
          <strong>{metrics.totalStories}</strong>
          <span>所有草稿累计引用的 story 数量</span>
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
            <h2>日报生成</h2>
          </div>
          <span>{articlesQuery.isFetching ? "正在刷新" : "30 秒自动刷新"}</span>
        </header>

        <div className="article-generator-row">
          <label className="field-shell article-date-field">
            <span>目标日期</span>
            <input type="date" value={targetDate} onChange={(event) => setTargetDate(event.target.value)} />
          </label>
          <div className="action-row">
            <button
              type="button"
              className="button-primary"
              onClick={() => generateMutation.mutate(targetDate)}
              disabled={generateMutation.isPending}
            >
              {generateMutation.isPending ? "生成中..." : "生成或刷新日报"}
            </button>
          </div>
        </div>

        <div className="action-status">
          <span>仅消费已审核 stories；同一天再次生成会刷新已有草稿。</span>
          {generateMutation.isSuccess ? <strong>已生成草稿 #{generateMutation.data.id}</strong> : null}
          {generateMutation.isError ? <strong>日报生成失败，请检查已审核 stories 和后端日志。</strong> : null}
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
          {articlesQuery.isError ? <div className="empty-state">日报草稿加载失败，请确认 `/articles` 接口可用。</div> : null}
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
                    <span className={`status-pill status-${article.status}`}>{article.status}</span>
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
              <p>Draft Preview</p>
              <h2>草稿详情</h2>
            </div>
            <span>{selectedArticle ? `草稿 #${selectedArticle.id}` : "未选择草稿"}</span>
          </header>

          {!selectedArticle ? <div className="empty-state">选择左侧草稿后查看正文和短帖版本。</div> : null}

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

              {variantsQuery.isLoading ? <div className="empty-state">正在加载短帖变体...</div> : null}
              {variantsQuery.isError ? <div className="empty-state">短帖变体加载失败，请确认 `/articles/:articleId/variants` 接口可用。</div> : null}
            </div>
          ) : null}
        </article>
      </section>
    </div>
  );
}
