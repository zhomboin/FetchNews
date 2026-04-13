import React from "react";

import { formatSectionLabel } from "../../lib/api";
import type { ArticlePeriodType, StoryRecord } from "../../lib/api";
import type { ArticleSectionPlanRecord, ArticleWorkbenchRecord, DigestTemplateRecord } from "../../lib/editorial-api";
import type { ScopeMode } from "./article-editor-types";

type ArticleStrategyRailProps = {
  health: string;
  periodType: ArticlePeriodType;
  onPeriodTypeChange: (periodType: ArticlePeriodType) => void;
  targetDate: string;
  onTargetDateChange: (targetDate: string) => void;
  selectedTemplateId: number | null;
  onTemplateIdChange: (templateId: number | null) => void;
  selectedTemplate: DigestTemplateRecord | null;
  templates: DigestTemplateRecord[];
  approvedStories: StoryRecord[];
  scopeMode: ScopeMode;
  onScopeModeChange: (mode: ScopeMode) => void;
  selectedStoryIds: number[];
  onToggleStory: (storyId: number) => void;
  generationNote: string;
  onGenerationNoteChange: (generationNote: string) => void;
  onGenerate: () => void;
  isGenerating: boolean;
  canGenerate: boolean;
  selectedArticle: ArticleWorkbenchRecord | null;
  articles: ArticleWorkbenchRecord[];
  selectedArticleId: number | null;
  onSelectArticle: (articleId: number) => void;
  rebuildSectionKeys: string[];
  onToggleRebuildSection: (sectionKey: string) => void;
  onClearRebuildSections: () => void;
  onRebuildMixed: () => void;
  onRebuildSelectedSections: () => void;
  onRebuildFull: () => void;
  isRebuilding: boolean;
};

const PERIOD_OPTIONS = [
  { value: "daily", label: "日报", hint: "聚焦当天已审核资讯，快速形成审校初稿。" },
  { value: "weekly", label: "周报", hint: "按模板配额梳理一周栏目结构和重点脉络。" },
  { value: "monthly", label: "月报", hint: "更强调主题沉淀、栏目轮值和趋势回顾。" },
] as const satisfies ReadonlyArray<{ value: ArticlePeriodType; label: string; hint: string }>;

const PLATFORM_TEMPLATE_LABELS: Record<string, string> = {
  editorial_summary: "编辑摘要型，适合微信长文导读和栏目提要。",
  actionable_roundup: "行动摘要型，更强调结论、要点和跟进建议。",
  tracking_hook: "追踪钩子型，适合 X 的讨论开头和追问式 CTA。",
  discussion_hook: "讨论引导型，优先抛出争议点和跟进问题。",
  quick_bulletin: "速览简报型，偏向 Telegram 的紧凑清单。",
  discussion_brief: "讨论快报型，适合 Telegram 的互动续读。",
};

function resolvePeriodLabel(periodType: ArticlePeriodType): string {
  if (periodType === "weekly") return "周报";
  if (periodType === "monthly") return "月报";
  return "日报";
}

function buildTemplateSummary(sectionPlan: ArticleSectionPlanRecord[]): string {
  if (sectionPlan.length === 0) {
    return "当前周期没有附加模板配额，系统将按基础排序生成。";
  }
  return sectionPlan
    .map((plan) => `${plan.sectionLabel}${plan.targetRatio === null ? "" : ` ${Math.round(plan.targetRatio * 100)}%`}`)
    .join(" / ");
}

function buildPlatformTemplateEntries(selectedTemplate: DigestTemplateRecord | null): Array<[string, string]> {
  if (selectedTemplate === null) {
    return [];
  }
  return Object.entries(selectedTemplate.defaultPlatformTemplates);
}

