import { useEffect, useMemo, useState } from 'react'
import type { FormEvent } from 'react'
import { useNavigate } from 'react-router-dom'
import { Layout } from '../../components/layout/Layout'
import { SearchBar } from '../../components/search/SearchBar'
import { SearchResults } from '../../components/search/SearchResults'
import { JudgmentFilters } from '../../components/judgments/JudgmentFilters'
import { useJudgmentsSearch } from '../../hooks/useJudgmentsSearch'
import { judgmentsApi } from '../../api/judgments'
import type { JudgmentResult, SortMode, ViewMode } from '../../types'

const PAGE_SIZE = 8

/** Map source filter value → fragment of source_url (from filters.py CASE expression) */
const SOURCE_URL_MAP: Record<string, string> = {
  nsa:  'nsa.gov.pl',
  saos: 'saos.org.pl',
  sn:   'sn.pl',
  cjeu: 'curia.europa.eu',
}

function matchesSource(j: JudgmentResult, source: string): boolean {
  if (!source) return true
  const src = (j.source ?? '').toLowerCase()
  if (src === source.toLowerCase()) return true
  const url = (j.source_url ?? '').toLowerCase()
  const needle = SOURCE_URL_MAP[source.toLowerCase()] ?? source.toLowerCase()
  return url.includes(needle)
}

