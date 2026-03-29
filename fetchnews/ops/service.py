from __future__ import annotations

from collections import defaultdict
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from fetchnews.models import ArticleDraft, ArticleStatus, IngestRun, IngestRunStatus, PublishJob, PublishJobStatus, Story, StoryStatus
from fetchnews.schemas import FailureGroupResponse, OpsSummaryResponse


def build_ops_summary(session: Session, now: datetime | None = None) -> OpsSummaryResponse:
    current_time = now or datetime.now(UTC)
    ingest_runs_total = session.scalar(select(func.count()).select_from(IngestRun)) or 0
    ingest_runs_failed = session.scalar(
        select(func.count())
        .select_from(IngestRun)
        .where(IngestRun.status.in_([IngestRunStatus.FAILED, IngestRunStatus.COMPLETED_WITH_ERRORS]))
    ) or 0
    items_ingested_total = session.scalar(select(func.coalesce(func.sum(IngestRun.items_ingested), 0))) or 0
    stories_total = session.scalar(select(func.count()).select_from(Story)) or 0
    stories_approved = session.scalar(
        select(func.count()).select_from(Story).where(Story.status == StoryStatus.APPROVED)
    ) or 0
    stories_pending = session.scalar(
        select(func.count()).select_from(Story).where(Story.status == StoryStatus.PENDING)
    ) or 0
    articles_total = session.scalar(select(func.count()).select_from(ArticleDraft)) or 0
    articles_ready = session.scalar(
        select(func.count())
        .select_from(ArticleDraft)
        .where(ArticleDraft.status.in_([ArticleStatus.READY, ArticleStatus.SCHEDULED]))
    ) or 0
    articles_published = session.scalar(
        select(func.count()).select_from(ArticleDraft).where(ArticleDraft.status == ArticleStatus.PUBLISHED)
    ) or 0
    articles_failed = session.scalar(
        select(func.count()).select_from(ArticleDraft).where(ArticleDraft.status == ArticleStatus.FAILED)
    ) or 0
    publish_jobs_total = session.scalar(select(func.count()).select_from(PublishJob)) or 0
    publish_jobs_scheduled = session.scalar(
        select(func.count()).select_from(PublishJob).where(PublishJob.status == PublishJobStatus.SCHEDULED)
    ) or 0
    publish_jobs_published = session.scalar(
        select(func.count()).select_from(PublishJob).where(PublishJob.status == PublishJobStatus.PUBLISHED)
    ) or 0
    publish_jobs_failed = session.scalar(
        select(func.count()).select_from(PublishJob).where(PublishJob.status == PublishJobStatus.FAILED)
    ) or 0
    terminal_jobs = publish_jobs_published + publish_jobs_failed
    publish_success_rate = publish_jobs_published / terminal_jobs if terminal_jobs else 0.0
    due_publish_jobs = session.scalar(
        select(func.count())
        .select_from(PublishJob)
        .where(PublishJob.status == PublishJobStatus.SCHEDULED)
        .where(PublishJob.scheduled_for <= current_time)
    ) or 0

    return OpsSummaryResponse(
        ingest_runs_total=ingest_runs_total,
        ingest_runs_failed=ingest_runs_failed,
        items_ingested_total=items_ingested_total,
        stories_total=stories_total,
        stories_approved=stories_approved,
        stories_pending=stories_pending,
        articles_total=articles_total,
        articles_ready=articles_ready,
        articles_published=articles_published,
        articles_failed=articles_failed,
        publish_jobs_total=publish_jobs_total,
        publish_jobs_scheduled=publish_jobs_scheduled,
        publish_jobs_published=publish_jobs_published,
        publish_jobs_failed=publish_jobs_failed,
        publish_success_rate=publish_success_rate,
        due_publish_jobs=due_publish_jobs,
        recent_failure_groups=_build_failure_groups(session),
    )


def _build_failure_groups(session: Session) -> list[FailureGroupResponse]:
    grouped: dict[tuple[str, str], dict[str, object]] = {}

    recent_failed_jobs = session.scalars(
        select(PublishJob)
        .where(PublishJob.status == PublishJobStatus.FAILED)
        .order_by(PublishJob.updated_at.desc(), PublishJob.id.desc())
        .limit(20)
    ).all()
    for job in recent_failed_jobs:
        reason = (job.error_message or "unknown publish failure").strip()
        key = ("publish", reason)
        entry = grouped.setdefault(
            key,
            {
                "category": "publish",
                "reason": reason,
                "count": 0,
                "targets": set(),
                "suggestion": _suggest_publish_retry(reason),
            },
        )
        entry["count"] = int(entry["count"]) + 1
        targets = entry["targets"]
        assert isinstance(targets, set)
        targets.add(job.platform)

    recent_failed_runs = session.scalars(
        select(IngestRun)
        .where(IngestRun.status.in_([IngestRunStatus.FAILED, IngestRunStatus.COMPLETED_WITH_ERRORS]))
        .order_by(IngestRun.finished_at.desc(), IngestRun.id.desc())
        .limit(10)
    ).all()
    for run in recent_failed_runs:
        for error in run.errors:
            reason = error.get("message", "unknown ingest failure").strip()
            key = ("ingest", reason)
            entry = grouped.setdefault(
                key,
                {
                    "category": "ingest",
                    "reason": reason,
                    "count": 0,
                    "targets": set(),
                    "suggestion": _suggest_ingest_retry(reason),
                },
            )
            entry["count"] = int(entry["count"]) + 1
            targets = entry["targets"]
            assert isinstance(targets, set)
            targets.add(error.get("source_slug", "unknown"))

    ordered_groups = sorted(
        grouped.values(),
        key=lambda entry: (-int(entry["count"]), str(entry["category"]), str(entry["reason"])),
    )
    return [
        FailureGroupResponse(
            category=str(entry["category"]),
            reason=str(entry["reason"]),
            count=int(entry["count"]),
            targets=sorted(str(target) for target in entry["targets"]),
            suggestion=str(entry["suggestion"]),
        )
        for entry in ordered_groups
    ]


def _suggest_publish_retry(reason: str) -> str:
    lowered = reason.lower()
    if "rate limit" in lowered or "limit" in lowered:
        return "等待平台限流窗口恢复后再重试，并降低单批发布密度。"
    if "rejected" in lowered or "moderation" in lowered:
        return "检查平台内容策略、账号状态或文案后再执行重试。"
    if "credential" in lowered or "auth" in lowered or "token" in lowered:
        return "先修复平台凭证或授权状态，再重新入队失败任务。"
    return "检查发布日志后执行单任务重试，必要时重新生成对应平台文案。"


def _suggest_ingest_retry(reason: str) -> str:
    lowered = reason.lower()
    if "rate limit" in lowered or "limit" in lowered:
        return "降低采集频率并等待源站限流恢复，再重新触发采集。"
    if "timeout" in lowered or "timed out" in lowered:
        return "检查源站可达性和网络波动，确认恢复后再重试。"
    if "parse" in lowered or "schema" in lowered:
        return "检查解析规则或字段映射，修正后重新抓取该来源。"
    return "检查来源配置和连接器日志，确认原因后再执行重试。"