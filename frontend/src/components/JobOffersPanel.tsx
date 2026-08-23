"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useMemo, useState } from "react";

import { apiRequest } from "@/lib/api";
import { classifyOffers, PIPELINE_SECTIONS, type OfferPipelineSection } from "@/lib/offerPipeline";
import type { ApplicationArchive, ApplicationDraft, ApplyMatchStatus, JobOffer, MatchResult } from "@/types";

interface Props {
  offers: JobOffer[];
  results: MatchResult[];
  drafts: ApplicationDraft[];
  archives: ApplicationArchive[];
  profileId: number;
  refreshErrors?: string[];
}

interface OfferAction { offerId: number; offerTitle: string }

const statusLabels: Record<ApplyMatchStatus, string> = {
  new: "Nouvelle", eligible: "Éligible", low_score: "Score faible",
  manual_review: "Validation humaine", documents_ready: "Documents prêts",
  sending: "Envoi en cours", applied: "Candidature confirmée",
  rejected: "Rejetée par les règles", expired: "Expirée", failed: "Échec d’envoi",
};

export default function JobOffersPanel({
  offers, results, drafts, archives, profileId, refreshErrors = [],
}: Props) {
  const queryClient = useQueryClient();
  const [search, setSearch] = useState("");
  const [feedback, setFeedback] = useState("");
  const [section, setSection] = useState<OfferPipelineSection>("new");
  const resultsByOfferId = useMemo(
    () => new Map(results.map((result) => [result.offer_id, result])), [results],
  );
  const classified = useMemo(
    () => classifyOffers(offers, results, drafts, archives),
    [offers, results, drafts, archives],
  );
  const sectionItems = classified.get(section) ?? [];
  const filteredItems = useMemo(() => {
    const value = search.trim().toLocaleLowerCase("fr");
    if (!value) return sectionItems;
    return sectionItems.filter(({ offer }) =>
      [offer.title, offer.company, offer.location, offer.contract_type, offer.source]
        .join(" ").toLocaleLowerCase("fr").includes(value),
    );
  }, [sectionItems, search]);

  const invalidateWorkflow = () => Promise.all([
    queryClient.invalidateQueries({ queryKey: ["job-offers"] }),
    queryClient.invalidateQueries({ queryKey: ["match-results"] }),
    queryClient.invalidateQueries({ queryKey: ["application-drafts"] }),
    queryClient.invalidateQueries({ queryKey: ["application-archives"] }),
    queryClient.invalidateQueries({ queryKey: ["gmail-deliveries"] }),
  ]);

  const matchingMutation = useMutation({
    mutationFn: ({ offerId }: OfferAction) => apiRequest<MatchResult>(
      `/matching/profile/${profileId}/offer/${offerId}`, { method: "POST" },
    ),
    onSuccess: async (matching, variables) => {
      setFeedback(`${variables.offerTitle} analysée : ${matching.score}/100`);
      await invalidateWorkflow();
    },
    onError: () => setFeedback(""),
  });
  const markAppliedMutation = useMutation({
    mutationFn: ({ offerId }: OfferAction) => apiRequest<JobOffer>(
      `/job-offers/${offerId}/mark-applied`, { method: "POST" },
    ),
    onSuccess: async (_, variables) => {
      setFeedback(`${variables.offerTitle} déplacée dans « Déjà postulé ».`);
      await invalidateWorkflow();
      setSection("applied");
    },
    onError: () => setFeedback(""),
  });
  const deleteOfferMutation = useMutation({
    mutationFn: ({ offerId }: OfferAction) => apiRequest<void>(
      `/job-offers/${offerId}`, { method: "DELETE" },
    ),
    onSuccess: async (_, variables) => {
      setFeedback(`${variables.offerTitle} supprimée.`);
      await Promise.all([
        invalidateWorkflow(),
        queryClient.invalidateQueries({ queryKey: ["validation-queue"] }),
        queryClient.invalidateQueries({ queryKey: ["notifications"] }),
        queryClient.invalidateQueries({ queryKey: ["notifications-unread-count"] }),
      ]);
    },
    onError: () => setFeedback(""),
  });

  const handleDeleteOffer = (offerId: number, offerTitle: string) => {
    if (window.confirm(`Supprimer « ${offerTitle} » ? Cette offre semble ne pas correspondre à un vrai poste. Cette action est définitive.`)) {
      deleteOfferMutation.mutate({ offerId, offerTitle });
    }
  };

  return (
    <section className="mb-8 rounded-2xl border border-slate-800 bg-slate-900 p-6">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <p className="text-sm font-semibold uppercase tracking-[0.2em] text-cyan-400">Parcours de candidature</p>
          <h2 className="mt-2 text-2xl font-bold">Suivi sans doublons</h2>
          <p className="mt-2 text-sm text-slate-400">Chaque offre appartient à une seule section. Le seuil prioritaire est fixé à 60/100.</p>
        </div>
        <label className="grid gap-2 text-sm text-slate-300">Rechercher
          <input type="search" value={search} onChange={(event) => setSearch(event.target.value)}
            placeholder="Poste, entreprise, lieu..."
            className="w-full rounded-lg border border-slate-700 bg-slate-950 px-4 py-2 lg:w-80" />
        </label>
      </div>

      <div className="mt-6 grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
        {PIPELINE_SECTIONS.map((item) => (
          <button key={item.key} type="button" onClick={() => setSection(item.key)}
            className={`rounded-xl border p-4 text-left transition ${section === item.key
              ? "border-cyan-500 bg-cyan-950/60" : "border-slate-700 bg-slate-950 hover:border-slate-500"}`}>
            <span className="flex items-center justify-between gap-3">
              <span className="font-semibold text-slate-100">{item.label}</span>
              <span className="rounded-full bg-slate-800 px-2.5 py-1 text-xs text-cyan-300">{classified.get(item.key)?.length ?? 0}</span>
            </span>
            <span className="mt-2 block text-xs text-slate-400">{item.description}</span>
          </button>
        ))}
      </div>

      {refreshErrors.length > 0 && (
        <div className="mt-5 rounded-xl border border-red-900 bg-red-950/40 p-4 text-sm text-red-300">
          {refreshErrors.map((error) => <p key={error}>{error}</p>)}
        </div>
      )}
      <div className="mt-6 flex items-center justify-between text-sm text-slate-400">
        <p>{filteredItems.length} offre{filteredItems.length > 1 ? "s" : ""} affichée{filteredItems.length > 1 ? "s" : ""}</p>
        <p>{offers.length} offre{offers.length > 1 ? "s" : ""} au total</p>
      </div>
      {sectionItems.length === 0 && <EmptyMessage text="Aucune offre dans cette section." />}
      {sectionItems.length > 0 && filteredItems.length === 0 && <EmptyMessage text="Aucune offre ne correspond à cette recherche." />}

      <div className="mt-6 grid gap-4">
        {filteredItems.map(({ offer, status }) => {
          const matching = resultsByOfferId.get(offer.id);
          const isMatching = matchingMutation.isPending && matchingMutation.variables?.offerId === offer.id;
          const isApplying = markAppliedMutation.isPending && markAppliedMutation.variables?.offerId === offer.id;
          return (
            <article key={offer.id} className="rounded-xl border border-slate-800 bg-slate-950 p-5">
              <div className="flex flex-col gap-5 lg:flex-row lg:items-center lg:justify-between">
                <div className="min-w-0">
                  <div className="flex flex-wrap items-center gap-2">
                    <p className="text-sm font-medium text-cyan-400">{offer.company}</p>
                    <span className="rounded-full border border-slate-700 px-3 py-1 text-xs text-slate-300">{statusLabels[status]}</span>
                    {matching && <span className="rounded-full border border-emerald-800 bg-emerald-950 px-3 py-1 text-xs text-emerald-300">{matching.score}/100</span>}
                  </div>
                  <h3 className="mt-2 text-lg font-semibold">{offer.title}</h3>
                  <p className="mt-2 text-sm text-slate-400">{offer.location} · {offer.contract_type} · {offer.source}</p>
                </div>
                <div className="flex shrink-0 flex-wrap gap-3">
                  {offer.source_url && <a href={offer.source_url} target="_blank" rel="noreferrer"
                    className="rounded-lg border border-slate-700 px-4 py-2 text-sm font-semibold hover:border-cyan-600">Voir l’offre</a>}
                  {status !== "applied" && status !== "failed" && (
                    <button type="button" disabled={matchingMutation.isPending || markAppliedMutation.isPending || deleteOfferMutation.isPending}
                      onClick={() => matchingMutation.mutate({ offerId: offer.id, offerTitle: offer.title })}
                      className="rounded-lg bg-cyan-500 px-4 py-2 text-sm font-semibold text-slate-950 disabled:opacity-50">
                      {isMatching ? "Analyse..." : matching ? "Réanalyser" : "Analyser"}
                    </button>
                  )}
                  {status !== "applied" && (
                    <button type="button" disabled={matchingMutation.isPending || markAppliedMutation.isPending || deleteOfferMutation.isPending}
                      onClick={() => window.confirm("Confirmer l’envoi réel de cette candidature ?") &&
                        markAppliedMutation.mutate({ offerId: offer.id, offerTitle: offer.title })}
                      className="rounded-lg border border-emerald-700 bg-emerald-950 px-4 py-2 text-sm font-semibold text-emerald-300 disabled:opacity-50">
                      {isApplying ? "Enregistrement..." : "J’ai postulé"}
                    </button>
                  )}
                  <button type="button"
                    disabled={matchingMutation.isPending || markAppliedMutation.isPending ||
                      (deleteOfferMutation.isPending && deleteOfferMutation.variables?.offerId === offer.id)}
                    onClick={() => handleDeleteOffer(offer.id, offer.title)}
                    className="rounded-lg border border-red-900 bg-red-950/40 px-4 py-2 text-sm font-semibold text-red-300 hover:border-red-700 hover:bg-red-950 disabled:cursor-not-allowed disabled:opacity-50">
                    {deleteOfferMutation.isPending && deleteOfferMutation.variables?.offerId === offer.id
                      ? "Suppression..." : "Ce n’est pas un vrai poste — Supprimer"}
                  </button>
                </div>
              </div>
            </article>
          );
        })}
      </div>
      {feedback && <p className="mt-5 rounded-lg border border-emerald-800 bg-emerald-950/40 p-4 text-sm text-emerald-300">{feedback}</p>}
      {matchingMutation.error && <ErrorMessage prefix="Échec de l’analyse" error={matchingMutation.error} />}
      {markAppliedMutation.error && <ErrorMessage prefix="Impossible d’enregistrer la candidature" error={markAppliedMutation.error} />}
      {deleteOfferMutation.error && <ErrorMessage prefix="Impossible de supprimer l’offre" error={deleteOfferMutation.error} />}
    </section>
  );
}

function EmptyMessage({ text }: { text: string }) {
  return <div className="mt-6 rounded-xl border border-slate-800 bg-slate-950 p-6 text-center text-slate-400">{text}</div>;
}

function ErrorMessage({ prefix, error }: { prefix: string; error: Error }) {
  return <p className="mt-5 rounded-lg border border-red-900 bg-red-950/40 p-4 text-sm text-red-300">{prefix} : {error.message}</p>;
}
