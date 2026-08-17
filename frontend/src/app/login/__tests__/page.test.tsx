import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import LoginPage from "@/app/login/page";


const mocks = vi.hoisted(() => ({
  apiRequest: vi.fn(),
  hasValidAccessToken: vi.fn(() => false),
  replace: vi.fn(),
  setAccessToken: vi.fn(),
}));


vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace: mocks.replace }),
}));

vi.mock("@/lib/api", () => ({
  apiRequest: mocks.apiRequest,
}));

vi.mock("@/lib/auth", () => ({
  hasValidAccessToken: mocks.hasValidAccessToken,
  setAccessToken: mocks.setAccessToken,
}));


describe("LoginPage", () => {
  beforeEach(() => {
    mocks.hasValidAccessToken.mockReturnValue(false);
  });

  it("authenticates and redirects the administrator", async () => {
    const user = userEvent.setup();

    mocks.apiRequest.mockResolvedValue({
      access_token: "valid-token",
      token_type: "bearer",
      expires_in: 1800,
    });

    render(<LoginPage />);

    await user.type(
      screen.getByLabelText("Adresse e-mail"),
      "admin@applymatch.test",
    );
    await user.type(
      screen.getByLabelText("Mot de passe"),
      "MotDePasse-Test-2026!",
    );
    await user.click(
      screen.getByRole("button", { name: "Se connecter" }),
    );

    await waitFor(() => {
      expect(mocks.apiRequest).toHaveBeenCalledWith(
        "/auth/login",
        expect.objectContaining({ method: "POST" }),
      );
    });
    expect(mocks.setAccessToken).toHaveBeenCalledWith(
      "valid-token",
    );
    expect(mocks.replace).toHaveBeenCalledWith("/");
  });

  it("displays an authentication error", async () => {
    const user = userEvent.setup();

    mocks.apiRequest.mockRejectedValue(
      new Error("Identifiants incorrects"),
    );

    render(<LoginPage />);

    await user.type(
      screen.getByLabelText("Adresse e-mail"),
      "admin@applymatch.test",
    );
    await user.type(
      screen.getByLabelText("Mot de passe"),
      "mot-de-passe-invalide",
    );
    await user.click(
      screen.getByRole("button", { name: "Se connecter" }),
    );

    expect(
      await screen.findByText("Identifiants incorrects"),
    ).toBeInTheDocument();
  });
});
