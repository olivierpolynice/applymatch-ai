"use client";

import {
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";
import { useState } from "react";

import { apiRequest, downloadApiFile } from "@/lib/api";
import type {
  ApplicationDraft,
  ApplicationDocuments,
  ApplicationDraftStatus,
  ApplicationDraftUpdate,
  AutomationChannel,
  AutomationEvaluation,
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
            Documents de candidature
          </h2>

          <p className="mt-2 max-w-2xl text-sm text-slate-400">
            Vérifie les documents, ouvre l’offre pour postuler, puis confirme
            l’envoi afin de déplacer l’offre dans « Déjà postulé ».
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
        Sécurité par défaut : toute candidature non éligible passe dans la
        file d’approbation manuelle.
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
  const [automationChannel, setAutomationChannel] =
    useState<AutomationChannel>("unsupported");
  const [channelAuthorized, setChannelAuthorized] =
    useState(false);
  const [hasUnknownQuestions, setHasUnknownQuestions] =
    useState(false);

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

  const documentsMutation = useMutation({
    mutationFn: () =>
      apiRequest<ApplicationDocuments>(
        `/application-drafts/${draft.id}/documents`,
        { method: "POST" },
      ),
  });

  const automationMutation = useMutation({
    mutationFn: () =>
      apiRequest<AutomationEvaluation>(
        "/application-automation/evaluate",
        {
          method: "POST",
          body: JSON.stringify({
            draft_id: draft.id,
            channel: automationChannel,
            channel_authorized: channelAuthorized,
            has_unknown_questions: hasUnknownQuestions,
          }),
        },
      ),
  });

  const markAppliedMutation = useMutation({
    mutationFn: () =>
      apiRequest<JobOffer>(
        `/job-offers/${draft.offer_id}/mark-applied`,
        {
          method: "POST",
        },
      ),
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({
          queryKey: ["job-offers"],
        }),
        queryClient.invalidateQueries({
          queryKey: ["application-drafts"],
        }),
        queryClient.invalidateQueries({
          queryKey: ["application-archives"],
        }),
        queryClient.invalidateQueries({
          queryKey: ["validation-queue"],
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
  const generatedDocuments = documentsMutation.data;

  const handleRegenerate = () => {
    const confirmed = window.confirm(
      "La régénération remplacera les modifications non enregistrées par une nouvelle version. Continuer ?",
    );

    if (confirmed) {
      regenerateMutation.mutate();
    }
  };

  const handleMarkApplied = () => {
    const confirmed = window.confirm(
      "Confirmer que la candidature a réellement été envoyée à l’entreprise ?",
    );

    if (confirmed) {
      markAppliedMutation.mutate();
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

      {documentsMutation.isError && (
        <p className="mt-4 rounded-lg border border-red-900 bg-red-950/40 p-3 text-sm text-red-300">
          Impossible de générer les fichiers :{" "}
          {documentsMutation.error instanceof Error
            ? documentsMutation.error.message
            : "erreur inconnue"}
        </p>
      )}

      {generatedDocuments && (
        <div className={`mt-4 rounded-lg border p-4 text-sm ${
          generatedDocuments.validation.valid
            ? "border-emerald-800 bg-emerald-950/40 text-emerald-200"
            : "border-red-800 bg-red-950/40 text-red-200"
        }`}>
          <p className="font-semibold">
            {generatedDocuments.validation.valid
              ? "Documents générés et vérifiés automatiquement."
              : "Les documents contiennent des erreurs à corriger."}
          </p>
          {generatedDocuments.validation.errors.length > 0 && (
            <ul className="mt-2 list-disc pl-5">
              {generatedDocuments.validation.errors.map((error) => (
                <li key={error}>{error}</li>
              ))}
            </ul>
          )}
          {generatedDocuments.validation.valid && (
            <div className="mt-3 flex flex-wrap gap-2">
              <button type="button" onClick={() => downloadApiFile(
                generatedDocuments.cover_letter_pdf_url,
                "lettre-motivation.pdf",
              )} className="rounded-lg bg-violet-700 px-3 py-2 font-semibold text-white">
                Lettre PDF
              </button>
              <button type="button" onClick={() => downloadApiFile(
                generatedDocuments.cover_letter_docx_url,
                "lettre-motivation.docx",
              )} className="rounded-lg bg-blue-700 px-3 py-2 font-semibold text-white">
                Lettre Word
              </button>
              <button type="button" onClick={() => downloadApiFile(
                generatedDocuments.adapted_cv_pdf_url,
                "cv-adapte.pdf",
              )} className="rounded-lg bg-cyan-700 px-3 py-2 font-semibold text-white">
                CV adapté PDF
              </button>
            </div>
          )}
        </div>
      )}

      {markAppliedMutation.isError && (
        <p className="mt-4 rounded-lg border border-red-900 bg-red-950/40 p-3 text-sm text-red-300">
          Impossible d’archiver la candidature :{" "}
          {markAppliedMutation.error instanceof Error
            ? markAppliedMutation.error.message
            : "erreur inconnue"}
        </p>
      )}

      {markAppliedMutation.isSuccess && (
        <p className="mt-4 rounded-lg border border-emerald-900 bg-emerald-950/40 p-3 text-sm text-emerald-300">
          Candidature confirmée et déplacée dans « Déjà postulé ».
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

        <button
          type="button"
          disabled={documentsMutation.isPending || hasChanges}
          onClick={() => documentsMutation.mutate()}
          className="rounded-lg border border-cyan-700 bg-cyan-950/40 px-4 py-2 text-sm font-semibold text-cyan-200 transition hover:bg-cyan-900/60 disabled:cursor-not-allowed disabled:opacity-50"
        >
          {documentsMutation.isPending
            ? "Génération des fichiers..."
            : "Générer CV, Word et PDF"}
        </button>
      </div>

      {draft.status !== "archived" ? (
        <div className="mt-6 rounded-xl border border-cyan-800 bg-cyan-950/30 p-4">
          <h4 className="font-semibold text-cyan-100">
            Étape finale : envoyer la candidature
          </h4>
          <p className="mt-1 text-sm text-cyan-200">
            Ouvre l’offre, effectue l’envoi sur le site, puis confirme-le ici.
          </p>
          <div className="mt-4 flex flex-wrap gap-3">
            {offer?.source_url ? (
              <a
                href={offer.source_url}
                target="_blank"
                rel="noreferrer"
                className="rounded-lg border border-cyan-700 bg-slate-950 px-4 py-2 text-sm font-semibold text-cyan-200 transition hover:bg-cyan-950"
              >
                Voir et postuler
              </a>
            ) : (
              <span className="rounded-lg border border-amber-800 bg-amber-950/40 px-4 py-2 text-sm text-amber-300">
                Lien de candidature indisponible
              </span>
            )}
            <button
              type="button"
              onClick={handleMarkApplied}
              disabled={markAppliedMutation.isPending}
              className="rounded-lg bg-emerald-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-emerald-500 disabled:cursor-not-allowed disabled:opacity-50"
            >
              {markAppliedMutation.isPending
                ? "Confirmation..."
                : "Confirmer que j’ai postulé"}
            </button>
          </div>
        </div>
      ) : (
        <p className="mt-6 rounded-lg border border-slate-700 bg-slate-900 p-4 text-sm text-slate-300">
          Cette candidature est déjà classée dans « Déjà postulé ».
        </p>
      )}

      <div className="mt-6 rounded-xl border border-slate-700 bg-slate-900 p-4">
        <h4 className="font-semibold text-slate-100">
          Vérification de l’envoi automatique
        </h4>
        <p className="mt-1 text-sm text-slate-400">
          Le score, le métier, le contrat, la localisation, les compétences,
          les questions et le canal doivent tous être validés.
        </p>
        <div className="mt-4 grid gap-3 md:grid-cols-3">
          <select
            value={automationChannel}
            onChange={(event) =>
              setAutomationChannel(event.target.value as AutomationChannel)
            }
            className="rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm"
          >
            <option value="unsupported">Canal non compatible</option>
            <option value="official_api">API officielle</option>
            <option value="recruitment_email">E-mail recrutement</option>
            <option value="authorized_form">Formulaire autorisé</option>
          </select>
          <label className="flex items-center gap-2 text-sm text-slate-300">
            <input
              type="checkbox"
              checked={channelAuthorized}
              onChange={(event) => setChannelAuthorized(event.target.checked)}
            />
            Canal vérifié et autorisé
          </label>
          <label className="flex items-center gap-2 text-sm text-slate-300">
            <input
              type="checkbox"
              checked={hasUnknownQuestions}
              onChange={(event) => setHasUnknownQuestions(event.target.checked)}
            />
            Question inconnue présente
          </label>
        </div>
        <button
          type="button"
          onClick={() => automationMutation.mutate()}
          disabled={automationMutation.isPending}
          className="mt-4 rounded-lg bg-cyan-700 px-4 py-2 text-sm font-semibold text-white hover:bg-cyan-600 disabled:opacity-50"
        >
          {automationMutation.isPending
            ? "Vérification..."
            : "Vérifier les conditions"}
        </button>
        {automationMutation.data && (
          <div className={`mt-4 rounded-lg border p-3 text-sm ${
            automationMutation.data.eligible
              ? "border-emerald-800 bg-emerald-950/40 text-emerald-200"
              : "border-amber-800 bg-amber-950/40 text-amber-200"
          }`}>
            <p className="font-semibold">
              {automationMutation.data.eligible
                ? "Éligible à l’envoi automatique via un connecteur confirmé."
                : "Approbation manuelle obligatoire."}
            </p>
            {automationMutation.data.reasons.length > 0 && (
              <ul className="mt-2 list-disc pl-5">
                {automationMutation.data.reasons.map((reason) => (
                  <li key={reason}>{reason}</li>
                ))}
              </ul>
            )}
          </div>
        )}
      </div>

      <p className="mt-4 text-xs text-amber-300">
        Enregistrer ou régénérer ce brouillon ne
        transmet aucun document à l’entreprise.
      </p>
    </article>
  );
}
