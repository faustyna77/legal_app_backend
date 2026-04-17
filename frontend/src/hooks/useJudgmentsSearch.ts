import { useEffect, useMemo, useState } from 'react'
import { filtersApi } from '../api/filters'
import { searchApi } from '../api/search'
import { judgmentsApi } from '../api/judgments'
import type {
  ChatTurn,
  FiltersPayload,
  JudgmentResult,
  SearchFilters,
  SearchResponse,
  SummaryPayload,
  SummaryResponse,
} from '../types'

export type SearchParams = {
  query: string
  selectedSource: string
  selectedYear: string
  selectedLegalArea: string
  selectedCity: string
  selectedCourt: string
  selectedCourtType: string
}

export function useJudgmentsSearch() {
  const [filters, setFilters] = useState<FiltersPayload | null>(null)
  const [loadingFilters, setLoadingFilters] = useState(false)
  const [searchResult, setSearchResult] = useState<SearchResponse | null>(null)
  const [loadingSearch, setLoadingSearch] = useState(false)
  const [searchError, setSearchError] = useState('')
  const [selectedJudgment, setSelectedJudgment] = useState<JudgmentResult | null>(null)
  const [summaryData, setSummaryData] = useState<SummaryResponse | null>(null)
  const [loadingSummary, setLoadingSummary] = useState(false)
  const [summaryError, setSummaryError] = useState('')
  const [chatTurns, setChatTurns] = useState<ChatTurn[]>([])
  const [loadingChat, setLoadingChat] = useState(false)
  const [chatError, setChatError] = useState('')

  useEffect(() => {
    const load = async () => {
      setLoadingFilters(true)
      try {
        setFilters(await filtersApi.getFilters())
      } catch (error) {
        setSearchError(
          `Nie udało się pobrać filtrów: ${error instanceof Error ? error.message : 'nieznany błąd'}`,
        )
      } finally {
        setLoadingFilters(false)
      }
    }
    void load()
  }, [])

  const loadSummary = async (id: number) => {
    setLoadingSummary(true)
    setSummaryError('')
    try {
      setSummaryData(await judgmentsApi.getSummary(id))
    } catch (error) {
      setSummaryData(null)
      setSummaryError(
        `Nie udało się pobrać podsumowania: ${error instanceof Error ? error.message : 'nieznany błąd'}`,
      )
    } finally {
      setLoadingSummary(false)
    }
  }

  const runSearch = async (params: SearchParams) => {
    if (!params.query.trim()) return

    setLoadingSearch(true)
    setSearchError('')
    setSelectedJudgment(null)
    setSummaryData(null)
    setChatTurns([])

    const filtersPayload: SearchFilters = {}
    if (params.selectedSource) filtersPayload.source = params.selectedSource
    if (params.selectedYear) {
      filtersPayload.date_from = `${params.selectedYear}-01-01`
      filtersPayload.date_to = `${params.selectedYear}-12-31`
    }
    if (params.selectedLegalArea) filtersPayload.legal_area = params.selectedLegalArea
    if (params.selectedCity) filtersPayload.city = params.selectedCity
    if (params.selectedCourt) filtersPayload.court = params.selectedCourt
    if (params.selectedCourtType) filtersPayload.court_type = params.selectedCourtType

    try {
      const payload = await searchApi.search(params.query.trim(), filtersPayload)
      setSearchResult(payload)
      if (payload.judgments.length > 0) {
        const first = payload.judgments[0]
        setSelectedJudgment(first)
        void loadSummary(first.id)
      }
    } catch (error) {
      setSearchError(
        `Wyszukiwanie nie powiodło się: ${error instanceof Error ? error.message : 'nieznany błąd'}`,
      )
    } finally {
      setLoadingSearch(false)
    }
  }

  const selectJudgment = (judgment: JudgmentResult) => {
    setSelectedJudgment(judgment)
    setSummaryData(null)
    setSummaryError('')
    setChatTurns([])
    void loadSummary(judgment.id)
  }

  const askAboutJudgment = async (question: string) => {
    if (!selectedJudgment || !question.trim()) return

    setLoadingChat(true)
    setChatError('')
    try {
      const payload = await judgmentsApi.chat(selectedJudgment.id, question.trim())
      setChatTurns((prev) => [
        ...prev,
        {
          id: Date.now(),
          question,
          answer: payload.answer,
          evidence_quotes: payload.evidence_quotes ?? [],
        },
      ])
    } catch (error) {
      setChatError(
        `Nie udało się uzyskać odpowiedzi: ${error instanceof Error ? error.message : 'nieznany błąd'}`,
      )
    } finally {
      setLoadingChat(false)
    }
  }

  /** Normalise summary — backend may return summary as raw string or structured object */
  const summaryObject = useMemo<SummaryPayload | null>(() => {
    if (!summaryData) return null
    if (typeof summaryData.summary === 'string') {
      return {
        teza: summaryData.summary,
        stan_faktyczny: '',
        rozstrzygniecie: '',
        podstawa_prawna: '',
      }
    }
    return summaryData.summary
  }, [summaryData])

  return {
    filters,
    loadingFilters,
    searchResult,
    loadingSearch,
    searchError,
    selectedJudgment,
    selectJudgment,
    runSearch,
    summaryObject,
    loadingSummary,
    summaryError,
    chatTurns,
    loadingChat,
    chatError,
    askAboutJudgment,
  }
}
