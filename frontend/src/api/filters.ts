import { apiClient } from './client'
import type { FilterOption, FiltersPayload } from '../types'

export const filtersApi = {
  /** Fetches all filter data in parallel from 3 endpoints and merges. */
  async getFilters(): Promise<FiltersPayload> {
    const [main, courts, courtTypes] = await Promise.all([
      apiClient.get<Omit<FiltersPayload, 'courts' | 'court_types'>>('/filters'),
      apiClient.get<{ courts: FilterOption[] }>('/filters/courts'),
      apiClient.get<{ court_types: FilterOption[] }>('/filters/court-types'),
    ])
    return {
      ...main.data,
      courts: courts.data.courts,
      court_types: courtTypes.data.court_types,
    }
  },
}
