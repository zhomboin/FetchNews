import React from "react";

import type { PostVariantRecord, PublishJobRecord } from "../../lib/api";
import type { ArticleBlockRecord, ArticleRevisionRecord, ArticleWorkbenchRecord, EditorialActionRecord } from "../../lib/editorial-api";
import type {
  BlockDraftRecord,
  BlockDraftState,
  PublishFeedbackField,
  PublishFeedbackFormState,
  RevisionDiffSummary,
} from "./article-editor-types";
import {
  formatPlatformLabel,
  hasBlockDraftChanges,
  resolveEditorialActionLabel,
  resolveRevisionChangeLabel,
} from "./article-editor-types";

type ArticleHistoryPanelProps = {
  article: ArticleWorkbenchRecord | null;
  revisions: ArticleRevisionRecord[];
  selectedRevisionId: number | null;
  onSelectRevision: (revisionId: number) => void;
  onRestoreRevision: (revisionId: number) => void;
  restoringRevisionId: number | null;
  revisionDiffSummary: RevisionDiffSummary;
  editorialActions: EditorialActionRecord[];
  platformBlocks: ArticleBlockRecord[];
  blockDrafts: BlockDraftState;
  pendingBlockId: number | null;
  onDraftChange: (blockId: number, patch: Partial<BlockDraftRecord>) => void;
  onResetBlock: (blockId: number) => void;
  onSaveBlock: (block: ArticleBlockRecord) => void;
  onToggleBlockLock: (block: ArticleBlockRecord) => void;
  variants: PostVariantRecord[];
  publishJobs: PublishJobRecord[];
  selectedPlatforms: string[];
  onTogglePlatform: (platform: string) => void;
  scheduledFor: string;
  onScheduledForChange: (scheduledFor: string) => void;
  onCreatePublishJobs: () => void;
  onDispatchPublishJobs: () => void;
  onPollPublishJobs: () => void;
  canPublish: boolean;
  publishPending: boolean;
  dispatchPending: boolean;
  pollPending: boolean;
  onMarkPublished: (jobId: number) => void;
  onMarkFailed: (jobId: number) => void;
  onRetryJob: (jobId: number) => void;
  isJobActionPending: boolean;
  feedbackForms: Record<number, PublishFeedbackFormState>;
  onFeedbackChange: (jobId: number, field: PublishFeedbackField, value: string) => void;
  onResetFeedback: (job: PublishJobRecord) => void;
  onSaveFeedback: (jobId: number, state: PublishFeedbackFormState) => void;
  feedbackPending: boolean;
};

const PUBLISH_PLATFORMS = ["wechat", "x", "telegram"] as const;
const FEEDBACK_FIELDS = [
  ["impressions", "曝光"],
  ["opens", "打开"],
  ["clicks", "点击"],
  ["interactions", "互动"],
] as const satisfies ReadonlyArray<readonly [PublishFeedbackField, string]>;

