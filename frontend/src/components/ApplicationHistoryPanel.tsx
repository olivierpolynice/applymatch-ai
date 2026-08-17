"use client";

import { useMemo, useState } from "react";

import type { JobOffer } from "@/types";

interface ApplicationHistoryPanelProps {
  offers: JobOffer[];
}

export default function ApplicationHistoryPanel({
  offers,
}: ApplicationHistoryPanelProps) {
  const [search, setSearch] = useState("");

  const applications = useMemo(() => {
    const normalizedSearch = search.trim().toLocaleLowerCase("fr");

    return offers
      .filter((offer) => offer.status === "applied")
      .filter((offer) => {
        if (!normalizedSearch) {
          return true;
        }

        return [offer.title, offer.company, offer.location, offer.source]
          .join(" ")
          .toLocaleLowerCase("fr")
          .includes(normalizedSearch);
      })
      .sort((first, second) => {
        const firstDate = first.applied_at ?? first.updated_at;
        const secondDate = second.applied_at ?? second.updated_at;

        return Date.parse(secondDate) - Date.parse(firstDate);
      });
  }, [offers, search]);

  const totalApplications = offers.filter(
    (offer) => offer.status === "applied",
  ).length;

  return (
    <section
      id="application-history"
      className="mb-8 rounded-2xl border border-slate-800 bg-slate-900 p-6"
    >
      <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <p className="text-sm font-semibold uppercase tracking-[0.2em] text-emerald-400">
            Suivi manuel
          </p>
          <h2 className="mt-2 text-2xl font-bold">
            Historique des candidatures
          </h2>
          <p className="mt-2 text-sm text-slate-400">
            Les offres auxquelles tu as confirmé avoir postulé manuellement.
          </p>
        </div>

        <label className="grid gap-2 text-sm text-slate-300">
          Rechercher dans l’historique
          <input
            type="search"
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            placeholder="Poste, entreprise, lieu..."
            className="w-full rounded-lg border border-slate-700 bg-slate-950 px-4 py-2 lg:w-80"
          />
        </label>
      </div>

      <p className="mt-5 text-sm text-slate-400">
        {totalApplications} candidature
        {totalApplications > 1 ? "s" : ""} enregistrée
        {totalApplications > 1 ? "s" : ""}
      </p>

      {totalApplications === 0 && (
        <div className="mt-5 rounded-xl border border-slate-800 bg-slate-950 p-6 text-center text-slate-400">
          Aucune candidature enregistrée pour le moment.
        </div>
      )}

      {totalApplications > 0 && applications.length === 0 && (
        <div className="mt-5 rounded-xl border border-slate-800 bg-slate-950 p-6 text-center text-slate-400">
          Aucune candidature ne correspond à cette recherche.
        </div>
      )}

      {applications.length > 0 && (
        <div className="mt-5 grid gap-4">
          {applications.map((offer) => (
            <article
              key={offer.id}
              className="rounded-xl border border-slate-800 bg-slate-950 p-5"
            >
              <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
                <div>
                  <p className="text-sm font-medium text-cyan-400">
                    {offer.company}
                  </p>
                  <h3 className="mt-1 text-lg font-semibold">
                    {offer.title}
                  </h3>
                  <p className="mt-2 text-sm text-slate-400">
                    {offer.location} · {offer.contract_type} · {offer.source}
                  </p>
                  <p className="mt-2 text-sm text-emerald-300">
                    Candidature enregistrée le {formatDate(
                      offer.applied_at ?? offer.updated_at,
                    )}
                  </p>
                </div>

                {offer.source_url && (
                  <a
                    href={offer.source_url}
                    target="_blank"
                    rel="noreferrer"
                    className="shrink-0 rounded-lg border border-slate-700 px-4 py-2 text-sm font-semibold text-slate-200 transition hover:border-cyan-600 hover:text-cyan-300"
                  >
                    Revoir l’offre
                  </a>
                )}
              </div>
            </article>
          ))}
        </div>
      )}
    </section>
  );
}

function formatDate(value: string): string {
  return new Intl.DateTimeFormat("fr-FR", {
    dateStyle: "long",
    timeStyle: "short",
  }).format(new Date(value));
}
