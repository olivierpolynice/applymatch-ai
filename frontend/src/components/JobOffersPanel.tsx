"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useMemo, useState } from "react";

import { apiRequest } from "@/lib/api";
import type { JobOffer, MatchResult } from "@/types";

interface JobOffersPanelProps {
  offers: JobOffer[];
  priorityOffers: JobOffer[];
  results: MatchResult[];
  profileId: number;
}

interface OfferActionRequest {
  offerId: number;
  offerTitle: string;
}

type OfferSection = "new" | "manual" | "priority" | "rejected";

export default function JobOffersPanel({
  offers,
  priorityOffers,
  results,
  profileId,
}: JobOffersPanelProps) {
  const queryClient = useQueryClient();
  const [search, setSearch] = useState("");
  const [feedback, setFeedback] = useState("");
  const [section, setSection] = useState<OfferSection>("new");

  const resultsByOfferId = useMemo(
    () => new Map(
      results.map((result) => [result.offer_id, result]),
    ),
    [results],
  );

  const priorityOfferIds = useMemo(
    () => new Set(priorityOffers.map((offer) => offer.id)),
    [priorityOffers],
  );

  const sectionOffers = useMemo(() => {
    return offers.filter((offer) => {
      if (offer.status === "applied" || offer.status === "archived") {
        return false;
      }
      const matching = resultsByOfferId.get(offer.id);
      if (section === "rejected") {
        return offer.status === "rejected" || matching?.decision === "rejected";
      }
      if (!priorityOfferIds.has(offer.id)) {
        return false;
      }
      if (offer.status === "rejected" || matching?.decision === "rejected") {
        return false;
      }
      if (section === "priority") {
        return matching?.decision === "automatic_ready";
      }
      if (section === "manual") {
        return matching?.decision === "manual_review";
      }
      return matching === undefined;
    });
  }, [offers, priorityOfferIds, resultsByOfferId, section]);

  const sectionCounts = {
    new: offers.filter((offer) =>
      priorityOfferIds.has(offer.id) &&
      offer.status === "new" &&
      !resultsByOfferId.has(offer.id),
    ).length,
    manual: results.filter((result) =>
      priorityOfferIds.has(result.offer_id) &&
      result.decision === "manual_review",
    ).length,
    priority: results.filter((result) =>
      priorityOfferIds.has(result.offer_id) &&
      result.decision === "automatic_ready",
    ).length,
    rejected: offers.filter((offer) =>
      offer.status === "rejected" ||
      resultsByOfferId.get(offer.id)?.decision === "rejected",
    ).length,
  };

  const filteredOffers = useMemo(() => {
    const normalizedSearch = search.trim().toLocaleLowerCase("fr");

    if (!normalizedSearch) {
      return sectionOffers;
    }

    return sectionOffers.filter((offer) =>
      [
        offer.title,
        offer.company,
        offer.location,
        offer.contract_type,
        offer.source,
      ]
        .join(" ")
        .toLocaleLowerCase("fr")
        .includes(normalizedSearch),
    );
  }, [sectionOffers, search]);

  const matchingMutation = useMutation({
    mutationFn: ({ offerId }: OfferActionRequest) =>
      apiRequest<MatchResult>(
        `/matching/profile/${profileId}/offer/${offerId}`,
        { method: "POST" },
      ),
    onSuccess: async (matching, variables) => {
      setFeedback(
        `${variables.offerTitle} analysée : ${matching.score}/100`,
      );
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["match-results"] }),
        queryClient.invalidateQueries({ queryKey: ["job-offers"] }),
      ]);
    },
    onError: () => setFeedback(""),
  });

  const markAppliedMutation = useMutation({
    mutationFn: ({ offerId }: OfferActionRequest) =>
      apiRequest<JobOffer>(
        `/job-offers/${offerId}/mark-applied`,
        { method: "POST" },
      ),
    onSuccess: async (_, variables) => {
      setFeedback(
        `${variables.offerTitle} déplacée dans l’historique des candidatures.`,
      );
      await queryClient.invalidateQueries({
        queryKey: ["job-offers"],
      });
    },
    onError: () => setFeedback(""),
  });

  return (
    <section className="mb-8 rounded-2xl border border-slate-800 bg-slate-900 p-6">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <p className="text-sm font-semibold uppercase tracking-[0.2em] text-cyan-400">
            Offres enregistrées
          </p>
          <h2 className="mt-2 text-2xl font-bold">Offres collectées</h2>
          <p className="mt-2 text-sm text-slate-400">
            Les offres sont séparées selon le nouvel algorithme. Un score
            d’au moins 70 prépare la candidature prioritaire ; l’envoi réel
            exige toujours un canal compatible et une confirmation.
          </p>
        </div>

        <label className="grid gap-2 text-sm text-slate-300">
          Rechercher une offre
          <input
            type="search"
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            placeholder="Poste, entreprise, lieu..."
            className="w-full rounded-lg border border-slate-700 bg-slate-950 px-4 py-2 lg:w-80"
          />
        </label>
      </div>

      <div className="mt-6 flex flex-wrap gap-2">
        {([
          ["new", "Nouvelles"],
          ["manual", "À examiner (<70)"],
          ["priority", "Prioritaires (≥70)"],
          ["rejected", "Rejetées"],
        ] as const).map(([value, label]) => (
          <button
            key={value}
            type="button"
            onClick={() => setSection(value)}
            className={`rounded-lg border px-4 py-2 text-sm font-semibold ${
              section === value
                ? "border-cyan-500 bg-cyan-950 text-cyan-200"
                : "border-slate-700 bg-slate-950 text-slate-400"
            }`}
          >
            {label} ({sectionCounts[value]})
          </button>
        ))}
      </div>

      <div className="mt-6 flex items-center justify-between text-sm">
        <p className="text-slate-400">
          {filteredOffers.length} offre
          {filteredOffers.length > 1 ? "s" : ""} affichée
          {filteredOffers.length > 1 ? "s" : ""}
        </p>
        <p className="text-slate-500">
          {results.length} analysée{results.length > 1 ? "s" : ""}
        </p>
      </div>

      {sectionOffers.length === 0 && (
        <div className="mt-6 rounded-xl border border-slate-800 bg-slate-950 p-6 text-center text-slate-400">
          Aucune offre dans cette section.
        </div>
      )}

      {sectionOffers.length > 0 && filteredOffers.length === 0 && (
        <div className="mt-6 rounded-xl border border-slate-800 bg-slate-950 p-6 text-center text-slate-400">
          Aucune offre ne correspond à cette recherche.
        </div>
      )}

      {filteredOffers.length > 0 && (
        <div className="mt-6 grid gap-4">
          {filteredOffers.map((offer) => {
            const matching = resultsByOfferId.get(offer.id);
            const isMatching =
              matchingMutation.isPending &&
              matchingMutation.variables?.offerId === offer.id;
            const isMarkingApplied =
              markAppliedMutation.isPending &&
              markAppliedMutation.variables?.offerId === offer.id;

            return (
              <article
                key={offer.id}
                className="rounded-xl border border-slate-800 bg-slate-950 p-5"
              >
                <div className="flex flex-col gap-5 lg:flex-row lg:items-center lg:justify-between">
                  <div className="min-w-0">
                    <div className="flex flex-wrap items-center gap-2">
                      <p className="text-sm font-medium text-cyan-400">
                        {offer.company}
                      </p>
                      <StatusBadge
                        analyzed={matching !== undefined}
                        score={matching?.score}
                      />
                    </div>
                    <h3 className="mt-2 text-lg font-semibold">
                      {offer.title}
                    </h3>
                    <p className="mt-2 text-sm text-slate-400">
                      {offer.location} · {offer.contract_type} · {offer.source}
                    </p>
                    {matching && (
                      <p className="mt-3 text-sm text-slate-300">
                        {matching.recommendation}
                      </p>
                    )}
                  </div>

                  <div className="flex shrink-0 flex-wrap gap-3">
                    {offer.source_url ? (
                      <a
                        href={offer.source_url}
                        target="_blank"
                        rel="noreferrer"
                        className="rounded-lg border border-slate-700 px-4 py-2 text-sm font-semibold text-slate-200 transition hover:border-cyan-600 hover:text-cyan-300"
                      >
                        Voir et postuler
                      </a>
                    ) : (
                      <span className="rounded-lg border border-slate-800 px-4 py-2 text-sm text-slate-600">
                        Lien indisponible
                      </span>
                    )}

                    {section !== "rejected" && (<>
                    <button
                      type="button"
                      disabled={
                        matchingMutation.isPending ||
                        markAppliedMutation.isPending
                      }
                      onClick={() =>
                        matchingMutation.mutate({
                          offerId: offer.id,
                          offerTitle: offer.title,
                        })
                      }
                      className="rounded-lg bg-cyan-500 px-4 py-2 text-sm font-semibold text-slate-950 transition hover:bg-cyan-400 disabled:cursor-not-allowed disabled:opacity-50"
                    >
                      {isMatching
                        ? "Analyse..."
                        : matching
                          ? "Relancer l’analyse"
                          : "Analyser l’offre"}
                    </button>

                    <button
                      type="button"
                      disabled={
                        matchingMutation.isPending ||
                        markAppliedMutation.isPending
                      }
                      onClick={() => {
                        if (
                          window.confirm(
                            "Confirmer que tu as postulé manuellement à cette offre ?",
                          )
                        ) {
                          markAppliedMutation.mutate({
                            offerId: offer.id,
                            offerTitle: offer.title,
                          });
                        }
                      }}
                      className="rounded-lg border border-emerald-700 bg-emerald-950 px-4 py-2 text-sm font-semibold text-emerald-300 transition hover:bg-emerald-900 disabled:cursor-not-allowed disabled:opacity-50"
                    >
                      {isMarkingApplied ? "Enregistrement..." : "Confirmer ma candidature"}
                    </button>
                    </>)}
                  </div>
                </div>
              </article>
            );
          })}
        </div>
      )}

      {feedback && (
        <p className="mt-5 rounded-lg border border-emerald-800 bg-emerald-950/40 p-4 text-sm text-emerald-300">
          {feedback}
        </p>
      )}

      {matchingMutation.error && (
        <ErrorMessage prefix="Échec de l’analyse" error={matchingMutation.error} />
      )}
      {markAppliedMutation.error && (
        <ErrorMessage
          prefix="Impossible d’enregistrer la candidature"
          error={markAppliedMutation.error}
        />
      )}
    </section>
  );
}

function ErrorMessage({ prefix, error }: { prefix: string; error: Error }) {
  return (
    <p className="mt-5 rounded-lg border border-red-900 bg-red-950/40 p-4 text-sm text-red-300">
      {prefix} : {error.message}
    </p>
  );
}

function StatusBadge({
  analyzed,
  score,
}: {
  analyzed: boolean;
  score?: number;
}) {
  if (!analyzed) {
    return (
      <span className="rounded-full border border-slate-700 bg-slate-900 px-3 py-1 text-xs text-slate-400">
        À analyser
      </span>
    );
  }

  return (
    <span className="rounded-full border border-emerald-800 bg-emerald-950 px-3 py-1 text-xs text-emerald-300">
      Analysée · {score}/100
    </span>
  );
}
