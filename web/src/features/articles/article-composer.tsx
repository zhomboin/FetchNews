import React from "react";

import { formatSectionLabel } from "../../lib/api";
import type { ArticleBlockRecord, ArticleWorkbenchRecord } from "../../lib/editorial-api";
import type { BlockDraftRecord, BlockDraftState } from "./article-editor-types";
import { hasBlockDraftChanges, resolveBlockTypeLabel } from "./article-editor-types";

type ArticleComposerProps = {
  article: ArticleWorkbenchRecord | null;
  blocks: ArticleBlockRecord[];
  blockDrafts: BlockDraftState;
  pendingBlockId: number | null;
  onDraftChange: (blockId: number, patch: Partial<BlockDraftRecord>) => void;
  onResetBlock: (blockId: number) => void;
  onSaveBlock: (block: ArticleBlockRecord) => void;
  onToggleBlockLock: (block: ArticleBlockRecord) => void;
  onMoveBlockUp: (block: ArticleBlockRecord) => void;
  onMoveBlockDown: (block: ArticleBlockRecord) => void;
};

function isBodyBlock(block: ArticleBlockRecord): boolean {
  return block.platformScope === null;
}

function isReorderableBlock(block: ArticleBlockRecord): boolean {
  return block.blockType === "story_paragraph";
}

export function ArticleComposer({
  article,
  blocks,
  blockDrafts,
  pendingBlockId,
  onDraftChange,
  onResetBlock,
  onSaveBlock,
  onToggleBlockLock,
  onMoveBlockUp,
  onMoveBlockDown,
}: ArticleComposerProps): React.JSX.Element {
  const bodyBlocks = blocks.filter(isBodyBlock);
  const reorderableBlocks = bodyBlocks.filter(isReorderableBlock);

  if (article === null) {
    return (
      <section className="panel editorial-workbench-composer">
        <header className="section-title editorial-section-title">
          <div>
            <p>正文编排</p>
            <h2>段落编排</h2>
          </div>
        </header>
        <div className="empty-state">先在左侧选择一篇稿件，再对正文块进行锁定、改写和混合重建。</div>
      </section>
    );
  }

  return (
    <section className="panel editorial-workbench-composer">
      <header className="section-title editorial-section-title">
        <div>
          <p>正文编排</p>
          <h2>段落编排</h2>
        </div>
        <span>{bodyBlocks.length} 个正文块</span>
      </header>

      <section className="article-hero-card editorial-composer-hero">
        <div className="article-hero-copy">
          <p>{article.targetDate}</p>
          <h3>{article.title}</h3>
          <span>{article.summary}</span>
        </div>
        <div className="article-hero-meta">
          <div>
            <strong>{article.templateName ?? "系统默认"}</strong>
            <span>模板</span>
          </div>
          <div>
            <strong>{article.blockCount}</strong>
            <span>内容块</span>
          </div>
          <div>
            <strong>{article.storyCount}</strong>
            <span>资讯数</span>
          </div>
        </div>
      </section>

      <div className="editorial-block-list">
        {bodyBlocks.map((block) => {
          const draft = blockDrafts[block.id] ?? {
            content: block.content,
            title: block.title ?? "",
            isLocked: block.isLocked,
          };
          const changed = hasBlockDraftChanges(block, draft);
          const reorderableIndex = reorderableBlocks.findIndex((item) => item.id === block.id);
          const canMoveUp = reorderableIndex > 0;
          const canMoveDown = reorderableIndex !== -1 && reorderableIndex < reorderableBlocks.length - 1;

          return (
            <article key={block.id} className="editorial-block-card">
              <header className="editorial-block-head">
                <div>
                  <p className="eyebrow editorial-block-kicker">{resolveBlockTypeLabel(block.blockType)}</p>
                  <h3>{draft.title || block.title || formatSectionLabel(block.sectionKey ?? "community")}</h3>
                </div>
                <div className="article-row-pills">
                  {block.sectionKey ? (
                    <span className="section-badge section-badge-soft">{formatSectionLabel(block.sectionKey)}</span>
                  ) : null}
                  <span className={`status-pill ${draft.isLocked ? "status-approved" : "status-draft"}`}>
                    {draft.isLocked ? "已锁定" : "可重建"}
                  </span>
                </div>
              </header>

              {block.blockType === "story_paragraph" ? (
                <>
                  <label className="field-shell">
                    <span>段落标题</span>
                    <input
                      type="text"
                      value={draft.title}
                      onChange={(event) => onDraftChange(block.id, { title: event.target.value })}
                    />
                  </label>
                  <div className="editorial-order-actions">
                    <button
                      type="button"
                      className="button-secondary"
                      aria-label={`move-up-${block.id}`}
                      onClick={() => onMoveBlockUp(block)}
                      disabled={!canMoveUp || pendingBlockId === block.id}
                    >
                      上移
                    </button>
                    <button
                      type="button"
                      className="button-secondary"
                      aria-label={`move-down-${block.id}`}
                      onClick={() => onMoveBlockDown(block)}
                      disabled={!canMoveDown || pendingBlockId === block.id}
                    >
                      下移
                    </button>
                  </div>
                </>
              ) : null}

              <label className="field-shell article-note-field">
                <span>正文内容</span>
                <textarea
                  rows={block.blockType === "story_paragraph" ? 7 : 5}
                  value={draft.content}
                  onChange={(event) => onDraftChange(block.id, { content: event.target.value })}
                />
              </label>

              <div className="editorial-block-actions">
                <button type="button" className="button-secondary" onClick={() => onToggleBlockLock(block)} disabled={pendingBlockId === block.id}>
                  {draft.isLocked ? "解除锁定" : "锁定段落"}
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
  );
}
