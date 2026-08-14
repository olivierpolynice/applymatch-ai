"use client";

import {
  useMutation,
  useQueryClient,
} from "@tanstack/react-query";

import { apiRequest } from "@/lib/api";
import type { CollectorRunResult } from "@/types";

export default function CollectorPanel() {
  const queryClient = useQueryClient();

  const collectorMutation = useMutation({
    mutationFn: () =>
      apiRequest<CollectorRunResult>(
        "/collectors/la-bonne-alternance/run",
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
          queryKey: ["match-results"],
        }),
      ]);
    },
  });

  const result = collectorMutation.data;

  return (
    <section className="mb-8 rounded-2xl border border-cyan-900 bg-slate-900 p-6">
      <div className="flex flex-col gap-5 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <p className="text-sm font-semibold uppercase tracking-[0.2em] text-cyan-400">
            Collecteur automatique
          </p>

          <h2 className="mt-2 text-xl font-semibold">
            La Bonne Alternance
          </h2>

          <p className="mt-2 max-w-2xl text-sm text-slate-400">
            Recherche les nouvelles offres d’alternance, les
            enregistre et ignore automatiquement les doublons.
            Aucune candidature n’est envoyée.
          </p>
        </div>

        <button
          type="button"
          disabled={collectorMutation.isPending}
          onClick={() => collectorMutation.mutate()}
          className="shrink-0 rounded-lg bg-cyan-500 px-5 py-3 font-semibold text-slate-950 transition hover:bg-cyan-400 disabled:cursor-not-allowed disabled:opacity-50"
        >
          {collectorMutation.isPending
            ? "Collecte en cours..."
            : "Lancer la collecte"}
        </button>
      </div>

      {result && (
        <div className="mt-6 grid gap-3 sm:grid-cols-4">
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
                : "text-slate-300"
            }
          />
        </div>
      )}

      {collectorMutation.error && (
        <p className="mt-5 rounded-lg border border-red-900 bg-red-950/40 p-4 text-sm text-red-300">
          Échec de la collecte :{" "}
          {collectorMutation.error instanceof Error
            ? collectorMutation.error.message
            : "erreur inconnue"}
        </p>
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
      <p className="text-xs uppercase tracking-wider text-slate-500">
        {label}
      </p>

      <p className={`mt-2 text-2xl font-bold ${color}`}>
        {value}
      </p>
    </article>
  );
}