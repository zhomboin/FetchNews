import { buildAuthorizedRequestInit } from "./api";
import type { ArticlePeriodType } from "./api";
import { getApiBase } from "./runtime-config";

const API_BASE = getApiBase();

type ApiArticleSectionPlan = {
  section_key: string;
  section_label: string;
  target_ratio: number | null;
  story_count: number;
  story_ids: number[];
};

type ApiArticleBlock = {
  id: number;
  article_id: number;
  revision_id: number;
  block_key: string;
  block_type: string;
  section_key: string | null;
  platform_scope: string | null;
  story_id: number | null;
  title: string | null;
  content: string;
  sort_order: number;
  is_locked: boolean;
  is_manual: boolean;
  payload: Record<string, unknown>;
  updated_at: string;
};

type ApiArticleRevision = {
  id: number;
  article_id: number;
  version_number: number;
  change_type: string;
  change_note: string | null;
  template_id: number | null;
  snapshot: Record<string, unknown>;
  created_by_user_id: number | null;
  created_at: string;
};

type ApiDigestTemplate = {
  id: number;
  name: string;
  period_type: string;
  description: string | null;
  section_quotas: Record<string, number>;
  section_order: string[];
  default_platform_templates: Record<string, string>;
  is_default: boolean;
  created_at: string;
  updated_at: string;
};

type ApiEditorialAction = {
  id: number;
  article_id: number;
  revision_id: number | null;
  actor_user_id: number | null;
  action_type: string;
  target_type: string;
  target_id: string | null;
  detail: Record<string, unknown>;
  created_at: string;
};

type ApiArticleDraft = {
  id: number;
  period_type: string;
  target_date: string;
  title: string;
  summary: string;
  body: string;
  story_ids: number[];
  story_keys: string[];
  sections: string[];
  generation_note: string | null;
  template_id: number | null;
  template_name: string | null;
  active_revision_id: number | null;
  block_count: number;
  section_plan: ApiArticleSectionPlan[];
  blocks: ApiArticleBlock[];
  status: string;
  story_count: number;
  variant_count: number;
  created_at: string;
  updated_at: string;
};

export type ArticleSectionPlanRecord = {
  sectionKey: string;
  sectionLabel: string;
  targetRatio: number | null;
  storyCount: number;
  storyIds: number[];
};

export type ArticleBlockRecord = {
  id: number;
  articleId: number;
  revisionId: number;
  blockKey: string;
  blockType: string;
  sectionKey: string | null;
  platformScope: string | null;
  storyId: number | null;
  title: string | null;
  content: string;
  sortOrder: number;
  isLocked: boolean;
  isManual: boolean;
  payload: Record<string, unknown>;
  updatedAt: string;
};

export type ArticleRevisionRecord = {
  id: number;
  articleId: number;
  versionNumber: number;
  changeType: string;
  changeNote: string | null;
  templateId: number | null;
  snapshot: Record<string, unknown>;
  createdByUserId: number | null;
  createdAt: string;
};

export type DigestTemplateRecord = {
  id: number;
  name: string;
  periodType: string;
  description: string | null;
  sectionQuotas: Record<string, number>;
  sectionOrder: string[];
  defaultPlatformTemplates: Record<string, string>;
  isDefault: boolean;
  createdAt: string;
  updatedAt: string;
};

export type EditorialActionRecord = {
  id: number;
  articleId: number;
  revisionId: number | null;
  actorUserId: number | null;
  actionType: string;
  targetType: string;
  targetId: string | null;
  detail: Record<string, unknown>;
  createdAt: string;
};

export type ArticleWorkbenchRecord = {
  id: number;
  periodType: ArticlePeriodType;
  targetDate: string;
  title: string;
  summary: string;
  body: string;
  storyIds: number[];
  storyKeys: string[];
  sections: string[];
  generationNote: string | null;
  templateId: number | null;
  templateName: string | null;
  activeRevisionId: number | null;
  blockCount: number;
  sectionPlan: ArticleSectionPlanRecord[];
  blocks: ArticleBlockRecord[];
  status: string;
  storyCount: number;
  variantCount: number;
  createdAt: string;
  updatedAt: string;
};

