import React from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { PageHeader } from "../../components/console";
import {
  dispatchDuePublishJobs,
  fetchArticleVariants,
  fetchPublishJobs,
  fetchStories,
  pollPublishJobs,
  publishArticle,
  retryPublishJob,
  writePublishJobFeedback,
  writePublishJobResult,
} from "../../lib/api";
import {
  fetchArticleBlocks,
  fetchArticleRevisions,
  fetchDigestTemplates,
  fetchEditorialActions,
  fetchWorkbenchArticles,
  generateWorkbenchArticle,
  rebuildWorkbenchArticle,
  restoreWorkbenchRevision,
  updateArticleBlock,
} from "../../lib/editorial-api";
import type {
  ArticleBlockRecord,
  ArticleRebuildPayload,
  ArticleWorkbenchRecord,
  DigestTemplateRecord,
} from "../../lib/editorial-api";
import { ArticleComposer } from "./article-composer";
import { ArticleHistoryPanel } from "./article-history-panel";
import { ArticleStrategyRail } from "./article-strategy-rail";
import type {
  BlockDraftRecord,
  BlockDraftState,
  PublishFeedbackField,
  PublishFeedbackFormState,
  ScopeMode,
} from "./article-editor-types";
import { buildBlockDraftState, buildRevisionDiffSummary, hasBlockDraftChanges } from "./article-editor-types";

const ARTICLES_QUERY_KEY = ["workbenchArticles"] as const;
const STORIES_QUERY_KEY = ["stories"] as const;
const TEMPLATES_QUERY_KEY = ["digestTemplates"] as const;
const PUBLISH_JOBS_QUERY_KEY = ["publishJobs"] as const;
const ARTICLE_VARIANTS_QUERY_KEY = (articleId: number | null) => ["articleVariants", articleId] as const;
const ARTICLE_BLOCKS_QUERY_KEY = (articleId: number | null) => ["articleBlocks", articleId] as const;
const ARTICLE_REVISIONS_QUERY_KEY = (articleId: number | null) => ["articleRevisions", articleId] as const;
const EDITORIAL_ACTIONS_QUERY_KEY = (articleId: number | null) => ["editorialActions", articleId] as const;
const ARTICLE_REFRESH_INTERVAL_MS = 30_000;
const ARTICLE_REFRESH_INTERVAL = globalThis.navigator?.userAgent?.includes("jsdom") ? false : ARTICLE_REFRESH_INTERVAL_MS;
const MANUAL_FAILURE_MESSAGE = "人工审核标记失败，等待重新入队。";

type ArticlesPageProps = {
  health: string;
};

type PublishFeedbackPayload = {
  impressions?: number;
  opens?: number;
  clicks?: number;
  interactions?: number;
};

function getTodayDateInput(): string {
  const now = new Date();
  const year = now.getFullYear();
  const month = `${now.getMonth() + 1}`.padStart(2, "0");
  const day = `${now.getDate()}`.padStart(2, "0");
  return `${year}-${month}-${day}`;
}

function getDefaultScheduleInput(): string {
  const next = new Date();
  next.setMinutes(next.getMinutes() + 30);
  const year = next.getFullYear();
  const month = `${next.getMonth() + 1}`.padStart(2, "0");
  const day = `${next.getDate()}`.padStart(2, "0");
  const hour = `${next.getHours()}`.padStart(2, "0");
  const minute = `${next.getMinutes()}`.padStart(2, "0");
  return `${year}-${month}-${day}T${hour}:${minute}`;
}

function toUtcIsoString(value: string): string | null {
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return null;
  return parsed.toISOString();
}

function buildBlockDraft(block: ArticleBlockRecord): BlockDraftRecord {
  return {
    content: block.content,
    title: block.title ?? "",
    isLocked: block.isLocked,
  };
}

function findDefaultTemplateId(templates: DigestTemplateRecord[], periodType: ArticleWorkbenchRecord["periodType"]): number | null {
  const matchedTemplate = templates.find((template) => template.periodType === periodType && template.isDefault);
  return matchedTemplate?.id ?? null;
}

function parseOptionalMetric(value: string): number | undefined {
  const trimmed = value.trim();
  if (trimmed === "") return undefined;
  const parsed = Number(value);
  if (!Number.isFinite(parsed) || parsed < 0) return undefined;
  return Math.trunc(parsed);
}

