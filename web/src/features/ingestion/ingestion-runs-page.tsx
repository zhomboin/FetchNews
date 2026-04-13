import React from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { IngestRunRecord, SourceSpec, fetchIngestRuns, fetchSourceSpecs, triggerIngestRun } from "../../lib/api";

const SOURCE_SPECS_QUERY_KEY = ["sourceSpecs"] as const;
const INGEST_RUNS_QUERY_KEY = ["ingestRuns"] as const;
const RUN_POLLING_INTERVAL_MS = 30_000;
const RUNNING_LABEL = "运行中";

type IngestionRunsPageProps = {
  health: string;
};

type IngestionMetrics = {
  totalRuns: number;
  failedRuns: number;
  totalItems: number;
  totalSources: number;
};

function formatDateTime(value: string | null): string {
  if (!value) {
    return RUNNING_LABEL;
  }

  return new Intl.DateTimeFormat("zh-CN", {
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(value));
}

function summarizeRuns(runs: IngestRunRecord[]): IngestionMetrics {
  return {
    totalRuns: runs.length,
    failedRuns: runs.filter((run) => run.sourcesFailed > 0).length,
    totalItems: runs.reduce((sum, run) => sum + run.itemsIngested, 0),
    totalSources: runs.reduce((sum, run) => sum + run.sourcesTotal, 0),
  };
}

function getDefaultP0Selection(sources: SourceSpec[]): string[] {
  return sources.filter((source) => source.priority === "P0").map((source) => source.slug);
}

function asNumber(value: unknown): number | null {
  if (typeof value === "number") {
    return value;
  }
  if (typeof value === "string") {
    const parsed = Number(value);
    return Number.isFinite(parsed) ? parsed : null;
  }
  return null;
}

const POSITIVE_GOVERNANCE_FLAGS = new Set(["high_engagement", "steady_engagement"]);

function readSignal(source: SourceSpec, key: string): number {
  const value = source.feedbackSignals[key];
  return typeof value === "number" ? value : 0;
}

function isPositiveGovernanceFlag(flag: string): boolean {
  return POSITIVE_GOVERNANCE_FLAGS.has(flag);
}

function getGovernanceTone(source: SourceSpec): "watch" | "calm" {
  if (source.governanceFlags.some((flag) => !isPositiveGovernanceFlag(flag))) {
    return "watch";
  }
  if ((source.effectiveScoreMultiplier ?? 1) < 0.9) {
    return "watch";
  }
  return "calm";
}

function formatGovernanceSummary(source: SourceSpec): string {
  const baseTrustScore = asNumber(source.config.trust_score) ?? source.effectiveTrustScore;
  const baseScoreMultiplier = asNumber(source.config.score_multiplier) ?? source.effectiveScoreMultiplier;
  const parts: string[] = [];

  if (baseTrustScore !== null && source.effectiveTrustScore !== null) {
    parts.push(`信任分 ${baseTrustScore.toFixed(1)} -> ${source.effectiveTrustScore.toFixed(1)}`);
  }
  if (baseScoreMultiplier !== null && source.effectiveScoreMultiplier !== null) {
    parts.push(`排序倍率 ${baseScoreMultiplier.toFixed(2)}x -> ${source.effectiveScoreMultiplier.toFixed(2)}x`);
  }

  const failedRuns = readSignal(source, "failed_ingest_runs");
  const pendingStories = readSignal(source, "pending_stories");
  const flaggedStories = readSignal(source, "flagged_stories");
  if (failedRuns > 0 || pendingStories > 0 || flaggedStories > 0) {
    parts.push(`失败 ${failedRuns} / 待审核 ${pendingStories} / 需复核 ${flaggedStories}`);
  }

  const engagementImpressions = readSignal(source, "engagement_impressions");
  const engagementClicks = readSignal(source, "engagement_clicks");
  const clickThroughRate = readSignal(source, "click_through_rate");
  if (engagementImpressions > 0) {
    parts.push(`Engagement ${engagementClicks}/${engagementImpressions} clicks (${Math.round(clickThroughRate * 100)}% CTR)`);
  }

  if (source.incrementalCursor) {
    parts.push(`Cursor ${source.incrementalCursor}`);
  }
  if (source.lastSuccessAt) {
    parts.push(`Last success ${formatDateTime(source.lastSuccessAt)}`);
  }

  return parts.join(" · ");
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

/**
 * Shows recent ingestion runs, source governance, and manual trigger controls.
 */
export function IngestionRunsPage({ health }: IngestionRunsPageProps): React.JSX.Element {
  const queryClient = useQueryClient();
  const sourcesQuery = useQuery({
    queryKey: SOURCE_SPECS_QUERY_KEY,
    queryFn: fetchSourceSpecs,
  });
  const runsQuery = useQuery({
    queryKey: INGEST_RUNS_QUERY_KEY,
    queryFn: fetchIngestRuns,
    refetchInterval: RUN_POLLING_INTERVAL_MS,
  });
  const [selectedSlugs, setSelectedSlugs] = React.useState<string[]>([]);

  React.useEffect(() => {
    if (sourcesQuery.data && selectedSlugs.length === 0) {
      setSelectedSlugs(getDefaultP0Selection(sourcesQuery.data));
    }
  }, [selectedSlugs.length, sourcesQuery.data]);

  const triggerMutation = useMutation({
    mutationFn: (sourceSlugs: string[]) => triggerIngestRun({ sourceSlugs }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: INGEST_RUNS_QUERY_KEY });
      void queryClient.invalidateQueries({ queryKey: SOURCE_SPECS_QUERY_KEY });
    },
  });

  const runs = runsQuery.data ?? [];
  const metrics = summarizeRuns(runs);
  const sourceSpecs = sourcesQuery.data ?? [];

  function toggleSource(slug: string): void {
    setSelectedSlugs((current) =>
      current.includes(slug) ? current.filter((item) => item !== slug) : [...current, slug],
    );
  }

  function selectAllSources(): void {
    setSelectedSlugs(sourceSpecs.map((source) => source.slug));
  }

  function selectP0Sources(): void {
    setSelectedSlugs(getDefaultP0Selection(sourceSpecs));
  }

  return (
    <div className="page-stack">
      <section className="hero-panel">
        <div>
          <p className="eyebrow">采集台账</p>
          <h1>采集运行台</h1>
          <p className="lede">
            在一个控制台视图里查看来源运行批次、治理调节、覆盖范围和手动触发入口，确保采集链路稳定可控。
          </p>
        </div>

        <div className="hero-meta">
          <div className="signal-pill">
            <span className="signal-dot-live" />
            <strong>{health}</strong>
          </div>
          <div className="meta-chip">
            <span>调度模式</span>
            <strong>默认来源按节奏运行</strong>
          </div>
        </div>
      </section>

      <section className="stats-grid" aria-label="采集摘要">
        <article className="metric-cell">
          <p>运行批次</p>
          <strong>{metrics.totalRuns}</strong>
          <span>接口当前返回的最近采集批次</span>
        </article>
        <article className="metric-cell">
          <p>失败批次</p>
          <strong>{metrics.failedRuns}</strong>
          <span>至少包含一个失败来源的批次</span>
        </article>
        <article className="metric-cell">
          <p>采集条目</p>
          <strong>{metrics.totalItems}</strong>
          <span>当前可见批次累计写入的原始条目数</span>
        </article>
        <article className="metric-cell">
          <p>处理来源</p>
          <strong>{metrics.totalSources}</strong>
          <span>同一时间窗内累计处理的来源次数</span>
        </article>
      </section>

      <section className="panel trigger-panel">
        <header className="section-title ingestion-head">
          <div>
            <p>手动触发</p>
            <h2>启动一次手动采集</h2>
          </div>
          <span>默认勾选 P0 来源</span>
        </header>

        {sourcesQuery.isLoading ? <div className="empty-state">正在加载来源目录...</div> : null}
        {sourcesQuery.isError ? <div className="empty-state">来源目录加载失败，请检查 `/sources` 接口。</div> : null}

        {!sourcesQuery.isLoading && !sourcesQuery.isError ? (
          <div className="trigger-layout">
            <div className="source-selector">
              {sourceSpecs.map((source) => {
                const selected = selectedSlugs.includes(source.slug);
                return (
                  <button
                    key={source.slug}
                    type="button"
                    className={`selector-chip ${selected ? "selected" : ""}`}
                    onClick={() => toggleSource(source.slug)}
                  >
                    <span>{source.label}</span>
                    <strong>{source.priority}</strong>
                  </button>
                );
              })}
            </div>

            <div className="action-row">
              <button type="button" className="button-secondary" onClick={selectP0Sources} disabled={sourcesQuery.isLoading}>
                选择 P0
              </button>
              <button type="button" className="button-secondary" onClick={selectAllSources} disabled={sourcesQuery.isLoading}>
                选择全部启用来源
              </button>
              <button
                type="button"
                className="button-primary"
                onClick={() => triggerMutation.mutate(selectedSlugs)}
                disabled={selectedSlugs.length === 0 || triggerMutation.isPending}
              >
                {triggerMutation.isPending ? "执行中..." : "立即执行采集"}
              </button>
            </div>

            <div className="action-status">
              <span>已选择 {selectedSlugs.length} 个来源</span>
              {triggerMutation.isSuccess ? <strong>已创建采集批次 #{triggerMutation.data.id}</strong> : null}
              {triggerMutation.isError ? <strong>手动触发失败，请检查日志后重试。</strong> : null}
            </div>
          </div>
        ) : null}
      </section>

      <section className="panel source-governance-panel">
        <header className="section-title ingestion-head">
          <div>
            <p>来源治理</p>
            <h2>反馈调节后的来源状态</h2>
          </div>
          <span>{sourceSpecs.length} 个来源</span>
        </header>

        {!sourcesQuery.isLoading && !sourcesQuery.isError ? (
          <div className="source-governance-grid">
            {sourceSpecs.map((source) => (
              <article key={`governance-${source.slug}`} className="source-governance-card" data-tone={getGovernanceTone(source)}>
                <div className="source-governance-head">
                  <div>
                    <p>{source.platform}</p>
                    <strong>{source.label}</strong>
                  </div>
                  <span className="source-chip">{source.priority}</span>
                </div>
                <span className="source-governance-note">
                  {formatGovernanceSummary(source) || "当前还没有额外的治理调整。"}
                </span>
                {source.governanceFlags.length > 0 ? (
                  <div className="failure-chip-list">
                    {source.governanceFlags.map((flag) => (
                      <span
                        key={`${source.slug}-${flag}`}
                        className={isPositiveGovernanceFlag(flag) ? "source-chip source-chip-soft" : "failure-target-chip"}
                      >
                        {flag}
                      </span>
                    ))}
                  </div>
                ) : null}
              </article>
            ))}
          </div>
        ) : null}
      </section>

      <section className="panel ingestion-panel">
        <header className="section-title ingestion-head">
          <div>
            <p>运行历史</p>
            <h2>最近采集批次</h2>
          </div>
          <span>{runsQuery.isFetching ? "刷新中" : "每 30 秒自动刷新"}</span>
        </header>

        {runsQuery.isLoading ? <div className="empty-state">正在加载采集历史...</div> : null}
        {runsQuery.isError ? <div className="empty-state">采集历史加载失败，请检查后端接口。</div> : null}
        {!runsQuery.isLoading && !runsQuery.isError && runs.length === 0 ? (
          <div className="empty-state">当前还没有采集批次记录。</div>
        ) : null}

        {!runsQuery.isLoading && !runsQuery.isError && runs.length > 0 ? (
          <div className="ingest-run-list">
            {runs.map((run) => (
              <article key={run.id} className="ingest-run-row">
                <div className="run-main">
                  <div className="run-head">
                    <h3>采集批次 #{run.id}</h3>
                    <span className={`status-pill status-${run.status}`}>{formatRunStatus(run.status)}</span>
                  </div>

                  <div className="source-chip-list">
                    {run.sourceSlugs.map((slug) => (
                      <span key={slug} className="source-chip">
                        {slug}
                      </span>
                    ))}
                  </div>

                  {run.errors.length > 0 ? (
                    <div className="run-errors">
                      {run.errors.map((error) => (
                        <p key={`${run.id}-${error.sourceSlug}`}>
                          {error.sourceSlug}: {error.message}
                        </p>
                      ))}
                    </div>
                  ) : (
                        <p className="run-note">该批次没有记录到来源错误。</p>
                      )}
                    </div>

                    <div className="run-metrics">
                      <div>
                        <span>来源</span>
                        <strong>
                          {run.sourcesSucceeded}/{run.sourcesTotal}
                        </strong>
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
            ))}
          </div>
        ) : null}
      </section>
    </div>
  );
}
