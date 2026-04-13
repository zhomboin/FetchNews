import React from "react";
import { useQuery } from "@tanstack/react-query";
import { useSearchParams } from "react-router-dom";

import { DetailLink, EmptyState, PanelHeader, StatusPill } from "../../components/console";
import { formatSectionLabel } from "../../lib/api";
import {
  fetchArticleBlocks,
  fetchArticleRevisions,
  fetchEditorialActions,
  fetchWorkbenchArticles,
} from "../../lib/editorial-api";
import { buildRevisionDiffSummary, formatPlatformLabel, resolveEditorialActionLabel, resolveRevisionChangeLabel } from "./article-editor-types";

const ARTICLES_QUERY_KEY = ["workbenchArticles"] as const;
const ARTICLE_BLOCKS_QUERY_KEY = (articleId: number | null) => ["articleBlocks", articleId] as const;
const ARTICLE_REVISIONS_QUERY_KEY = (articleId: number | null) => ["articleRevisions", articleId] as const;
const EDITORIAL_ACTIONS_QUERY_KEY = (articleId: number | null) => ["editorialActions", articleId] as const;

function formatDateTime(value: string): string {
  return new Intl.DateTimeFormat("zh-CN", {
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(value));
}

export function ArticleHistoryDetailPage(): React.JSX.Element {
  const [searchParams, setSearchParams] = useSearchParams();
  const articleId = Number(searchParams.get("articleId") ?? "0") || null;
  const revisionId = Number(searchParams.get("revisionId") ?? "0") || null;

  const articlesQuery = useQuery({
    queryKey: ARTICLES_QUERY_KEY,
    queryFn: fetchWorkbenchArticles,
  });
  const blocksQuery = useQuery({
    queryKey: ARTICLE_BLOCKS_QUERY_KEY(articleId),
    queryFn: () => fetchArticleBlocks(articleId ?? 0),
    enabled: articleId !== null,
  });
  const revisionsQuery = useQuery({
    queryKey: ARTICLE_REVISIONS_QUERY_KEY(articleId),
    queryFn: () => fetchArticleRevisions(articleId ?? 0),
    enabled: articleId !== null,
  });
  const actionsQuery = useQuery({
    queryKey: EDITORIAL_ACTIONS_QUERY_KEY(articleId),
    queryFn: () => fetchEditorialActions(articleId ?? 0),
    enabled: articleId !== null,
  });

  const articles = articlesQuery.data ?? [];
  const selectedArticle = articles.find((article) => article.id === articleId) ?? articles[0] ?? null;
  const selectedArticleId = selectedArticle?.id ?? null;
  const blocks = blocksQuery.data ?? [];
  const revisions = revisionsQuery.data ?? [];
  const editorialActions = actionsQuery.data ?? [];

  React.useEffect(() => {
    if (selectedArticle !== null && selectedArticle.id !== articleId) {
      setSearchParams((current) => {
        current.set("articleId", String(selectedArticle.id));
        if (!current.get("revisionId") && selectedArticle.activeRevisionId) {
          current.set("revisionId", String(selectedArticle.activeRevisionId));
        }
        return current;
      });
    }
  }, [articleId, selectedArticle, setSearchParams]);

  const selectedRevision = revisions.find((revision) => revision.id === revisionId)
    ?? revisions.find((revision) => revision.id === selectedArticle?.activeRevisionId)
    ?? revisions[revisions.length - 1]
    ?? null;
  const diffSummary = buildRevisionDiffSummary(selectedRevision, blocks);

  return (
    <div className="page-stack editorial-history-detail-page">
      <section className="hero-panel">
        <div>
          <p className="eyebrow">编辑历史</p>
          <h1>编辑历史明细</h1>
          <p className="lede">按版本查看块级差异、渠道影响和人工干预记录，适合回滚前核对真实变更范围。</p>
        </div>
      </section>

        <section className="panel editorial-history-detail-shell">
          <PanelHeader
            className="editorial-section-title"
            kicker="版本下钻"
            title={selectedArticle?.title ?? "请选择稿件"}
            actions={<DetailLink to="/articles">返回编辑台</DetailLink>}
          />

        <div className="editorial-history-toolbar">
          <label className="field-shell">
            <span>稿件</span>
            <select
              className="editorial-select"
              value={selectedArticleId ?? ""}
              onChange={(event) => {
                const nextArticleId = Number(event.target.value);
                setSearchParams({ articleId: String(nextArticleId) });
              }}
            >
              {articles.map((article) => (
                <option key={article.id} value={article.id}>
                  {`${article.targetDate} · ${article.title}`}
                </option>
              ))}
            </select>
          </label>

          <label className="field-shell">
            <span>版本</span>
            <select
              className="editorial-select"
              value={selectedRevision?.id ?? ""}
              onChange={(event) => {
                setSearchParams({ articleId: String(selectedArticleId), revisionId: event.target.value });
              }}
            >
              {revisions.map((revision) => (
                <option key={revision.id} value={revision.id}>
                  {`v${revision.versionNumber} · ${resolveRevisionChangeLabel(revision.changeType)}`}
                </option>
              ))}
            </select>
          </label>
        </div>

        <div className="editorial-history-summary">
          <div className="risk-stat" data-tone={diffSummary.changedBlocks > 0 ? "watch" : "calm"}>
            <p>变更块</p>
            <strong>{diffSummary.changedBlocks}</strong>
            <span>内容、标题或锁定状态与当前激活版本不一致。</span>
          </div>
          <div className="risk-stat" data-tone={diffSummary.addedBlocks > 0 ? "watch" : "calm"}>
            <p>新增块</p>
            <strong>{diffSummary.addedBlocks}</strong>
            <span>当前版本多出的块，通常来自重建或模板变化。</span>
          </div>
          <div className="risk-stat" data-tone={diffSummary.removedBlocks > 0 ? "watch" : "calm"}>
            <p>移除块</p>
            <strong>{diffSummary.removedBlocks}</strong>
            <span>历史版本中的块在当前版本已不存在。</span>
          </div>
        </div>

        <div className="editorial-platform-token-row">
          {diffSummary.changedPlatforms.length === 0 ? (
            <span className="section-badge section-badge-soft">当前差异未影响平台文案</span>
          ) : (
            diffSummary.changedPlatforms.map((platform) => (
              <span key={platform} className="section-badge section-badge-soft editorial-template-token">
                {`影响平台：${formatPlatformLabel(platform)}`}
              </span>
            ))
          )}
        </div>

        <section className="editorial-history-grid">
          <div className="editorial-diff-list editorial-diff-list-full">
              {diffSummary.diffRecords.length === 0 ? (
                <EmptyState>所选版本与当前激活版本一致，没有额外差异。</EmptyState>
              ) : (
                diffSummary.diffRecords.map((record) => (
                <article key={`${record.blockKey}-${record.changeKind}`} className="editorial-diff-card editorial-diff-card-dense">
                  <div className="detail-card-header">
                    <div>
                      <p className="detail-kicker">{record.blockTypeLabel}</p>
                      <h3>{record.afterTitle || record.beforeTitle || record.blockKey}</h3>
                    </div>
                    <StatusPill status={record.changeKind === "removed" ? "failed" : record.changeKind === "added" ? "ready" : "draft"}>
                      {record.changeKind === "changed" ? "已变更" : record.changeKind === "added" ? "新增" : "已移除"}
                    </StatusPill>
                  </div>
                  <p className="detail-copy">
                    {record.sectionLabel ?? record.platformLabel ?? "系统块"}
                    {record.platformLabel ? " · 平台块" : ""}
                    {record.beforeLocked !== record.afterLocked ? ` · 锁定 ${record.beforeLocked ? "开" : "关"} → ${record.afterLocked ? "开" : "关"}` : ""}
                  </p>
                  <div className="editorial-diff-columns">
                    <div>
                      <strong>历史版本</strong>
                      <p>{record.beforeContent || "无内容"}</p>
                    </div>
                    <div>
                      <strong>当前版本</strong>
                      <p>{record.afterContent || "无内容"}</p>
                    </div>
                  </div>
                </article>
              ))
            )}
          </div>

          <div className="editorial-history-sidepanel">
            <section className="panel detail-side-panel">
              <header className="subsection-head">
                <strong>版本快照</strong>
                <span>{selectedRevision ? `v${selectedRevision.versionNumber}` : "未选择"}</span>
              </header>
              {selectedRevision ? (
                <div className="detail-side-copy">
                  <p>{resolveRevisionChangeLabel(selectedRevision.changeType)}</p>
                  <p>{selectedRevision.changeNote ?? "没有额外说明。"}</p>
                  <p>{`创建时间：${formatDateTime(selectedRevision.createdAt)}`}</p>
                </div>
                ) : (
                  <EmptyState className="compact-empty-state">当前没有可查看的版本。</EmptyState>
                )}
            </section>

            <section className="panel detail-side-panel">
              <header className="subsection-head">
                <strong>人工干预明细</strong>
                <span>{editorialActions.length} 条</span>
              </header>
              <div className="log-list">
                {editorialActions.map((action) => (
                  <article key={action.id} className="log-row log-info">
                    <div className="log-time">{formatDateTime(action.createdAt)}</div>
                    <div className="log-main">
                      <div className="log-head">
                        <strong>{resolveEditorialActionLabel(action.actionType)}</strong>
                        <span>{action.targetId ?? action.targetType}</span>
                      </div>
                      <p>
                        {action.targetType}
                        {Array.isArray(action.detail.section_keys) ? ` · 栏目 ${action.detail.section_keys.join(" / ")}` : ""}
                        {typeof action.detail.changed_fields === "object" && action.detail.changed_fields !== null ? ` · 字段 ${Object.keys(action.detail.changed_fields).join(" / ")}` : ""}
                      </p>
                    </div>
                  </article>
                ))}
              </div>
            </section>

            <section className="panel detail-side-panel">
              <header className="subsection-head">
                <strong>当前栏目计划</strong>
                <span>{selectedArticle?.sectionPlan.length ?? 0} 个栏目</span>
              </header>
              <div className="pill-list section-pill-list compact-gap">
                {(selectedArticle?.sectionPlan ?? []).map((plan) => (
                  <span key={plan.sectionKey} className="section-badge section-badge-soft">
                    {`${formatSectionLabel(plan.sectionKey)} · ${plan.storyCount}`}
                  </span>
                ))}
              </div>
            </section>
          </div>
        </section>
      </section>
    </div>
  );
}
