import { afterEach, describe, expect, it, vi } from "vitest";

import { buildAuthorizedRequestInit, configureAccessTokenResolver, fetchOpsSummary, fetchSourceSpecs } from "./api";

describe("buildAuthorizedRequestInit", () => {
  afterEach(() => {
    configureAccessTokenResolver(null);
    vi.restoreAllMocks();
  });

  it("adds the bearer token when a resolver returns one", () => {
    configureAccessTokenResolver(() => "token-123");

    const init = buildAuthorizedRequestInit();
    const headers = new Headers(init.headers);

    expect(headers.get("Authorization")).toBe("Bearer token-123");
  });

  it("keeps an explicit authorization header untouched", () => {
    configureAccessTokenResolver(() => "token-123");

    const init = buildAuthorizedRequestInit({
      headers: {
        Authorization: "Bearer explicit-token",
      },
    });
    const headers = new Headers(init.headers);

    expect(headers.get("Authorization")).toBe("Bearer explicit-token");
  });
});

describe("api field mapping", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("maps ops summary platform failure categories", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(
        JSON.stringify({
          ingest_runs_total: 1,
          ingest_runs_failed: 0,
          items_ingested_total: 2,
          stories_total: 1,
          stories_approved: 1,
          stories_pending: 0,
          articles_total: 1,
          articles_ready: 0,
          articles_published: 1,
          articles_failed: 0,
          publish_jobs_total: 1,
          publish_jobs_scheduled: 0,
          publish_jobs_published: 0,
          publish_jobs_failed: 1,
          publish_success_rate: 0,
          due_publish_jobs: 0,
          engagement_impressions_total: 0,
          engagement_opens_total: 0,
          engagement_clicks_total: 0,
          engagement_interactions_total: 0,
          alerts: [],
          recent_failure_groups: [],
          publish_platform_metrics: [
            {
              platform: "wechat",
              total_jobs: 1,
              scheduled_jobs: 0,
              published_jobs: 0,
              failed_jobs: 1,
              success_rate: 0,
              engagement_impressions: 0,
              engagement_opens: 0,
              engagement_clicks: 0,
              engagement_interactions: 0,
              click_through_rate: 0,
              interaction_rate: 0,
              last_error: "wechat auth token expired",
              last_failure_category: "auth",
            },
          ],
          section_review_metrics: [],
          feedback_recommendations: [],
        }),
        { status: 200, headers: { "Content-Type": "application/json" } },
      ),
    );

    const summary = await fetchOpsSummary();

    expect(summary.publishPlatformMetrics[0]?.lastFailureCategory).toBe("auth");
  });

  it("maps source incremental sync state", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(
        JSON.stringify([
          {
            slug: "github-openai-releases",
            label: "GitHub OpenAI Releases",
            platform: "github",
            priority: "P0",
            kind: "api",
            enabled: true,
            config: {},
            effective_trust_score: 6.2,
            effective_score_multiplier: 1.08,
            feedback_signals: {},
            governance_flags: [],
            incremental_cursor: "github-api-cursor-2",
            last_success_at: "2026-06-04T09:10:00Z",
          },
        ]),
        { status: 200, headers: { "Content-Type": "application/json" } },
      ),
    );

    const sources = await fetchSourceSpecs();

    expect(sources[0]?.incrementalCursor).toBe("github-api-cursor-2");
    expect(sources[0]?.lastSuccessAt).toBe("2026-06-04T09:10:00Z");
  });
});
