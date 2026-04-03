import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { ArticlesPage } from "./articles-page";

const apiMocks = vi.hoisted(() => ({
  fetchStories: vi.fn(),
  fetchArticleVariants: vi.fn(),
  fetchPublishJobs: vi.fn(),
  publishArticle: vi.fn(),
  dispatchDuePublishJobs: vi.fn(),
  pollPublishJobs: vi.fn(),
  retryPublishJob: vi.fn(),
  writePublishJobFeedback: vi.fn(),
  writePublishJobResult: vi.fn(),
  formatSectionLabel: vi.fn((value: string) => value),
}));

const editorialApiMocks = vi.hoisted(() => ({
  fetchWorkbenchArticles: vi.fn(),
  fetchArticleBlocks: vi.fn(),
  fetchArticleRevisions: vi.fn(),
  fetchDigestTemplates: vi.fn(),
  fetchEditorialActions: vi.fn(),
  generateWorkbenchArticle: vi.fn(),
  rebuildWorkbenchArticle: vi.fn(),
  restoreWorkbenchRevision: vi.fn(),
  updateArticleBlock: vi.fn(),
}));

vi.mock("../../lib/api", () => ({
  ...apiMocks,
}));

vi.mock("../../lib/editorial-api", () => ({
  ...editorialApiMocks,
}));

const queryClients: QueryClient[] = [];

const WORKBENCH_ARTICLE = {
  id: 1,
  periodType: "weekly",
  targetDate: "2026-04-03",
  title: "Weekly Digest",
  summary: "Workbench summary",
  body: "Intro\n\nBody A\n\nBody B",
  storyIds: [101, 102],
  storyKeys: ["story-101", "story-102"],
  sections: ["research", "open_source"],
  generationNote: "Keep research first.",
  templateId: 11,
  templateName: "Weekly Default",
  activeRevisionId: 51,
  blockCount: 5,
  sectionPlan: [
    {
      sectionKey: "research",
      sectionLabel: "Research",
      targetRatio: 0.6,
      storyCount: 1,
      storyIds: [101],
    },
    {
      sectionKey: "open_source",
      sectionLabel: "Open Source",
      targetRatio: 0.4,
      storyCount: 1,
      storyIds: [102],
    },
  ],
  blocks: [],
  status: "ready",
  storyCount: 2,
  variantCount: 1,
  createdAt: "2026-04-03T09:00:00Z",
  updatedAt: "2026-04-03T09:30:00Z",
};

function renderPage(): void {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false, gcTime: 0, refetchOnWindowFocus: false },
      mutations: { retry: false, gcTime: 0 },
    },
  });
  queryClients.push(queryClient);

  render(
    <QueryClientProvider client={queryClient}>
      <ArticlesPage health="FetchNews | ok" />
    </QueryClientProvider>,
  );
}

