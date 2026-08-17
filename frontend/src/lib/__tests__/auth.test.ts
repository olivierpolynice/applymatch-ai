import {
  clearAccessToken,
  getAccessToken,
  getAccessTokenExpiration,
  hasValidAccessToken,
  setAccessToken,
  subscribeToAuth,
} from "@/lib/auth";
import { createAccessToken } from "@/test/setup";
import { describe, expect, it, vi } from "vitest";


describe("auth", () => {
  it("stores and returns a valid access token", () => {
    const expiration = Date.now() + 60_000;
    const token = createAccessToken(expiration);

    setAccessToken(token);

    expect(getAccessToken()).toBe(token);
    expect(hasValidAccessToken()).toBe(true);
    expect(getAccessTokenExpiration()).toBe(
      Math.floor(expiration / 1000) * 1000,
    );
  });

  it("rejects and removes an expired access token", () => {
    const token = createAccessToken(Date.now() - 60_000);

    setAccessToken(token);

    expect(getAccessToken()).toBeNull();
    expect(hasValidAccessToken()).toBe(false);
  });

  it("notifies subscribers when the session changes", () => {
    const listener = vi.fn();
    const unsubscribe = subscribeToAuth(listener);

    setAccessToken(createAccessToken(Date.now() + 60_000));
    clearAccessToken();

    expect(listener).toHaveBeenCalledTimes(2);

    unsubscribe();
  });
});
