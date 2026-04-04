from __future__ import annotations


def classify_publish_failure(error_message: str | None) -> str:
    lowered = (error_message or "").strip().lower()
    if not lowered:
        return "publish_failed"
    if "rate limit" in lowered or "too many requests" in lowered:
        return "rate_limit"
    if "auth" in lowered or "token" in lowered or "credential" in lowered:
        return "auth"
    if "moderation" in lowered or "rejected" in lowered:
        return "moderation"
    if "timeout" in lowered or "timed out" in lowered:
        return "timeout"
    return "publish_failed"