function buildFeedbackPayload(state: PublishFeedbackFormState): PublishFeedbackPayload {
  return {
    impressions: parseOptionalMetric(state.impressions),
    opens: parseOptionalMetric(state.opens),
    clicks: parseOptionalMetric(state.clicks),
    interactions: parseOptionalMetric(state.interactions),
  };
}

function buildFeedbackFormState(job: { performanceMetrics: Record<string, number> }): PublishFeedbackFormState {
  return {
    impressions: `${job.performanceMetrics.impressions ?? ""}`,
    opens: `${job.performanceMetrics.opens ?? ""}`,
    clicks: `${job.performanceMetrics.clicks ?? ""}`,
    interactions: `${job.performanceMetrics.interactions ?? ""}`,
  };
}

export function ArticlesPage({ health }: ArticlesPageProps): React.JSX.Element {
  const queryClient = useQueryClient();
  const [periodType, setPeriodType] = React.useState<ArticleWorkbenchRecord["periodType"]>("daily");
  const [targetDate, setTargetDate] = React.useState(getTodayDateInput());
  const [selectedTemplateId, setSelectedTemplateId] = React.useState<number | null>(null);
  const [scopeMode, setScopeMode] = React.useState<ScopeMode>("allApproved");
  const [selectedStoryIds, setSelectedStoryIds] = React.useState<number[]>([]);
  const [generationNote, setGenerationNote] = React.useState("");
  const [selectedArticleId, setSelectedArticleId] = React.useState<number | null>(null);
  const [selectedRevisionId, setSelectedRevisionId] = React.useState<number | null>(null);
  const [pendingBlockId, setPendingBlockId] = React.useState<number | null>(null);
  const [blockDrafts, setBlockDrafts] = React.useState<BlockDraftState>({});
  const [selectedPlatforms, setSelectedPlatforms] = React.useState<string[]>(["wechat", "x", "telegram"]);
  const [scheduledFor, setScheduledFor] = React.useState(getDefaultScheduleInput());
  const [feedbackForms, setFeedbackForms] = React.useState<Record<number, PublishFeedbackFormState>>({});
  const [rebuildSectionKeys, setRebuildSectionKeys] = React.useState<string[]>([]);

  const articlesQuery = useQuery({
    queryKey: ARTICLES_QUERY_KEY,
    queryFn: fetchWorkbenchArticles,
    refetchInterval: ARTICLE_REFRESH_INTERVAL,
  });
  const storiesQuery = useQuery({
    queryKey: STORIES_QUERY_KEY,
    queryFn: fetchStories,
    refetchInterval: ARTICLE_REFRESH_INTERVAL,
  });
  const templatesQuery = useQuery({
    queryKey: TEMPLATES_QUERY_KEY,
    queryFn: fetchDigestTemplates,
  });
  const publishJobsQuery = useQuery({
    queryKey: PUBLISH_JOBS_QUERY_KEY,
    queryFn: fetchPublishJobs,
    refetchInterval: ARTICLE_REFRESH_INTERVAL,
  });
  const blocksQuery = useQuery({
    queryKey: ARTICLE_BLOCKS_QUERY_KEY(selectedArticleId),
    queryFn: () => fetchArticleBlocks(selectedArticleId ?? 0),
    enabled: selectedArticleId !== null,
    refetchInterval: ARTICLE_REFRESH_INTERVAL,
  });
  const revisionsQuery = useQuery({
    queryKey: ARTICLE_REVISIONS_QUERY_KEY(selectedArticleId),
    queryFn: () => fetchArticleRevisions(selectedArticleId ?? 0),
    enabled: selectedArticleId !== null,
    refetchInterval: ARTICLE_REFRESH_INTERVAL,
  });
  const editorialActionsQuery = useQuery({
    queryKey: EDITORIAL_ACTIONS_QUERY_KEY(selectedArticleId),
    queryFn: () => fetchEditorialActions(selectedArticleId ?? 0),
    enabled: selectedArticleId !== null,
    refetchInterval: ARTICLE_REFRESH_INTERVAL,
  });
  const variantsQuery = useQuery({
    queryKey: ARTICLE_VARIANTS_QUERY_KEY(selectedArticleId),
    queryFn: () => fetchArticleVariants(selectedArticleId ?? 0),
    enabled: selectedArticleId !== null,
    refetchInterval: ARTICLE_REFRESH_INTERVAL,
  });

  const articles = articlesQuery.data ?? [];
  const approvedStories = (storiesQuery.data ?? []).filter((story) => story.status === "approved");
  const templates = templatesQuery.data ?? [];
  const selectedArticle = articles.find((article) => article.id === selectedArticleId) ?? null;
  const selectedTemplate = templates.find((template) => template.id === selectedTemplateId) ?? null;
  const blocks = blocksQuery.data ?? [];
  const revisions = revisionsQuery.data ?? [];
  const editorialActions = editorialActionsQuery.data ?? [];
  const variants = variantsQuery.data ?? [];
  const publishJobs = (publishJobsQuery.data ?? [])
    .filter((job) => job.articleId === selectedArticleId)
    .sort((left, right) => new Date(right.scheduledFor).getTime() - new Date(left.scheduledFor).getTime());
  const currentRevision = revisions.find((revision) => revision.id === selectedRevisionId) ?? null;
  const revisionDiffSummary = buildRevisionDiffSummary(currentRevision, blocks);
  const articleSectionKeys = selectedArticle?.sectionPlan.map((plan) => plan.sectionKey) ?? [];

  function invalidateArticleWorkspace(articleId: number | null = selectedArticleId): void {
    void queryClient.invalidateQueries({ queryKey: ARTICLES_QUERY_KEY });
    void queryClient.invalidateQueries({ queryKey: PUBLISH_JOBS_QUERY_KEY });
    if (articleId !== null) {
      void queryClient.invalidateQueries({ queryKey: ARTICLE_BLOCKS_QUERY_KEY(articleId) });
      void queryClient.invalidateQueries({ queryKey: ARTICLE_REVISIONS_QUERY_KEY(articleId) });
      void queryClient.invalidateQueries({ queryKey: EDITORIAL_ACTIONS_QUERY_KEY(articleId) });
      void queryClient.invalidateQueries({ queryKey: ARTICLE_VARIANTS_QUERY_KEY(articleId) });
    }
  }

  React.useEffect(() => {
    if (articles.length === 0) {
      setSelectedArticleId(null);
      return;
    }
    if (selectedArticleId === null || !articles.some((article) => article.id === selectedArticleId)) {
      setSelectedArticleId(articles[0].id);
    }
  }, [articles, selectedArticleId]);

  React.useEffect(() => {
    if (selectedArticle === null) {
      return;
    }
    setPeriodType(selectedArticle.periodType);
    setTargetDate(selectedArticle.targetDate);
    setGenerationNote(selectedArticle.generationNote ?? "");
    setSelectedTemplateId(selectedArticle.templateId);
    setSelectedStoryIds(selectedArticle.storyIds.length > 0 ? selectedArticle.storyIds : []);
    setRebuildSectionKeys([]);
  }, [selectedArticle?.id]);

  React.useEffect(() => {
    if (templates.length === 0) {
      return;
    }
    if (periodType === "daily") {
      setSelectedTemplateId(null);
      return;
    }
    const visibleTemplateIds = templates.filter((template) => template.periodType === periodType).map((template) => template.id);
    if (selectedTemplateId === null || !visibleTemplateIds.includes(selectedTemplateId)) {
      setSelectedTemplateId(findDefaultTemplateId(templates, periodType));
    }
  }, [periodType, selectedTemplateId, templates]);

  React.useEffect(() => {
    if (scopeMode === "custom" && selectedStoryIds.length === 0 && approvedStories.length > 0) {
      setSelectedStoryIds(approvedStories.map((story) => story.id));
    }
  }, [approvedStories, scopeMode, selectedStoryIds.length]);

  React.useEffect(() => {
    setBlockDrafts(buildBlockDraftState(blocks));
  }, [blocks]);

  React.useEffect(() => {
    if (revisions.length === 0) {
      setSelectedRevisionId(null);
      return;
    }
    const activeRevisionId = selectedArticle?.activeRevisionId ?? revisions[revisions.length - 1]?.id ?? null;
    if (activeRevisionId !== null && !revisions.some((revision) => revision.id === selectedRevisionId)) {
      setSelectedRevisionId(activeRevisionId);
    }
  }, [revisions, selectedArticle?.activeRevisionId, selectedRevisionId]);

  const generateMutation = useMutation({
    mutationFn: () =>
      generateWorkbenchArticle({
        periodType,
        targetDate,
        storyIds: scopeMode === "custom" ? selectedStoryIds : undefined,
        generationNote: generationNote.trim() || undefined,
        templateId: selectedTemplateId,
      }),
    onSuccess: (article) => {
      setSelectedArticleId(article.id);
      invalidateArticleWorkspace(article.id);
    },
  });

  const rebuildMutation = useMutation({
    mutationFn: (payload: ArticleRebuildPayload) => rebuildWorkbenchArticle(selectedArticleId ?? 0, payload),
    onSuccess: (article) => {
      setSelectedArticleId(article.id);
      invalidateArticleWorkspace(article.id);
    },
  });

  const restoreMutation = useMutation({
    mutationFn: (revisionId: number) => restoreWorkbenchRevision(selectedArticleId ?? 0, revisionId),
    onSuccess: (article) => {
      setSelectedArticleId(article.id);
      invalidateArticleWorkspace(article.id);
    },
  });

  const updateBlockMutation = useMutation({
    mutationFn: ({
      blockId,
      payload,
    }: {
      blockId: number;
      payload: { content?: string; title?: string; isLocked?: boolean; sortOrder?: number };
    }) => updateArticleBlock(selectedArticleId ?? 0, blockId, payload),
    onSuccess: (_block, variables) => {
      setPendingBlockId(null);
      invalidateArticleWorkspace(selectedArticleId);
      const currentBlock = blocks.find((item) => item.id === variables.blockId);
      if (currentBlock) {
        setBlockDrafts((drafts) => ({
          ...drafts,
          [variables.blockId]: {
            content: variables.payload.content ?? currentBlock.content,
            title: variables.payload.title ?? currentBlock.title ?? "",
            isLocked: variables.payload.isLocked ?? currentBlock.isLocked,
          },
        }));
      }
    },
    onError: () => {
      setPendingBlockId(null);
    },
  });

  const publishMutation = useMutation({
    mutationFn: () => {
      const scheduledIso = toUtcIsoString(scheduledFor);
      if (selectedArticleId === null || scheduledIso === null) {
        throw new Error("invalid_publish_state");
      }
      return publishArticle(selectedArticleId, {
        platforms: selectedPlatforms,
        scheduledFor: scheduledIso,
      });
    },
    onSuccess: () => invalidateArticleWorkspace(),
  });

  const dispatchMutation = useMutation({
    mutationFn: dispatchDuePublishJobs,
    onSuccess: () => invalidateArticleWorkspace(),
  });

  const pollMutation = useMutation({
    mutationFn: pollPublishJobs,
    onSuccess: () => invalidateArticleWorkspace(),
  });

  const markPublishedMutation = useMutation({
    mutationFn: (jobId: number) => writePublishJobResult(jobId, { status: "published" }),
    onSuccess: () => invalidateArticleWorkspace(),
  });

  const markFailedMutation = useMutation({
    mutationFn: (jobId: number) => writePublishJobResult(jobId, { status: "failed", errorMessage: MANUAL_FAILURE_MESSAGE }),
    onSuccess: () => invalidateArticleWorkspace(),
  });

  const retryMutation = useMutation({
    mutationFn: retryPublishJob,
    onSuccess: () => invalidateArticleWorkspace(),
  });

  const feedbackMutation = useMutation({
    mutationFn: ({ jobId, state }: { jobId: number; state: PublishFeedbackFormState }) =>
      writePublishJobFeedback(jobId, buildFeedbackPayload(state)),
    onSuccess: () => invalidateArticleWorkspace(),
  });

  function buildRebuildPayload(mode: "mixed" | "force_full", sectionKeys?: string[]): ArticleRebuildPayload {
    return {
      mode,
      templateId: selectedTemplateId,
      sectionKeys: sectionKeys && sectionKeys.length > 0 ? sectionKeys : undefined,
    };
  }

  function toggleSelectedStory(storyId: number): void {
    setSelectedStoryIds((current) =>
      current.includes(storyId) ? current.filter((id) => id !== storyId) : [...current, storyId],
    );
  }

  function updateDraft(blockId: number, patch: Partial<BlockDraftRecord>): void {
    setBlockDrafts((drafts) => ({
      ...drafts,
      [blockId]: {
        ...(drafts[blockId] ?? buildBlockDraft(blocks.find((block) => block.id === blockId)!)),
        ...patch,
      },
    }));
  }

  function resetBlock(blockId: number): void {
    const block = blocks.find((item) => item.id === blockId);
    if (!block) {
      return;
    }
    setBlockDrafts((drafts) => ({
      ...drafts,
      [blockId]: buildBlockDraft(block),
    }));
  }

  function saveBlock(block: ArticleBlockRecord): void {
    const draft = blockDrafts[block.id] ?? buildBlockDraft(block);
    if (!hasBlockDraftChanges(block, draft)) {
      return;
    }
    setPendingBlockId(block.id);
    updateBlockMutation.mutate({
      blockId: block.id,
      payload: {
        content: draft.content !== block.content ? draft.content : undefined,
        title: draft.title !== (block.title ?? "") ? draft.title : undefined,
        isLocked: draft.isLocked !== block.isLocked ? draft.isLocked : undefined,
      },
    });
  }

  function toggleBlockLock(block: ArticleBlockRecord): void {
    const draft = blockDrafts[block.id] ?? buildBlockDraft(block);
    const nextLockState = !draft.isLocked;
    setPendingBlockId(block.id);
    setBlockDrafts((drafts) => ({
      ...drafts,
      [block.id]: {
        ...draft,
        isLocked: nextLockState,
      },
    }));
    updateBlockMutation.mutate({
      blockId: block.id,
      payload: { isLocked: nextLockState },
    });
  }

  function moveBlockUp(block: ArticleBlockRecord): void {
    const reorderableBlocks = blocks
      .filter((item) => item.platformScope === null && item.blockType === "story_paragraph")
      .sort((left, right) => left.sortOrder - right.sortOrder);
    const index = reorderableBlocks.findIndex((item) => item.id === block.id);
    if (index <= 0) {
      return;
    }
    const previousBlock = reorderableBlocks[index - 1];
    setPendingBlockId(block.id);
    updateBlockMutation.mutate({
      blockId: block.id,
      payload: { sortOrder: previousBlock.sortOrder - 5 },
    });
  }

  function moveBlockDown(block: ArticleBlockRecord): void {
    const reorderableBlocks = blocks
      .filter((item) => item.platformScope === null && item.blockType === "story_paragraph")
      .sort((left, right) => left.sortOrder - right.sortOrder);
    const index = reorderableBlocks.findIndex((item) => item.id === block.id);
    if (index === -1 || index >= reorderableBlocks.length - 1) {
      return;
    }
    const nextBlock = reorderableBlocks[index + 1];
    setPendingBlockId(block.id);
    updateBlockMutation.mutate({
      blockId: block.id,
      payload: { sortOrder: nextBlock.sortOrder + 5 },
    });
  }

  function toggleRebuildSection(sectionKey: string): void {
    if (!articleSectionKeys.includes(sectionKey)) {
      return;
    }
    setRebuildSectionKeys((current) =>
      current.includes(sectionKey) ? current.filter((item) => item !== sectionKey) : [...current, sectionKey],
    );
  }

  function togglePlatform(platform: string): void {
    setSelectedPlatforms((current) =>
      current.includes(platform) ? current.filter((item) => item !== platform) : [...current, platform],
    );
  }

  function updateFeedbackForm(jobId: number, field: PublishFeedbackField, value: string): void {
    setFeedbackForms((forms) => ({
      ...forms,
      [jobId]: {
        ...(forms[jobId] ?? { impressions: "", opens: "", clicks: "", interactions: "" }),
        [field]: value,
      },
    }));
  }

  function resetFeedback(jobId: number): void {
    const job = publishJobs.find((item) => item.id === jobId);
    if (!job) {
      return;
    }
    setFeedbackForms((forms) => ({
      ...forms,
      [jobId]: buildFeedbackFormState(job),
    }));
  }

  const platformBlocks = blocks.filter((block) => block.platformScope !== null);
  const canGenerate = scopeMode === "allApproved" ? approvedStories.length > 0 : selectedStoryIds.length > 0;
  const canPublish = selectedArticleId !== null && selectedPlatforms.length > 0 && toUtcIsoString(scheduledFor) !== null;
  const isJobActionPending =
    dispatchMutation.isPending ||
    pollMutation.isPending ||
    markPublishedMutation.isPending ||
    markFailedMutation.isPending ||
    retryMutation.isPending ||
    feedbackMutation.isPending;

  return (
    <div className="page-stack editorial-workbench-page">
      <PageHeader
        eyebrow="编辑工作台"
        title="三栏编辑工作台"
        lead="把模板策略、段落级人工干预、版本恢复和多平台分发放进一条可追溯的编辑链路里，确保系统生成与人工修改不会互相覆盖。"
        health={health}
      />

      <section className="editorial-workbench-grid">
        <ArticleStrategyRail
          health={health}
          periodType={periodType}
          onPeriodTypeChange={setPeriodType}
          targetDate={targetDate}
          onTargetDateChange={setTargetDate}
          selectedTemplateId={selectedTemplateId}
          onTemplateIdChange={setSelectedTemplateId}
          selectedTemplate={selectedTemplate}
          templates={templates}
          approvedStories={approvedStories}
          scopeMode={scopeMode}
          onScopeModeChange={setScopeMode}
          selectedStoryIds={selectedStoryIds}
          onToggleStory={toggleSelectedStory}
          generationNote={generationNote}
          onGenerationNoteChange={setGenerationNote}
          onGenerate={() => generateMutation.mutate()}
          isGenerating={generateMutation.isPending}
          canGenerate={canGenerate}
          selectedArticle={selectedArticle}
          articles={articles}
          selectedArticleId={selectedArticleId}
          onSelectArticle={setSelectedArticleId}
          rebuildSectionKeys={rebuildSectionKeys}
          onToggleRebuildSection={toggleRebuildSection}
          onClearRebuildSections={() => setRebuildSectionKeys([])}
          onRebuildMixed={() => rebuildMutation.mutate(buildRebuildPayload("mixed"))}
          onRebuildSelectedSections={() => rebuildMutation.mutate(buildRebuildPayload("mixed", rebuildSectionKeys))}
          onRebuildFull={() => rebuildMutation.mutate(buildRebuildPayload("force_full"))}
          isRebuilding={rebuildMutation.isPending}
        />

        <ArticleComposer
          article={selectedArticle}
          blocks={blocks}
          blockDrafts={blockDrafts}
          pendingBlockId={pendingBlockId}
          onDraftChange={updateDraft}
          onResetBlock={resetBlock}
          onSaveBlock={saveBlock}
          onToggleBlockLock={toggleBlockLock}
          onMoveBlockUp={moveBlockUp}
          onMoveBlockDown={moveBlockDown}
        />

        <ArticleHistoryPanel
          article={selectedArticle}
          revisions={revisions}
          selectedRevisionId={selectedRevisionId}
          onSelectRevision={setSelectedRevisionId}
          onRestoreRevision={(revisionId) => restoreMutation.mutate(revisionId)}
          restoringRevisionId={restoreMutation.isPending ? restoreMutation.variables ?? null : null}
          revisionDiffSummary={revisionDiffSummary}
          editorialActions={editorialActions}
          platformBlocks={platformBlocks}
          blockDrafts={blockDrafts}
          pendingBlockId={pendingBlockId}
          onDraftChange={updateDraft}
          onResetBlock={resetBlock}
          onSaveBlock={saveBlock}
          onToggleBlockLock={toggleBlockLock}
          variants={variants}
          publishJobs={publishJobs}
          selectedPlatforms={selectedPlatforms}
          onTogglePlatform={togglePlatform}
          scheduledFor={scheduledFor}
          onScheduledForChange={setScheduledFor}
          onCreatePublishJobs={() => publishMutation.mutate()}
          onDispatchPublishJobs={() => dispatchMutation.mutate()}
          onPollPublishJobs={() => pollMutation.mutate()}
          canPublish={canPublish}
          publishPending={publishMutation.isPending}
          dispatchPending={dispatchMutation.isPending}
          pollPending={pollMutation.isPending}
          onMarkPublished={(jobId) => markPublishedMutation.mutate(jobId)}
          onMarkFailed={(jobId) => markFailedMutation.mutate(jobId)}
          onRetryJob={(jobId) => retryMutation.mutate(jobId)}
          isJobActionPending={isJobActionPending}
          feedbackForms={feedbackForms}
          onFeedbackChange={updateFeedbackForm}
          onResetFeedback={(job) => resetFeedback(job.id)}
          onSaveFeedback={(jobId, state) => feedbackMutation.mutate({ jobId, state })}
          feedbackPending={feedbackMutation.isPending}
        />
      </section>
    </div>
  );
}
