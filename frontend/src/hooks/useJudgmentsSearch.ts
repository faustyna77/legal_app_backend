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
  selectedSource: string[]
  selectedYear: string
  selectedLegalArea: string[]
  selectedCity: string[]
  selectedCourt: string[]
  selectedCourtType: string[]
  selectedDateFrom?: string
  selectedDateTo?: string
  selectedArticle?: string
  selectedActTitle?: string
  selectedJudgmentType?: string[]
  selectedIsFinal?: string
}

export type Filters = SearchFilters

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
  const [mode, setMode] = useState<'rag' | 'filter'>('filter')
  const [ragAnswer, setRagAnswer] = useState<string | null>(null)
  const [ragLatencyMs, setRagLatencyMs] = useState<number | undefined>()
  const [applyFiltersToRAG, setApplyFiltersToRAG] = useState(false)
  const [activeFilters, setActiveFilters] = useState<Filters>({})
  const [results, setResults] = useState<JudgmentResult[]>([])
  const [resultsTotal, setResultsTotal] = useState<number | null>(null)

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

  const buildFiltersFromParams = (params: SearchParams): Filters => {
    const filtersPayload: Filters = {}
    if (params.selectedSource.length) filtersPayload.source = params.selectedSource
    if (params.selectedDateFrom) filtersPayload.date_from = params.selectedDateFrom
    if (params.selectedDateTo) filtersPayload.date_to = params.selectedDateTo
    if (!params.selectedDateFrom && !params.selectedDateTo && params.selectedYear) {
      filtersPayload.date_from = `${params.selectedYear}-01-01`
      filtersPayload.date_to = `${params.selectedYear}-12-31`
    }
    if (params.selectedLegalArea.length) filtersPayload.legal_area = params.selectedLegalArea
    if (params.selectedCity.length) filtersPayload.city = params.selectedCity
    if (params.selectedCourt.length) filtersPayload.court = params.selectedCourt
    if (params.selectedCourtType.length) filtersPayload.court_type = params.selectedCourtType
    if (params.selectedArticle) filtersPayload.article = params.selectedArticle
    if (params.selectedActTitle) filtersPayload.act_title = params.selectedActTitle
    if (params.selectedJudgmentType?.length) filtersPayload.judgment_type = params.selectedJudgmentType
    if (params.selectedIsFinal) filtersPayload.is_final = params.selectedIsFinal
    return filtersPayload
  }

  const searchRAG = async (query: string, filtersOverride?: Filters) => {
    if (!query.trim()) return

    const effectiveFilters = filtersOverride ?? activeFilters
    const filtersToSend = filtersOverride ?? (applyFiltersToRAG ? effectiveFilters : {})

    setLoadingSearch(true)
    setSearchError('')
    setMode('rag')
    setSelectedJudgment(null)
    setSummaryData(null)
    setChatTurns([])

    try {
      const payload = await searchApi.search(
        query.trim(),
        filtersToSend,
      )
      setSearchResult(payload)
      setResults(payload.judgments)
      setResultsTotal(typeof payload.total === 'number' ? payload.total : payload.judgments.length)
      setRagAnswer(payload.answer ?? null)
      setRagLatencyMs(payload.latency_ms)
      if (payload.judgments.length > 0) {
        const first = payload.judgments[0]
        setSelectedJudgment(first)
        void loadSummary(first.id)
      }
    } catch (error) {
      setSearchResult(null)
      setResults([])
      setResultsTotal(0)
      setRagAnswer(null)
      setRagLatencyMs(undefined)
      setSearchError(
        `Wyszukiwanie inteligentne nie powiodło się: ${error instanceof Error ? error.message : 'nieznany błąd'}`,
      )
    } finally {
      setLoadingSearch(false)
    }
  }

  const filterJudgments = async (filtersOverride?: Filters) => {
    const effectiveFilters = filtersOverride ?? activeFilters

    setLoadingSearch(true)
    setSearchError('')
    setMode('filter')
    setRagAnswer(null)
    setRagLatencyMs(undefined)
    setSelectedJudgment(null)
    setSummaryData(null)
    setChatTurns([])

    try {
      const payload = await judgmentsApi.list({
        limit: 100,
        ...(effectiveFilters.source ? { source: effectiveFilters.source } : {}),
        ...(effectiveFilters.legal_area ? { legal_area: effectiveFilters.legal_area } : {}),
        ...(effectiveFilters.city ? { city: effectiveFilters.city } : {}),
        ...(effectiveFilters.court ? { court: effectiveFilters.court } : {}),
        ...(effectiveFilters.court_type ? { court_type: effectiveFilters.court_type } : {}),
        ...(effectiveFilters.date_from ? { date_from: effectiveFilters.date_from } : {}),
        ...(effectiveFilters.date_to ? { date_to: effectiveFilters.date_to } : {}),
        ...(effectiveFilters.article ? { article: effectiveFilters.article } : {}),
        ...(effectiveFilters.act_title ? { act_title: effectiveFilters.act_title } : {}),
        ...(effectiveFilters.judgment_type ? { judgment_type: effectiveFilters.judgment_type } : {}),
        ...(effectiveFilters.is_final ? { is_final: effectiveFilters.is_final } : {}),
      })
      setSearchResult({ judgments: payload.judgments, total: payload.total })
      setResults(payload.judgments)
      setResultsTotal(payload.total)
    } catch (error) {
      setSearchResult(null)
      setResults([])
      setResultsTotal(0)
      setSearchError(
        `Filtrowanie nie powiodło się: ${error instanceof Error ? error.message : 'nieznany błąd'}`,
      )
    } finally {
      setLoadingSearch(false)
    }
  }

  const runSearch = async (params: SearchParams) => {
    const builtFilters = buildFiltersFromParams(params)
    setActiveFilters(builtFilters)
    await searchRAG(params.query, builtFilters)
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
    searchRAG,
    filterJudgments,
    mode,
    ragAnswer,
    ragLatencyMs,
    applyFiltersToRAG,
    setApplyFiltersToRAG,
    activeFilters,
    setActiveFilters,
    results,
    resultsTotal,
    summaryObject,
    loadingSummary,
    summaryError,
    chatTurns,
    loadingChat,
    chatError,
    askAboutJudgment,
  }
}
