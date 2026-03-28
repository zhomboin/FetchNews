import React from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import {
  NormalizedItemRecord,
  StoryRecord,
  approveStory,
  fetchNormalizedItems,
  fetchStories,
  rebuildStoriesPipeline,
} from "../../lib/api";

const STORIES_QUERY_KEY = ["stories"] as const;
const NORMALIZED_ITEMS_QUERY_KEY = ["normalizedItems"] as const;
const STORY_REFRESH_INTERVAL_MS = 30_000;
const NORMALIZED_ITEM_LIMIT = 10;
const STORY_STATUS_OPTIONS = [
  { value: "all", label: "全部状态" },
  { value: "pending", label: "待审核" },
  { value: "approved", label: "已审核" },
] as const;
const STORY_RISK_OPTIONS = [
  { value: "all", label: "全部风险" },
  { value: "watch", label: "需复核" },
  { value: "clean", label: "低风险" },
] as const;
const RISK_FLAG_LABELS: Record<string, string> = {
  secondary_sources_only: "仅次级来源",
};
const RISK_FLAG_DETAILS: Record<string, string> = {
  secondary_sources_only: "当前聚类尚未关联到 P0 一手来源，进入生成链路前建议人工复核。",
};

type StoriesPageProps = {
  health: string;
};

type StoryMetrics = {
  totalStories: number;
  filteredStories: number;
  approvedStories: number;
  totalStoryItems: number;
  flaggedStories: number;
};

type StoryStatusFilter = (typeof STORY_STATUS_OPTIONS)[number]["value"];
type StoryRiskFilter = (typeof STORY_RISK_OPTIONS)[number]["value"];
type StoryRiskTone = "calm" | "watch" | "alert";

type StoryRiskPresentation = {
  tone: StoryRiskTone;
  label: string;
  detail: string;
};

