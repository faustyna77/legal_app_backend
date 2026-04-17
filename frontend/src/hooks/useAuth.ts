import { useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { authApi } from '../api'
import type { LoginPayload } from '../api'
import { useAuthStore } from '../contexts/authStore'
import { ROUTES } from '../config'

export function useAuth() {
  const { user, token, isAuthenticated, setAuth, clearAuth } = useAuthStore()
  const navigate = useNavigate()

  const login = useCallback(
    async (payload: LoginPayload) => {
      const tokens = await authApi.login(payload)
      // TODO: replace mock user with real /auth/me call after login
      const mockUser = { id: 1, email: payload.email, role: 'user' as const }
      setAuth(mockUser, tokens.access_token)
      navigate(ROUTES.SEARCH)
    },
    [setAuth, navigate],
  )

  const logout = useCallback(() => {
    clearAuth()
    navigate(ROUTES.LOGIN)
  }, [clearAuth, navigate])

  return { user, token, isAuthenticated, login, logout }
}
