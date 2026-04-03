import { formatSectionLabel } from "../../lib/api";
import type { ArticleBlockRecord, ArticleRevisionRecord } from "../../lib/editorial-api";

export type ScopeMode = "allApproved" | "custom";
export type PublishFeedbackField = "impressions" | "opens" | "clicks" | "interactions";
export type PublishFeedbackFormState = Record<PublishFeedbackField, string>;

export type BlockDraftRecord = {
  content: string;
  title: string;
  isLocked: boolean;
};

export type BlockDraftState = Record<number, BlockDraftRecord>;

export type RevisionDiffRecord = {
  blockKey: string;
  blockType: string;
  blockTypeLabel: string;
  sectionLabel: string | null;
  platformLabel: string | null;
  changeKind: "changed" | "added" | "removed";
  beforeTitle: string;
  afterTitle: string;
  beforeContent: string;
  afterContent: string;
  beforeLocked: boolean;
  afterLocked: boolean;
  sortOrder: number;
};

export type RevisionDiffSummary = {
  changedBlocks: number;
  addedBlocks: number;
  removedBlocks: number;
  changedPlatforms: string[];
  diffRecords: RevisionDiffRecord[];
};

type RevisionSnapshotBlock = {
  block_key: string;
  block_type: string;
  section_key?: string | null;
  platform_scope?: string | null;
  title?: string | null;
  content?: string;
  sort_order?: number;
  is_locked?: boolean;
};

export function buildBlockDraftState(blocks: ArticleBlockRecord[]): BlockDraftState {
  return blocks.reduce<BlockDraftState>((drafts, block) => {
    drafts[block.id] = {
      content: block.content,
      title: block.title ?? "",
      isLocked: block.isLocked,
    };
    return drafts;
  }, {});
}

export function hasBlockDraftChanges(block: ArticleBlockRecord, draft: BlockDraftRecord | undefined): boolean {
  if (!draft) {
    return false;
  }
  return (
    draft.content !== block.content ||
    draft.title !== (block.title ?? "") ||
    draft.isLocked !== block.isLocked
  );
}

export function resolveBlockTypeLabel(blockType: string): string {
  if (blockType === "title") return "标题块";
  if (blockType === "summary") return "摘要块";
  if (blockType === "intro") return "导语块";
  if (blockType === "section_heading") return "栏目标题";
  if (blockType === "story_paragraph") return "资讯段落";
  if (blockType === "platform_body") return "平台文案";
  if (blockType === "cta") return "结尾 CTA";
  return blockType;
}

export function resolveRevisionChangeLabel(changeType: string): string {
  if (changeType === "generate") return "系统生成";
  if (changeType === "rebuild") return "混合重建";
  if (changeType === "restore") return "版本恢复";
  return changeType;
}

export function resolveEditorialActionLabel(actionType: string): string {
  if (actionType === "edit_block") return "修改内容块";
  if (actionType === "rebuild_article") return "执行重建";
  if (actionType === "restore_revision") return "恢复历史版本";
  return actionType;
}

export function formatPlatformLabel(platform: string): string {
  if (platform === "wechat") return "微信";
  if (platform === "telegram") return "Telegram";
  if (platform === "x") return "X";
  return platform;
}

function readSnapshotBlocks(revision: ArticleRevisionRecord | null): RevisionSnapshotBlock[] {
  if (revision === null || !Array.isArray(revision.snapshot.blocks)) {
    return [];
  }
  return revision.snapshot.blocks as RevisionSnapshotBlock[];
}

