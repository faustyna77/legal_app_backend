import { useState, useEffect, useCallback } from 'react'
import { judgmentsApi } from '../api/judgments'
import type { JudgmentUpdate } from '../types'

const STORAGE_KEY = 'judgment_updates_seen_at'
const POLL_INTERVAL_MS = 5 * 60 * 1000

function getSeenAt(): string | null {
  return localStorage.getItem(STORAGE_KEY)
}

function markAllSeen() {
  localStorage.setItem(STORAGE_KEY, new Date().toISOString())
}

export function useJudgmentUpdates() {
  const [updates, setUpdates] = useState<JudgmentUpdate[]>([])
  const [unseenCount, setUnseenCount] = useState(0)
  const [open, setOpen] = useState(false)

  const fetchUpdates = useCallback(async () => {
    try {
      const { updates: items } = await judgmentsApi.getRecentUpdates(7)
      setUpdates(items)
      const seenAt = getSeenAt()
      const unseen = seenAt
        ? items.filter((u) => u.content_updated_at > seenAt).length
        : items.length
      setUnseenCount(unseen)
    } catch {
      // ignoruj błędy sieciowe
    }
  }, [])

  useEffect(() => {
    void fetchUpdates()
    const id = setInterval(() => void fetchUpdates(), POLL_INTERVAL_MS)
    return () => clearInterval(id)
  }, [fetchUpdates])

  const openDropdown = useCallback(() => {
    setOpen(true)
    markAllSeen()
    setUnseenCount(0)
  }, [])

  const closeDropdown = useCallback(() => setOpen(false), [])

  return { updates, unseenCount, open, openDropdown, closeDropdown }
}
