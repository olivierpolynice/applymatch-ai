"use client";

import {
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";
import { useState } from "react";

import { apiRequest } from "@/lib/api";
import type {
  ApplicationDraft,
  ApplicationDraftStatus,
  ApplicationDraftUpdate,
  JobOffer,
} from "@/types";

interface ApplicationDraftsPanelProps {
  profileId: number;
  offers: JobOffer[];
}

function getStatusLabel(
  status: ApplicationDraftStatus,
): string {
  const labels: Record<
    ApplicationDraftStatus,
    string
  > = {
    draft: "Brouillon",
    reviewed: "Vérifié",
    archived: "Archivé",
  };

  return labels[status];
}

function getStatusClasses(
  status: ApplicationDraftStatus,
): string {
  const classes: Record<
    ApplicationDraftStatus,
    string
  > = {
    draft:
      "border-amber-800 bg-amber-950/50 text-amber-300",
    reviewed:
      "border-emerald-800 bg-emerald-950/50 text-emerald-300",
    archived:
      "border-slate-700 bg-slate-950 text-slate-400",
  };

  return classes[status];
}

function formatDate(value: string): string {
  return new Intl.DateTimeFormat("fr-FR", {
    dateStyle: "short",
    timeStyle: "short",
  }).format(new Date(value));
}

export default function ApplicationDraftsPanel({
  profileId,
  offers,
}: ApplicationDraftsPanelProps) {
  const [statusFilter, setStatusFilter] =
    useState<ApplicationDraftStatus | "all">(
      "all",
    );

  const draftsQuery = useQuery({
    queryKey: [
      "application-drafts",
      profileId,
      statusFilter,
    ],
    queryFn: () => {
      const parameters = new URLSearchParams({
        profile_id: String(profileId),
      });

      if (statusFilter !== "all") {
        parameters.set(
          "status",
          statusFilter,
        );
      }

      return apiRequest<ApplicationDraft[]>(
        `/application-drafts?${parameters.toString()}`,
      );
    },
  });

  const offersById = new Map(
    offers.map((offer) => [
      offer.id,
      offer,
    ]),
  );

  return (
    <section
      id="application-drafts"
      className="mb-8 scroll-mt-6 rounded-2xl border border-slate-800 bg-slate-900 p-6"
    >
      <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <p className="text-sm font-semibold uppercase tracking-[0.2em] text-emerald-400">
            Documents
          </p>

          <h2 className="mt-2 text-2xl font-bold">
            Brouillons de candidature
          </h2>

          <p className="mt-2 max-w-2xl text-sm text-slate-400">
            Vérifie et adapte chaque document avant
            de l’utiliser. ApplyMatch AI ne transmet
            aucun document et n’envoie aucune
            candidature automatiquement.
          </p>
        </div>

        <label className="flex flex-col gap-2 text-sm text-slate-300">
          Statut

          <select
            value={statusFilter}
            onChange={(event) =>
              setStatusFilter(
                event.target.value as
                  | ApplicationDraftStatus
                  | "all",
              )
            }
            className="rounded-lg border border-slate-700 bg-slate-950 px-3 py-2"
          >
            <option value="all">
              Tous
            </option>

            <option value="draft">
              Brouillons
            </option>

            <option value="reviewed">
              Vérifiés
            </option>

            <option value="archived">
              Archivés
            </option>
          </select>
        </label>
      </div>

      <div className="mt-5 rounded-xl border border-cyan-900 bg-cyan-950/30 p-4 text-sm text-cyan-200">
        Aucun envoi automatique : les textes
        affichés ici restent des brouillons jusqu’à
        une action manuelle de ta part.
      </div>

      {draftsQuery.isLoading && (
        <p className="mt-6 text-sm text-slate-400">
          Chargement des brouillons...
        </p>
      )}

      {draftsQuery.isError && (
        <p className="mt-6 rounded-xl border border-red-900 bg-red-950/40 p-4 text-sm text-red-300">
          Impossible de charger les brouillons :{" "}
          {draftsQuery.error instanceof Error
            ? draftsQuery.error.message
            : "erreur inconnue"}
        </p>
      )}

      {!draftsQuery.isLoading &&
        !draftsQuery.isError &&
        draftsQuery.data?.length === 0 && (
          <p className="mt-6 rounded-xl border border-slate-800 bg-slate-950 p-5 text-sm text-slate-400">
            Aucun brouillon disponible. Une
            candidature doit d’abord être approuvée
            dans la file de validation.
          </p>
        )}

      {draftsQuery.data &&
        draftsQuery.data.length > 0 && (
          <div className="mt-6 grid gap-6">
            {draftsQuery.data.map((draft) => (
              <DraftCard
                key={`${draft.id}-${draft.version}-${draft.updated_at}`}
                draft={draft}
                offer={offersById.get(
                  draft.offer_id,
                )}
              />
            ))}
          </div>
        )}
    </section>
  );
}

interface DraftCardProps {
  draft: ApplicationDraft;
  offer?: JobOffer;
}

function DraftCard({
  draft,
  offer,
}: DraftCardProps) {
  const queryClient = useQueryClient();

  const [coverLetter, setCoverLetter] =
    useState(draft.cover_letter);

  const [shortMessage, setShortMessage] =
    useState(draft.short_message);

  const [
    cvAdaptationTips,
    setCvAdaptationTips,
  ] = useState(draft.cv_adaptation_tips);

  const [status, setStatus] =
    useState<ApplicationDraftStatus>(
      draft.status,
    );

  const updateMutation = useMutation({
    mutationFn: () => {
      const data: ApplicationDraftUpdate = {
        cover_letter: coverLetter,
        short_message: shortMessage,
        cv_adaptation_tips:
          cvAdaptationTips,
        status,
      };

      return apiRequest<ApplicationDraft>(
        `/application-drafts/${draft.id}`,
        {
          method: "PATCH",
          body: JSON.stringify(data),
        },
      );
    },
    onSuccess: async () => {
      await queryClient.invalidateQueries({
        queryKey: ["application-drafts"],
      });
    },
  });

  const regenerateMutation = useMutation({
    mutationFn: () =>
      apiRequest<ApplicationDraft>(
        `/application-drafts/${draft.id}/regenerate`,
        {
          method: "POST",
        },
      ),
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({
          queryKey: ["application-drafts"],
        }),
        queryClient.invalidateQueries({
          queryKey: ["notifications"],
        }),
        queryClient.invalidateQueries({
          queryKey: [
            "notifications-unread-count",
          ],
        }),
      ]);
    },
  });

  const hasChanges =
    coverLetter !== draft.cover_letter ||
    shortMessage !== draft.short_message ||
    cvAdaptationTips !==
      draft.cv_adaptation_tips ||
    status !== draft.status;

  const handleRegenerate = () => {
    const confirmed = window.confirm(
      "La régénération remplacera les modifications non enregistrées par une nouvelle version. Continuer ?",
    );

    if (confirmed) {
      regenerateMutation.mutate();
    }
  };

  return (
    <article
      id={`draft-${draft.id}-version-${draft.version}`}
      className="scroll-mt-6 rounded-xl border border-slate-800 bg-slate-950 p-5"
    >
      <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
        <div>
          <p className="text-sm font-medium text-cyan-400">
            {offer?.company ??
              "Entreprise inconnue"}
          </p>

          <h3 className="mt-1 text-xl font-bold">
            {offer?.title ??
              `Offre numéro ${draft.offer_id}`}
          </h3>

          <p className="mt-2 text-sm text-slate-400">
            Version {draft.version}
            {" · "}
            générée le{" "}
            {formatDate(draft.generated_at)}
          </p>
        </div>

        <span
          className={`w-fit rounded-full border px-3 py-1 text-xs font-semibold ${getStatusClasses(
            draft.status,
          )}`}
        >
          {getStatusLabel(draft.status)}
        </span>
      </div>

      <div className="mt-6 grid gap-6">
        <label className="grid gap-2">
          <span className="text-sm font-semibold text-slate-300">
            Lettre de motivation
          </span>

          <textarea
            value={coverLetter}
            onChange={(event) =>
              setCoverLetter(
                event.target.value,
              )
            }
            rows={18}
            className="w-full resize-y rounded-xl border border-slate-700 bg-slate-900 px-4 py-3 text-sm leading-6 text-slate-100 outline-none transition focus:border-cyan-500"
          />
        </label>

        <label className="grid gap-2">
          <span className="text-sm font-semibold text-slate-300">
            Message court au recruteur
          </span>

          <textarea
            value={shortMessage}
            onChange={(event) =>
              setShortMessage(
                event.target.value,
              )
            }
            rows={6}
            className="w-full resize-y rounded-xl border border-slate-700 bg-slate-900 px-4 py-3 text-sm leading-6 text-slate-100 outline-none transition focus:border-cyan-500"
          />
        </label>

        <label className="grid gap-2">
          <span className="text-sm font-semibold text-slate-300">
            Conseils d’adaptation du CV
          </span>

          <textarea
            value={cvAdaptationTips}
            onChange={(event) =>
              setCvAdaptationTips(
                event.target.value,
              )
            }
            rows={9}
            className="w-full resize-y rounded-xl border border-slate-700 bg-slate-900 px-4 py-3 text-sm leading-6 text-slate-100 outline-none transition focus:border-cyan-500"
          />
        </label>

        <label className="flex flex-col gap-2 text-sm text-slate-300 sm:max-w-xs">
          Statut du document

          <select
            value={status}
            onChange={(event) =>
              setStatus(
                event.target
                  .value as ApplicationDraftStatus,
              )
            }
            className="rounded-lg border border-slate-700 bg-slate-900 px-3 py-2"
          >
            <option value="draft">
              Brouillon
            </option>

            <option value="reviewed">
              Vérifié
            </option>

            <option value="archived">
              Archivé
            </option>
          </select>
        </label>
      </div>

      {updateMutation.isError && (
        <p className="mt-4 rounded-lg border border-red-900 bg-red-950/40 p-3 text-sm text-red-300">
          Impossible d’enregistrer :{" "}
          {updateMutation.error instanceof Error
            ? updateMutation.error.message
            : "erreur inconnue"}
        </p>
      )}

      {regenerateMutation.isError && (
        <p className="mt-4 rounded-lg border border-red-900 bg-red-950/40 p-3 text-sm text-red-300">
          Impossible de régénérer :{" "}
          {regenerateMutation.error instanceof Error
            ? regenerateMutation.error.message
            : "erreur inconnue"}
        </p>
      )}

      {updateMutation.isSuccess &&
        !hasChanges && (
          <p className="mt-4 rounded-lg border border-emerald-900 bg-emerald-950/40 p-3 text-sm text-emerald-300">
            Les modifications sont enregistrées.
          </p>
        )}

      {regenerateMutation.isSuccess && (
        <p className="mt-4 rounded-lg border border-cyan-900 bg-cyan-950/40 p-3 text-sm text-cyan-300">
          Une nouvelle version du brouillon a été
          générée.
        </p>
      )}

      <div className="mt-5 flex flex-wrap gap-3">
        <button
          type="button"
          disabled={
            !hasChanges ||
            updateMutation.isPending ||
            regenerateMutation.isPending
          }
          onClick={() =>
            updateMutation.mutate()
          }
          className="rounded-lg bg-emerald-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-emerald-500 disabled:cursor-not-allowed disabled:opacity-50"
        >
          {updateMutation.isPending
            ? "Enregistrement..."
            : "Enregistrer les modifications"}
        </button>

        <button
          type="button"
          disabled={
            updateMutation.isPending ||
            regenerateMutation.isPending
          }
          onClick={handleRegenerate}
          className="rounded-lg border border-violet-700 bg-violet-950/40 px-4 py-2 text-sm font-semibold text-violet-200 transition hover:bg-violet-900/60 disabled:cursor-not-allowed disabled:opacity-50"
        >
          {regenerateMutation.isPending
            ? "Régénération..."
            : "Régénérer une nouvelle version"}
        </button>
      </div>

      <p className="mt-4 text-xs text-amber-300">
        Enregistrer ou régénérer ce brouillon ne
        transmet aucun document à l’entreprise.
      </p>
    </article>
  );
}