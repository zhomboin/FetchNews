import { describe, expect, it, vi } from "vitest";

vi.mock("../../lib/api", () => ({
  formatSectionLabel: (value: string) => `栏目:${value}`,
}));

import {
  buildBlockDraftState,
  buildRevisionDiffSummary,
  formatPlatformLabel,
  hasBlockDraftChanges,
  resolveRevisionChangeLabel,
} from "./article-editor-types";

describe("article-editor-types", () => {
  it("builds block draft state and detects draft changes", () => {
    const blocks = [
      {
        id: 201,
        articleId: 1,
        revisionId: 51,
        blockKey: "story-101",
        blockType: "story_paragraph",
        sectionKey: "research",
        platformScope: null,
        storyId: 101,
        title: "Research block",
        content: "Original body",
        sortOrder: 100,
        isLocked: false,
        isManual: false,
        payload: {},
        updatedAt: "2026-04-03T09:30:00Z",
      },
    ];

    const drafts = buildBlockDraftState(blocks);

    expect(drafts[201]).toEqual({
      content: "Original body",
      title: "Research block",
      isLocked: false,
    });
    expect(hasBlockDraftChanges(blocks[0], drafts[201])).toBe(false);
    expect(
      hasBlockDraftChanges(blocks[0], {
        ...drafts[201],
        content: "Edited body",
      }),
    ).toBe(true);
  });

  it("summarizes revision diffs across changed, added, and removed blocks", () => {
    const revision = {
      id: 51,
      articleId: 1,
      versionNumber: 1,
      changeType: "generate",
      changeNote: null,
      templateId: 11,
      snapshot: {
        blocks: [
          {
            block_key: "title",
            block_type: "title",
            title: null,
            content: "Weekly Digest",
            is_locked: false,
            sort_order: 10,
          },
          {
            block_key: "wechat-body",
            block_type: "platform_body",
            platform_scope: "wechat",
            title: null,
            content: "Old WeChat body",
            is_locked: false,
            sort_order: 200,
          },
          {
            block_key: "removed-block",
            block_type: "story_paragraph",
            section_key: "research",
            title: "Removed block",
            content: "Removed body",
            is_locked: false,
            sort_order: 300,
          },
        ],
      },
      createdByUserId: 1,
      createdAt: "2026-04-03T09:30:00Z",
    };

    const activeBlocks = [
      {
        id: 201,
        articleId: 1,
        revisionId: 52,
        blockKey: "title",
        blockType: "title",
        sectionKey: null,
        platformScope: null,
        storyId: null,
        title: null,
        content: "Weekly Digest updated",
        sortOrder: 10,
        isLocked: false,
        isManual: false,
        payload: {},
        updatedAt: "2026-04-03T10:00:00Z",
      },
      {
        id: 202,
        articleId: 1,
        revisionId: 52,
        blockKey: "wechat-body",
        blockType: "platform_body",
        sectionKey: null,
        platformScope: "wechat",
        storyId: null,
        title: null,
        content: "New WeChat body",
        sortOrder: 200,
        isLocked: true,
        isManual: false,
        payload: {},
        updatedAt: "2026-04-03T10:00:00Z",
      },
      {
        id: 203,
        articleId: 1,
        revisionId: 52,
        blockKey: "new-block",
        blockType: "story_paragraph",
        sectionKey: "open_source",
        platformScope: null,
        storyId: 102,
        title: "New block",
        content: "New body",
        sortOrder: 250,
        isLocked: false,
        isManual: false,
        payload: {},
        updatedAt: "2026-04-03T10:00:00Z",
      },
    ];

    const summary = buildRevisionDiffSummary(revision, activeBlocks);

    expect(summary.changedBlocks).toBe(2);
    expect(summary.addedBlocks).toBe(1);
    expect(summary.removedBlocks).toBe(1);
    expect(summary.changedPlatforms).toEqual(["wechat"]);
    expect(summary.diffRecords.map((record) => record.changeKind)).toEqual([
      "changed",
      "changed",
      "added",
      "removed",
    ]);
    expect(summary.diffRecords[1]).toMatchObject({
      blockKey: "wechat-body",
      platformLabel: "微信",
    });
    expect(summary.diffRecords[2]).toMatchObject({
      blockKey: "new-block",
      sectionLabel: "栏目:open_source",
    });
  });

  it("formats platform and revision labels for the editorial UI", () => {
    expect(formatPlatformLabel("wechat")).toBe("微信");
    expect(formatPlatformLabel("x")).toBe("X");
    expect(resolveRevisionChangeLabel("rebuild")).toBe("混合重建");
  });
});