export type GenerateWorkbenchArticlePayload = {
  periodType: ArticlePeriodType;
  targetDate: string;
  storyIds?: number[];
  generationNote?: string;
  templateId?: number | null;
};

export type ArticleBlockUpdatePayload = {
  content?: string;
  title?: string;
  isLocked?: boolean;
  sortOrder?: number;
};

export type ArticleRebuildMode = "mixed" | "force_full";

export type ArticleRebuildPayload = {
  mode: ArticleRebuildMode;
  templateId?: number | null;
  sectionKeys?: string[];
};

async function requestJson<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, buildAuthorizedRequestInit(init));
  if (!response.ok) {
    throw new Error(`Request failed: ${response.status}`);
  }
  return response.json() as Promise<T>;
}

function mapArticleSectionPlan(apiPlan: ApiArticleSectionPlan): ArticleSectionPlanRecord {
  return {
    sectionKey: apiPlan.section_key,
    sectionLabel: apiPlan.section_label,
    targetRatio: apiPlan.target_ratio,
    storyCount: apiPlan.story_count,
    storyIds: apiPlan.story_ids,
  };
}

function mapArticleBlock(apiBlock: ApiArticleBlock): ArticleBlockRecord {
  return {
    id: apiBlock.id,
    articleId: apiBlock.article_id,
    revisionId: apiBlock.revision_id,
    blockKey: apiBlock.block_key,
    blockType: apiBlock.block_type,
    sectionKey: apiBlock.section_key,
    platformScope: apiBlock.platform_scope,
    storyId: apiBlock.story_id,
    title: apiBlock.title,
    content: apiBlock.content,
    sortOrder: apiBlock.sort_order,
    isLocked: apiBlock.is_locked,
    isManual: apiBlock.is_manual,
    payload: apiBlock.payload,
    updatedAt: apiBlock.updated_at,
  };
}

function mapArticleRevision(apiRevision: ApiArticleRevision): ArticleRevisionRecord {
  return {
    id: apiRevision.id,
    articleId: apiRevision.article_id,
    versionNumber: apiRevision.version_number,
    changeType: apiRevision.change_type,
    changeNote: apiRevision.change_note,
    templateId: apiRevision.template_id,
    snapshot: apiRevision.snapshot,
    createdByUserId: apiRevision.created_by_user_id,
    createdAt: apiRevision.created_at,
  };
}

function mapDigestTemplate(apiTemplate: ApiDigestTemplate): DigestTemplateRecord {
  return {
    id: apiTemplate.id,
    name: apiTemplate.name,
    periodType: apiTemplate.period_type,
    description: apiTemplate.description,
    sectionQuotas: apiTemplate.section_quotas,
    sectionOrder: apiTemplate.section_order,
    defaultPlatformTemplates: apiTemplate.default_platform_templates,
    isDefault: apiTemplate.is_default,
    createdAt: apiTemplate.created_at,
    updatedAt: apiTemplate.updated_at,
  };
}

function mapEditorialAction(apiAction: ApiEditorialAction): EditorialActionRecord {
  return {
    id: apiAction.id,
    articleId: apiAction.article_id,
    revisionId: apiAction.revision_id,
    actorUserId: apiAction.actor_user_id,
    actionType: apiAction.action_type,
    targetType: apiAction.target_type,
    targetId: apiAction.target_id,
    detail: apiAction.detail,
    createdAt: apiAction.created_at,
  };
}

function mapArticleWorkbench(apiArticle: ApiArticleDraft): ArticleWorkbenchRecord {
  return {
    id: apiArticle.id,
    periodType: apiArticle.period_type as ArticlePeriodType,
    targetDate: apiArticle.target_date,
    title: apiArticle.title,
    summary: apiArticle.summary,
    body: apiArticle.body,
    storyIds: apiArticle.story_ids,
    storyKeys: apiArticle.story_keys,
    sections: apiArticle.sections,
    generationNote: apiArticle.generation_note,
    templateId: apiArticle.template_id,
    templateName: apiArticle.template_name,
    activeRevisionId: apiArticle.active_revision_id,
    blockCount: apiArticle.block_count,
    sectionPlan: apiArticle.section_plan.map(mapArticleSectionPlan),
    blocks: apiArticle.blocks.map(mapArticleBlock),
    status: apiArticle.status,
    storyCount: apiArticle.story_count,
    variantCount: apiArticle.variant_count,
    createdAt: apiArticle.created_at,
    updatedAt: apiArticle.updated_at,
  };
}

