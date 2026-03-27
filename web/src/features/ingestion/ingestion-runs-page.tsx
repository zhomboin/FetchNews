import React from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { IngestRunRecord, SourceSpec, fetchIngestRuns, fetchSourceSpecs, triggerIngestRun } from "../../lib/api";

type IngestionRunsPageProps = {
  health: string;
};

function formatDateTime(value: string | null): string {
  if (!value) {
    return "进行中";
  }

  return new Intl.DateTimeFormat("zh-CN", {
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(value));
}

function summarize(runs: IngestRunRecord[]) {
  return {
    totalRuns: runs.length,
    failedRuns: runs.filter((run) => run.sources_failed > 0).length,
    totalItems: runs.reduce((sum, run) => sum + run.items_ingested, 0),
    totalSources: runs.reduce((sum, run) => sum + run.sources_total, 0),
  };
}

function defaultP0Selection(sources: SourceSpec[]): string[] {
  return sources.filter((source) => source.priority === "P0").map((source) => source.slug);
}

export function IngestionRunsPage({ health }: IngestionRunsPageProps) {
  const queryClient = useQueryClient();
  const sourcesQuery = useQuery({
    queryKey: ["source-specs"],
    queryFn: fetchSourceSpecs,
  });
  const runsQuery = useQuery({
    queryKey: ["ingest-runs"],
    queryFn: fetchIngestRuns,
    refetchInterval: 30_000,
  });
  const [selectedSlugs, setSelectedSlugs] = React.useState<string[]>([]);

  React.useEffect(() => {
    if (sourcesQuery.data && selectedSlugs.length === 0) {
      setSelectedSlugs(defaultP0Selection(sourcesQuery.data));
    }
  }, [selectedSlugs.length, sourcesQuery.data]);

  const triggerMutation = useMutation({
    mutationFn: (sourceSlugs: string[]) => triggerIngestRun({ source_slugs: sourceSlugs }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["ingest-runs"] });
    },
  });

  const runs = runsQuery.data ?? [];
  const metrics = summarize(runs);
  const sourceSpecs = sourcesQuery.data ?? [];

  function toggleSource(slug: string) {
    setSelectedSlugs((current) =>
      current.includes(slug) ? current.filter((item) => item !== slug) : [...current, slug],
    );
  }

  function selectAll() {
    setSelectedSlugs(sourceSpecs.map((source) => source.slug));
  }

  function selectP0() {
    setSelectedSlugs(defaultP0Selection(sourceSpecs));
  }

  return (
    <div className="page-stack">
      <section className="hero-panel">
        <div>
          <p className="eyebrow">Ingestion Ledger</p>
          <h1>采集运行</h1>
          <p className="lede">
            查看最近的来源抓取批次、来源覆盖、失败情况和入库结果。现在也支持从这个页面直接触发一次手动采集。
          </p>
        </div>

        <div className="hero-meta">
          <div className="signal-pill">
            <span className="signal-dot-live" />
            <strong>{health}</strong>
          </div>
          <div className="meta-chip">
            <span>自动调度</span>
            <strong>默认来源周期抓取</strong>
          </div>
        </div>
      </section>

      <section className="stats-grid" aria-label="采集运行摘要">
        <article className="metric-cell">
          <p>运行批次</p>
          <strong>{metrics.totalRuns}</strong>
          <span>最近接口返回的批次数量</span>
        </article>
        <article className="metric-cell">
          <p>异常批次</p>
          <strong>{metrics.failedRuns}</strong>
          <span>含失败来源的运行数</span>
        </article>
        <article className="metric-cell">
          <p>入库条目</p>
          <strong>{metrics.totalItems}</strong>
          <span>原始事件累计写入数</span>
        </article>
        <article className="metric-cell">
          <p>来源处理</p>
          <strong>{metrics.totalSources}</strong>
          <span>批次中执行过的来源数</span>
        </article>
      </section>

      <section className="panel trigger-panel">
        <header className="section-title ingestion-head">
          <div>
            <p>Manual Trigger</p>
            <h2>手动触发采集</h2>
          </div>
          <span>默认勾选 P0 来源</span>
        </header>

        {sourcesQuery.isLoading ? <div className="empty-state">正在载入来源目录…</div> : null}
        {sourcesQuery.isError ? <div className="empty-state">来源目录加载失败，请确认 `/sources` 接口可用。</div> : null}

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
              <button type="button" className="button-secondary" onClick={selectP0} disabled={sourcesQuery.isLoading}>
                仅选 P0
              </button>
              <button type="button" className="button-secondary" onClick={selectAll} disabled={sourcesQuery.isLoading}>
                全选启用来源
              </button>
              <button
                type="button"
                className="button-primary"
                onClick={() => triggerMutation.mutate(selectedSlugs)}
                disabled={selectedSlugs.length === 0 || triggerMutation.isPending}
              >
                {triggerMutation.isPending ? "采集中…" : "立即采集"}
              </button>
            </div>

            <div className="action-status">
              <span>已选 {selectedSlugs.length} 个来源</span>
              {triggerMutation.isSuccess ? <strong>已创建采集批次 #{triggerMutation.data.id}</strong> : null}
              {triggerMutation.isError ? <strong>触发失败，请稍后重试。</strong> : null}
            </div>
          </div>
        ) : null}
      </section>

      <section className="panel ingestion-panel">
        <header className="section-title ingestion-head">
          <div>
            <p>Run History</p>
            <h2>最近采集批次</h2>
          </div>
          <span>{runsQuery.isFetching ? "刷新中" : "30 秒自动刷新"}</span>
        </header>

        {runsQuery.isLoading ? <div className="empty-state">正在载入采集批次…</div> : null}
        {runsQuery.isError ? <div className="empty-state">采集批次加载失败，请确认后端接口可用。</div> : null}
        {!runsQuery.isLoading && !runsQuery.isError && runs.length === 0 ? <div className="empty-state">还没有采集运行记录。</div> : null}

        {!runsQuery.isLoading && !runsQuery.isError && runs.length > 0 ? (
          <div className="ingest-run-list">
            {runs.map((run) => (
              <article key={run.id} className="ingest-run-row">
                <div className="run-main">
                  <div className="run-head">
                    <h3>批次 #{run.id}</h3>
                    <span className={`status-pill status-${run.status}`}>{run.status}</span>
                  </div>

                  <div className="source-chip-list">
                    {run.source_slugs.map((slug) => (
                      <span key={slug} className="source-chip">
                        {slug}
                      </span>
                    ))}
                  </div>

                  {run.errors.length > 0 ? (
                    <div className="run-errors">
                      {run.errors.map((error) => (
                        <p key={`${run.id}-${error.source_slug}`}>
                          {error.source_slug}: {error.message}
                        </p>
                      ))}
                    </div>
                  ) : (
                    <p className="run-note">本批次未记录错误。</p>
                  )}
                </div>

                <div className="run-metrics">
                  <div>
                    <span>来源</span>
                    <strong>
                      {run.sources_succeeded}/{run.sources_total}
                    </strong>
                  </div>
                  <div>
                    <span>入库</span>
                    <strong>{run.items_ingested}</strong>
                  </div>
                  <div>
                    <span>开始</span>
                    <strong>{formatDateTime(run.started_at)}</strong>
                  </div>
                  <div>
                    <span>完成</span>
                    <strong>{formatDateTime(run.finished_at)}</strong>
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
