from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from fetchnews.models import PublishJob, PublishJobStatus


@dataclass(slots=True)
class PlatformCopyProfile:
    platform: str
    published_jobs: int = 0
    engagement_impressions: int = 0
    engagement_opens: int = 0
    engagement_clicks: int = 0
    engagement_interactions: int = 0
    strategy: str = "balanced"

    @property
    def open_rate(self) -> float:
        if self.engagement_impressions <= 0:
            return 0.0
        return self.engagement_opens / self.engagement_impressions

    @property
    def click_through_rate(self) -> float:
        if self.engagement_impressions <= 0:
            return 0.0
        return self.engagement_clicks / self.engagement_impressions

    @property
    def interaction_rate(self) -> float:
        if self.engagement_impressions <= 0:
            return 0.0
        return self.engagement_interactions / self.engagement_impressions


def build_platform_copy_profiles(session: Session) -> dict[str, PlatformCopyProfile]:
    profiles = {
        platform: PlatformCopyProfile(platform=platform, strategy=_default_strategy(platform))
        for platform in ("wechat", "x", "telegram")
    }

    jobs = session.scalars(select(PublishJob).where(PublishJob.status == PublishJobStatus.PUBLISHED)).all()
    for job in jobs:
        profile = profiles.setdefault(job.platform, PlatformCopyProfile(platform=job.platform, strategy="balanced"))
        profile.published_jobs += 1
        metrics = job.performance_metrics or {}
        profile.engagement_impressions += _read_metric(metrics, "impressions")
        profile.engagement_opens += _read_metric(metrics, "opens")
        profile.engagement_clicks += _read_metric(metrics, "clicks")
        profile.engagement_interactions += _read_metric(metrics, "interactions")

    for profile in profiles.values():
        profile.strategy = _classify_platform_strategy(profile)
    return profiles


def _classify_platform_strategy(profile: PlatformCopyProfile) -> str:
    if profile.platform == "wechat":
        if profile.engagement_opens >= 200 and profile.open_rate >= 0.3:
            return "editorial"
        if profile.engagement_clicks >= 80 and profile.click_through_rate >= 0.07:
            return "actionable"
        return "balanced"

    if profile.platform == "x":
        if profile.engagement_interactions >= 30 and profile.interaction_rate >= 0.045:
            return "conversational"
        if profile.engagement_clicks >= 50 and profile.click_through_rate >= 0.055:
            return "link_out"
        return "headline"

    if profile.platform == "telegram":
        if profile.engagement_clicks >= 60 and profile.click_through_rate >= 0.08:
            return "bulletin"
        if profile.engagement_interactions >= 25 and profile.interaction_rate >= 0.03:
            return "discussion"
        return "digest"

    return "balanced"


def _default_strategy(platform: str) -> str:
    defaults = {
        "wechat": "balanced",
        "x": "headline",
        "telegram": "digest",
    }
    return defaults.get(platform, "balanced")


def _read_metric(metrics: dict[str, object], key: str) -> int:
    value = metrics.get(key)
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str):
        try:
            return int(value)
        except ValueError:
            return 0
    return 0
