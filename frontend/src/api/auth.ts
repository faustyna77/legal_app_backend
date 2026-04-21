import { authApiClient } from './client'
import type { AuthTokens, User } from '../types'

export interface LoginPayload {
  email: string
  password: string
}

export interface RegisterPayload {
  email: string
  password: string
  name?: string
}

export interface RefreshPayload {
  refresh_token: string
}

export const authApi = {
  async login(payload: LoginPayload): Promise<AuthTokens> {
    const { data } = await authApiClient.post<AuthTokens>('/auth/login', payload)
    return data
  },

  async register(payload: RegisterPayload): Promise<AuthTokens> {
    const { data } = await authApiClient.post<AuthTokens>('/auth/register', payload)
    return data
  },

  async me(): Promise<User> {
    const { data } = await authApiClient.get<User>('/auth/me')
    return data
  },

  async refresh(payload: RefreshPayload): Promise<AuthTokens> {
    const { data } = await authApiClient.post<AuthTokens>('/auth/refresh', payload)
    return data
  },

  async logout(payload: RefreshPayload): Promise<void> {
    await authApiClient.post('/auth/logout', payload)
  },
}
