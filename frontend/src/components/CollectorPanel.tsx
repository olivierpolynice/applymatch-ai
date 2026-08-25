"use client";

import {
  useMutation,
  useQueryClient,
} from "@tanstack/react-query";

import { apiRequest } from "@/lib/api";
import type { CollectorRunResult } from "@/types";

export default function CollectorPanel() {
  const queryClient = useQueryClient();

  const collectionMutation = useMutation({
    mutationFn: () =>
      apiRequest<CollectorRunResult>(
        "/collectors/run-all",
        {
          method: "POST",
        },
      ),
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({
          queryKey: ["collector-runs"],
        }),
        queryClient.invalidateQueries({
          queryKey: ["job-offers"],
        }),
        queryClient.invalidateQueries({
          queryKey: ["match-results"],
        }),
        queryClient.invalidateQueries({
          queryKey: ["notifications"],
        }),
        queryClient.invalidateQueries({
          queryKey: ["notification-unread-count"],
        }),
        queryClient.invalidateQueries({
          queryKey: ["validation-queue"],
        }),
      ]);
    },
  });

  const result = collectionMutation.data;

  return (
    <section
      id="collector"
      className="mb-8 scroll-mt-6 rounded-2xl border border-cyan-900 bg-slate-900 p-6"
    >
      <div className="flex flex-col gap-5 lg:flex-row lg:items-start lg:justify-between">
        <div>
          <p className="text-sm font-semibold uppercase tracking-[0.25em] text-cyan-400">
            Collecte multi-sources
          </p>

          <h2 className="mt-2 text-2xl font-bold">
            Recherche automatique d’offres
          </h2>

          <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-400">
            Recherche sur La Bonne Alternance, France
            Travail et Jooble. Les doublons sont ignorés
            et les nouvelles offres sont analysées
            automatiquement. Aucune candidature n’est
            envoyée.
          </p>
        </div>

        <button
          type="button"
          onClick={() => collectionMutation.mutate()}
          disabled={collectionMutation.isPending}
          className="shrink-0 rounded-xl bg-cyan-500 px-6 py-3 font-semibold text-slate-950 transition hover:bg-cyan-400 disabled:cursor-not-allowed disabled:opacity-60"
        >
          {collectionMutation.isPending
            ? "Collecte en cours..."
            : "Lancer toutes les collectes"}
        </button>
      </div>

      {collectionMutation.isError && (
        <div
          role="alert"
          className="mt-6 rounded-xl border border-red-800 bg-red-950/40 p-4 text-sm text-red-300"
        >
          Échec de la collecte :{" "}
          {collectionMutation.error instanceof Error
            ? collectionMutation.error.message
            : "erreur inconnue"}
        </div>
      )}

      {collectionMutation.isSuccess && result && (
        <div
          role="status"
          className="mt-6"
        >
          <p className="mb-4 rounded-xl border border-emerald-800 bg-emerald-950/30 p-4 text-sm text-emerald-300">
            Collecte terminée. Le dashboard a été
            actualisé automatiquement.
          </p>

          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <ResultCard
              label="Trouvées"
              value={result.found}
              color="text-cyan-300"
            />

            <ResultCard
              label="Ajoutées"
              value={result.added}
              color="text-emerald-300"
            />

            <ResultCard
              label="Doublons"
              value={result.duplicates}
              color="text-amber-300"
            />

            <ResultCard
              label="Erreurs"
              value={result.errors}
              color={
                result.errors > 0
                  ? "text-red-300"
                  : "text-slate-200"
              }
            />
          </div>
        </div>
      )}
    </section>
  );
}

interface ResultCardProps {
  label: string;
  value: number;
  color: string;
}

function ResultCard({
  label,
  value,
  color,
}: ResultCardProps) {
  return (
    <article className="rounded-xl border border-slate-800 bg-slate-950 p-4">
      <p className="text-xs font-medium uppercase tracking-wider text-slate-500">
        {label}
      </p>

      <p className={`mt-2 text-3xl font-bold ${color}`}>
        {value}
      </p>
    </article>
  );
}