describe("ArticlesPage", () => {
  afterEach(() => {
    cleanup();
    while (queryClients.length > 0) {
      queryClients.pop()?.clear();
    }
  });

  beforeEach(() => {
    apiMocks.fetchStories.mockResolvedValue([
      {
        id: 101,
        status: "approved",
        storyKey: "story-101",
        clusterTitle: "Research block A",
        summary: "Story A summary",
        highlights: ["A"],
        sourceLinks: ["https://example.com/story-101"],
        tags: ["research"],
        riskFlags: [],
        score: 9.4,
        itemCount: 1,
        firstSeenAt: "2026-04-03T08:00:00Z",
        lastSeenAt: "2026-04-03T08:00:00Z",
        primarySection: "research",
        sections: ["research"],
      },
      {
        id: 102,
        status: "approved",
        storyKey: "story-102",
        clusterTitle: "Open source block B",
        summary: "Story B summary",
        highlights: ["B"],
        sourceLinks: ["https://example.com/story-102"],
        tags: ["open_source"],
        riskFlags: [],
        score: 8.8,
        itemCount: 1,
        firstSeenAt: "2026-04-03T09:00:00Z",
        lastSeenAt: "2026-04-03T09:00:00Z",
        primarySection: "open_source",
        sections: ["open_source"],
      },
    ]);
    apiMocks.fetchArticleVariants.mockResolvedValue([]);
    apiMocks.fetchPublishJobs.mockResolvedValue([]);
    apiMocks.publishArticle.mockResolvedValue([]);
    apiMocks.dispatchDuePublishJobs.mockResolvedValue({ jobsDispatched: 0, jobsFailed: 0 });
    apiMocks.pollPublishJobs.mockResolvedValue({ jobsPolled: 0, jobsCompleted: 0, jobsFailed: 0 });
    apiMocks.retryPublishJob.mockResolvedValue({});
    apiMocks.writePublishJobFeedback.mockResolvedValue({});
    apiMocks.writePublishJobResult.mockResolvedValue({});

    editorialApiMocks.fetchWorkbenchArticles.mockResolvedValue([WORKBENCH_ARTICLE]);
    editorialApiMocks.fetchDigestTemplates.mockResolvedValue([
      {
        id: 11,
        name: "Weekly Default",
        periodType: "weekly",
        description: "Template for weekly digest",
        sectionQuotas: { research: 0.6, open_source: 0.4 },
        sectionOrder: ["research", "open_source"],
        defaultPlatformTemplates: {
          wechat: "editorial_summary",
          x: "discussion_hook",
        },
        isDefault: true,
        createdAt: "2026-04-03T08:00:00Z",
        updatedAt: "2026-04-03T08:00:00Z",
      },
    ]);
    editorialApiMocks.fetchArticleBlocks.mockResolvedValue([
      {
        id: 201,
        articleId: 1,
        revisionId: 51,
        blockKey: "title",
        blockType: "title",
        sectionKey: null,
        platformScope: null,
        storyId: null,
        title: null,
        content: "Weekly Digest",
        sortOrder: 10,
        isLocked: false,
        isManual: false,
        payload: {},
        updatedAt: "2026-04-03T09:30:00Z",
      },
      {
        id: 202,
        articleId: 1,
        revisionId: 51,
        blockKey: "story-101",
        blockType: "story_paragraph",
        sectionKey: "research",
        platformScope: null,
        storyId: 101,
        title: "Research block A",
        content: "Story A summary",
        sortOrder: 100,
        isLocked: false,
        isManual: false,
        payload: {},
        updatedAt: "2026-04-03T09:30:00Z",
      },
      {
        id: 204,
        articleId: 1,
        revisionId: 51,
        blockKey: "story-102",
        blockType: "story_paragraph",
        sectionKey: "open_source",
        platformScope: null,
        storyId: 102,
        title: "Open source block B",
        content: "Story B summary",
        sortOrder: 110,
        isLocked: false,
        isManual: false,
        payload: {},
        updatedAt: "2026-04-03T09:30:00Z",
      },
      {
        id: 203,
        articleId: 1,
        revisionId: 51,
        blockKey: "platform-wechat",
        blockType: "platform_body",
        sectionKey: null,
        platformScope: "wechat",
        storyId: null,
        title: null,
        content: "WeChat copy",
        sortOrder: 200,
        isLocked: false,
        isManual: false,
        payload: {},
        updatedAt: "2026-04-03T09:30:00Z",
      },
    ]);
    editorialApiMocks.fetchArticleRevisions.mockResolvedValue([
      {
        id: 51,
        articleId: 1,
        versionNumber: 1,
        changeType: "generate",
        changeNote: null,
        templateId: 11,
        snapshot: {
          blocks: [
            { block_key: "title", content: "Weekly Digest", title: null, is_locked: false },
            { block_key: "story-101", content: "Story A summary", title: "Research block A", is_locked: false },
          ],
        },
        createdByUserId: 1,
        createdAt: "2026-04-03T09:30:00Z",
      },
      {
        id: 52,
        articleId: 1,
        versionNumber: 2,
        changeType: "rebuild",
        changeNote: "mixed",
        templateId: 11,
        snapshot: {
          blocks: [
            { block_key: "title", content: "Weekly Digest rebuilt", title: null, is_locked: false },
            { block_key: "story-101", content: "Rebuilt body", title: "Research block A", is_locked: false },
          ],
        },
        createdByUserId: 1,
        createdAt: "2026-04-03T10:00:00Z",
      },
    ]);
    editorialApiMocks.fetchEditorialActions.mockResolvedValue([
      {
        id: 601,
        articleId: 1,
        revisionId: 51,
        actorUserId: 1,
        actionType: "edit_block",
        targetType: "article_block",
        targetId: "202",
        detail: { changed_fields: { title: true } },
        createdAt: "2026-04-03T10:10:00Z",
      },
    ]);
    editorialApiMocks.generateWorkbenchArticle.mockResolvedValue(WORKBENCH_ARTICLE);
    editorialApiMocks.rebuildWorkbenchArticle.mockResolvedValue(WORKBENCH_ARTICLE);
    editorialApiMocks.restoreWorkbenchRevision.mockResolvedValue(WORKBENCH_ARTICLE);
    editorialApiMocks.updateArticleBlock.mockResolvedValue({});
  });

  it("renders the three-column editorial workbench", async () => {
    renderPage();

    expect(await screen.findByText("Strategy Rail")).toBeInTheDocument();
    expect(screen.getByText("Paragraph Composer")).toBeInTheDocument();
    expect(screen.getByText("History & Channels")).toBeInTheDocument();
    expect(screen.getByText("Weekly Digest")).toBeInTheDocument();
    expect(screen.getByDisplayValue("Weekly Default")).toBeInTheDocument();
  });

  it("saves a modified body block and restores a revision", async () => {
    const user = userEvent.setup();
    renderPage();

    const blockTitleInput = await screen.findByDisplayValue("Research block A");
    await user.clear(blockTitleInput);
    await user.type(blockTitleInput, "Research block A edited");
    await user.click(screen.getAllByRole("button", { name: "保存修改" })[0]);

    await waitFor(() => {
      expect(editorialApiMocks.updateArticleBlock).toHaveBeenCalledWith(
        1,
        202,
        expect.objectContaining({ title: "Research block A edited" }),
      );
    });

    await user.click(screen.getAllByRole("button", { name: "恢复为当前版本" })[0]);

    await waitFor(() => {
      expect(editorialApiMocks.restoreWorkbenchRevision).toHaveBeenCalledWith(1, 51);
    });
  });

  it("shows platform template strategy and can move a story block upward", async () => {
    const user = userEvent.setup();
    renderPage();

    expect(await screen.findByText("wechat · editorial_summary")).toBeInTheDocument();
    expect(screen.getByText("x · discussion_hook")).toBeInTheDocument();
    expect(screen.getByText("Template for weekly digest")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "move-up-204" }));

    await waitFor(() => {
      expect(editorialApiMocks.updateArticleBlock).toHaveBeenCalledWith(
        1,
        204,
        expect.objectContaining({ sortOrder: 95 }),
      );
    });
  });

  it("passes selected sections and template when triggering a partial rebuild", async () => {
    const user = userEvent.setup();
    renderPage();

    expect(await screen.findByText("按栏目局部重建")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Research · 1" }));
    await user.click(screen.getByRole("button", { name: "仅重建所选栏目" }));

    await waitFor(() => {
      expect(editorialApiMocks.rebuildWorkbenchArticle).toHaveBeenCalledWith(
        1,
        expect.objectContaining({
          mode: "mixed",
          templateId: 11,
          sectionKeys: ["research"],
        }),
      );
    });

    expect(screen.getByRole("link", { name: "打开历史明细页" })).toHaveAttribute(
      "href",
      "/articles/history?articleId=1&revisionId=51",
    );
  });
});
