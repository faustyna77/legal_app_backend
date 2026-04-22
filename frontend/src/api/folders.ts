import { apiClient, authApiClient } from './client'
import type {
  Folder,
  FolderChatHistoryResponse,
  FolderChatResponse,
  FolderCreatePayload,
  FolderJudgmentListResponse,
  FolderJudgmentPayload,
  FolderListResponse,
} from '../types'

export const foldersApi = {
  async list(): Promise<FolderListResponse> {
    const { data } = await authApiClient.get<FolderListResponse>('/folders')
    return data
  },

  async getById(folderId: number): Promise<Folder> {
    const { data } = await authApiClient.get<Folder>(`/folders/${folderId}`)
    return data
  },

  async create(payload: FolderCreatePayload): Promise<Folder> {
    const { data } = await authApiClient.post<Folder>('/folders', payload)
    return data
  },

  async listJudgments(folderId: number): Promise<FolderJudgmentListResponse> {
    const { data } = await authApiClient.get<FolderJudgmentListResponse>(`/folders/${folderId}/judgments`)
    return data
  },

  async addJudgment(folderId: number, payload: FolderJudgmentPayload): Promise<void> {
    await authApiClient.post(`/folders/${folderId}/judgments`, payload)
  },

  async removeJudgment(folderId: number, judgmentId: number): Promise<void> {
    await authApiClient.delete(`/folders/${folderId}/judgments/${judgmentId}`)
  },

  async chat(judgmentIds: number[], question: string): Promise<FolderChatResponse> {
    const { data } = await apiClient.post<FolderChatResponse>('/folder-chat', {
      judgment_ids: judgmentIds,
      question,
    })
    return data
  },

  async getChatHistory(folderId: number): Promise<FolderChatHistoryResponse> {
    const { data } = await authApiClient.get<FolderChatHistoryResponse>(`/history/folder-chat/${folderId}`)
    return data
  },
}
