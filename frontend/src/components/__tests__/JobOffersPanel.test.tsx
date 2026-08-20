import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import JobOffersPanel from "@/components/JobOffersPanel";
import type { JobOffer } from "@/types";


const mocks = vi.hoisted(() => ({
  apiRequest: vi.fn(),
}));


vi.mock("@/lib/api", () => ({
  apiRequest: mocks.apiRequest,
}));


const activeOffer: JobOffer = {
  id: 1,
  title: "Alternance ingénieur cloud",
  company: "Entreprise Test",
  location: "Paris",
  contract_type: "Alternance",
  description: "Administration et sécurisation des services cloud.",
  source: "Greenhouse",
  source_url: "https://example.com/offer/1",
  status: "new",
  published_at: null,
  applied_at: null,
  created_at: "2026-08-17T10:00:00Z",
  updated_at: "2026-08-17T10:00:00Z",
};

const appliedOffer: JobOffer = {
  ...activeOffer,
  id: 2,
  title: "Offre déjà postulée",
  status: "applied",
  applied_at: "2026-08-17T11:00:00Z",
};


function renderPanel() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });

  return render(
    <QueryClientProvider client={queryClient}>
      <JobOffersPanel
        offers={[activeOffer, appliedOffer]}
        results={[]}
        profileId={1}
      />
    </QueryClientProvider>,
  );
}


describe("JobOffersPanel", () => {
  beforeEach(() => {
    vi.spyOn(window, "confirm").mockReturnValue(true);
  });

  it("hides offers already marked as applied", () => {
    renderPanel();

    expect(
      screen.getByText("Alternance ingénieur cloud"),
    ).toBeInTheDocument();
    expect(
      screen.queryByText("Offre déjà postulée"),
    ).not.toBeInTheDocument();
  });

  it("records a manually submitted application", async () => {
    const user = userEvent.setup();

    mocks.apiRequest.mockResolvedValue({
      ...activeOffer,
      status: "applied",
      applied_at: "2026-08-17T12:00:00Z",
    });

    renderPanel();

    await user.click(
      screen.getByRole("button", { name: "Confirmer ma candidature" }),
    );

    await waitFor(() => {
      expect(mocks.apiRequest).toHaveBeenCalledWith(
        "/job-offers/1/mark-applied",
        { method: "POST" },
      );
    });
    expect(window.confirm).toHaveBeenCalledOnce();
  });
});
