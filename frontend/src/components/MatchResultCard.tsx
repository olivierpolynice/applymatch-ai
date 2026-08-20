"use client";

import {
  useMutation,
  useQueryClient,
} from "@tanstack/react-query";

import { apiRequest } from "@/lib/api";
import type {
  JobOffer,
  MatchResult,
  ValidationQueueCreate,
  ValidationQueueItem,
} from "@/types";

interface MatchResultCardProps {
  result: MatchResult;
  offer?: JobOffer;
}

export default function MatchResultCard({
  result,
  offer,
}: MatchResultCardProps) {
  const queryClient = useQueryClient();

  const addToQueueMutation = useMutation({
    mutationFn: () => {
      const data: ValidationQueueCreate = {
        match_result_id: result.id,
      };

      return apiRequest<ValidationQueueItem>(
        "/validation-queue",
        {
          method: "POST",
          body: JSON.stringify(data),
        },
      );
    },
    onSuccess: async () => {
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

  const isEligible =
    result.decision !== "rejected";

  return (
    <article
      id={`match-${result.id}`}
      className="scroll-mt-6 rounded-2xl border border-slate-800 bg-slate-900 p-6"
    >
      <div className="flex flex-col gap-5 lg:flex-row lg:items-start lg:justify-between">
        <div>
          <p className="text-sm font-medium text-cyan-400">
            {offer?.company ??
              "Entreprise inconnue"}
          </p>

          <h2 className="mt-1 text-xl font-bold">
            {offer?.title ??
              `Offre numéro ${result.offer_id}`}
          </h2>

          <p className="mt-2 text-sm text-slate-400">
            {offer?.location ??
              "Localisation inconnue"}
            {" · "}
            {offer?.contract_type ??
              "Contrat non renseigné"}
          </p>

          <div className="mt-4 flex flex-wrap gap-2">
            <Badge
              label={`Confiance : ${result.confidence}`}
              color="border-cyan-800 bg-cyan-950 text-cyan-300"
            />

            <Badge
              label={`Décision : ${formatDecision(
                result.decision,
              )}`}
              color={decisionColor(
                result.decision,
              )}
            />

            <Badge
              label={`Priorité : ${formatPriority(
                result.application_priority,
              )}`}
              color={priorityColor(
                result.application_priority,
              )}
            />
          </div>

          <p className="mt-4 font-medium text-slate-200">
            {result.recommendation}
          </p>
        </div>

        <div className="flex h-24 w-24 shrink-0 items-center justify-center rounded-full border-4 border-cyan-400 bg-slate-950">
          <div className="text-center">
            <p className="text-3xl font-bold">
              {result.score}
            </p>

            <p className="text-xs text-slate-400">
              sur 100
            </p>
          </div>
        </div>
      </div>

      <section className="mt-6">
        <h3 className="mb-3 text-sm font-semibold uppercase tracking-wider text-slate-300">
          Détail du score
        </h3>

        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          <ScoreCard
            label="Compétences"
            score={
              result.details.skills_score
            }
            maximum={30}
            matched={
              result.matched_skills.length > 0
            }
          />

          <ScoreCard
            label="Métier"
            score={result.details.role_score}
            maximum={25}
            matched={
              result.details.role_match
            }
          />

          <ScoreCard
            label="Contrat"
            score={
              result.details.contract_score
            }
            maximum={15}
            matched={
              result.details.contract_match
            }
          />

          <ScoreCard
            label="Localisation"
            score={
              result.details.location_score
            }
            maximum={10}
            matched={
              result.details.location_match
            }
          />

          <ScoreCard
            label="Profil/missions"
            score={
              result.details.education_score
            }
            maximum={5}
            matched={
              result.details.education_match
            }
          />

          <ScoreCard
            label="Expérience 0–2 ans"
            score={result.details.experience_score}
            maximum={10}
            matched={result.details.experience_match}
          />

          <ScoreCard
            label="Fraîcheur"
            score={result.details.freshness_score}
            maximum={5}
            matched={result.details.freshness_score > 0}
          />
        </div>
      </section>

      <section className="mt-6 grid gap-5 lg:grid-cols-3">
        <SkillList
          title="Compétences maîtrisées"
          skills={result.matched_skills}
          emptyMessage="Aucune compétence détectée"
          titleColor="text-emerald-400"
          badgeColor="bg-emerald-950 text-emerald-300"
        />

        <SkillList
          title="Compétences à renforcer"
          skills={
            result.skills_to_strengthen
          }
          emptyMessage="Aucune compétence à renforcer"
          titleColor="text-amber-400"
          badgeColor="bg-amber-950 text-amber-300"
        />

        <SkillList
          title="Compétences manquantes"
          skills={result.missing_skills}
          emptyMessage="Aucune compétence manquante"
          titleColor="text-red-400"
          badgeColor="bg-red-950 text-red-300"
        />
      </section>

      <section className="mt-6 rounded-xl border border-slate-800 bg-slate-950 p-5">
        <h3 className="text-sm font-semibold uppercase tracking-wider text-violet-300">
          Actions recommandées
        </h3>

        {result.actions.length > 0 ? (
          <ul className="mt-3 grid gap-2">
            {result.actions.map(
              (action, index) => (
                <li
                  key={`${result.id}-${index}`}
                  className="flex gap-3 text-sm text-slate-300"
                >
                  <span className="text-violet-400">
                    •
                  </span>

                  <span>{action}</span>
                </li>
              ),
            )}
          </ul>
        ) : (
          <p className="mt-3 text-sm text-slate-500">
            Aucune action particulière
            recommandée.
          </p>
        )}
      </section>

      <section className="mt-5 rounded-xl border border-slate-800 bg-slate-950 p-5">
        <h3 className="text-sm font-semibold uppercase tracking-wider text-cyan-300">
          Validation manuelle
        </h3>

        {!isEligible && (
          <p className="mt-3 text-sm text-slate-400">
            Cette offre a été classée « Ignorer » et
            ne peut pas être ajoutée à la file de
            validation.
          </p>
        )}

        {isEligible &&
          !addToQueueMutation.isSuccess && (
            <>
              <p className="mt-3 text-sm text-slate-400">
                Ajoute cette opportunité à la file
                pour pouvoir l’approuver ou la
                rejeter manuellement.
              </p>

              <button
                type="button"
                disabled={
                  addToQueueMutation.isPending
                }
                onClick={() =>
                  addToQueueMutation.mutate()
                }
                className="mt-4 rounded-lg bg-cyan-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-cyan-500 disabled:cursor-not-allowed disabled:opacity-50"
              >
                {addToQueueMutation.isPending
                  ? "Ajout en cours..."
                  : "Ajouter à la validation"}
              </button>
            </>
          )}

        {addToQueueMutation.isSuccess && (
          <div className="mt-3 rounded-lg border border-emerald-800 bg-emerald-950/40 p-4 text-sm text-emerald-300">
            Cette opportunité a été ajoutée à la
            file de validation.
          </div>
        )}

        {addToQueueMutation.isError && (
          <div className="mt-3 rounded-lg border border-red-900 bg-red-950/40 p-4 text-sm text-red-300">
            Impossible d’ajouter cette opportunité :{" "}
            {addToQueueMutation.error instanceof Error
              ? addToQueueMutation.error.message
              : "erreur inconnue"}
          </div>
        )}
      </section>

      {offer?.source_url && (
        <a
          href={offer.source_url}
          target="_blank"
          rel="noreferrer"
          className="mt-5 inline-flex text-sm font-semibold text-cyan-400 transition hover:text-cyan-300"
        >
          Consulter l’offre
        </a>
      )}
    </article>
  );
}

interface ScoreCardProps {
  label: string;
  score: number;
  maximum: number;
  matched: boolean;
}

function ScoreCard({
  label,
  score,
  maximum,
  matched,
}: ScoreCardProps) {
  const percentage = Math.min(
    100,
    Math.round((score / maximum) * 100),
  );

  return (
    <div className="rounded-xl border border-slate-800 bg-slate-950 p-4">
      <div className="flex items-center justify-between gap-2">
        <p className="text-sm text-slate-400">
          {label}
        </p>

        <span
          className={
            matched
              ? "text-emerald-400"
              : "text-slate-600"
          }
        >
          {matched ? "✓" : "—"}
        </span>
      </div>

      <p className="mt-2 text-xl font-bold">
        {score}
        <span className="text-sm font-normal text-slate-500">
          /{maximum}
        </span>
      </p>

      <div className="mt-3 h-1.5 overflow-hidden rounded-full bg-slate-800">
        <div
          className="h-full rounded-full bg-cyan-400"
          style={{
            width: `${percentage}%`,
          }}
        />
      </div>
    </div>
  );
}

interface SkillListProps {
  title: string;
  skills: string[];
  emptyMessage: string;
  titleColor: string;
  badgeColor: string;
}

function SkillList({
  title,
  skills,
  emptyMessage,
  titleColor,
  badgeColor,
}: SkillListProps) {
  return (
    <div>
      <h3
        className={`mb-2 text-sm font-semibold ${titleColor}`}
      >
        {title}
      </h3>

      <div className="flex flex-wrap gap-2">
        {skills.length > 0 ? (
          skills.map((skill) => (
            <span
              key={skill}
              className={`rounded-full px-3 py-1 text-xs ${badgeColor}`}
            >
              {skill}
            </span>
          ))
        ) : (
          <span className="text-sm text-slate-500">
            {emptyMessage}
          </span>
        )}
      </div>
    </div>
  );
}

interface BadgeProps {
  label: string;
  color: string;
}

function Badge({
  label,
  color,
}: BadgeProps) {
  return (
    <span
      className={`rounded-full border px-3 py-1 text-xs font-medium ${color}`}
    >
      {label}
    </span>
  );
}

function formatDecision(
  decision: string,
): string {
  const labels: Record<string, string> = {
    automatic_ready: "Prioritaire (≥70)",
    manual_review: "À examiner",
    rejected: "Rejetée",
  };

  return labels[decision] ?? decision;
}

function formatPriority(
  priority: string,
): string {
  const labels: Record<string, string> = {
    high: "Haute",
    medium: "Moyenne",
    low: "Faible",
  };

  return labels[priority] ?? priority;
}

function decisionColor(
  decision: string,
): string {
  if (decision === "automatic_ready") {
    return "border-emerald-800 bg-emerald-950 text-emerald-300";
  }

  if (decision === "manual_review") {
    return "border-amber-800 bg-amber-950 text-amber-300";
  }

  return "border-slate-700 bg-slate-950 text-slate-400";
}

function priorityColor(
  priority: string,
): string {
  if (priority === "high") {
    return "border-red-800 bg-red-950 text-red-300";
  }

  if (priority === "medium") {
    return "border-amber-800 bg-amber-950 text-amber-300";
  }

  return "border-slate-700 bg-slate-950 text-slate-400";
}
