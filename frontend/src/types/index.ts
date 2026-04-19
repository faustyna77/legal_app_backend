// ── Primitive unions ────────────────────────────────────────────────────────
export type SortMode = 'relevance' | 'newest' | 'oldest'
export type ViewMode = 'list' | 'grid'

// ── Filters ─────────────────────────────────────────────────────────────────
export interface FilterOption {
  value: string
  count: number
}

/** Merged from GET /filters + GET /filters/courts + GET /filters/court-types */
export interface FiltersPayload {
  sources: FilterOption[]
  legal_areas: FilterOption[]
  finality: FilterOption[]
  cities: FilterOption[]
  years: FilterOption[]
  courts: FilterOption[]
  court_types: FilterOption[]
}

/** Params sent to POST /search → filters field */
export interface SearchFilters {
  source?: string
  date_from?: string
  date_to?: string
  court?: string
  court_type?: string
  legal_area?: string
  city?: string
}

// ── Judgment references (attached by rag.py _attach_judgment_references) ────
export interface JudgmentReferenceOut {
  referenced_case_number: string
  referenced_judgment_id: number | null
  case_number: string | null
  court: string | null
  date: string | null
  source_url: string | null
}

export interface JudgmentReferenceIn {
  judgment_id: number
  case_number: string
  court: string | null
  date: string | null
  source_url: string | null
}

// ── Judgments ────────────────────────────────────────────────────────────────
export interface JudgmentResult {
  id: number
  case_number: string
  date: string
  court: string
  thesis?: string
  content?: string
  source?: string
  source_url?: string
  similarity?: number
  /** Populated by search (rag._attach_judgment_references) */
  references_out?: JudgmentReferenceOut[]
  references_in?: JudgmentReferenceIn[]
}

export interface SearchResponse {
  judgments: JudgmentResult[]
  latency_ms?: number
  answer?: string
}

/** Matches GET /judgments response (list with pagination) */
export interface JudgmentListParams {
  source?: string
  legal_area?: string
  city?: string
  court?: string
  court_type?: string
  date_from?: string
  date_to?: string
  limit?: number
  offset?: number
}

// ── Summary ──────────────────────────────────────────────────────────────────
export interface SummaryPayload {
  teza: string
  stan_faktyczny: string
  rozstrzygniecie: string
  podstawa_prawna: string
}

/** Matches GET /judgments/{id}/summary response exactly */
export interface SummaryResponse {
  id: number
  case_number: string
  court: string
  date: string
  summary: string | SummaryPayload
  cached: boolean
}

// ── Chat ─────────────────────────────────────────────────────────────────────
export interface ChatResponse {
  judgment_id: number
  case_number: string
  court: string
  question: string
  answer: string
  chunks_used: number
  evidence_quotes: string[]
  chunks: { content: string; similarity: number }[]
}

export interface ChatTurn {
  id: number
  question: string
  answer: string
  evidence_quotes: string[]
}

// ── Auth ─────────────────────────────────────────────────────────────────────
export interface User {
  id: number
  email: string
  role: 'admin' | 'user'
}

export interface AuthTokens {
  access_token: string
  token_type: string
}
