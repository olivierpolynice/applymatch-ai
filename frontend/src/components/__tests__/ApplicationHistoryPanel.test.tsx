import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import ApplicationHistoryPanel from "@/components/ApplicationHistoryPanel";
import type { JobOffer } from "@/types";


const application: JobOffer = {
  id: 4,
  title: "Alternance cybersécurité",
  company: "Entreprise Sécurité",
  location: "Paris",
  contract_type: "Apprentissage",
  description: "Participation aux missions de sécurité informatique.",
  source: "France Travail",
  source_url: "https://example.com/offer/4",
  status: "applied",
  published_at: null,
  applied_at: "2026-08-17T12:00:00Z",
  created_at: "2026-08-17T10:00:00Z",
  updated_at: "2026-08-17T12:00:00Z",
};


describe("ApplicationHistoryPanel", () => {
  it("displays manually recorded applications", () => {
    render(<ApplicationHistoryPanel offers={[application]} />);

    expect(
      screen.getByText("Historique des candidatures"),
    ).toBeInTheDocument();
    expect(
      screen.getByText("Alternance cybersécurité"),
    ).toBeInTheDocument();
    expect(
      screen.getByText(/Candidature enregistrée le/),
    ).toBeInTheDocument();
  });

  it("shows an empty state", () => {
    render(<ApplicationHistoryPanel offers={[]} />);

    expect(
      screen.getByText(
        "Aucune candidature enregistrée pour le moment.",
      ),
    ).toBeInTheDocument();
  });
});
