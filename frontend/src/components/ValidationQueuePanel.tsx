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
  ApplicationDraftCreate,
  JobOffer,
  ValidationDecision,
  ValidationQueueDecisionUpdate,
  ValidationQueueItem,
  ValidationQueueStatus,
} from "@/types";

interface ValidationQueuePanelProps {
  offers: JobOffer[];
}

interface DecisionVariables {
  itemId: number;
  decision: ValidationDecision;
  reviewerComment: string | null;
}

function getStatusLabel(
  status: ValidationQueueStatus,
): string {
  const labels: Record<
    ValidationQueueStatus,
    string
  > = {
    pending: "En attente",
    approved: "Approuvée",
    rejected: "Rejetée",
    archived: "Archivée",
  };

  return labels[status];
}

function getStatusClasses(
  status: ValidationQueueStatus,
): string {
  const classes: Record<
    ValidationQueueStatus,
    string
  > = {
    pending:
      "border-amber-800 bg-amber-950/50 text-amber-300",
    approved:
      "border-emerald-800 bg-emerald-950/50 text-emerald-300",
    rejected:
      "border-red-800 bg-red-950/50 text-red-300",
    archived:
      "border-slate-700 bg-slate-950 text-slate-400",
  };

  return classes[status];
}

function getPriorityLabel(priority: string): string {
  const labels: Record<string, string> = {
    high: "Haute",
    medium: "Moyenne",
    low: "Faible",
  };

  return labels[priority] ?? priority;
}

function getPriorityClasses(
  priority: string,
): string {
  if (priority === "high") {
    return "border-red-800 bg-red-950/50 text-red-300";
  }

  if (priority === "medium") {
    return "border-amber-800 bg-amber-950/50 text-amber-300";
  }

  return "border-slate-700 bg-slate-950 text-slate-400";
}

function formatDate(value: string | null): string {
  if (!value) {
    return "Non renseignée";
  }

  return new Intl.DateTimeFormat("fr-FR", {
    dateStyle: "short",
    timeStyle: "short",
  }).format(new Date(value));
}

