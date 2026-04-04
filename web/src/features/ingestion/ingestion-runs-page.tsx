import React from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { IngestRunRecord, SourceSpec, fetchIngestRuns, fetchSourceSpecs, triggerIngestRun } from "../../lib/api";

const SOURCE_SPECS_QUERY_KEY = ["sourceSpecs"] as const;
const INGEST_RUNS_QUERY_KEY = ["ingestRuns"] as const;
const RUN_POLLING_INTERVAL_MS = 30_000;
const RUNNING_LABEL = "Running";

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
    parts.push(`Trust ${baseTrustScore.toFixed(1)} -> ${source.effectiveTrustScore.toFixed(1)}`);
  }
  if (baseScoreMultiplier !== null && source.effectiveScoreMultiplier !== null) {
    parts.push(`Rank ${baseScoreMultiplier.toFixed(2)}x -> ${source.effectiveScoreMultiplier.toFixed(2)}x`);
  }

  const failedRuns = readSignal(source, "failed_ingest_runs");
  const pendingStories = readSignal(source, "pending_stories");
  const flaggedStories = readSignal(source, "flagged_stories");
  if (failedRuns > 0 || pendingStories > 0 || flaggedStories > 0) {
    parts.push(`Failures ${failedRuns} / Pending ${pendingStories} / Flagged ${flaggedStories}`);
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
          <p className="eyebrow">Ingestion Ledger</p>
          <h1>Ingestion operations</h1>
          <p className="lede">
            Inspect recent source runs, governance adjustments, coverage breadth, and manual trigger controls from one
            control surface.
          </p>
        </div>

        <div className="hero-meta">
          <div className="signal-pill">
            <span className="signal-dot-live" />
            <strong>{health}</strong>
          </div>
          <div className="meta-chip">
            <span>Scheduler</span>
            <strong>Default sources on cadence</strong>
          </div>
        </div>
      </section>

      <section className="stats-grid" aria-label="Ingestion summary">
        <article className="metric-cell">
          <p>Runs</p>
          <strong>{metrics.totalRuns}</strong>
          <span>Recent ingestion batches returned by the API</span>
        </article>
        <article className="metric-cell">
          <p>Failed runs</p>
          <strong>{metrics.failedRuns}</strong>
          <span>Batches that contained at least one failed source</span>
        </article>
        <article className="metric-cell">
          <p>Items ingested</p>
          <strong>{metrics.totalItems}</strong>
          <span>Total raw items persisted across visible runs</span>
        </article>
        <article className="metric-cell">
          <p>Sources processed</p>
          <strong>{metrics.totalSources}</strong>
          <span>Total source executions across the same run history</span>
        </article>
      </section>

      <section className="panel trigger-panel">
        <header className="section-title ingestion-head">
          <div>
            <p>Manual Trigger</p>
            <h2>Launch a manual ingest run</h2>
          </div>
          <span>P0 sources selected by default</span>
        </header>

        {sourcesQuery.isLoading ? <div className="empty-state">Loading source catalog...</div> : null}
        {sourcesQuery.isError ? <div className="empty-state">Source catalog failed to load. Check the /sources endpoint.</div> : null}

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
                Select P0
              </button>
              <button type="button" className="button-secondary" onClick={selectAllSources} disabled={sourcesQuery.isLoading}>
                Select all enabled
              </button>
              <button
                type="button"
                className="button-primary"
                onClick={() => triggerMutation.mutate(selectedSlugs)}
                disabled={selectedSlugs.length === 0 || triggerMutation.isPending}
              >
                {triggerMutation.isPending ? "Running..." : "Run ingest now"}
              </button>
            </div>

            <div className="action-status">
              <span>{selectedSlugs.length} sources selected</span>
              {triggerMutation.isSuccess ? <strong>Created ingest run #{triggerMutation.data.id}</strong> : null}
              {triggerMutation.isError ? <strong>Manual trigger failed. Try again after checking the logs.</strong> : null}
            </div>
          </div>
        ) : null}
      </section>

      <section className="panel source-governance-panel">
        <header className="section-title ingestion-head">
          <div>
            <p>Source Governance</p>
            <h2>Feedback-adjusted source posture</h2>
          </div>
          <span>{sourceSpecs.length} sources</span>
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
                  {formatGovernanceSummary(source) || "No additional governance adjustments applied yet."}
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
            <p>Run History</p>
            <h2>Recent ingestion batches</h2>
          </div>
          <span>{runsQuery.isFetching ? "Refreshing" : "Auto refresh every 30s"}</span>
        </header>

        {runsQuery.isLoading ? <div className="empty-state">Loading ingestion history...</div> : null}
        {runsQuery.isError ? <div className="empty-state">Ingestion history failed to load. Check the backend API.</div> : null}
        {!runsQuery.isLoading && !runsQuery.isError && runs.length === 0 ? (
          <div className="empty-state">No ingestion runs recorded yet.</div>
        ) : null}

        {!runsQuery.isLoading && !runsQuery.isError && runs.length > 0 ? (
          <div className="ingest-run-list">
            {runs.map((run) => (
              <article key={run.id} className="ingest-run-row">
                <div className="run-main">
                  <div className="run-head">
                    <h3>Run #{run.id}</h3>
                    <span className={`status-pill status-${run.status}`}>{run.status}</span>
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
                    <p className="run-note">No source errors were recorded for this batch.</p>
                  )}
                </div>

                <div className="run-metrics">
                  <div>
                    <span>Sources</span>
                    <strong>
                      {run.sourcesSucceeded}/{run.sourcesTotal}
                    </strong>
                  </div>
                  <div>
                    <span>Items</span>
                    <strong>{run.itemsIngested}</strong>
                  </div>
                  <div>
                    <span>Started</span>
                    <strong>{formatDateTime(run.startedAt)}</strong>
                  </div>
                  <div>
                    <span>Finished</span>
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
