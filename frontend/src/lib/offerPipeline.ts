import type {
  ApplicationArchive,
  ApplicationDraft,
  ApplyMatchStatus,
  JobOffer,
  MatchResult,
} from "@/types";

export type OfferPipelineSection =
  | "new"
  | "priority"
  | "validation"
  | "documents"
  | "applied"
  | "failed";

export const PIPELINE_SECTIONS: ReadonlyArray<{
  key: OfferPipelineSection;
  label: string;
  description: string;
}> = [
  { key: "new", label: "Nouvelles offres", description: "Publiées il y a moins de 24 heures" },
  { key: "priority", label: "Priorité haute", description: "Score supérieur ou égal à 60" },
  { key: "validation", label: "À valider", description: "Décision humaine nécessaire" },
  { key: "documents", label: "Documents prêts", description: "CV et lettre disponibles" },
  { key: "applied", label: "Déjà postulé", description: "Envoi confirmé et archivé" },
  { key: "failed", label: "Problèmes d’envoi", description: "Action ou nouvelle tentative nécessaire" },
];

interface ClassificationContext {
  result?: MatchResult;
  draft?: ApplicationDraft;
  archived: boolean;
  now?: Date;
}

export interface ClassifiedOffer {
  offer: JobOffer;
  status: ApplyMatchStatus;
}

function isRecent(offer: JobOffer, now: Date): boolean {
  if (!offer.published_at) return false;
  const published = new Date(offer.published_at).getTime();
  const age = now.getTime() - published;
  return age >= 0 && age < 24 * 60 * 60 * 1000;
}

export function deriveApplyMatchStatus(
  offer: JobOffer,
  { result, draft, archived, now = new Date() }: ClassificationContext,
): ApplyMatchStatus {
  if (
    archived ||
    offer.status === "applied" ||
    offer.application_status === "sent" ||
    offer.application_status === "applied"
  ) return "applied";

  if (offer.application_status === "failed") return "failed";
  if (
    offer.application_status === "rejected" ||
    offer.status === "rejected" || result?.decision === "rejected"
  ) return "rejected";
  if (
    offer.application_status === "expired" || offer.status === "expired" ||
    (offer.expires_at !== null && offer.expires_at !== undefined &&
      new Date(offer.expires_at).getTime() <= now.getTime())
  ) return "expired";
  if (offer.application_status === "sending") return "sending";
  if (offer.application_status === "documents_ready") return "documents_ready";
  if (draft && draft.status !== "archived") return "documents_ready";
  if (offer.application_status === "manual_review") return "manual_review";
  if (offer.application_status === "low_score") return "low_score";
  if (result?.decision === "manual_review") return "manual_review";
  if (result && result.score < 60) return "low_score";
  if (offer.application_status === "eligible") return "eligible";
  if (result && result.score >= 60) return "eligible";
  return isRecent(offer, now) ? "new" : "manual_review";
}

export function sectionForStatus(status: ApplyMatchStatus): OfferPipelineSection {
  if (status === "applied") return "applied";
  if (status === "failed") return "failed";
  if (status === "documents_ready" || status === "sending") return "documents";
  if (
    status === "manual_review" || status === "low_score" ||
    status === "rejected" || status === "expired"
  ) return "validation";
  if (status === "eligible") return "priority";
  return "new";
}

export function classifyOffers(
  offers: JobOffer[],
  results: MatchResult[],
  drafts: ApplicationDraft[],
  archives: ApplicationArchive[],
  now = new Date(),
): Map<OfferPipelineSection, ClassifiedOffer[]> {
  const resultsByOffer = new Map(results.map((result) => [result.offer_id, result]));
  const draftsByOffer = new Map(drafts.map((draft) => [draft.offer_id, draft]));
  const archivedOfferIds = new Set(archives.map((archive) => archive.offer_id));
  const sections = new Map<OfferPipelineSection, ClassifiedOffer[]>(
    PIPELINE_SECTIONS.map(({ key }) => [key, [] as ClassifiedOffer[]]),
  );

  for (const offer of offers) {
    const status = deriveApplyMatchStatus(offer, {
      result: resultsByOffer.get(offer.id),
      draft: draftsByOffer.get(offer.id),
      archived: archivedOfferIds.has(offer.id),
      now,
    });
    sections.get(sectionForStatus(status))!.push({ offer, status });
  }
  return sections;
}
