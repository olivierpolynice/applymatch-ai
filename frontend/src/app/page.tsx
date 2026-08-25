"use client";

import { useQuery } from "@tanstack/react-query";
import { useState } from "react";

import ApplicationDraftsPanel from "@/components/ApplicationDraftsPanel";
import AuthGuard from "@/components/AuthGuard";
import CollectorHistoryPanel from "@/components/CollectorHistoryPanel";
import CollectorPanel from "@/components/CollectorPanel";
import JobOffersPanel from "@/components/JobOffersPanel";
import LogoutButton from "@/components/LogoutButton";
import MatchResultCard from "@/components/MatchResultCard";
import NotificationCenter from "@/components/NotificationCenter";
import ValidationQueuePanel from "@/components/ValidationQueuePanel";
import { apiRequest } from "@/lib/api";
import type {
  ApplicationArchive,
  ApplicationDraft,
  CandidateProfile,
  GmailDelivery,
  JobOffer,
  MatchResult,
} from "@/types";

export default function Home() {
  const [minimumScore, setMinimumScore] = useState(0);

  const profilesQuery = useQuery({
    queryKey: ["candidate-profiles"],
    queryFn: () =>
      apiRequest<CandidateProfile[]>(
        "/candidate-profiles",
      ),
  });

  const activeProfile = profilesQuery.data
    ?.filter((profile) => profile.is_active)
    .sort(
      (first, second) => second.id - first.id,
    )[0];

  const offersQuery = useQuery({
    queryKey: ["job-offers"],
    queryFn: () =>
      // priority_only=true applique le filtre strict déjà défini côté
      // serveur : alternance/stage uniquement (jamais CDI/CDD/intérim),
      // publiée il y a moins de 24h, expérience 0-2 ans, et jamais une
      // offre réservée à une école partenaire spécifique. Sans ce
      // paramètre, l'API renvoie tout, non filtré.
      apiRequest<JobOffer[]>(
        "/job-offers?priority_only=true",
      ),
    refetchInterval: 15_000,
  });

  const archivesQuery = useQuery({
    queryKey: ["application-archives"],
    queryFn: () =>
      apiRequest<ApplicationArchive[]>(
        "/application-automation/archives",
      ),
    refetchInterval: 15_000,
  });

  const draftsQuery = useQuery({
    queryKey: ["application-drafts"],
    queryFn: () => apiRequest<ApplicationDraft[]>("/application-drafts"),
    refetchInterval: 15_000,
  });

  const gmailDeliveriesQuery = useQuery({
    queryKey: ["gmail-deliveries"],
    queryFn: () => apiRequest<GmailDelivery[]>("/gmail/deliveries"),
    refetchInterval: 15_000,
  });

  const resultsQuery = useQuery({
    queryKey: [
      "match-results",
      activeProfile?.id,
      minimumScore,
    ],
    queryFn: () =>
      apiRequest<MatchResult[]>(
        `/matching/profile/${activeProfile!.id}/results` +
          `?minimum_score=${minimumScore}`,
      ),
    enabled: activeProfile !== undefined,
    refetchInterval: 15_000,
  });

  const offersById = new Map(
    (offersQuery.data ?? []).map((offer) => [
      offer.id,
      offer,
    ]),
  );

  const isLoading =
    profilesQuery.isLoading ||
    offersQuery.isLoading ||
    draftsQuery.isLoading ||
    archivesQuery.isLoading ||
    gmailDeliveriesQuery.isLoading ||
    (activeProfile !== undefined &&
      resultsQuery.isLoading);

  const error =
    profilesQuery.error ??
    offersQuery.error ??
    draftsQuery.error ??
    archivesQuery.error ??
    gmailDeliveriesQuery.error ??
    resultsQuery.error;

  return (
    <AuthGuard>
      <main className="min-h-screen bg-slate-950 px-4 py-10 text-slate-100">
        <NotificationCenter />

        <div className="mx-auto max-w-6xl">
          <header className="mb-10 flex flex-col gap-6 sm:flex-row sm:items-start sm:justify-between">
            <div>
              <p className="mb-3 text-sm font-semibold uppercase tracking-[0.3em] text-cyan-400">
                ApplyMatch AI
              </p>

              <h1 className="text-4xl font-bold">
                Tableau de bord des opportunités
              </h1>

              <p className="mt-3 max-w-2xl text-slate-400">
                Consulte les offres analysées et leur
                compatibilité avec ton profil. Aucune
                candidature n’est automatisée sans règles strictes et canal autorisé.
              </p>

              {activeProfile && (
                <p className="mt-4 text-sm text-cyan-300">
                  Profil actif : {activeProfile.full_name}
                </p>
              )}
            </div>

            <LogoutButton />
          </header>

          <CollectorPanel />

          <CollectorHistoryPanel />

          <section className="mb-8 grid gap-4 sm:grid-cols-3">
            <article className="rounded-2xl border border-slate-800 bg-slate-900 p-5">
              <p className="text-sm text-slate-400">
                Offres importées
              </p>

              <p className="mt-2 text-3xl font-bold">
                {offersQuery.data?.length ?? 0}
              </p>
            </article>

            <article className="rounded-2xl border border-slate-800 bg-slate-900 p-5">
              <p className="text-sm text-slate-400">
                Offres analysées
              </p>

              <p className="mt-2 text-3xl font-bold">
                {resultsQuery.data?.length ?? 0}
              </p>
            </article>

            <article className="rounded-2xl border border-slate-800 bg-slate-900 p-5">
              <p className="text-sm text-slate-400">
                Validation
              </p>

              <p className="mt-2 text-lg font-semibold text-emerald-400">
                Priorité à partir de 60 si le canal est autorisé
              </p>
            </article>
          </section>

          {activeProfile &&
            !offersQuery.isLoading &&
            !offersQuery.error &&
            !draftsQuery.isLoading &&
            !archivesQuery.isLoading && (
              <JobOffersPanel
                offers={offersQuery.data ?? []}
                results={resultsQuery.data ?? []}
                drafts={draftsQuery.data ?? []}
                archives={archivesQuery.data ?? []}
                profileId={activeProfile.id}
                refreshErrors={[
                  draftsQuery.error instanceof Error ? `Documents : ${draftsQuery.error.message}` : "",
                  archivesQuery.error instanceof Error ? `Archives : ${archivesQuery.error.message}` : "",
                  gmailDeliveriesQuery.error instanceof Error ? `Envois : ${gmailDeliveriesQuery.error.message}` : "",
                ].filter(Boolean)}
              />
            )}

          {!offersQuery.isLoading &&
            !offersQuery.error && (
              <ValidationQueuePanel
                offers={offersQuery.data ?? []}
              />
            )}

          {activeProfile &&
            !offersQuery.isLoading &&
            !offersQuery.error && (
              <ApplicationDraftsPanel
                profileId={activeProfile.id}
                offers={offersQuery.data ?? []}
              />
            )}

          <section className="mb-6 flex flex-col gap-4 rounded-2xl border border-slate-800 bg-slate-900 p-5 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <h2 className="text-xl font-semibold">
                Résultats du matching
              </h2>

              <p className="mt-1 text-sm text-slate-400">
                Les offres sont classées du meilleur au
                moins bon score.
              </p>
            </div>

            <label className="flex items-center gap-3 text-sm">
              Score minimal

              <select
                value={minimumScore}
                onChange={(event) =>
                  setMinimumScore(
                    Number(event.target.value),
                  )
                }
                className="rounded-lg border border-slate-700 bg-slate-950 px-3 py-2"
              >
                <option value={0}>Tous</option>
                <option value={50}>50 et plus</option>
                <option value={60}>60 et plus</option>
                <option value={85}>85 et plus</option>
              </select>
            </label>
          </section>

          {isLoading && (
            <div className="rounded-2xl border border-slate-800 bg-slate-900 p-8 text-center text-slate-400">
              Chargement des données...
            </div>
          )}

          {error && (
            <div className="rounded-2xl border border-red-900 bg-red-950/40 p-6 text-red-300">
              Impossible de charger les données :{" "}
              {error instanceof Error
                ? error.message
                : "erreur inconnue"}
            </div>
          )}

          {!isLoading &&
            !error &&
            profilesQuery.data &&
            !activeProfile && (
              <div className="rounded-2xl border border-amber-900 bg-amber-950/40 p-6 text-amber-300">
                Aucun profil actif n’a été trouvé.
              </div>
            )}

          {!isLoading &&
            !error &&
            activeProfile &&
            resultsQuery.data?.length === 0 && (
              <div className="rounded-2xl border border-slate-800 bg-slate-900 p-8 text-center">
                <p className="font-semibold">
                  Aucun résultat trouvé
                </p>

                <p className="mt-2 text-sm text-slate-400">
                  Aucune offre analysée ne correspond au
                  filtre sélectionné pour{" "}
                  {activeProfile.full_name}.
                </p>
              </div>
            )}

          {!isLoading && !error && (
            <section className="grid gap-5">
              {resultsQuery.data
                // offersById ne contient que les offres qui ont passé le
                // filtre strict (priority_only=true) : alternance/stage,
                // moins de 24h, expérience 0-2 ans, jamais une offre
                // réservée à une école partenaire. Un résultat dont
                // l'offre n'y figure plus (CDI, doublon, etc.) est
                // donc écarté ici aussi, au lieu de rester visible.
                ?.filter((result) =>
                  offersById.has(result.offer_id),
                )
                .map((result) => (
                  <MatchResultCard
                    key={result.id}
                    result={result}
                    offer={offersById.get(
                      result.offer_id,
                    )}
                  />
                ))}
            </section>
          )}
        </div>
      </main>
    </AuthGuard>
  );
}
