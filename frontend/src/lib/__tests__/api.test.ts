import { apiRequest } from "@/lib/api";
import { setAccessToken } from "@/lib/auth";
import { createAccessToken } from "@/test/setup";
import { beforeEach, describe, expect, it, vi } from "vitest";


describe("apiRequest", () => {
  beforeEach(() => {
    vi.stubGlobal("fetch", vi.fn());
  });

  it("adds the JWT to authenticated requests", async () => {
    setAccessToken(createAccessToken(Date.now() + 60_000));
    const fetchMock = vi.mocked(fetch);

    fetchMock.mockResolvedValue(
      new Response(JSON.stringify({ status: "ok" }), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
    );

    await apiRequest<{ status: string }>("/health");

    const [, options] = fetchMock.mock.calls[0];
    const headers = new Headers(options?.headers);

    expect(headers.get("Authorization")).toMatch(/^Bearer /);
    expect(headers.get("Content-Type")).toBe("application/json");
  });

  it("returns the backend error detail", async () => {
    vi.mocked(fetch).mockResolvedValue(
      new Response(
        JSON.stringify({ detail: "Identifiants incorrects" }),
        {
          status: 401,
          headers: { "Content-Type": "application/json" },
        },
      ),
    );

    await expect(
      apiRequest("/auth/login", { method: "POST" }),
    ).rejects.toThrow("Identifiants incorrects");
  });

  it("supports responses without a body", async () => {
    vi.mocked(fetch).mockResolvedValue(
      new Response(null, { status: 204 }),
    );

    await expect(
      apiRequest("/job-offers/1", { method: "DELETE" }),
    ).resolves.toBeUndefined();
  });
});
