"use client";

import {
  useMutation,
  useQueryClient,
} from "@tanstack/react-query";
import { useMemo, useState } from "react";

import { apiRequest } from "@/lib/api";
import type {
  JobOffer,
  MatchResult,
} from "@/types";

interface JobOffersPanelProps {
  offers: JobOffer[];
  results: MatchResult[];
  profileId: number;
}

interface MatchingRequest {
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

  const resultsByOfferId = new Map(
    results.map((result) => [
      result.offer_id,
      result,
    ]),
  );

  const filteredOffers = useMemo(() => {
    const normalizedSearch = search
      .trim()
      .toLocaleLowerCase("fr");

    if (!normalizedSearch) {
      return offers;
    }

    return offers.filter((offer) => {
      const searchableText = [
        offer.title,
        offer.company,
        offer.location,
        offer.contract_type,
        offer.source,
      ]
        .join(" ")
        .toLocaleLowerCase("fr");

      return searchableText.includes(normalizedSearch);
    });
  }, [offers, search]);

  const matchingMutation = useMutation({
    mutationFn: ({
      offerId,
    }: MatchingRequest) =>
      apiRequest<MatchResult>(
        `/matching/profile/${profileId}/offer/${offerId}`,
        {
          method: "POST",
        },
      ),

    onSuccess: async (
      matching,
      variables,
    ) => {
      setFeedback(
        `${variables.offerTitle} analysée : ` +
          `${matching.score}/100`,
      );

      await queryClient.invalidateQueries({
        queryKey: ["match-results"],
      });
    },

    onError: () => {
      setFeedback("");
    },
  });

  return (
    <section className="mb-8 rounded-2xl border border-slate-800 bg-slate-900 p-6">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <p className="text-sm font-semibold uppercase tracking-[0.2em] text-cyan-400">
            Offres enregistrées
          </p>

          <h2 className="mt-2 text-2xl font-bold">
            Offres collectées
          </h2>

          <p className="mt-2 text-sm text-slate-400">
            Consulte les offres et lance leur analyse
            avec ton profil.
          </p>
        </div>

        <label className="grid gap-2 text-sm text-slate-300">
          Rechercher une offre

          <input
            type="search"
            value={search}
            onChange={(event) =>
              setSearch(event.target.value)
            }
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
          {results.length} analysée
          {results.length > 1 ? "s" : ""}
        </p>
      </div>

      {offers.length === 0 && (
        <div className="mt-6 rounded-xl border border-slate-800 bg-slate-950 p-6 text-center text-slate-400">
          Aucune offre enregistrée. Lance d’abord le
          collecteur.
        </div>
      )}

      {offers.length > 0 &&
        filteredOffers.length === 0 && (
          <div className="mt-6 rounded-xl border border-slate-800 bg-slate-950 p-6 text-center text-slate-400">
            Aucune offre ne correspond à cette recherche.
          </div>
        )}

      {filteredOffers.length > 0 && (
        <div className="mt-6 grid gap-4">
          {filteredOffers.map((offer) => {
            const matching = resultsByOfferId.get(
              offer.id,
            );

            const isCurrentOfferPending =
              matchingMutation.isPending &&
              matchingMutation.variables?.offerId ===
                offer.id;

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
                      {offer.location}
                      {" · "}
                      {offer.contract_type}
                      {" · "}
                      {offer.source}
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
                        matchingMutation.isPending
                      }
                      onClick={() =>
                        matchingMutation.mutate({
                          offerId: offer.id,
                          offerTitle: offer.title,
                        })
                      }
                      className="rounded-lg bg-cyan-500 px-4 py-2 text-sm font-semibold text-slate-950 transition hover:bg-cyan-400 disabled:cursor-not-allowed disabled:opacity-50"
                    >
                      {isCurrentOfferPending
                        ? "Analyse..."
                        : matching
                          ? "Relancer l’analyse"
                          : "Analyser l’offre"}
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
        <p className="mt-5 rounded-lg border border-red-900 bg-red-950/40 p-4 text-sm text-red-300">
          Échec de l’analyse :{" "}
          {matchingMutation.error instanceof Error
            ? matchingMutation.error.message
            : "erreur inconnue"}
        </p>
      )}
    </section>
  );
}

interface StatusBadgeProps {
  analyzed: boolean;
  score?: number;
}

function StatusBadge({
  analyzed,
  score,
}: StatusBadgeProps) {
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