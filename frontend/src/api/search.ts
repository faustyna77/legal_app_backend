import { apiClient } from './client'
import type { SearchFilters, SearchResponse } from '../types'

export const searchApi = {
  async search(query: string, filters: SearchFilters = {}): Promise<SearchResponse> {
    const { data } = await apiClient.post<SearchResponse>('/search', { query, filters })
    return data
  },
}
