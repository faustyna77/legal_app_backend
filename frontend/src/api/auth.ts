import { apiClient } from './client'
import type { AuthTokens, User } from '../types'

export interface LoginPayload {
  email: string
  password: string
}

export interface RegisterPayload {
  email: string
  password: string
}

export const authApi = {
  /** Mock login — swap for real endpoint when backend auth is ready. */
  async login(payload: LoginPayload): Promise<AuthTokens> {
    if (payload.email === 'admin@test.pl' && payload.password === 'password') {
      return { access_token: 'mock-token', token_type: 'bearer' }
    }
    throw new Error('Nieprawidłowe dane logowania')
  },

  async register(payload: RegisterPayload): Promise<User> {
    const { data } = await apiClient.post<User>('/auth/register', payload)
    return data
  },

  async me(): Promise<User> {
    const { data } = await apiClient.get<User>('/auth/me')
    return data
  },
}
