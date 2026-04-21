import { authApiClient } from './client'
import type { ChatHistoryResponse, SearchHistoryResponse } from '../types'

export const historyApi = {
  async listSearch(page = 1, limit = 20): Promise<SearchHistoryResponse> {
    const { data } = await authApiClient.get<SearchHistoryResponse>('/history/search', {
      params: { page, limit },
    })
    return data
  },

  async deleteSearch(historyId: number): Promise<void> {
    await authApiClient.delete(`/history/search/${historyId}`)
  },

  async listChat(page = 1, limit = 20): Promise<ChatHistoryResponse> {
    const { data } = await authApiClient.get<ChatHistoryResponse>('/history/chat', {
      params: { page, limit },
    })
    return data
  },

  async deleteChat(historyId: number): Promise<void> {
    await authApiClient.delete(`/history/chat/${historyId}`)
  },
}
