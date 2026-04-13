import React from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { EmptyState, StatusPill } from "../../components/console";
import {
  NormalizedItemRecord,
  StoryRecord,
  approveStory,
  fetchNormalizedItems,
  fetchStories,
  formatSectionLabel,
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
  demoted_source_signal: "来源已降权",
};
const RISK_FLAG_DETAILS: Record<string, string> = {
  secondary_sources_only: "当前聚类还没有覆盖 P0 一手来源，进入生成链路前建议人工复核。",
  demoted_source_signal: "当前 story 引用了被降权的来源信号，建议优先检查转载和讨论贴。",
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
  return status === "approved" ? "已审核" : "待审核";
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
  return `${item.sourceSlug} / ${item.sourcePriority}`;
}

function getRiskFlagLabel(flag: string): string {
  return RISK_FLAG_LABELS[flag] ?? flag.split("_").join(" ");
}

function getRiskPresentation(story: StoryRecord): StoryRiskPresentation {
  if (story.riskFlags.length === 0) {
    return {
      tone: "calm",
      label: "低风险",
      detail: "当前聚类已覆盖较强来源，可直接进入人工审核和后续排版。",
    };
  }

  if (story.riskFlags.includes("secondary_sources_only") || story.riskFlags.includes("demoted_source_signal")) {
    return {
      tone: "watch",
      label: "需复核",
      detail: story.riskFlags.map((flag) => RISK_FLAG_DETAILS[flag]).filter(Boolean).join(" "),
    };
  }

  return {
    tone: "alert",
    label: "高关注",
    detail: "检测到未归类的风险标记，建议先检查来源和聚类质量。",
  };
}