export default function ValidationQueuePanel({
  offers,
}: ValidationQueuePanelProps) {
  const queryClient = useQueryClient();

  const [statusFilter, setStatusFilter] =
    useState<ValidationQueueStatus | "all">(
      "pending",
    );

  const [comments, setComments] = useState<
    Record<number, string>
  >({});

  const queueQuery = useQuery({
    queryKey: [
      "validation-queue",
      statusFilter,
    ],
    queryFn: () => {
      const query =
        statusFilter === "all"
          ? ""
          : `?status=${statusFilter}`;

      return apiRequest<ValidationQueueItem[]>(
        `/validation-queue${query}`,
      );
    },
    refetchInterval: 30_000,
  });

  const draftsQuery = useQuery({
    queryKey: ["application-drafts"],
    queryFn: () =>
      apiRequest<ApplicationDraft[]>(
        "/application-drafts",
      ),
  });

  const decisionMutation = useMutation({
    mutationFn: ({
      itemId,
      decision,
      reviewerComment,
    }: DecisionVariables) => {
      const data: ValidationQueueDecisionUpdate = {
        decision,
        reviewer_comment: reviewerComment,
      };

      return apiRequest<ValidationQueueItem>(
        `/validation-queue/${itemId}/decision`,
        {
          method: "PATCH",
          body: JSON.stringify(data),
        },
      );
    },
    onSuccess: async (_, variables) => {
      setComments((currentComments) => {
        const nextComments = {
          ...currentComments,
        };

        delete nextComments[variables.itemId];

        return nextComments;
      });

      await Promise.all([
        queryClient.invalidateQueries({
          queryKey: ["validation-queue"],
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

  const generateDraftMutation = useMutation({
    mutationFn: (queueItemId: number) => {
      const data: ApplicationDraftCreate = {
        validation_queue_item_id: queueItemId,
      };

      return apiRequest<ApplicationDraft>(
        "/application-drafts",
        {
          method: "POST",
          body: JSON.stringify(data),
        },
      );
    },
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

  const offersById = new Map(
    offers.map((offer) => [
      offer.id,
      offer,
    ]),
  );

  const handleDecision = (
    item: ValidationQueueItem,
    decision: ValidationDecision,
  ) => {
    const reviewerComment =
      comments[item.id]?.trim() || null;

    decisionMutation.mutate({
      itemId: item.id,
      decision,
      reviewerComment,
    });
  };

  return (
    <section
      id="validation-queue"
      className="mb-8 scroll-mt-6 rounded-2xl border border-slate-800 bg-slate-900 p-6"
    >
      <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <p className="text-sm font-semibold uppercase tracking-[0.2em] text-violet-400">
            Contrôle humain
          </p>

          <h2 className="mt-2 text-2xl font-bold">
            File de validation manuelle
          </h2>

          <p className="mt-2 max-w-2xl text-sm text-slate-400">
            Vérifie chaque opportunité avant
            d’autoriser la génération des documents.
            Aucune candidature n’est envoyée
            automatiquement.
          </p>
        </div>

        <label className="flex flex-col gap-2 text-sm text-slate-300">
          Statut

          <select
            value={statusFilter}
            onChange={(event) =>
              setStatusFilter(
                event.target.value as
                  | ValidationQueueStatus
                  | "all",
              )
            }
            className="rounded-lg border border-slate-700 bg-slate-950 px-3 py-2"
          >
            <option value="pending">
              En attente
            </option>

            <option value="approved">
              Approuvées
            </option>

            <option value="rejected">
              Rejetées
            </option>

            <option value="archived">
              Archivées
            </option>

            <option value="all">
              Toutes
            </option>
          </select>
        </label>
      </div>

      {queueQuery.isLoading && (
        <p className="mt-6 text-sm text-slate-400">
          Chargement de la file de validation...
        </p>
      )}

      {queueQuery.isError && (
        <p className="mt-6 rounded-xl border border-red-900 bg-red-950/40 p-4 text-sm text-red-300">
          Impossible de charger la file :{" "}
          {queueQuery.error instanceof Error
            ? queueQuery.error.message
            : "erreur inconnue"}
        </p>
      )}

      {decisionMutation.isError && (
        <p className="mt-6 rounded-xl border border-red-900 bg-red-950/40 p-4 text-sm text-red-300">
          Impossible d’enregistrer la décision :{" "}
          {decisionMutation.error instanceof Error
            ? decisionMutation.error.message
            : "erreur inconnue"}
        </p>
      )}

      {!queueQuery.isLoading &&
        !queueQuery.isError &&
        queueQuery.data?.length === 0 && (
          <p className="mt-6 rounded-xl border border-slate-800 bg-slate-950 p-5 text-sm text-slate-400">
            Aucune candidature ne correspond à ce
            statut.
          </p>
        )}

      {queueQuery.data &&
        queueQuery.data.length > 0 && (
          <div className="mt-6 grid gap-4">
            {queueQuery.data.map((item) => {
              const offer = offersById.get(
                item.offer_id,
              );

              const isPending =
                item.status === "pending";

              const isThisItemPending =
                decisionMutation.isPending &&
                decisionMutation.variables
                  ?.itemId === item.id;

              const existingDraft =
                draftsQuery.data?.find(
                  (draft) =>
                    draft.validation_queue_item_id ===
                    item.id,
                );

              const isThisDraftGenerating =
                generateDraftMutation.isPending &&
                generateDraftMutation.variables ===
                  item.id;

              const isThisDraftError =
                generateDraftMutation.isError &&
                generateDraftMutation.variables ===
                  item.id;

              return (
                <article
                  key={item.id}
                  id={`validation-${item.id}`}
                  className="scroll-mt-6 rounded-xl border border-slate-800 bg-slate-950 p-5"
                >
                  <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
                    <div>
                      <p className="text-sm font-medium text-cyan-400">
                        {offer?.company ??
                          "Entreprise inconnue"}
                      </p>

                      <h3 className="mt-1 text-lg font-bold">
                        {offer?.title ??
                          `Offre numéro ${item.offer_id}`}
                      </h3>

                      <p className="mt-2 text-sm text-slate-400">
                        {offer?.location ??
                          "Localisation inconnue"}
                        {" · "}
                        {offer?.contract_type ??
                          "Contrat non renseigné"}
                      </p>
                    </div>

                    <div className="flex flex-wrap gap-2">
                      <span
                        className={`rounded-full border px-3 py-1 text-xs font-semibold ${getStatusClasses(
                          item.status,
                        )}`}
                      >
                        {getStatusLabel(
                          item.status,
                        )}
                      </span>

                      <span
                        className={`rounded-full border px-3 py-1 text-xs font-semibold ${getPriorityClasses(
                          item.priority,
                        )}`}
                      >
                        Priorité{" "}
                        {getPriorityLabel(
                          item.priority,
                        )}
                      </span>
                    </div>
                  </div>

                  <div className="mt-4 grid gap-2 text-sm text-slate-400 sm:grid-cols-2">
                    <p>
                      Ajoutée le :{" "}
                      {formatDate(item.created_at)}
                    </p>

                    {item.decided_at && (
                      <p>
                        Décidée le :{" "}
                        {formatDate(
                          item.decided_at,
                        )}
                      </p>
                    )}
                  </div>

                  {isPending ? (
                    <div className="mt-5">
                      <label
                        htmlFor={`comment-${item.id}`}
                        className="text-sm font-medium text-slate-300"
                      >
                        Commentaire du vérificateur
                      </label>

                      <textarea
                        id={`comment-${item.id}`}
                        value={
                          comments[item.id] ?? ""
                        }
                        onChange={(event) =>
                          setComments(
                            (currentComments) => ({
                              ...currentComments,
                              [item.id]:
                                event.target.value,
                            }),
                          )
                        }
                        rows={3}
                        placeholder="Ajoute un commentaire facultatif avant de décider..."
                        className="mt-2 w-full resize-y rounded-xl border border-slate-700 bg-slate-900 px-4 py-3 text-sm text-slate-100 outline-none transition placeholder:text-slate-600 focus:border-cyan-500"
                      />

                      <div className="mt-4 flex flex-wrap gap-3">
                        <button
                          type="button"
                          disabled={
                            decisionMutation.isPending
                          }
                          onClick={() =>
                            handleDecision(
                              item,
                              "approved",
                            )
                          }
                          className="rounded-lg bg-emerald-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-emerald-500 disabled:cursor-not-allowed disabled:opacity-50"
                        >
                          {isThisItemPending &&
                          decisionMutation.variables
                            ?.decision ===
                            "approved"
                            ? "Approbation..."
                            : "Approuver"}
                        </button>

                        <button
                          type="button"
                          disabled={
                            decisionMutation.isPending
                          }
                          onClick={() =>
                            handleDecision(
                              item,
                              "rejected",
                            )
                          }
                          className="rounded-lg bg-red-700 px-4 py-2 text-sm font-semibold text-white transition hover:bg-red-600 disabled:cursor-not-allowed disabled:opacity-50"
                        >
                          {isThisItemPending &&
                          decisionMutation.variables
                            ?.decision ===
                            "rejected"
                            ? "Rejet..."
                            : "Rejeter"}
                        </button>
                      </div>

                      <p className="mt-3 text-xs text-amber-300">
                        La génération des documents
                        reste bloquée tant que cette
                        candidature n’est pas approuvée.
                      </p>
                    </div>
                  ) : (
                    <div className="mt-5 rounded-lg border border-slate-800 bg-slate-900 p-4">
                      <p className="text-sm font-semibold text-slate-300">
                        Commentaire
                      </p>

                      <p className="mt-2 whitespace-pre-wrap text-sm text-slate-400">
                        {item.reviewer_comment ||
                          "Aucun commentaire."}
                      </p>

                      {item.status ===
                        "approved" && (
                        <div className="mt-4 border-t border-slate-800 pt-4">
                          {existingDraft ? (
                            <div className="rounded-lg border border-emerald-900 bg-emerald-950/40 p-3 text-sm text-emerald-300">
                              Le brouillon version{" "}
                              {existingDraft.version} est
                              disponible dans la section
                              « Brouillons de candidature ».
                            </div>
                          ) : (
                            <>
                              <p className="text-sm text-emerald-300">
                                Cette candidature est
                                approuvée. Tu peux maintenant
                                générer ses documents.
                              </p>

                              <button
                                type="button"
                                disabled={
                                  generateDraftMutation.isPending ||
                                  draftsQuery.isLoading
                                }
                                onClick={() =>
                                  generateDraftMutation.mutate(
                                    item.id,
                                  )
                                }
                                className="mt-3 rounded-lg bg-violet-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-violet-500 disabled:cursor-not-allowed disabled:opacity-50"
                              >
                                {isThisDraftGenerating
                                  ? "Génération..."
                                  : "Générer le brouillon"}
                              </button>
                            </>
                          )}

                          {isThisDraftError && (
                            <p className="mt-3 rounded-lg border border-red-900 bg-red-950/40 p-3 text-sm text-red-300">
                              Impossible de générer le
                              brouillon :{" "}
                              {generateDraftMutation.error instanceof
                              Error
                                ? generateDraftMutation.error
                                    .message
                                : "erreur inconnue"}
                            </p>
                          )}

                          <p className="mt-3 text-xs text-amber-300">
                            La génération prépare uniquement
                            les textes. Aucun document n’est
                            envoyé automatiquement.
                          </p>
                        </div>
                      )}
                    </div>
                  )}
                </article>
              );
            })}
          </div>
        )}
    </section>
  );
}