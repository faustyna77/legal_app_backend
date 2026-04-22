// ── API connection ───────────────────────────────────────────────────────────
export const API_BASE_URL =
  (import.meta.env.VITE_API_BASE_URL as string | undefined) ?? 'http://localhost:8000'

export const AUTH_API_BASE_URL =
  (import.meta.env.VITE_AUTH_API_BASE_URL as string | undefined) ?? 'http://localhost:8001'

export const INTERNAL_API_KEY =
  (import.meta.env.VITE_INTERNAL_API_KEY as string | undefined) ?? ''

// ── Client-side routes ───────────────────────────────────────────────────────
export const ROUTES = {
  HOME: '/',
  SEARCH: '/search',
  JUDGMENTS: '/judgments',
  JUDGMENT_DETAIL: '/judgments/:id',
  LOGIN: '/login',
  REGISTER: '/register',
  ADMIN: '/admin',
  ORGANIZATION: '/folders',
  FOLDER_DETAIL: '/folders/:id',
  FOLDER_CHAT: '/folders/:id/chat',
  HISTORY: '/history',
} as const

// ── React Query cache keys ────────────────────────────────────────────────────
export const QUERY_KEYS = {
  FILTERS: ['filters'] as const,
  SEARCH: (query: string) => ['search', query] as const,
  SUMMARY: (id: number) => ['summary', id] as const,
  JUDGMENT: (id: number) => ['judgment', id] as const,
} as const