export function buildRevisionDiffSummary(
  revision: ArticleRevisionRecord | null,
  activeBlocks: ArticleBlockRecord[],
): RevisionDiffSummary {
  if (revision === null) {
    return { changedBlocks: 0, addedBlocks: 0, removedBlocks: 0, changedPlatforms: [], diffRecords: [] };
  }

  const snapshotBlocks = readSnapshotBlocks(revision);
  const snapshotByKey = new Map(snapshotBlocks.map((block) => [block.block_key, block]));
  const activeByKey = new Map(activeBlocks.map((block) => [block.blockKey, block]));
  const diffRecords: RevisionDiffRecord[] = [];
  const changedPlatforms = new Set<string>();

  for (const block of activeBlocks) {
    const snapshotBlock = snapshotByKey.get(block.blockKey);
    if (!snapshotBlock) {
      diffRecords.push({
        blockKey: block.blockKey,
        blockType: block.blockType,
        blockTypeLabel: resolveBlockTypeLabel(block.blockType),
        sectionLabel: block.sectionKey ? formatSectionLabel(block.sectionKey) : null,
        platformLabel: block.platformScope ? formatPlatformLabel(block.platformScope) : null,
        changeKind: "added",
        beforeTitle: "",
        afterTitle: block.title ?? "",
        beforeContent: "",
        afterContent: block.content,
        beforeLocked: false,
        afterLocked: block.isLocked,
        sortOrder: block.sortOrder,
      });
      if (block.platformScope) {
        changedPlatforms.add(block.platformScope);
      }
      continue;
    }

    const beforeTitle = snapshotBlock.title ?? "";
    const afterTitle = block.title ?? "";
    const beforeContent = snapshotBlock.content ?? "";
    const afterContent = block.content;
    const beforeLocked = Boolean(snapshotBlock.is_locked ?? false);
    const afterLocked = block.isLocked;
    if (beforeTitle === afterTitle && beforeContent === afterContent && beforeLocked === afterLocked) {
      continue;
    }

    diffRecords.push({
      blockKey: block.blockKey,
      blockType: block.blockType,
      blockTypeLabel: resolveBlockTypeLabel(block.blockType),
      sectionLabel: block.sectionKey ? formatSectionLabel(block.sectionKey) : null,
      platformLabel: block.platformScope ? formatPlatformLabel(block.platformScope) : null,
      changeKind: "changed",
      beforeTitle,
      afterTitle,
      beforeContent,
      afterContent,
      beforeLocked,
      afterLocked,
      sortOrder: block.sortOrder,
    });
    if (block.platformScope) {
      changedPlatforms.add(block.platformScope);
    }
  }

  for (const snapshotBlock of snapshotBlocks) {
    if (activeByKey.has(snapshotBlock.block_key)) {
      continue;
    }
    diffRecords.push({
      blockKey: snapshotBlock.block_key,
      blockType: snapshotBlock.block_type,
      blockTypeLabel: resolveBlockTypeLabel(snapshotBlock.block_type),
      sectionLabel: snapshotBlock.section_key ? formatSectionLabel(snapshotBlock.section_key) : null,
      platformLabel: snapshotBlock.platform_scope ? formatPlatformLabel(snapshotBlock.platform_scope) : null,
      changeKind: "removed",
      beforeTitle: snapshotBlock.title ?? "",
      afterTitle: "",
      beforeContent: snapshotBlock.content ?? "",
      afterContent: "",
      beforeLocked: Boolean(snapshotBlock.is_locked ?? false),
      afterLocked: false,
      sortOrder: snapshotBlock.sort_order ?? Number.MAX_SAFE_INTEGER,
    });
    if (snapshotBlock.platform_scope) {
      changedPlatforms.add(snapshotBlock.platform_scope);
    }
  }

  diffRecords.sort((left, right) => left.sortOrder - right.sortOrder || left.blockKey.localeCompare(right.blockKey));

  return {
    changedBlocks: diffRecords.filter((record) => record.changeKind === "changed").length,
    addedBlocks: diffRecords.filter((record) => record.changeKind === "added").length,
    removedBlocks: diffRecords.filter((record) => record.changeKind === "removed").length,
    changedPlatforms: [...changedPlatforms],
    diffRecords,
  };
}
