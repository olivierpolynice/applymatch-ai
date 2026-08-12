export type JobOfferStatus =
  | "new"
  | "reviewed"
  | "saved"
  | "ignored"
  | "applied";

export interface JobOffer {
  id: number;
  title: string;
  company: string;
  location: string;
  contract_type: string;
  description: string;
  source: string;
  source_url: string;
  status: JobOfferStatus;
  published_at: string | null;
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
  role_match: boolean;
  contract_match: boolean;
  location_match: boolean;
}

export interface MatchResult {
  id: number;
  profile_id: number;
  offer_id: number;
  score: number;
  recommendation: string;
  matched_skills: string[];
  missing_skills: string[];
  skills_score: number;
  role_score: number;
  contract_score: number;
  location_score: number;
  role_match: boolean;
  contract_match: boolean;
  location_match: boolean;
  created_at: string;
  updated_at: string;
}

export interface MatchResponse {
  score: number;
  recommendation: string;
  matched_skills: string[];
  missing_skills: string[];
  details: MatchDetails;
}