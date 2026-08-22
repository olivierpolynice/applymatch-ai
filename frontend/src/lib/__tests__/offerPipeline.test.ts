import { describe, expect, it } from "vitest";

import { classifyOffers, sectionForStatus } from "@/lib/offerPipeline";
import type { ApplyMatchStatus, JobOffer } from "@/types";

const now = new Date("2026-08-21T12:00:00Z");

function offer(id: number): JobOffer {
  return {
    id,
    title: `Offre ${id}`,
    company: "Entreprise",
    location: "Paris",
    contract_type: "Alternance",
    description: "Description",
    source: "test",
    source_url: `https://example.com/${id}`,
    status: "new",
    published_at: "2026-08-21T10:00:00Z",
    applied_at: null,
    created_at: "2026-08-21T10:00:00Z",
    updated_at: "2026-08-21T10:00:00Z",
  };
}

describe("offer pipeline", () => {
  it("maps every typed status to exactly one section", () => {
    const statuses: ApplyMatchStatus[] = [
      "new", "eligible", "low_score", "manual_review", "documents_ready",
      "sending", "applied", "rejected", "expired", "failed",
    ];
    expect(statuses.map(sectionForStatus)).toEqual([
      "new", "priority", "validation", "validation", "documents",
      "documents", "applied", "validation", "validation", "failed",
    ]);
  });

  it("places each offer in one section only", () => {
    const offers = [offer(1), offer(2), offer(3), offer(4), offer(5), offer(6)];
    offers[4].status = "applied";
    offers[5].application_status = "failed";
    const results = [
      { offer_id: 2, score: 80, decision: "documents_ready" },
      { offer_id: 3, score: 45, decision: "manual_review" },
      { offer_id: 4, score: 75, decision: "documents_ready" },
    ] as never;
    const drafts = [{ offer_id: 4, status: "draft" }] as never;
    const classified = classifyOffers(offers, results, drafts, [], now);
    const allIds = [...classified.values()].flat().map(({ offer }) => offer.id);

    expect(allIds.sort()).toEqual([1, 2, 3, 4, 5, 6]);
    expect(new Set(allIds).size).toBe(offers.length);
    expect(classified.get("new")?.map(({ offer }) => offer.id)).toEqual([1]);
    expect(classified.get("priority")?.map(({ offer }) => offer.id)).toEqual([2]);
    expect(classified.get("validation")?.map(({ offer }) => offer.id)).toEqual([3]);
    expect(classified.get("documents")?.map(({ offer }) => offer.id)).toEqual([4]);
    expect(classified.get("applied")?.map(({ offer }) => offer.id)).toEqual([5]);
    expect(classified.get("failed")?.map(({ offer }) => offer.id)).toEqual([6]);
  });
});