export function ArticleStrategyRail({
  health,
  periodType,
  onPeriodTypeChange,
  targetDate,
  onTargetDateChange,
  selectedTemplateId,
  onTemplateIdChange,
  selectedTemplate,
  templates,
  approvedStories,
  scopeMode,
  onScopeModeChange,
  selectedStoryIds,
  onToggleStory,
  generationNote,
  onGenerationNoteChange,
  onGenerate,
  isGenerating,
  canGenerate,
  selectedArticle,
  articles,
  selectedArticleId,
  onSelectArticle,
  rebuildSectionKeys,
  onToggleRebuildSection,
  onClearRebuildSections,
  onRebuildMixed,
  onRebuildSelectedSections,
  onRebuildFull,
  isRebuilding,
}: ArticleStrategyRailProps): React.JSX.Element {
  const visibleTemplates = templates.filter((template) => template.periodType === periodType);
  const templateSectionPlan = selectedArticle?.sectionPlan ?? [];
  const platformTemplateEntries = buildPlatformTemplateEntries(selectedTemplate);
  const canRebuildSelectedSections = selectedArticle !== null && rebuildSectionKeys.length > 0 && !isRebuilding;

  return (
    <section className="panel editorial-workbench-rail">
      <header className="section-title editorial-section-title">
        <div>
          <p>策略侧栏</p>
          <h2>编辑策略</h2>
        </div>
        <span>{health}</span>
      </header>

      <div className="editorial-period-stack">
        {PERIOD_OPTIONS.map((option) => (
          <button
            key={option.value}
            type="button"
            className={`period-option ${periodType === option.value ? "active" : ""}`}
            onClick={() => onPeriodTypeChange(option.value)}
          >
            <strong>{option.label}</strong>
            <span>{option.hint}</span>
          </button>
        ))}
      </div>

      <label className="field-shell">
        <span>目标日期</span>
        <input type="date" value={targetDate} onChange={(event) => onTargetDateChange(event.target.value)} />
      </label>

      <label className="field-shell">
        <span>模板策略</span>
        <select
          className="editorial-select"
          value={selectedTemplateId ?? ""}
          onChange={(event) => onTemplateIdChange(event.target.value === "" ? null : Number(event.target.value))}
        >
          <option value="">系统默认</option>
          {visibleTemplates.map((template) => (
            <option key={template.id} value={template.id}>
              {template.name}
            </option>
          ))}
        </select>
      </label>

      <div className="editorial-template-panel">
        <div className="subsection-head">
          <strong>模板配额</strong>
          <span>{selectedTemplate?.name ?? selectedArticle?.templateName ?? resolvePeriodLabel(periodType)}</span>
        </div>
        <p className="article-note-copy">{selectedTemplate?.description ?? "当前周期将使用系统默认模板策略。"}</p>
        <p className="article-note-copy">{buildTemplateSummary(templateSectionPlan)}</p>
        <div className="pill-list section-pill-list compact-gap top-gap">
          {templateSectionPlan.map((plan) => (
            <span key={plan.sectionKey} className="section-badge section-badge-soft">
              {`${plan.sectionLabel} · ${plan.storyCount}`}
            </span>
          ))}
        </div>
      </div>

      <div className="editorial-template-panel">
        <div className="subsection-head">
          <strong>平台模板</strong>
          <span>{platformTemplateEntries.length} 条策略</span>
        </div>
        {platformTemplateEntries.length === 0 ? (
          <p className="article-note-copy">当前模板没有额外的平台偏好，将沿用系统默认平台文案策略。</p>
        ) : (
          <div className="editorial-template-list">
            {platformTemplateEntries.map(([platform, templateKey]) => (
              <article key={`${platform}-${templateKey}`} className="editorial-template-card">
                <strong>{`${platform} · ${templateKey}`}</strong>
                <p>{PLATFORM_TEMPLATE_LABELS[templateKey] ?? "沿用该平台的默认生成语气和结构。"}</p>
              </article>
            ))}
          </div>
        )}
      </div>

      <div className="filter-group">
        <p className="filter-caption">Story 范围</p>
        <div className="filter-chip-row">
          <button
            type="button"
            className={`filter-chip ${scopeMode === "allApproved" ? "active" : ""}`}
            onClick={() => onScopeModeChange("allApproved")}
          >
            全部已审核
          </button>
          <button
            type="button"
            className={`filter-chip ${scopeMode === "custom" ? "active" : ""}`}
            onClick={() => onScopeModeChange("custom")}
          >
            自定义范围
          </button>
        </div>
      </div>

      {scopeMode === "custom" ? (
        <div className="story-scope-panel editorial-story-scope-panel">
          <div className="story-scope-head">
            <strong>纳入本次生成的 stories</strong>
            <span>
              {selectedStoryIds.length} / {approvedStories.length}
            </span>
          </div>
          <div className="story-scope-list compact">
            {approvedStories.map((story) => (
              <button
                key={story.id}
                type="button"
                className={`story-scope-chip ${selectedStoryIds.includes(story.id) ? "selected" : ""}`}
                onClick={() => onToggleStory(story.id)}
              >
                <div className="story-scope-chip-copy">
                  <span>{story.clusterTitle}</span>
                  <small>{formatSectionLabel(story.primarySection)}</small>
                </div>
                <strong>{story.status === "approved" ? "已审" : "待审"}</strong>
              </button>
            ))}
          </div>
        </div>
      ) : null}

      <label className="field-shell article-note-field">
        <span>生成说明</span>
        <textarea
          rows={4}
          value={generationNote}
          onChange={(event) => onGenerationNoteChange(event.target.value)}
          placeholder="例如：强化研究进展与开源基础设施栏目，压缩社区转载内容。"
        />
      </label>

      {selectedArticle !== null && templateSectionPlan.length > 0 ? (
        <div className="editorial-template-panel">
          <div className="subsection-head">
            <strong>按栏目局部重建</strong>
            <button type="button" className="detail-link detail-link-soft" onClick={onClearRebuildSections}>
              清空选择
            </button>
          </div>
          <p className="article-note-copy">只重建未锁定且命中的栏目块，其他正文块、平台块和人工修改会继续保留。</p>
          <div className="filter-chip-row wrap-gap">
            {templateSectionPlan.map((plan) => (
              <button
                key={plan.sectionKey}
                type="button"
                className={`filter-chip ${rebuildSectionKeys.includes(plan.sectionKey) ? "active" : ""}`}
                onClick={() => onToggleRebuildSection(plan.sectionKey)}
              >
                {`${plan.sectionLabel} · ${plan.storyCount}`}
              </button>
            ))}
          </div>
          <button type="button" className="button-secondary top-gap" onClick={onRebuildSelectedSections} disabled={!canRebuildSelectedSections}>
            {isRebuilding ? "局部重建中..." : "仅重建所选栏目"}
          </button>
        </div>
      ) : null}

      <div className="action-row editorial-action-row">
        <button type="button" className="button-primary" onClick={onGenerate} disabled={!canGenerate || isGenerating}>
          {isGenerating ? "正在生成..." : "生成或覆盖当前稿件"}
        </button>
        <button type="button" className="button-secondary" onClick={onRebuildMixed} disabled={selectedArticle === null || isRebuilding}>
          {isRebuilding ? "重建中..." : "混合重建"}
        </button>
        <button type="button" className="button-secondary" onClick={onRebuildFull} disabled={selectedArticle === null || isRebuilding}>
          全量重建
        </button>
      </div>

      <div className="action-status">
        <span>
          {scopeMode === "allApproved"
            ? `将使用全部 ${approvedStories.length} 条已审核 stories。`
            : `将使用 ${selectedStoryIds.length} 条 stories 生成当前稿件。`}
        </span>
      </div>

      <div className="editorial-draft-list">
        <div className="subsection-head">
          <strong>稿件列表</strong>
          <span>{articles.length} 篇</span>
        </div>
        <div className="article-list editorial-article-list compact-gap">
          {articles.map((article) => (
            <button
              key={article.id}
              type="button"
              className={`article-row ${article.id === selectedArticleId ? "selected" : ""}`}
              onClick={() => onSelectArticle(article.id)}
            >
              <div className="article-row-topline">
                <p>{article.targetDate}</p>
                <div className="article-row-pills">
                  <span className="period-pill" data-period={article.periodType}>
                    {resolvePeriodLabel(article.periodType)}
                  </span>
                </div>
              </div>
              <h3>{article.title}</h3>
              <p>{article.summary}</p>
              <div className="pill-list section-pill-list compact-gap">
                {article.sections.map((section) => (
                  <span key={`${article.id}-${section}`} className="section-badge section-badge-soft">
                    {formatSectionLabel(section)}
                  </span>
                ))}
              </div>
            </button>
          ))}
        </div>
      </div>
    </section>
  );
}
