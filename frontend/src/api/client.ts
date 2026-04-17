import axios from 'axios'
import { API_BASE_URL, INTERNAL_API_KEY } from '../config'

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: { 'Content-Type': 'application/json' },
})

// Request: attach internal key + Bearer token from localStorage
apiClient.interceptors.request.use((config) => {
  if (INTERNAL_API_KEY) {
    config.headers['x-internal-key'] = INTERNAL_API_KEY
  }
  const token = localStorage.getItem('access_token')
  if (token) {
    config.headers['Authorization'] = `Bearer ${token}`
  }
  return config
})

// Response: normalise errors, handle 401 globally
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (axios.isAxiosError(error)) {
      const status = error.response?.status
      if (status === 401) {
        localStorage.removeItem('access_token')
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
