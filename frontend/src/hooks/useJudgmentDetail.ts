import { useEffect, useMemo, useState } from 'react'
import { judgmentsApi } from '../api/judgments'
import type { JudgmentReferencesResponse, JudgmentRegulationsResponse } from '../api/judgments'
import type { ChatTurn, JudgmentResult, SummaryPayload, SummaryResponse } from '../types'

export function useJudgmentDetail(id: number) {
  const [judgment, setJudgment] = useState<JudgmentResult | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const [summaryData, setSummaryData] = useState<SummaryResponse | null>(null)
  const [loadingSummary, setLoadingSummary] = useState(false)
  const [summaryError, setSummaryError] = useState('')

  const [similar, setSimilar] = useState<JudgmentResult[]>([])

  const [references, setReferences] = useState<JudgmentReferencesResponse | null>(null)
  const [regulations, setRegulations] = useState<JudgmentRegulationsResponse | null>(null)

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

        // load similar, references, regulations (fire-and-forget)
        judgmentsApi.getSimilar(id, 5).then(setSimilar).catch(() => {})
        judgmentsApi.getReferences(id).then(setReferences).catch(() => {})
        judgmentsApi.getRegulations(id).then(setRegulations).catch(() => {})

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

    let s = summaryData.summary

    // If summary came back as a raw string, try to parse it as JSON
    if (typeof s === 'string') {
      const cleaned = s.replace(/```json/g, '').replace(/```/g, '').trim()
      try { s = JSON.parse(cleaned) } catch { /* keep as string */ }
      if (typeof s === 'string') {
        return { teza: s, stan_faktyczny: '', rozstrzygniecie: '', podstawa_prawna: '' }
      }
    }

    const payload = s as SummaryPayload

    // If teza itself looks like a raw JSON dump (fallback stored full LLM response there)
    if (payload && typeof payload.teza === 'string' && payload.teza.trimStart().startsWith('{')) {
      const cleaned = payload.teza.replace(/```json/g, '').replace(/```/g, '').trim()
      try {
        const inner = JSON.parse(cleaned) as SummaryPayload
        if (inner?.teza) return inner
      } catch { /* ignore, display as-is */ }
    }

    return payload
  }, [summaryData])

  return {
    judgment,
    loading,
    error,
    summaryObject,
    loadingSummary,
    summaryError,
    similar,
    references,
    regulations,
    chatTurns,
    loadingChat,
    chatError,
    askQuestion,
  }
}
