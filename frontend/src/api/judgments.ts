import { apiClient } from './client'
import type {
  ChatResponse,
  JudgmentListParams,
  JudgmentListResponse,
  JudgmentResult,
  SummaryResponse,
} from '../types'

export interface JudgmentReferencesResponse {
  judgment_id: number
  references_out: {
    case_number: string
    court: string | null
    date: string | null
    source_url: string | null
    in_database: boolean
  }[]
  references_in: {
    judgment_id: number
    case_number: string
    court: string | null
    date: string | null
    source_url: string | null
  }[]
}

export interface JudgmentRegulationsResponse {
  judgment_id: number
  regulations: { act_title: string; act_year: number | null; articles: string[] }[]
}

export const judgmentsApi = {
  /** GET /judgments — paginated list */
  async list(params: JudgmentListParams = {}): Promise<JudgmentListResponse> {
    const { data } = await apiClient.get<JudgmentListResponse>('/judgments', {
      params,
      paramsSerializer: {
        serialize: (raw) => {
          const sp = new URLSearchParams()
          Object.entries(raw).forEach(([key, value]) => {
            if (value === undefined || value === null || value === '') return
            if (Array.isArray(value)) {
              value.forEach((v) => {
                if (v !== undefined && v !== null && v !== '') sp.append(key, String(v))
              })
              return
            }
            sp.append(key, String(value))
          })
          return sp.toString()
        },
      },
    })
    return data
  },

  /** GET /judgments/{id} */
  async getById(id: number): Promise<JudgmentResult> {
    const { data } = await apiClient.get<JudgmentResult>(`/judgments/${id}`)
    return data
  },

  /** GET /judgments/{id}/similar */
  async getSimilar(id: number, limit = 5): Promise<JudgmentResult[]> {
    const { data } = await apiClient.get<JudgmentResult[]>(
      `/judgments/${id}/similar`,
      { params: { limit } },
    )
    return data
  },

  /** GET /judgments/{id}/summary */
  async getSummary(id: number): Promise<SummaryResponse> {
    const { data } = await apiClient.get<SummaryResponse>(`/judgments/${id}/summary`)
    return data
  },

  /** GET /judgments/{id}/references */
  async getReferences(id: number): Promise<JudgmentReferencesResponse> {
    const { data } = await apiClient.get<JudgmentReferencesResponse>(
      `/judgments/${id}/references`,
    )
    return data
  },

  /** GET /judgments/{id}/regulations */
  async getRegulations(id: number): Promise<JudgmentRegulationsResponse> {
    const { data } = await apiClient.get<JudgmentRegulationsResponse>(
      `/judgments/${id}/regulations`,
    )
    return data
  },

  /** POST /judgments/{id}/chat */
  async chat(id: number, question: string): Promise<ChatResponse> {
    const { data } = await apiClient.post<ChatResponse>(`/judgments/${id}/chat`, {
      question,
    })
    return data
  },
}
