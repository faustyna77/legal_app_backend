import { useEffect, useMemo, useState } from 'react'
import { judgmentsApi } from '../api/judgments'
import type { ChatTurn, JudgmentResult, SummaryPayload, SummaryResponse } from '../types'

export function useJudgmentDetail(id: number) {
  const [judgment, setJudgment] = useState<JudgmentResult | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const [summaryData, setSummaryData] = useState<SummaryResponse | null>(null)
  const [loadingSummary, setLoadingSummary] = useState(false)
  const [summaryError, setSummaryError] = useState('')

  const [similar, setSimilar] = useState<JudgmentResult[]>([])

  const [chatTurns, setChatTurns] = useState<ChatTurn[]>([])
  const [loadingChat, setLoadingChat] = useState(false)
  const [chatError, setChatError] = useState('')

  useEffect(() => {
    if (!id) return
    let cancelled = false

    const load = async () => {
      setLoading(true)
      setError('')
      setSummaryData(null)
      setChatTurns([])

      try {
        const j = await judgmentsApi.getById(id)
        if (cancelled) return
        setJudgment(j)

        // load similar judgments (fire-and-forget, no blocking)
        judgmentsApi.getSimilar(id, 5).then(setSimilar).catch(() => {})

        // auto-load summary
        setLoadingSummary(true)
        setSummaryError('')
        try {
          const s = await judgmentsApi.getSummary(id)
          if (!cancelled) setSummaryData(s)
        } catch (e) {
          if (!cancelled)
            setSummaryError(
              `Nie udało się wygenerować podsumowania: ${e instanceof Error ? e.message : 'błąd'}`,
            )
        } finally {
          if (!cancelled) setLoadingSummary(false)
        }
      } catch (e) {
        if (!cancelled)
          setError(
            `Nie udało się załadować orzeczenia: ${e instanceof Error ? e.message : 'błąd'}`,
          )
      } finally {
        if (!cancelled) setLoading(false)
      }
    }

    void load()
    return () => { cancelled = true }
  }, [id])

  const askQuestion = async (question: string) => {
    if (!question.trim()) return
    setLoadingChat(true)
    setChatError('')
    try {
      const payload = await judgmentsApi.chat(id, question.trim())
      setChatTurns((prev) => [
        ...prev,
        {
          id: Date.now(),
          question,
          answer: payload.answer,
          evidence_quotes: payload.evidence_quotes ?? [],
        },
      ])
    } catch (e) {
      setChatError(
        `Nie udało się uzyskać odpowiedzi: ${e instanceof Error ? e.message : 'błąd'}`,
      )
    } finally {
      setLoadingChat(false)
    }
  }

  const summaryObject = useMemo<SummaryPayload | null>(() => {
    if (!summaryData) return null
    if (typeof summaryData.summary === 'string') {
      return { teza: summaryData.summary, stan_faktyczny: '', rozstrzygniecie: '', podstawa_prawna: '' }
    }
    return summaryData.summary
  }, [summaryData])

  return {
    judgment,
    loading,
    error,
    summaryObject,
    loadingSummary,
    summaryError,
    similar,
    chatTurns,
    loadingChat,
    chatError,
    askQuestion,
  }
}
