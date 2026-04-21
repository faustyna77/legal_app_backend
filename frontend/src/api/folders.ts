import { authApiClient } from './client'
import type {
  Folder,
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
}