/**
 * 加载带工作台元数据的稿件列表。
 */
export async function fetchWorkbenchArticles(): Promise<ArticleWorkbenchRecord[]> {
  const apiArticles = await requestJson<ApiArticleDraft[]>("/articles");
  return apiArticles.map(mapArticleWorkbench);
}

/**
 * 加载周报/月报模板列表。
 */
export async function fetchDigestTemplates(): Promise<DigestTemplateRecord[]> {
  const apiTemplates = await requestJson<ApiDigestTemplate[]>("/templates/digests");
  return apiTemplates.map(mapDigestTemplate);
}

/**
 * 统一生成或重建指定周期的稿件。
 */
export async function generateWorkbenchArticle(
  payload: GenerateWorkbenchArticlePayload,
): Promise<ArticleWorkbenchRecord> {
  const apiArticle = await requestJson<ApiArticleDraft>("/articles/generate", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      period_type: payload.periodType,
      target_date: payload.targetDate,
      story_ids: payload.storyIds,
      generation_note: payload.generationNote,
      template_id: payload.templateId ?? undefined,
    }),
  });
  return mapArticleWorkbench(apiArticle);
}

/**
 * 加载稿件当前激活版本的块数据。
 */
export async function fetchArticleBlocks(articleId: number): Promise<ArticleBlockRecord[]> {
  const apiBlocks = await requestJson<ApiArticleBlock[]>(`/articles/${articleId}/blocks`);
  return apiBlocks.map(mapArticleBlock);
}

/**
 * 加载稿件的版本历史。
 */
export async function fetchArticleRevisions(articleId: number): Promise<ArticleRevisionRecord[]> {
  const apiRevisions = await requestJson<ApiArticleRevision[]>(`/articles/${articleId}/revisions`);
  return apiRevisions.map(mapArticleRevision);
}

/**
 * 加载稿件的人工干预历史。
 */
export async function fetchEditorialActions(articleId: number): Promise<EditorialActionRecord[]> {
  const apiActions = await requestJson<ApiEditorialAction[]>(`/articles/${articleId}/editorial-actions`);
  return apiActions.map(mapEditorialAction);
}

/**
 * 更新一个正文块或平台块。
 */
export async function updateArticleBlock(
  articleId: number,
  blockId: number,
  payload: ArticleBlockUpdatePayload,
): Promise<ArticleBlockRecord> {
  const apiBlock = await requestJson<ApiArticleBlock>(`/articles/${articleId}/blocks/${blockId}`, {
    method: "PATCH",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      content: payload.content,
      title: payload.title,
      is_locked: payload.isLocked,
      sort_order: payload.sortOrder,
    }),
  });
  return mapArticleBlock(apiBlock);
}

/**
 * 对当前稿件执行混合或全量重建。
 */
export async function rebuildWorkbenchArticle(
  articleId: number,
  payload: ArticleRebuildPayload,
): Promise<ArticleWorkbenchRecord> {
  const apiArticle = await requestJson<ApiArticleDraft>(`/articles/${articleId}/rebuild`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      mode: payload.mode,
      template_id: payload.templateId ?? undefined,
      section_keys: payload.sectionKeys,
    }),
  });
  return mapArticleWorkbench(apiArticle);
}

/**
 * 从历史版本创建一个新的当前版本。
 */
export async function restoreWorkbenchRevision(
  articleId: number,
  revisionId: number,
): Promise<ArticleWorkbenchRecord> {
  const apiArticle = await requestJson<ApiArticleDraft>(`/articles/${articleId}/revisions/${revisionId}/restore`, {
    method: "POST",
  });
  return mapArticleWorkbench(apiArticle);
}
