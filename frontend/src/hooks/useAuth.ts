import { useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { authApi } from '../api'
import type { LoginPayload, RegisterPayload } from '../api'
import { useAuthStore } from '../contexts/authStore'
import { ROUTES } from '../config'

export function useAuth() {
  const { user, token, isAuthenticated, refreshToken, setAuth, clearAuth } = useAuthStore()
  const navigate = useNavigate()

  const login = useCallback(
    async (payload: LoginPayload) => {
      const tokens = await authApi.login(payload)
      localStorage.setItem('access_token', tokens.access_token)
      localStorage.setItem('refresh_token', tokens.refresh_token)
      const me = await authApi.me()
      setAuth(me, tokens.access_token, tokens.refresh_token)
      navigate(ROUTES.SEARCH)
    },
    [setAuth, navigate],
  )

  const register = useCallback(
    async (payload: RegisterPayload) => {
      const tokens = await authApi.register(payload)
      localStorage.setItem('access_token', tokens.access_token)
      localStorage.setItem('refresh_token', tokens.refresh_token)
      const me = await authApi.me()
      setAuth(me, tokens.access_token, tokens.refresh_token)
      navigate(ROUTES.SEARCH)
    },
    [setAuth, navigate],
  )

  const logout = useCallback(async () => {
    const storedRefresh = refreshToken ?? localStorage.getItem('refresh_token')
    if (storedRefresh) {
      try {
        await authApi.logout({ refresh_token: storedRefresh })
      } catch (e) {
        void e
      }
    }
    clearAuth()
    navigate(ROUTES.LOGIN)
  }, [refreshToken, clearAuth, navigate])

  return { user, token, isAuthenticated, login, register, logout }
}
