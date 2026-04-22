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
  judgment_types: FilterOption[]
  cities: FilterOption[]
  years: FilterOption[]
  courts: FilterOption[]
  court_types: FilterOption[]
}

/** Params sent to POST /search → filters field */
export interface SearchFilters {
  source?: string | string[]
  date_from?: string
  date_to?: string
  court?: string | string[]
  court_type?: string | string[]
  legal_area?: string | string[]
  city?: string | string[]
  article?: string | string[]
  act_title?: string | string[]
  judgment_type?: string | string[]
  is_final?: string
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
  total?: number
  latency_ms?: number
  answer?: string
}

/** Params for GET /judgments */
export interface JudgmentListParams {
  source?: string | string[]
  legal_area?: string | string[]
  city?: string | string[]
  court?: string | string[]
  court_type?: string | string[]
  date_from?: string
  date_to?: string
  article?: string | string[]
  act_title?: string | string[]
  judgment_type?: string | string[]
  is_final?: string
  limit?: number
  offset?: number
}

export interface JudgmentListResponse {
  judgments: JudgmentResult[]
  total: number
  limit: number
  offset: number
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

// ── Judgment updates (uzasadnienie added) ─────────────────────────────────────
export interface JudgmentUpdate {
  id: number
  case_number: string
  court: string
  date: string
  source_url: string | null
  content_updated_at: string
}

export interface JudgmentUpdatesResponse {
  updates: JudgmentUpdate[]
  days: number
}

// ── Auth ─────────────────────────────────────────────────────────────────────
export interface User {
  id: number
  email: string
  name?: string | null
  is_active?: boolean
  created_at?: string
}

export interface AuthTokens {
  access_token: string
  refresh_token: string
  token_type: string
}

export interface Folder {
  id: number
  name: string
  description: string | null
  created_at: string
  judgment_count?: number
}

export interface FolderListResponse {
  folders: Folder[]
}

export interface FolderCreatePayload {
  name: string
  description?: string
}

export interface FolderJudgmentPayload {
  judgment_id: number
  case_number: string
  court?: string | null
  date?: string | null
  note?: string
}

export interface FolderJudgmentItem {
  judgment_id: number
  case_number: string
  court: string | null
  date: string | null
  note: string | null
  created_at: string
}

export interface FolderJudgmentListResponse {
  judgments: FolderJudgmentItem[]
}

export interface SearchHistoryItem {
  id: number
  query: string
  filters: Record<string, unknown> | null
  answer: string | null
  case_numbers: string[]
  created_at: string
}

export interface SearchHistoryResponse {
  history: SearchHistoryItem[]
}

export interface ChatHistoryItem {
  id: number
  judgment_id: number
  case_number: string
  court: string | null
  question: string
  answer: string
  created_at: string
}

export interface ChatHistoryResponse {
  history: ChatHistoryItem[]
}

export interface FolderChatResponse {
  answer: string
  question: string
  chunks_used: number
  judgment_ids: number[]
}

export interface FolderChatHistoryItem {
  id: number
  folder_id: number
  folder_name: string | null
  question: string
  answer: string
  created_at: string
}

export interface FolderChatHistoryResponse {
  history: FolderChatHistoryItem[]
}
