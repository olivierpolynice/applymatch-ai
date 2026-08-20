export interface CandidateProfile {
  id: number;
  full_name: string;
  education_level: string;
  program: string;
  target_contract: string;
  availability: string;
  work_schedule: string;
  location: string;
  target_roles: string;
  skills: string;
  professional_summary: string | null;
  experience_highlights: string | null;
  project_highlights: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export type JobOfferStatus =
  | "new"
  | "saved"
  | "applied"
  | "rejected"
  | "archived";

export interface JobOffer {
  id: number;
  title: string;
  company: string;
  location: string;
  contract_type: string;
  description: string;
  source: string;
  source_url: string | null;
  status: JobOfferStatus;
  published_at: string | null;
  applied_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface JobOfferCreate {
  title: string;
  company: string;
  location: string;
  contract_type: string;
  description: string;
  source: string;
  source_url: string;
  published_at: string | null;
}

export interface MatchDetails {
  skills_score: number;
  role_score: number;
  contract_score: number;
  location_score: number;
  education_score: number;
  experience_score: number;
  freshness_score: number;
  role_match: boolean;
  contract_match: boolean;
  location_match: boolean;
  education_match: boolean;
  experience_match: boolean;
  eligibility_reasons: string[];
}

export interface MatchResult {
  id: number;
  profile_id: number;
  offer_id: number;
  score: number;
  recommendation: string;
  confidence: string;
  decision: string;
  application_priority: string;
  actions: string[];
  matched_skills: string[];
  skills_to_strengthen: string[];
  missing_skills: string[];
  details: MatchDetails;
  created_at: string;
  updated_at: string;
}

export type MatchResponse = MatchResult;

export interface CollectorRunResult {
  found: number;
  added: number;
  duplicates: number;
  errors: number;
}

export type ValidationQueueStatus =
  | "pending"
  | "approved"
  | "rejected"
  | "archived";

export type ValidationDecision =
  | "approved"
  | "rejected";

export interface ValidationQueueItem {
  id: number;
  profile_id: number;
  offer_id: number;
  match_result_id: number;
  status: ValidationQueueStatus;
  priority: string;
  reviewer_comment: string | null;
  decided_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface ValidationQueueCreate {
  match_result_id: number;
}

export interface ValidationQueueDecisionUpdate {
  decision: ValidationDecision;
  reviewer_comment?: string | null;
}

export type ApplicationDraftStatus =
  | "draft"
  | "reviewed"
  | "archived";

export interface ApplicationDraft {
  id: number;
  validation_queue_item_id: number;
  profile_id: number;
  offer_id: number;
  status: ApplicationDraftStatus;
  version: number;
  cover_letter: string;
  short_message: string;
  cv_adaptation_tips: string;
  adapted_cv_snapshot: string;
  proposed_answers: Array<{
    question: string;
    answer: string;
  }>;
  generated_at: string;
  created_at: string;
  updated_at: string;
}

export type AutomationChannel =
  | "official_api"
  | "recruitment_email"
  | "authorized_form"
  | "unsupported";

export interface AutomationEvaluation {
  mode: "automatic" | "manual_approval";
  eligible: boolean;
  reasons: string[];
}

export interface ApplicationArchive {
  id: number;
  draft_id: number;
  profile_id: number;
  offer_id: number;
  company: string;
  offer_title: string;
  application_mode: "automatic" | "manual";
  channel: AutomationChannel;
  provider_confirmation_id: string;
  cv_snapshot: string;
  cover_letter_snapshot: string;
  short_message_snapshot: string;
  proposed_answers_snapshot: Array<{
    question: string;
    answer: string;
  }>;
  sent_at: string;
  archived_at: string;
}

export interface ApplicationDraftCreate {
  validation_queue_item_id: number;
}

export interface ApplicationDraftUpdate {
  cover_letter?: string;
  short_message?: string;
  cv_adaptation_tips?: string;
  status?: ApplicationDraftStatus;
}
export type NotificationType =
  | "collector_completed"
  | "new_offers"
  | "high_score"
  | "validation_required"
  | "draft_ready"
  | "system_error";

export type NotificationLevel =
  | "info"
  | "success"
  | "warning"
  | "error";

export interface Notification {
  id: number;
  notification_type: NotificationType;
  level: NotificationLevel;
  title: string;
  message: string;
  target_url: string | null;
  is_read: boolean;
  read_at: string | null;
  created_at: string;
}

export interface NotificationUnreadCount {
  unread_count: number;
}
export type CollectorTrigger =
  | "manual"
  | "scheduled";

export type CollectorRunStatus =
  | "running"
  | "completed"
  | "failed";

export interface CollectorRunHistory {
  id: number;
  collector: string;
  trigger: CollectorTrigger;
  status: CollectorRunStatus;
  found: number;
  added: number;
  duplicates: number;
  errors: number;
  error_message: string | null;
  started_at: string;
  finished_at: string | null;
}
