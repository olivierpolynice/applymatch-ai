"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useMemo, useState } from "react";

import { apiRequest } from "@/lib/api";
import type { JobOffer, MatchResult } from "@/types";

interface JobOffersPanelProps {
  offers: JobOffer[];
  results: MatchResult[];
  profileId: number;
}

interface OfferActionRequest {
  offerId: number;
  offerTitle: string;
}

export default function JobOffersPanel({
  offers,
  results,
  profileId,
}: JobOffersPanelProps) {
  const queryClient = useQueryClient();
  const [search, setSearch] = useState("");
  const [feedback, setFeedback] = useState("");

  const activeOffers = useMemo(
    () =>
      offers.filter(
        (offer) =>
          offer.status !== "applied" &&
          offer.status !== "rejected" &&
          offer.status !== "archived",
      ),
    [offers],
  );

  const resultsByOfferId = new Map(
    results.map((result) => [result.offer_id, result]),
  );

  const filteredOffers = useMemo(() => {
    const normalizedSearch = search.trim().toLocaleLowerCase("fr");

    if (!normalizedSearch) {
      return activeOffers;
    }

    return activeOffers.filter((offer) =>
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
  }, [activeOffers, search]);

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
      await queryClient.invalidateQueries({
        queryKey: ["match-results"],
      });
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
            Analyse les offres actives et enregistre manuellement tes
            candidatures. ApplyMatch AI n’envoie rien automatiquement.
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

      {activeOffers.length === 0 && (
        <div className="mt-6 rounded-xl border border-slate-800 bg-slate-950 p-6 text-center text-slate-400">
          Aucune offre active. Lance le collecteur ou consulte l’historique.
        </div>
      )}

      {activeOffers.length > 0 && filteredOffers.length === 0 && (
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
                        Voir l’offre
                      </a>
                    ) : (
                      <span className="rounded-lg border border-slate-800 px-4 py-2 text-sm text-slate-600">
                        Lien indisponible
                      </span>
                    )}

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
                      {isMarkingApplied ? "Enregistrement..." : "J’ai postulé"}
                    </button>
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
