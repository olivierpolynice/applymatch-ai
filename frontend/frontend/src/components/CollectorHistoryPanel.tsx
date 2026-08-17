"use client";

import { useQuery } from "@tanstack/react-query";

import { apiRequest } from "@/lib/api";
import type {
  CollectorRunHistory,
  CollectorRunStatus,
  CollectorTrigger,
} from "@/types";

function getStatusLabel(
  status: CollectorRunStatus,
): string {
  const labels: Record<CollectorRunStatus, string> = {
    running: "En cours",
    completed: "Terminée",
    failed: "Échec",
  };

  return labels[status];
}

function getStatusClasses(
  status: CollectorRunStatus,
): string {
  const classes: Record<CollectorRunStatus, string> = {
    running:
      "border-amber-800 bg-amber-950/40 text-amber-300",
    completed:
      "border-emerald-800 bg-emerald-950/40 text-emerald-300",
    failed:
      "border-red-800 bg-red-950/40 text-red-300",
  };

  return classes[status];
}

function getTriggerLabel(
  trigger: CollectorTrigger,
): string {
  const labels: Record<CollectorTrigger, string> = {
    manual: "Manuelle",
    scheduled: "Planifiée",
  };

  return labels[trigger];
}

function formatDate(value: string | null): string {
  if (!value) {
    return "En cours";
  }

  return new Intl.DateTimeFormat("fr-FR", {
    dateStyle: "short",
    timeStyle: "short",
  }).format(new Date(value));
}

export default function CollectorHistoryPanel() {
  const historyQuery = useQuery({
    queryKey: ["collector-runs"],
    queryFn: () =>
      apiRequest<CollectorRunHistory[]>(
        "/collectors/runs?limit=10",
      ),
    refetchInterval: 30_000,
  });

  return (
    <section
      id="collector-history"
      className="mb-8 scroll-mt-6 rounded-2xl border border-slate-800 bg-slate-900 p-6"
    >
      <div>
        <p className="text-sm font-semibold uppercase tracking-[0.2em] text-cyan-400">
          Automatisation
        </p>

        <h2 className="mt-2 text-2xl font-bold text-slate-100">
          Historique des collectes
        </h2>

        <p className="mt-2 text-sm text-slate-400">
          Dix dernières exécutions manuelles et
          planifiées.
        </p>
      </div>

      {historyQuery.isLoading && (
        <p className="mt-6 text-sm text-slate-400">
          Chargement de l’historique...
        </p>
      )}

      {historyQuery.isError && (
        <p className="mt-6 rounded-lg border border-red-900 bg-red-950/40 p-4 text-sm text-red-300">
          Impossible de charger l’historique :{" "}
          {historyQuery.error instanceof Error
            ? historyQuery.error.message
            : "erreur inconnue"}
        </p>
      )}

      {!historyQuery.isLoading &&
        !historyQuery.isError &&
        historyQuery.data?.length === 0 && (
          <p className="mt-6 rounded-xl border border-slate-800 bg-slate-950 p-5 text-sm text-slate-400">
            Aucune collecte enregistrée.
          </p>
        )}

      {historyQuery.data &&
        historyQuery.data.length > 0 && (
          <div className="mt-6 overflow-x-auto">
            <table className="min-w-full text-left text-sm">
              <thead className="border-b border-slate-700 text-xs uppercase tracking-wider text-slate-400">
                <tr>
                  <th className="px-3 py-3">
                    Collecteur
                  </th>

                  <th className="px-3 py-3">
                    Déclenchement
                  </th>

                  <th className="px-3 py-3">
                    Statut
                  </th>

                  <th className="px-3 py-3 text-right">
                    Trouvées
                  </th>

                  <th className="px-3 py-3 text-right">
                    Ajoutées
                  </th>

                  <th className="px-3 py-3 text-right">
                    Doublons
                  </th>

                  <th className="px-3 py-3 text-right">
                    Erreurs
                  </th>

                  <th className="px-3 py-3">
                    Démarrage
                  </th>

                  <th className="px-3 py-3">
                    Fin
                  </th>
                </tr>
              </thead>

              <tbody className="divide-y divide-slate-800">
                {historyQuery.data.map((run) => (
                  <tr
                    key={run.id}
                    className="text-slate-300 transition hover:bg-slate-800/50"
                  >
                    <td className="whitespace-nowrap px-3 py-4 font-medium text-slate-100">
                      {run.collector}
                    </td>

                    <td className="whitespace-nowrap px-3 py-4">
                      {getTriggerLabel(run.trigger)}
                    </td>

                    <td className="whitespace-nowrap px-3 py-4">
                      <span
                        className={`inline-flex rounded-full border px-2.5 py-1 text-xs font-semibold ${getStatusClasses(
                          run.status,
                        )}`}
                      >
                        {getStatusLabel(run.status)}
                      </span>
                    </td>

                    <td className="px-3 py-4 text-right">
                      {run.found}
                    </td>

                    <td className="px-3 py-4 text-right text-emerald-300">
                      {run.added}
                    </td>

                    <td className="px-3 py-4 text-right">
                      {run.duplicates}
                    </td>

                    <td className="px-3 py-4 text-right text-red-300">
                      {run.errors}
                    </td>

                    <td className="whitespace-nowrap px-3 py-4">
                      {formatDate(run.started_at)}
                    </td>

                    <td className="whitespace-nowrap px-3 py-4">
                      {formatDate(run.finished_at)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>

            {historyQuery.data.some(
              (run) => run.error_message,
            ) && (
              <div className="mt-5 space-y-2">
                {historyQuery.data
                  .filter((run) => run.error_message)
                  .map((run) => (
                    <p
                      key={`error-${run.id}`}
                      className="rounded-lg border border-red-900 bg-red-950/30 p-3 text-sm text-red-300"
                    >
                      <span className="font-semibold">
                        Collecte #{run.id} :
                      </span>{" "}
                      {run.error_message}
                    </p>
                  ))}
              </div>
            )}
          </div>
        )}
    </section>
  );
}