function getTopSections(stories: StoryRecord[]): string[] {
  const sectionCounts = new Map<string, number>();

  for (const story of stories) {
    for (const section of story.sections) {
      sectionCounts.set(section, (sectionCounts.get(section) ?? 0) + 1);
    }
  }

  return [...sectionCounts.entries()]
    .sort((left, right) => right[1] - left[1] || left[0].localeCompare(right[0]))
    .slice(0, 8)
    .map(([section]) => section);
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
    ...story.sections,
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
 * Shows clustered stories and the underlying normalized items for Phase 03 and thematic section verification.
 */
export function StoriesPage({ health }: StoriesPageProps): React.JSX.Element {
  const queryClient = useQueryClient();
  const [searchValue, setSearchValue] = React.useState("");
  const [statusFilter, setStatusFilter] = React.useState<StoryStatusFilter>("all");
  const [riskFilter, setRiskFilter] = React.useState<StoryRiskFilter>("all");
  const [sectionFilter, setSectionFilter] = React.useState<string>("all");

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
  const topSections = getTopSections(stories);
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
    .filter((story) => (sectionFilter === "all" ? true : story.sections.includes(sectionFilter)))
    .filter((story) => matchesStorySearch(story, searchValue))
    .sort((left, right) => {
      if (left.score !== right.score) {
        return right.score - left.score;
      }
      return new Date(right.lastSeenAt).getTime() - new Date(left.lastSeenAt).getTime();
    });
  const filteredNormalizedItems = normalizedItems
    .filter((item) =>
      sectionFilter === "all"
        ? true
        : item.tags.includes(sectionFilter) || item.keywords.includes(sectionFilter),
    )
    .filter((item) => matchesNormalizedSearch(item, searchValue));
  const metrics = summarizeStories(stories, filteredStories);
  const cleanStories = filteredStories.length - metrics.flaggedStories;

  return (
    <div className="page-stack">
      <section className="hero-panel">
        <div>
          <p className="eyebrow">审核聚类台</p>
          <h1>标准化与栏目检查</h1>
          <p className="lede">
            在这一页同时检查聚类结果、主题栏目、风险标记和标准化条目，确认内容是否适合进入日报、周报与月报生成链路。
          </p>
        </div>

        <div className="hero-meta">
          <div className="signal-pill">
            <span className="signal-dot-live" />
            <strong>{health}</strong>
          </div>
          <div className="meta-chip">
            <span>流水线状态</span>
            <strong>{rebuildMutation.isPending ? "手动重建中" : "采集完成后自动刷新"}</strong>
          </div>
        </div>
      </section>

      <section className="stats-grid" aria-label="标准化与聚类摘要">
        <article className="metric-cell">
          <p>聚类故事</p>
          <strong>{metrics.filteredStories}</strong>
          <span>当前筛选结果，共 {metrics.totalStories} 条故事</span>
        </article>
        <article className="metric-cell">
          <p>已审核</p>
          <strong>{metrics.approvedStories}</strong>
          <span>当前筛选条件下已人工确认的 story</span>
        </article>
        <article className="metric-cell">
          <p>聚合条目</p>
          <strong>{metrics.totalStoryItems}</strong>
          <span>当前 story 覆盖的原始来源总数</span>
        </article>
        <article className="metric-cell">
          <p>需复核</p>
          <strong>{metrics.flaggedStories}</strong>
          <span>存在风险标记的 story，建议优先复核</span>
        </article>
      </section>

      <section className="panel story-panel">
        <header className="section-title ingestion-head">
          <div>
            <p>流程控制</p>
            <h2>筛选、重建与栏目总览</h2>
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
              placeholder="按标题、摘要、栏目、标签、亮点或风险标记筛选"
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
            className={`filter-chip ${sectionFilter === "all" ? "active" : ""}`}
            onClick={() => setSectionFilter("all")}
          >
            全部栏目
          </button>
          {topSections.map((section) => (
            <button
              key={section}
              type="button"
              className={`filter-chip ${sectionFilter === section ? "active" : ""}`}
              onClick={() => setSectionFilter(section)}
            >
              {formatSectionLabel(section)}
            </button>
          ))}
        </div>

        <div className="risk-overview-grid">
          <article className="risk-stat" data-tone="watch">
            <p>需复核故事</p>
            <strong>{metrics.flaggedStories}</strong>
            <span>当前筛选结果里存在风险标记，建议先看来源质量。</span>
          </article>
          <article className="risk-stat" data-tone="calm">
            <p>低风险故事</p>
            <strong>{cleanStories}</strong>
            <span>已覆盖较强来源，可直接进入人工审核和排版。</span>
          </article>
          <article className="risk-stat" data-tone="default">
            <p>当前栏目</p>
            <strong>{sectionFilter === "all" ? "全部栏目" : formatSectionLabel(sectionFilter)}</strong>
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
            {rebuildMutation.isPending ? "重建中..." : "重建聚类流水线"}
          </button>
          <button
            type="button"
            className="button-secondary"
            onClick={() => {
              setSearchValue("");
              setStatusFilter("all");
              setRiskFilter("all");
              setSectionFilter("all");
            }}
          >
            清空筛选
          </button>
        </div>

        <div className="action-status">
          {rebuildMutation.isSuccess ? (
            <strong>
              已重建 {rebuildMutation.data.normalizedItems} 条标准化条目，生成 {rebuildMutation.data.stories} 条聚类故事
            </strong>
          ) : null}
          {rebuildMutation.isError ? <strong>重建失败，请检查后端日志。</strong> : null}
          {approveMutation.isSuccess ? <strong>故事已标记为已审核。</strong> : null}
          {approveMutation.isError ? <strong>故事审核失败，请稍后重试。</strong> : null}
        </div>
      </section>

      <section className="story-layout">
        <article className="panel story-list-panel">
          <header className="section-title">
            <div>
              <p>聚类结果</p>
              <h2>聚类结果</h2>
            </div>
            <span>
              {filteredStories.length} / {stories.length} 条
            </span>
          </header>

          {storiesQuery.isLoading ? <EmptyState>正在加载聚类结果...</EmptyState> : null}
          {storiesQuery.isError ? <EmptyState>聚类结果加载失败，请确认 `/stories` 接口可用。</EmptyState> : null}
          {!storiesQuery.isLoading && !storiesQuery.isError && stories.length === 0 ? (
            <EmptyState>当前还没有聚类故事。先执行一次采集，或手动重建流水线。</EmptyState>
          ) : null}
          {!storiesQuery.isLoading && !storiesQuery.isError && stories.length > 0 && filteredStories.length === 0 ? (
            <EmptyState>当前筛选条件下没有聚类故事，调整筛选后再试。</EmptyState>
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
                          <StatusPill status={story.status}>{formatStoryStatus(story.status)}</StatusPill>
                          <span className="section-badge">{formatSectionLabel(story.primarySection)}</span>
                        </div>
                        <h3>{story.clusterTitle}</h3>
                      </div>
                      <div className="story-score-pill">
                        <span>评分</span>
                        <strong>{story.score.toFixed(1)}</strong>
                      </div>
                    </div>

                    <div className="story-risk-rail" data-tone={risk.tone}>
                      <div className="story-risk-copy">
                        <p>风险信号</p>
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
                          <span className="source-chip">低风险</span>
                        )}
                      </div>
                    </div>

                    <p className="story-summary">{story.summary}</p>

                    <div className="story-meta-row">
                      <span>{story.itemCount} 条来源</span>
                      <span>
                        {formatDateTime(story.firstSeenAt)} - {formatDateTime(story.lastSeenAt)}
                      </span>
                      <span>{story.sections.map(formatSectionLabel).join(" / ")}</span>
                    </div>

                    <div className="pill-list section-pill-list">
                      {story.sections.map((section) => (
                        <span key={`${story.storyKey}-${section}`} className="section-badge section-badge-soft">
                          {formatSectionLabel(section)}
                        </span>
                      ))}
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
                      <span>
                        {story.status === "approved" ? "该故事已完成人工确认。" : "确认后可进入后续日报、周报与月报生成链路。"}
                      </span>
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
              <p>标准化条目</p>
              <h2>标准化结果</h2>
            </div>
            <span>{filteredNormalizedItems.length} 条</span>
          </header>

          {normalizedItemsQuery.isLoading ? <EmptyState>正在加载标准化条目...</EmptyState> : null}
          {normalizedItemsQuery.isError ? <EmptyState>标准化条目加载失败，请确认 `/normalized-items` 接口可用。</EmptyState> : null}
          {!normalizedItemsQuery.isLoading && !normalizedItemsQuery.isError && filteredNormalizedItems.length === 0 ? (
            <EmptyState>当前筛选条件下没有标准化条目。</EmptyState>
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