function formatDateTime(value: string): string {
  return new Intl.DateTimeFormat("zh-CN", {
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(value));
}

function formatPublishStatus(status: string): string {
  if (status === "scheduled") return "待发布";
  if (status === "published") return "已发布";
  if (status === "failed") return "失败";
  if (status === "pending") return "排队中";
  return status;
}

function readMetrics(job: PublishJobRecord, forms: Record<number, PublishFeedbackFormState>): PublishFeedbackFormState {
  return (
    forms[job.id] ?? {
      impressions: `${job.performanceMetrics.impressions ?? ""}`,
      opens: `${job.performanceMetrics.opens ?? ""}`,
      clicks: `${job.performanceMetrics.clicks ?? ""}`,
      interactions: `${job.performanceMetrics.interactions ?? ""}`,
    }
  );
}

function hasFeedbackPayload(state: PublishFeedbackFormState): boolean {
  return Object.values(state).some((value) => value.trim() !== "");
}

function describeActionTarget(action: EditorialActionRecord): string {
  if (action.targetId) {
    return `${action.targetType} · ${action.targetId}`;
  }
  return action.targetType;
}

function describeActionDetail(action: EditorialActionRecord): string {
  const detail = action.detail ?? {};
  if (action.actionType === "edit_block") {
    const changedFields = Array.isArray(detail.changed_fields)
      ? detail.changed_fields.join("、")
      : typeof detail.changed_fields === "object" && detail.changed_fields !== null
        ? Object.keys(detail.changed_fields).join("、")
        : "内容";
    return `修改字段：${changedFields || "内容"}`;
  }
  if (action.actionType === "rebuild_article") {
    const sectionKeys = Array.isArray(detail.section_keys) ? detail.section_keys.join("、") : "全部栏目";
    return `模式：${detail.mode ?? "mixed"}；范围：${sectionKeys || "全部栏目"}`;
  }
  if (action.actionType === "restore_revision") {
    return `来源版本：${detail.source_revision_id ?? "未知"}`;
  }
  return JSON.stringify(detail);
}

export function ArticleHistoryPanel({
  article,
  revisions,
  selectedRevisionId,
  onSelectRevision,
  onRestoreRevision,
  restoringRevisionId,
  revisionDiffSummary,
  editorialActions,
  platformBlocks,
  blockDrafts,
  pendingBlockId,
  onDraftChange,
  onResetBlock,
  onSaveBlock,
  onToggleBlockLock,
  variants,
  publishJobs,
  selectedPlatforms,
  onTogglePlatform,
  scheduledFor,
  onScheduledForChange,
  onCreatePublishJobs,
  onDispatchPublishJobs,
  onPollPublishJobs,
  canPublish,
  publishPending,
  dispatchPending,
  pollPending,
  onMarkPublished,
  onMarkFailed,
  onRetryJob,
  isJobActionPending,
  feedbackForms,
  onFeedbackChange,
  onResetFeedback,
  onSaveFeedback,
  feedbackPending,
}: ArticleHistoryPanelProps): React.JSX.Element {
  if (article === null) {
    return (
      <section className="panel editorial-workbench-history">
        <header className="section-title editorial-section-title">
          <div>
            <p>History & Channels</p>
            <h2>版本历史与渠道</h2>
          </div>
        </header>
        <div className="empty-state">选择一篇稿件后，这里会显示版本差异、平台文案、编辑动作和发布前审核信息。</div>
      </section>
    );
  }

  const detailHref = `/articles/history?articleId=${article.id}${selectedRevisionId ? `&revisionId=${selectedRevisionId}` : ""}`;
  const diffPreview = revisionDiffSummary.diffRecords.slice(0, 4);

  return (
    <section className="panel editorial-workbench-history">
      <header className="section-title editorial-section-title">
        <div>
          <p>History & Channels</p>
          <h2>版本历史与渠道</h2>
        </div>
        <span>{revisions.length} 个版本</span>
      </header>

      <section className="editorial-history-summary">
        <div className="risk-stat" data-tone={revisionDiffSummary.changedBlocks > 0 ? "watch" : "calm"}>
          <p>变更块</p>
          <strong>{revisionDiffSummary.changedBlocks}</strong>
          <span>与当前激活版本相比，内容或锁定状态发生变化。</span>
        </div>
        <div className="risk-stat" data-tone={revisionDiffSummary.addedBlocks > 0 ? "watch" : "calm"}>
          <p>新增块</p>
          <strong>{revisionDiffSummary.addedBlocks}</strong>
          <span>当前版本新增了这些块，可用于确认生成器补充了什么。</span>
        </div>
        <div className="risk-stat" data-tone={revisionDiffSummary.removedBlocks > 0 ? "watch" : "calm"}>
          <p>移除块</p>
          <strong>{revisionDiffSummary.removedBlocks}</strong>
          <span>历史版本存在、当前版本已移除，适合核对回滚影响。</span>
        </div>
      </section>

      <div className="editorial-platform-token-row">
        {revisionDiffSummary.changedPlatforms.length === 0 ? (
          <span className="section-badge section-badge-soft">当前版本没有平台差异</span>
        ) : (
          revisionDiffSummary.changedPlatforms.map((platform) => (
            <span key={platform} className="section-badge section-badge-soft editorial-template-token">
              {`已影响 ${formatPlatformLabel(platform)}`}
            </span>
          ))
        )}
        <a className="detail-link" href={detailHref}>
          打开历史明细页
        </a>
      </div>

      <div className="editorial-revision-list">
        {revisions.map((revision) => (
          <article key={revision.id} className={`detail-card ${revision.id === selectedRevisionId ? "editorial-active-card" : ""}`}>
            <div className="detail-card-header">
              <div>
                <p className="detail-kicker">版本 {revision.versionNumber}</p>
                <h3>{resolveRevisionChangeLabel(revision.changeType)}</h3>
              </div>
              <span className="status-pill status-ready">{formatDateTime(revision.createdAt)}</span>
            </div>
            <p className="detail-copy">{revision.changeNote ?? "系统已记录这一版的模板、块快照和平台变体。"}</p>
            <div className="publish-job-actions">
              <button type="button" className="button-secondary" onClick={() => onSelectRevision(revision.id)}>
                查看差异
              </button>
              <button
                type="button"
                className="button-primary"
                onClick={() => onRestoreRevision(revision.id)}
                disabled={restoringRevisionId === revision.id}
              >
                {restoringRevisionId === revision.id ? "恢复中..." : "恢复为当前版本"}
              </button>
            </div>
          </article>
        ))}
      </div>

      <section className="editorial-diff-panel">
        <header className="subsection-head">
          <strong>块级差异预览</strong>
          <span>{revisionDiffSummary.diffRecords.length} 条</span>
        </header>
        {diffPreview.length === 0 ? (
          <div className="empty-state compact-empty-state">当前选中版本与激活版本一致，没有需要展示的块级差异。</div>
        ) : (
          <div className="editorial-diff-list">
            {diffPreview.map((record) => (
              <article key={`${record.blockKey}-${record.changeKind}`} className="editorial-diff-card">
                <div className="detail-card-header">
                  <div>
                    <p className="detail-kicker">{record.blockTypeLabel}</p>
                    <h3>{record.afterTitle || record.beforeTitle || record.blockKey}</h3>
                  </div>
                  <span className={`status-pill status-${record.changeKind === "removed" ? "failed" : record.changeKind === "added" ? "ready" : "draft"}`}>
                    {record.changeKind === "changed" ? "已变更" : record.changeKind === "added" ? "新增" : "已移除"}
                  </span>
                </div>
                <p className="detail-copy">
                  {record.sectionLabel ?? record.platformLabel ?? "系统块"}
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
            ))}
          </div>
        )}
      </section>

      <section className="editorial-platform-panel">
        <header className="subsection-head">
          <strong>平台文案</strong>
          <span>{platformBlocks.length} 个平台块</span>
        </header>
        <div className="editorial-platform-list">
          {platformBlocks.map((block) => {
            const draft = blockDrafts[block.id] ?? {
              content: block.content,
              title: block.title ?? "",
              isLocked: block.isLocked,
            };
            const changed = hasBlockDraftChanges(block, draft);
            const publishedVariant = variants.find((variant) => variant.platform === block.platformScope);
            return (
              <article key={block.id} className="editorial-block-card editorial-platform-card">
                <header className="editorial-block-head">
                  <div>
                    <p className="eyebrow editorial-block-kicker">{formatPlatformLabel(block.platformScope ?? "x")}</p>
                    <h3>{draft.isLocked ? "已锁定平台文案" : "可重建平台文案"}</h3>
                  </div>
                  <span className={`status-pill ${draft.isLocked ? "status-approved" : "status-draft"}`}>
                    {draft.isLocked ? "已锁定" : "可重建"}
                  </span>
                </header>
                <label className="field-shell article-note-field">
                  <span>平台正文</span>
                  <textarea
                    rows={5}
                    value={draft.content}
                    onChange={(event) => onDraftChange(block.id, { content: event.target.value })}
                  />
                </label>
                <div className="publish-job-note-stack">
                  <span className="publish-job-note">
                    最近一次变体更新时间：{publishedVariant ? formatDateTime(publishedVariant.updatedAt) : "尚未生成"}
                  </span>
                </div>
                <div className="editorial-block-actions">
                  <button type="button" className="button-secondary" onClick={() => onToggleBlockLock(block)} disabled={pendingBlockId === block.id}>
                    {draft.isLocked ? "解除锁定" : "锁定平台块"}
                  </button>
                  <button type="button" className="button-secondary" onClick={() => onResetBlock(block.id)} disabled={!changed || pendingBlockId === block.id}>
                    取消修改
                  </button>
                  <button type="button" className="button-primary" onClick={() => onSaveBlock(block)} disabled={!changed || pendingBlockId === block.id}>
                    {pendingBlockId === block.id ? "保存中..." : "保存修改"}
                  </button>
                </div>
              </article>
            );
          })}
        </div>
      </section>

      <section className="editorial-action-timeline">
        <header className="subsection-head">
          <strong>人工干预记录</strong>
          <span>{editorialActions.length} 条</span>
        </header>
        <div className="log-list">
          {editorialActions.map((action) => (
            <article key={action.id} className="log-row log-info">
              <div className="log-time">{formatDateTime(action.createdAt)}</div>
              <div className="log-main">
                <div className="log-head">
                  <strong>{resolveEditorialActionLabel(action.actionType)}</strong>
                  <span>{describeActionTarget(action)}</span>
                </div>
                <p>{describeActionDetail(action)}</p>
              </div>
            </article>
          ))}
        </div>
      </section>

      <section className="article-body-panel publish-review-panel">
        <header className="subsection-head">
          <strong>发布前审核</strong>
          <span>{publishJobs.length} 条任务</span>
        </header>

        <div className="filter-group">
          <p className="filter-caption">发布平台</p>
          <div className="filter-chip-row">
            {PUBLISH_PLATFORMS.map((platform) => (
              <button
                key={platform}
                type="button"
                className={`filter-chip ${selectedPlatforms.includes(platform) ? "active" : ""}`}
                onClick={() => onTogglePlatform(platform)}
              >
                {formatPlatformLabel(platform)}
              </button>
            ))}
          </div>
        </div>

        <label className="field-shell">
          <span>计划发布时间</span>
          <input type="datetime-local" value={scheduledFor} onChange={(event) => onScheduledForChange(event.target.value)} />
        </label>

        <div className="action-row publish-orchestration-row">
          <button type="button" className="button-secondary" onClick={onDispatchPublishJobs} disabled={dispatchPending || publishJobs.length === 0}>
            {dispatchPending ? "执行中..." : "执行到期发布"}
          </button>
          <button type="button" className="button-secondary" onClick={onPollPublishJobs} disabled={pollPending || publishJobs.length === 0}>
            {pollPending ? "轮询中..." : "轮询发布结果"}
          </button>
          <button type="button" className="button-primary" onClick={onCreatePublishJobs} disabled={!canPublish || publishPending}>
            {publishPending ? "创建中..." : "创建发布任务"}
          </button>
        </div>

        <div className="publish-job-list">
          {publishJobs.length === 0 ? (
            <div className="empty-state">当前稿件还没有发布任务。</div>
          ) : (
            publishJobs.map((job) => {
              const metrics = readMetrics(job, feedbackForms);
              return (
                <article key={job.id} className="publish-job-row">
                  <div className="publish-job-copy">
                    <div>
                      <strong>{formatPlatformLabel(job.platform)}</strong>
                      <p>{formatDateTime(job.scheduledFor)}</p>
                    </div>
                    <div className="publish-job-meta">
                      <span className={`status-pill status-${job.status}`}>{formatPublishStatus(job.status)}</span>
                      <span>重试 {job.retries}</span>
                    </div>
                  </div>
                  {job.errorMessage ? <span className="publish-job-error">{job.errorMessage}</span> : null}
                  {job.status === "published" ? (
                    <div className="publish-feedback-panel">
                      <div className="publish-feedback-grid">
                        {FEEDBACK_FIELDS.map(([field, label]) => (
                          <label key={`${job.id}-${field}`} className="field-shell publish-feedback-field">
                            <span>{label}</span>
                            <input
                              type="number"
                              min="0"
                              value={metrics[field]}
                              onChange={(event) => onFeedbackChange(job.id, field, event.target.value)}
                            />
                          </label>
                        ))}
                      </div>
                      <div className="publish-job-actions">
                        <button type="button" className="button-secondary" onClick={() => onResetFeedback(job)} disabled={feedbackPending}>
                          重置指标
                        </button>
                        <button
                          type="button"
                          className="button-primary"
                          onClick={() => onSaveFeedback(job.id, metrics)}
                          disabled={!hasFeedbackPayload(metrics) || feedbackPending}
                        >
                          {feedbackPending ? "保存中..." : "保存指标"}
                        </button>
                      </div>
                    </div>
                  ) : null}
                  <div className="publish-job-actions">
                    {job.status === "scheduled" ? (
                      <>
                        <button type="button" className="button-secondary" onClick={() => onMarkFailed(job.id)} disabled={isJobActionPending}>
                          标记失败
                        </button>
                        <button type="button" className="button-primary" onClick={() => onMarkPublished(job.id)} disabled={isJobActionPending}>
                          标记已发布
                        </button>
                      </>
                    ) : null}
                    {job.status === "failed" ? (
                      <button type="button" className="button-secondary" onClick={() => onRetryJob(job.id)} disabled={isJobActionPending}>
                        重新入队
                      </button>
                    ) : null}
                  </div>
                </article>
              );
            })
          )}
        </div>
      </section>
    </section>
  );
}
