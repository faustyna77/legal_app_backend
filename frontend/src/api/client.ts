import axios from 'axios'
import { API_BASE_URL, AUTH_API_BASE_URL, INTERNAL_API_KEY } from '../config'

function attachAuthInterceptors(client: ReturnType<typeof axios.create>) {
  client.interceptors.request.use((config) => {
    if (INTERNAL_API_KEY) {
      config.headers['x-internal-key'] = INTERNAL_API_KEY
    }
    const token = localStorage.getItem('access_token')
    if (token) {
      config.headers['Authorization'] = `Bearer ${token}`
    }
    return config
  })

  client.interceptors.response.use(
    (response) => response,
    (error) => {
      if (axios.isAxiosError(error)) {
        const status = error.response?.status
        const requestUrl = String(error.config?.url ?? '')
        const isAuthFormRequest = requestUrl.includes('/auth/login') || requestUrl.includes('/auth/register')
        if (status === 401 && !isAuthFormRequest && window.location.pathname !== '/login') {
          localStorage.removeItem('access_token')
          localStorage.removeItem('refresh_token')
          window.location.href = '/login'
        }
        const detail =
          (error.response?.data as Record<string, string> | undefined)?.detail
        const message = detail ?? `Błąd ${status ?? 'połączenia'}`
        return Promise.reject(new Error(message))
      }
      return Promise.reject(error)
    },
  )
}

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: { 'Content-Type': 'application/json' },
})

export const authApiClient = axios.create({
  baseURL: AUTH_API_BASE_URL,
  headers: { 'Content-Type': 'application/json' },
})

attachAuthInterceptors(apiClient)
attachAuthInterceptors(authApiClient)

