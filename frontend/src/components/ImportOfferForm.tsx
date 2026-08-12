"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { FormEvent, useState } from "react";

import { apiRequest } from "@/lib/api";
import type {
  JobOffer,
  JobOfferCreate,
  MatchResponse,
} from "@/types";

interface ImportOfferFormProps {
  profileId: number;
}

const INITIAL_FORM: JobOfferCreate = {
  title: "",
  company: "",
  location: "Paris, Île-de-France",
  contract_type: "Alternance",
  description: "",
  source: "Import manuel",
  source_url: "",
  published_at: null,
};

export default function ImportOfferForm({
  profileId,
}: ImportOfferFormProps) {
  const queryClient = useQueryClient();
  const [form, setForm] = useState<JobOfferCreate>(INITIAL_FORM);
  const [successMessage, setSuccessMessage] = useState("");

  const importMutation = useMutation({
    mutationFn: async (offerData: JobOfferCreate) => {
      const offer = await apiRequest<JobOffer>("/job-offers", {
        method: "POST",
        body: JSON.stringify(offerData),
      });

      const matching = await apiRequest<MatchResponse>(
        `/matching/profile/${profileId}/offer/${offer.id}`,
        { method: "POST" },
      );

      return { offer, matching };
    },

    onSuccess: async ({ offer, matching }) => {
      setSuccessMessage(
        `${offer.title} importée et analysée : ${matching.score}/100`,
      );
      setForm(INITIAL_FORM);

      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["job-offers"] }),
        queryClient.invalidateQueries({ queryKey: ["match-results"] }),
      ]);
    },

    onError: () => {
      setSuccessMessage("");
    },
  });

  function updateField(field: keyof JobOfferCreate, value: string) {
    setForm((current) => ({
      ...current,
      [field]: value,
    }));
  }

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSuccessMessage("");
    importMutation.mutate(form);
  }

  return (
    <section className="mb-8 rounded-2xl border border-slate-800 bg-slate-900 p-6">
      <div className="mb-6">
        <h2 className="text-xl font-semibold">
          Importer une nouvelle offre
        </h2>
        <p className="mt-1 text-sm text-slate-400">
          L’offre sera enregistrée puis analysée automatiquement. Aucune
          candidature ne sera envoyée.
        </p>
      </div>

      <form
        onSubmit={handleSubmit}
        className="grid gap-4 md:grid-cols-2"
      >
        <label className="grid gap-2 text-sm">
          Intitulé du poste
          <input
            required
            minLength={2}
            value={form.title}
            onChange={(event) => updateField("title", event.target.value)}
            className="rounded-lg border border-slate-700 bg-slate-950 px-3 py-2"
            placeholder="Alternance administrateur cybersécurité"
          />
        </label>

        <label className="grid gap-2 text-sm">
          Entreprise
          <input
            required
            minLength={2}
            value={form.company}
            onChange={(event) => updateField("company", event.target.value)}
            className="rounded-lg border border-slate-700 bg-slate-950 px-3 py-2"
            placeholder="Nom de l’entreprise"
          />
        </label>

        <label className="grid gap-2 text-sm">
          Localisation
          <input
            required
            minLength={2}
            value={form.location}
            onChange={(event) => updateField("location", event.target.value)}
            className="rounded-lg border border-slate-700 bg-slate-950 px-3 py-2"
            placeholder="Paris, Île-de-France"
          />
        </label>

        <label className="grid gap-2 text-sm">
          Type de contrat
          <select
            value={form.contract_type}
            onChange={(event) =>
              updateField("contract_type", event.target.value)
            }
            className="rounded-lg border border-slate-700 bg-slate-950 px-3 py-2"
          >
            <option value="Alternance">Alternance</option>
            <option value="Stage">Stage</option>
            <option value="CDI">CDI</option>
            <option value="CDD">CDD</option>
          </select>
        </label>

        <label className="grid gap-2 text-sm">
          Source
          <input
            required
            minLength={2}
            value={form.source}
            onChange={(event) => updateField("source", event.target.value)}
            className="rounded-lg border border-slate-700 bg-slate-950 px-3 py-2"
            placeholder="LinkedIn, APEC..."
          />
        </label>

        <label className="grid gap-2 text-sm">
          Lien de l’offre
          <input
            required
            type="url"
            minLength={5}
            value={form.source_url}
            onChange={(event) =>
              updateField("source_url", event.target.value)
            }
            className="rounded-lg border border-slate-700 bg-slate-950 px-3 py-2"
            placeholder="https://..."
          />
        </label>

        <label className="grid gap-2 text-sm md:col-span-2">
          Description complète
          <textarea
            required
            minLength={10}
            rows={8}
            value={form.description}
            onChange={(event) =>
              updateField("description", event.target.value)
            }
            className="resize-y rounded-lg border border-slate-700 bg-slate-950 px-3 py-2"
            placeholder="Colle ici la description de l’offre..."
          />
        </label>

        <div className="md:col-span-2">
          <button
            type="submit"
            disabled={importMutation.isPending}
            className="rounded-lg bg-cyan-500 px-5 py-3 font-semibold text-slate-950 transition hover:bg-cyan-400 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {importMutation.isPending
              ? "Importation et analyse..."
              : "Importer et analyser"}
          </button>
        </div>
      </form>

      {successMessage && (
        <p className="mt-5 rounded-lg border border-emerald-800 bg-emerald-950/40 p-4 text-sm text-emerald-300">
          {successMessage}
        </p>
      )}

      {importMutation.error && (
        <p className="mt-5 rounded-lg border border-red-900 bg-red-950/40 p-4 text-sm text-red-300">
          Échec de l’importation :{" "}
          {importMutation.error instanceof Error
            ? importMutation.error.message
            : "erreur inconnue"}
        </p>
      )}
    </section>
  );
}