function formatDateTime(value: string): string {
  return new Intl.DateTimeFormat("zh-CN", {
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(value));
}

function formatStoryStatus(status: StoryRecord["status"]): string {
  if (status === "approved") {
    return "已审核";
  }
  return "待审核";
}

function summarizeStories(allStories: StoryRecord[], filteredStories: StoryRecord[]): StoryMetrics {
  return {
    totalStories: allStories.length,
    filteredStories: filteredStories.length,
    approvedStories: filteredStories.filter((story) => story.status === "approved").length,
    totalStoryItems: filteredStories.reduce((sum, story) => sum + story.itemCount, 0),
    flaggedStories: filteredStories.filter((story) => story.riskFlags.length > 0).length,
  };
}

function getSourceLabel(item: NormalizedItemRecord): string {
  return `${item.sourceSlug} 路 ${item.sourcePriority}`;
}

function getRiskFlagLabel(flag: string): string {
  return RISK_FLAG_LABELS[flag] ?? flag.split("_").join(" ");
}

function getRiskPresentation(story: StoryRecord): StoryRiskPresentation {
  if (story.riskFlags.length === 0) {
    return {
      tone: "calm",
      label: "低风险",
      detail: "当前聚类已包含 P0 来源，可直接进入后续人工审核与生成链路。",
    };
  }

  if (story.riskFlags.includes("secondary_sources_only")) {
    return {
      tone: "watch",
      label: "需复核",
      detail: RISK_FLAG_DETAILS.secondary_sources_only,
    };
  }

  return {
    tone: "alert",
    label: "高关注",
    detail: "检测到未归类的风险标记，建议人工确认来源和聚类质量。",
  };
}

function getTopTags(stories: StoryRecord[]): string[] {
  const tagCounts = new Map<string, number>();

  for (const story of stories) {
    for (const tag of story.tags) {
      tagCounts.set(tag, (tagCounts.get(tag) ?? 0) + 1);
    }
  }

  return [...tagCounts.entries()]
    .sort((left, right) => right[1] - left[1] || left[0].localeCompare(right[0]))
    .slice(0, 8)
    .map(([tag]) => tag);
}

function matchesStorySearch(story: StoryRecord, searchValue: string): boolean {
  if (searchValue === "") {
    return true;
  }

  const haystack = [
    story.clusterTitle,
    story.summary,
    story.storyKey,
    ...story.tags,
    ...story.highlights,
    ...story.riskFlags,
  ]
    .join(" ")
    .toLowerCase();

  return haystack.includes(searchValue.toLowerCase());
}

function matchesNormalizedSearch(item: NormalizedItemRecord, searchValue: string): boolean {
  if (searchValue === "") {
    return true;
  }

  const haystack = [item.title, item.normalizedTitle, item.summary, ...item.keywords, ...item.tags]
    .join(" ")
    .toLowerCase();

  return haystack.includes(searchValue.toLowerCase());
}

/**
 * Shows clustered stories and the underlying normalized items for Phase 03 verification.
 */
export function StoriesPage({ health }: StoriesPageProps): React.JSX.Element {
  const queryClient = useQueryClient();
  const [searchValue, setSearchValue] = React.useState("");
  const [statusFilter, setStatusFilter] = React.useState<StoryStatusFilter>("all");
  const [riskFilter, setRiskFilter] = React.useState<StoryRiskFilter>("all");
  const [tagFilter, setTagFilter] = React.useState<string>("all");

  const storiesQuery = useQuery({
    queryKey: STORIES_QUERY_KEY,
    queryFn: fetchStories,
    refetchInterval: STORY_REFRESH_INTERVAL_MS,
  });
  const normalizedItemsQuery = useQuery({
    queryKey: NORMALIZED_ITEMS_QUERY_KEY,
    queryFn: () => fetchNormalizedItems(NORMALIZED_ITEM_LIMIT),
    refetchInterval: STORY_REFRESH_INTERVAL_MS,
  });
  const rebuildMutation = useMutation({
    mutationFn: rebuildStoriesPipeline,
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: STORIES_QUERY_KEY });
      void queryClient.invalidateQueries({ queryKey: NORMALIZED_ITEMS_QUERY_KEY });
    },
  });
  const approveMutation = useMutation({
    mutationFn: (storyId: number) => approveStory(storyId),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: STORIES_QUERY_KEY });
    },
  });

  const stories = storiesQuery.data ?? [];
  const normalizedItems = normalizedItemsQuery.data ?? [];
  const topTags = getTopTags(stories);
  const filteredStories = [...stories]
    .filter((story) => (statusFilter === "all" ? true : story.status === statusFilter))
    .filter((story) => {
      if (riskFilter === "all") {
        return true;
      }
      if (riskFilter === "watch") {
        return story.riskFlags.length > 0;
      }
      return story.riskFlags.length === 0;
    })
    .filter((story) => (tagFilter === "all" ? true : story.tags.includes(tagFilter)))
    .filter((story) => matchesStorySearch(story, searchValue))
    .sort((left, right) => {
      if (left.score !== right.score) {
        return right.score - left.score;
      }
      return new Date(right.lastSeenAt).getTime() - new Date(left.lastSeenAt).getTime();
    });
  const filteredNormalizedItems = normalizedItems
    .filter((item) => (tagFilter === "all" ? true : item.tags.includes(tagFilter) || item.keywords.includes(tagFilter)))
    .filter((item) => matchesNormalizedSearch(item, searchValue));
  const metrics = summarizeStories(stories, filteredStories);
  const cleanStories = filteredStories.length - metrics.flaggedStories;

  return (
    <div className="page-stack">
      <section className="hero-panel">
        <div>
          <p className="eyebrow">Story Clustering</p>
          <h1>标准化与聚类检查</h1>
          <p className="lede">
            在这一页同时检查 stories、风险标记和 normalized items，确认 URL 清洗、标题标准化与多源聚合是否符合预期。
          </p>
        </div>

        <div className="hero-meta">
          <div className="signal-pill">
            <span className="signal-dot-live" />
            <strong>{health}</strong>
          </div>
          <div className="meta-chip">
            <span>Pipeline 状态</span>
            <strong>{rebuildMutation.isPending ? "手动重建中" : "采集完成后自动刷新"}</strong>
          </div>
        </div>
      </section>

      <section className="stats-grid" aria-label="标准化与聚类摘要">
        <article className="metric-cell">
          <p>Stories</p>
          <strong>{metrics.filteredStories}</strong>
          <span>当前筛选结果，共 {metrics.totalStories} 条 story</span>
        </article>
        <article className="metric-cell">
          <p>已审核</p>
          <strong>{metrics.approvedStories}</strong>
          <span>当前筛选条件下已人工确认的 story</span>
        </article>
        <article className="metric-cell">
          <p>聚合条目</p>
          <strong>{metrics.totalStoryItems}</strong>
          <span>筛选后的 story 共包含 {metrics.totalStoryItems} 条来源</span>
        </article>
        <article className="metric-cell">
          <p>需复核</p>
          <strong>{metrics.flaggedStories}</strong>
          <span>存在风险标记的 story，需要优先检查</span>
        </article>
      </section>

      <section className="panel story-panel">
        <header className="section-title ingestion-head">
          <div>
            <p>Pipeline Controls</p>
            <h2>筛选、重建与风险总览</h2>
          </div>
          <span>{storiesQuery.isFetching || normalizedItemsQuery.isFetching ? "正在刷新" : "30 秒自动刷新"}</span>
        </header>

        <div className="story-filter-grid">
          <label className="field-shell">
            <span>关键词检索</span>
            <input
              type="search"
              value={searchValue}
              onChange={(event) => setSearchValue(event.target.value)}
              placeholder="按标题、摘要、标签、亮点或风险标记筛选"
            />
          </label>

          <div className="story-control-stack">
            <div className="filter-group">
              <p className="filter-caption">审核状态</p>
              <div className="filter-chip-row">
                {STORY_STATUS_OPTIONS.map((option) => (
                  <button
                    key={option.value}
                    type="button"
                    className={`filter-chip ${statusFilter === option.value ? "active" : ""}`}
                    onClick={() => setStatusFilter(option.value)}
                  >
                    {option.label}
                  </button>
                ))}
              </div>
            </div>

            <div className="filter-group">
              <p className="filter-caption">风险状态</p>
              <div className="filter-chip-row">
                {STORY_RISK_OPTIONS.map((option) => (
                  <button
                    key={option.value}
                    type="button"
                    className={`filter-chip ${riskFilter === option.value ? "active" : ""}`}
                    onClick={() => setRiskFilter(option.value)}
                  >
                    {option.label}
                  </button>
                ))}
              </div>
            </div>
          </div>
        </div>

        <div className="tag-filter-row">
          <button
            type="button"
            className={`filter-chip ${tagFilter === "all" ? "active" : ""}`}
            onClick={() => setTagFilter("all")}
          >
            全部主题
          </button>
          {topTags.map((tag) => (
            <button
              key={tag}
              type="button"
              className={`filter-chip ${tagFilter === tag ? "active" : ""}`}
              onClick={() => setTagFilter(tag)}
            >
              #{tag}
            </button>
          ))}
        </div>

        <div className="risk-overview-grid">
          <article className="risk-stat" data-tone="watch">
            <p>需复核 story</p>
            <strong>{metrics.flaggedStories}</strong>
            <span>当前筛选结果中有风险标记，需要先看来源质量。</span>
          </article>
          <article className="risk-stat" data-tone="calm">
            <p>低风险 story</p>
            <strong>{cleanStories}</strong>
            <span>已覆盖 P0 来源，可直接进入人工审核与排序。</span>
          </article>
          <article className="risk-stat" data-tone="default">
            <p>当前主题</p>
            <strong>{tagFilter === "all" ? "全部主题" : `#${tagFilter}`}</strong>
            <span>{searchValue === "" ? "未启用关键词检索" : `检索词：${searchValue}`}</span>
          </article>
        </div>

        <div className="action-row">
          <button
            type="button"
            className="button-primary"
            onClick={() => rebuildMutation.mutate()}
            disabled={rebuildMutation.isPending}
          >
            {rebuildMutation.isPending ? "重建中..." : "重建 Stories Pipeline"}
          </button>
          <button
            type="button"
            className="button-secondary"
            onClick={() => {
              setSearchValue("");
              setStatusFilter("all");
              setRiskFilter("all");
              setTagFilter("all");
            }}
          >
            清空筛选
          </button>
        </div>

        <div className="action-status">
          {rebuildMutation.isSuccess ? (
            <strong>
              已重建 {rebuildMutation.data.normalizedItems} 条 normalized items，生成 {rebuildMutation.data.stories} 条 stories
            </strong>
          ) : null}
          {rebuildMutation.isError ? <strong>重建失败，请检查后端日志。</strong> : null}
          {approveMutation.isSuccess ? <strong>story 已标记为已审核。</strong> : null}
          {approveMutation.isError ? <strong>story 审核失败，请稍后重试。</strong> : null}
        </div>
      </section>

      <section className="story-layout">
        <article className="panel story-list-panel">
          <header className="section-title">
            <div>
              <p>Clustered Stories</p>
              <h2>聚类结果</h2>
            </div>
            <span>
              {filteredStories.length} / {stories.length} 条
            </span>
          </header>

          {storiesQuery.isLoading ? <div className="empty-state">正在加载 stories...</div> : null}
          {storiesQuery.isError ? <div className="empty-state">stories 加载失败，请确认 `/stories` 接口可用。</div> : null}
          {!storiesQuery.isLoading && !storiesQuery.isError && stories.length === 0 ? (
            <div className="empty-state">当前还没有 story。先执行一次采集，或手动重建 pipeline。</div>
          ) : null}
          {!storiesQuery.isLoading && !storiesQuery.isError && stories.length > 0 && filteredStories.length === 0 ? (
            <div className="empty-state">当前筛选条件下没有 story，调整筛选后再试。</div>
          ) : null}

          {!storiesQuery.isLoading && !storiesQuery.isError && filteredStories.length > 0 ? (
            <div className="story-list">
              {filteredStories.map((story) => {
                const risk = getRiskPresentation(story);
                return (
                  <article key={story.storyKey} className="story-card" data-tone={risk.tone}>
                    <div className="story-card-header">
                      <div>
                        <div className="story-topline">
                          <p className="story-kicker">{story.storyKey}</p>
                          <span className={`status-pill status-${story.status}`}>{formatStoryStatus(story.status)}</span>
                        </div>
                        <h3>{story.clusterTitle}</h3>
                      </div>
                      <div className="story-score-pill">
                        <span>Score</span>
                        <strong>{story.score.toFixed(1)}</strong>
                      </div>
                    </div>

                    <div className="story-risk-rail" data-tone={risk.tone}>
                      <div className="story-risk-copy">
                        <p>Risk Signal</p>
                        <strong>{risk.label}</strong>
                        <span>{risk.detail}</span>
                      </div>
                      <div className="pill-list story-flag-list">
                        {story.riskFlags.length > 0 ? (
                          story.riskFlags.map((flag) => (
                            <span key={`${story.storyKey}-${flag}`} className="risk-chip">
                              {getRiskFlagLabel(flag)}
                            </span>
                          ))
                        ) : (
                          <span className="source-chip">P0 已覆盖</span>
                        )}
                      </div>
                    </div>

                    <p className="story-summary">{story.summary}</p>

                    <div className="story-meta-row">
                      <span>{story.itemCount} 条来源</span>
                      <span>
                        {formatDateTime(story.firstSeenAt)} - {formatDateTime(story.lastSeenAt)}
                      </span>
                      <span>{story.tags.slice(0, 3).join(" / ") || "未打标签"}</span>
                    </div>

                    <div className="pill-list">
                      {story.tags.map((tag) => (
                        <span key={`${story.storyKey}-${tag}`} className="source-chip">
                          {tag}
                        </span>
                      ))}
                    </div>

                    <div className="story-highlights">
                      {story.highlights.map((highlight) => (
                        <p key={`${story.storyKey}-${highlight}`} className="story-highlight">
                          {highlight}
                        </p>
                      ))}
                    </div>

                    <div className="story-links">
                      {story.sourceLinks.map((link) => (
                        <a key={link} href={link} target="_blank" rel="noreferrer" className="link-chip">
                          {link}
                        </a>
                      ))}
                    </div>

                    <div className="story-actions">
                      <span>{story.status === "approved" ? "该 story 已完成人工确认。" : "确认后可进入后续日报生成链路。"}</span>
                      <button
                        type="button"
                        className="button-secondary"
                        onClick={() => approveMutation.mutate(story.id)}
                        disabled={story.status === "approved" || approveMutation.isPending}
                      >
                        {story.status === "approved" ? "已审核" : "标记为已审核"}
                      </button>
                    </div>
                  </article>
                );
              })}
            </div>
          ) : null}
        </article>

        <article className="panel normalized-panel">
          <header className="section-title">
            <div>
              <p>Normalized Items</p>
              <h2>标准化结果</h2>
            </div>
            <span>{filteredNormalizedItems.length} 条</span>
          </header>

          {normalizedItemsQuery.isLoading ? <div className="empty-state">正在加载 normalized items...</div> : null}
          {normalizedItemsQuery.isError ? <div className="empty-state">normalized items 加载失败，请确认 `/normalized-items` 接口可用。</div> : null}
          {!normalizedItemsQuery.isLoading && !normalizedItemsQuery.isError && filteredNormalizedItems.length === 0 ? (
            <div className="empty-state">当前筛选条件下没有 normalized items。</div>
          ) : null}

          {!normalizedItemsQuery.isLoading && !normalizedItemsQuery.isError && filteredNormalizedItems.length > 0 ? (
            <div className="normalized-list">
              {filteredNormalizedItems.map((item) => (
                <article key={`${item.rawItemId}-${item.externalId}`} className="normalized-row">
                  <div className="normalized-head">
                    <strong>{item.title}</strong>
                    <span>{getSourceLabel(item)}</span>
                  </div>
                  <p>{item.normalizedTitle}</p>
                  <a href={item.canonicalUrl} target="_blank" rel="noreferrer" className="normalized-link">
                    {item.canonicalUrl}
                  </a>
                  <div className="pill-list">
                    <span className="source-chip">{item.language}</span>
                    {item.keywords.slice(0, 3).map((keyword) => (
                      <span key={`${item.externalId}-${keyword}`} className="source-chip">
                        {keyword}
                      </span>
                    ))}
                  </div>
                </article>
              ))}
            </div>
          ) : null}
        </article>
      </section>
    </div>
  );
}
