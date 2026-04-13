import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { StoriesPage } from "./stories-page";

const apiMocks = vi.hoisted(() => ({
  approveStory: vi.fn(),
  fetchNormalizedItems: vi.fn(),
  fetchStories: vi.fn(),
  formatSectionLabel: vi.fn((value: string) => value),
  rebuildStoriesPipeline: vi.fn(),
}));

vi.mock("../../lib/api", () => ({
  ...apiMocks,
}));

const queryClients: QueryClient[] = [];

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
      <StoriesPage health="FetchNews | ok" />
    </QueryClientProvider>,
  );
}

describe("StoriesPage", () => {
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
        status: "pending",
        storyKey: "story-101",
        clusterTitle: "Agent benchmark released",
        summary: "Research team shipped a new benchmark.",
        highlights: ["Includes evaluator templates"],
        sourceLinks: ["https://example.com/story-101"],
        tags: ["agents"],
        riskFlags: [],
        score: 9.4,
        itemCount: 3,
        firstSeenAt: "2026-04-13T08:00:00Z",
        lastSeenAt: "2026-04-13T09:00:00Z",
        primarySection: "agents",
        sections: ["agents"],
      },
      {
        id: 102,
        status: "pending",
        storyKey: "story-102",
        clusterTitle: "Open source release delayed",
        summary: "Only secondary sources have picked up the release note so far.",
        highlights: ["Still waiting for primary source"],
        sourceLinks: ["https://example.com/story-102"],
        tags: ["open_source"],
        riskFlags: ["secondary_sources_only"],
        score: 8.2,
        itemCount: 2,
        firstSeenAt: "2026-04-13T10:00:00Z",
        lastSeenAt: "2026-04-13T10:10:00Z",
        primarySection: "open_source",
        sections: ["open_source"],
      },
      {
        id: 103,
        status: "approved",
        storyKey: "story-103",
        clusterTitle: "Model release notes finalized",
        summary: "Release note now live on official blog.",
        highlights: ["Already approved"],
        sourceLinks: ["https://example.com/story-103"],
        tags: ["model_release"],
        riskFlags: [],
        score: 8.9,
        itemCount: 4,
        firstSeenAt: "2026-04-13T06:00:00Z",
        lastSeenAt: "2026-04-13T07:00:00Z",
        primarySection: "model_release",
        sections: ["model_release"],
      },
    ]);
    apiMocks.fetchNormalizedItems.mockResolvedValue([
      {
        rawItemId: 1,
        externalId: "item-1",
        sourceSlug: "openai-blog",
        sourcePriority: "P0",
        title: "OpenAI benchmark post",
        normalizedTitle: "OpenAI benchmark post",
        canonicalUrl: "https://example.com/item-1",
        language: "zh",
        keywords: ["agents"],
        tags: ["agents"],
        summary: "Normalized story item",
        author: "OpenAI",
        publishedAt: "2026-04-13T08:00:00Z",
      },
    ]);
    apiMocks.approveStory.mockResolvedValue({ id: 101, status: "approved" });
    apiMocks.rebuildStoriesPipeline.mockResolvedValue({ normalizedItems: 1, stories: 1 });
  });

  it("filters stories by risk state", async () => {
    const user = userEvent.setup();
    renderPage();

    expect(await screen.findByText("Agent benchmark released")).toBeInTheDocument();
    expect(screen.getByText("Open source release delayed")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "需复核" }));

    expect(screen.queryByText("Agent benchmark released")).not.toBeInTheDocument();
    expect(screen.getByText("Open source release delayed")).toBeInTheDocument();
  });

  it("approves selected pending stories in batch", async () => {
    const user = userEvent.setup();
    renderPage();

    expect(await screen.findByText("Agent benchmark released")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "选择 Agent benchmark released" }));
    await user.click(screen.getByRole("button", { name: "选择 Open source release delayed" }));
    await user.click(screen.getByRole("button", { name: "批量标记为已审核" }));

    await waitFor(() => {
      expect(apiMocks.approveStory).toHaveBeenCalledTimes(2);
    });
    expect(apiMocks.approveStory).toHaveBeenNthCalledWith(1, 101);
    expect(apiMocks.approveStory).toHaveBeenNthCalledWith(2, 102);
    expect(await screen.findByText("已提交 2 条故事的审核操作。")).toBeInTheDocument();
  });

  it("shows an empty state when filters hide all stories", async () => {
    const user = userEvent.setup();
    renderPage();

    expect(await screen.findByText("Agent benchmark released")).toBeInTheDocument();

    await user.type(screen.getByPlaceholderText("按标题、摘要、栏目、标签、亮点或风险标记筛选"), "not-found");

    expect(screen.getByText("当前筛选条件下没有聚类故事，调整筛选后再试。")).toBeInTheDocument();
  });
});
