import { afterEach, describe, expect, it } from "vitest";

import { buildAuthorizedRequestInit, configureAccessTokenResolver } from "./api";

describe("buildAuthorizedRequestInit", () => {
  afterEach(() => {
    configureAccessTokenResolver(null);
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
