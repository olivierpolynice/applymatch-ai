import { act, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import AuthGuard from "@/components/AuthGuard";


const mocks = vi.hoisted(() => ({
  clearAccessToken: vi.fn(),
  getAccessTokenExpiration: vi.fn<() => number | null>(),
  getAuthSnapshot: vi.fn(() => true),
  replace: vi.fn(),
}));


vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace: mocks.replace }),
}));

vi.mock("@/lib/auth", () => ({
  clearAccessToken: mocks.clearAccessToken,
  getAccessTokenExpiration: mocks.getAccessTokenExpiration,
  getAuthSnapshot: mocks.getAuthSnapshot,
  getServerAuthSnapshot: () => false,
  subscribeToAuth: () => () => undefined,
}));


describe("AuthGuard", () => {
  beforeEach(() => {
    mocks.getAuthSnapshot.mockReturnValue(true);
    mocks.getAccessTokenExpiration.mockReturnValue(
      Date.now() + 60_000,
    );
  });

  it("renders the dashboard for a valid session", () => {
    render(
      <AuthGuard>
        <p>Dashboard protégé</p>
      </AuthGuard>,
    );

    expect(
      screen.getByText("Dashboard protégé"),
    ).toBeInTheDocument();
  });

  it("redirects when no session is available", () => {
    vi.useFakeTimers();
    mocks.getAuthSnapshot.mockReturnValue(false);

    render(
      <AuthGuard>
        <p>Dashboard protégé</p>
      </AuthGuard>,
    );

    expect(
      screen.getByText("Vérification de la session..."),
    ).toBeInTheDocument();

    act(() => {
      vi.runAllTimers();
    });

    expect(mocks.replace).toHaveBeenCalledWith("/login");
    vi.useRealTimers();
  });

  it("clears a session without an expiration date", () => {
    mocks.getAccessTokenExpiration.mockReturnValue(null);

    render(
      <AuthGuard>
        <p>Dashboard protégé</p>
      </AuthGuard>,
    );

    expect(mocks.clearAccessToken).toHaveBeenCalledOnce();
    expect(mocks.replace).toHaveBeenCalledWith("/login");
  });
});
