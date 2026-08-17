import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import LogoutButton from "@/components/LogoutButton";


const mocks = vi.hoisted(() => ({
  clearAccessToken: vi.fn(),
  replace: vi.fn(),
}));


vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace: mocks.replace }),
}));

vi.mock("@/lib/auth", () => ({
  clearAccessToken: mocks.clearAccessToken,
}));


describe("LogoutButton", () => {
  it("clears the session and redirects to login", async () => {
    const user = userEvent.setup();

    render(<LogoutButton />);

    await user.click(
      screen.getByRole("button", { name: "Se déconnecter" }),
    );

    expect(mocks.clearAccessToken).toHaveBeenCalledOnce();
    expect(mocks.replace).toHaveBeenCalledWith("/login");
  });
});