export function SearchPage() {
  const navigate = useNavigate()

  // ── filter state ──────────────────────────────────────────────────────────
  const [query, setQuery] = useState('')
  const [selectedSource, setSelectedSource] = useState('')
  const [selectedYear, setSelectedYear] = useState('')
  const [selectedLegalArea, setSelectedLegalArea] = useState('')
  const [selectedCity, setSelectedCity] = useState('')
  const [selectedCourt, setSelectedCourt] = useState('')
  const [selectedCourtType, setSelectedCourtType] = useState('')
  const [sortMode, setSortMode] = useState<SortMode>('newest')
  const [viewMode, setViewMode] = useState<ViewMode>('list')
  const [page, setPage] = useState(1)

  // ── browse list (no search query) ─────────────────────────────────────────
  const [browseList, setBrowseList] = useState<JudgmentResult[]>([])
  const [loadingBrowse, setLoadingBrowse] = useState(true)
  const [hasSearched, setHasSearched] = useState(false)

  const loadBrowseList = (opts: {
    year?: string
    source?: string
    court?: string
  } = {}) => {
    setLoadingBrowse(true)
    const params: Parameters<typeof judgmentsApi.list>[0] = {
      limit: 100,                          // max allowed by backend
      ...(opts.court ? { court: opts.court } : {}),
      ...(opts.year ? {
        date_from: `${opts.year}-01-01`,
        date_to:   `${opts.year}-12-31`,
      } : {}),
    }
    judgmentsApi
      .list(params)
      .then((list) => {
        // court is filtered server-side; source_url is filtered client-side
        const filtered = list.filter((j) => matchesSource(j, opts.source ?? ''))
        setBrowseList(filtered)
      })
      .catch(() => {})
      .finally(() => setLoadingBrowse(false))
  }

  useEffect(() => { loadBrowseList() }, []) // initial load

  // ── search hook ──────────────────────────────────────────────────────────
  const { filters, loadingFilters, searchResult, loadingSearch, searchError, runSearch } =
    useJudgmentsSearch()

  // ── active list ───────────────────────────────────────────────────────────
  const activeJudgments: JudgmentResult[] = hasSearched
    ? (searchResult?.judgments ?? [])
    : browseList

  const sortedJudgments = useMemo(() => {
    const list = [...activeJudgments]
    if (sortMode === 'newest')
      return list.sort((a, b) => String(b.date).localeCompare(String(a.date)))
    if (sortMode === 'oldest')
      return list.sort((a, b) => String(a.date).localeCompare(String(b.date)))
    if (hasSearched)
      return list.sort((a, b) => (b.similarity ?? 0) - (a.similarity ?? 0))
    return list
  }, [activeJudgments, sortMode, hasSearched])

  const totalPages = Math.max(1, Math.ceil(sortedJudgments.length / PAGE_SIZE))

  const pagedJudgments = useMemo(() => {
    const start = (page - 1) * PAGE_SIZE
    return sortedJudgments.slice(start, start + PAGE_SIZE)
  }, [sortedJudgments, page])

  useEffect(() => {
    if (page > totalPages) setPage(1)
  }, [page, totalPages])

  // ── handlers ─────────────────────────────────────────────────────────────
  const handleSearch = (e: FormEvent) => {
    e.preventDefault()
    if (!query.trim()) return
    setPage(1)
    setHasSearched(true)
    void runSearch({
      query, selectedSource, selectedYear,
      selectedLegalArea, selectedCity,
      selectedCourt, selectedCourtType,
    })
  }

  const handleApplyFilters = () => {
    setPage(1)
    if (query.trim()) {
      // semantic search + all filters
      setHasSearched(true)
      void runSearch({
        query, selectedSource, selectedYear,
        selectedLegalArea, selectedCity,
        selectedCourt, selectedCourtType,
      })
      return
    }

    // browse mode (no query):
    // GET /judgments only supports court + date range.
    // For any other filter we must go through the search pipeline.
    const needsSearchPipeline = !!(
      selectedSource || selectedLegalArea || selectedCity || selectedCourtType
    )

    if (needsSearchPipeline) {
      setHasSearched(true)
      void runSearch({
        query: 'orzeczenie sądowe',
        selectedSource, selectedYear,
        selectedLegalArea, selectedCity,
        selectedCourt, selectedCourtType,
      })
    } else {
      // only court and/or year — use browse list (fast, no LLM)
      setHasSearched(false)
      loadBrowseList({
        year:   selectedYear,
        source: '',
        court:  selectedCourt,
      })
    }
  }

  const handleClearFilters = () => {
    setSelectedSource('')
    setSelectedYear('')
    setSelectedLegalArea('')
    setSelectedCity('')
    setSelectedCourt('')
    setSelectedCourtType('')
    setHasSearched(false)
    setPage(1)
    loadBrowseList()
  }

  const headerLabel = hasSearched
    ? `${sortedJudgments.length} wyników`
    : `Ostatnie orzeczenia (${sortedJudgments.length})`

  return (
    <Layout
      toolbar={
        <SearchBar
          query={query}
          onQueryChange={setQuery}
          loading={loadingSearch}
          onSubmit={handleSearch}
        />
      }
      sidebar={
        <JudgmentFilters
          filters={filters}
          loading={loadingFilters}
          selectedSource={selectedSource}     onSelectSource={setSelectedSource}
          selectedYear={selectedYear}         onSelectYear={setSelectedYear}
          selectedLegalArea={selectedLegalArea} onSelectLegalArea={setSelectedLegalArea}
          selectedCity={selectedCity}         onSelectCity={setSelectedCity}
          selectedCourt={selectedCourt}       onSelectCourt={setSelectedCourt}
          selectedCourtType={selectedCourtType} onSelectCourtType={setSelectedCourtType}
          onApplyFilters={handleApplyFilters}
          onClearFilters={handleClearFilters}
        />
      }
      content={
        <SearchResults
          headerLabel={headerLabel}
          latencyMs={hasSearched ? searchResult?.latency_ms : undefined}
          sortMode={sortMode}
          onSortChange={setSortMode}
          viewMode={viewMode}
          onViewModeChange={setViewMode}
          results={pagedJudgments}
          onSelectJudgment={(j) => navigate(`/judgments/${j.id}`)}
          answer={hasSearched ? searchResult?.answer : undefined}
          error={searchError}
          page={page}
          totalPages={totalPages}
          onPreviousPage={() => setPage((p) => Math.max(1, p - 1))}
          onNextPage={() => setPage((p) => Math.min(totalPages, p + 1))}
          loading={loadingSearch || (!hasSearched && loadingBrowse)}
        />
      }
    />
  )
}
