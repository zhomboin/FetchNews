from __future__ import annotations

from collections import OrderedDict

from sqlalchemy import select
from sqlalchemy.orm import Session

from fetchnews.models import DigestTemplate
from fetchnews.pipeline.sections import get_section_label
from fetchnews.schemas import ArticleSectionPlanResponse, DigestTemplateResponse, StoryCandidate

DEFAULT_DIGEST_TEMPLATES: tuple[dict, ...] = (
    {
        'name': '\u9ed8\u8ba4\u5468\u62a5\u6a21\u677f',
        'period_type': 'weekly',
        'description': '\u5f3a\u8c03\u7814\u7a76\u3001\u5f00\u6e90\u548c\u4ea7\u54c1\u52a8\u6001\u7684\u5e73\u8861\u5468\u62a5\u6a21\u677f\u3002',
        'section_quotas': {
            'research': 0.35,
            'open_source': 0.3,
            'product_updates': 0.2,
            'community': 0.15,
        },
        'section_order': ['research', 'open_source', 'product_updates', 'community'],
        'default_platform_templates': {
            'wechat': 'editorial_summary',
            'x': 'tracking_hook',
            'telegram': 'quick_bulletin',
        },
        'is_default': True,
    },
    {
        'name': '\u9ed8\u8ba4\u6708\u62a5\u6a21\u677f',
        'period_type': 'monthly',
        'description': '\u5f3a\u8c03\u6708\u5ea6\u4e3b\u7ebf\u680f\u76ee\u4e0e\u8d8b\u52bf\u4fe1\u53f7\u7684\u7efc\u5408\u6708\u62a5\u6a21\u677f\u3002',
        'section_quotas': {
            'research': 0.3,
            'product_updates': 0.25,
            'open_source': 0.25,
            'community': 0.2,
        },
        'section_order': ['research', 'product_updates', 'open_source', 'community'],
        'default_platform_templates': {
            'wechat': 'actionable_roundup',
            'x': 'tracking_hook',
            'telegram': 'discussion_brief',
        },
        'is_default': True,
    },
)


def ensure_default_digest_templates(session: Session) -> None:
    existing_defaults = {
        (template.period_type, template.name)
        for template in session.scalars(select(DigestTemplate)).all()
    }
    for template_seed in DEFAULT_DIGEST_TEMPLATES:
        template_key = (template_seed['period_type'], template_seed['name'])
        if template_key in existing_defaults:
            continue
        session.add(DigestTemplate(**template_seed))



def list_digest_templates(session: Session) -> list[DigestTemplateResponse]:
    templates = session.scalars(
        select(DigestTemplate).order_by(DigestTemplate.period_type.asc(), DigestTemplate.id.asc())
    ).all()
    return [template_to_response(template) for template in templates]



def resolve_digest_template(
    session: Session,
    *,
    period_type: str,
    template_id: int | None,
) -> DigestTemplate | None:
    if template_id is not None:
        template = session.get(DigestTemplate, template_id)
        if template is None:
            raise ValueError('Digest template not found')
        if template.period_type != period_type:
            raise ValueError('Digest template period type does not match the requested article type')
        return template

    if period_type == 'daily':
        return None

    template = session.scalar(
        select(DigestTemplate)
        .where(DigestTemplate.period_type == period_type, DigestTemplate.is_default.is_(True))
        .order_by(DigestTemplate.id.asc())
    )
    if template is None:
        raise ValueError(f'No default digest template is configured for {period_type}')
    return template



def order_stories_by_template(
    stories: list[StoryCandidate],
    template: DigestTemplate | None,
) -> list[StoryCandidate]:
    if template is None or not template.section_order:
        return list(stories)

    grouped: OrderedDict[str, list[StoryCandidate]] = OrderedDict()
    for story in stories:
        grouped.setdefault(story.primary_section, []).append(story)

    ordered_sections = list(template.section_order)
    for section in grouped.keys():
        if section not in ordered_sections:
            ordered_sections.append(section)

    ordered_stories: list[StoryCandidate] = []
    while any(grouped.get(section) for section in ordered_sections):
        for section in ordered_sections:
            section_bucket = grouped.get(section)
            if section_bucket:
                ordered_stories.append(section_bucket.pop(0))
    return ordered_stories



def build_section_plan(
    stories: list[StoryCandidate],
    template: DigestTemplate | None,
) -> list[ArticleSectionPlanResponse]:
    grouped: OrderedDict[str, list[StoryCandidate]] = OrderedDict()
    for story in stories:
        grouped.setdefault(story.primary_section, []).append(story)

    ordered_sections: list[str] = []
    if template is not None:
        ordered_sections.extend(template.section_order)
    for section in grouped.keys():
        if section not in ordered_sections:
            ordered_sections.append(section)

    section_quotas = template.section_quotas if template is not None else {}
    plan: list[ArticleSectionPlanResponse] = []
    for section in ordered_sections:
        section_stories = grouped.get(section, [])
        if not section_stories and template is None:
            continue
        plan.append(
            ArticleSectionPlanResponse(
                section_key=section,
                section_label=get_section_label(section),
                target_ratio=float(section_quotas.get(section)) if section in section_quotas else None,
                story_count=len(section_stories),
                story_ids=[story.payload_story_id for story in section_stories if story.payload_story_id is not None],
            )
        )
    return plan



def template_to_response(template: DigestTemplate) -> DigestTemplateResponse:
    return DigestTemplateResponse(
        id=template.id,
        name=template.name,
        period_type=template.period_type,
        description=template.description,
        section_quotas=template.section_quotas,
        section_order=template.section_order,
        default_platform_templates=template.default_platform_templates,
        is_default=template.is_default,
        created_at=template.created_at,
        updated_at=template.updated_at,
    )