import { useEffect, useMemo, useState } from 'react'
import type { FormEvent } from 'react'
import { NavLink, useNavigate } from 'react-router-dom'
import { Layout } from '../../components/layout/Layout'
import { SearchBar } from '../../components/search/SearchBar'
import { SearchResults } from '../../components/search/SearchResults'
import { JudgmentFilters } from '../../components/judgments/JudgmentFilters'
import { useJudgmentsSearch } from '../../hooks/useJudgmentsSearch'
import { judgmentsApi, foldersApi } from '../../api'
import type { Folder, JudgmentResult, SortMode, ViewMode } from '../../types'
import { useAuthStore } from '../../contexts/authStore'
import { ROUTES } from '../../config'

const PAGE_SIZE = 8

export function SearchPage() {
  const navigate = useNavigate()
  const { isAuthenticated } = useAuthStore()

  // ── filter state ──────────────────────────────────────────────────────────
  const [query, setQuery] = useState('')
  const [selectedSource, setSelectedSource] = useState<string[]>([])
  const [selectedYear, setSelectedYear] = useState('')
  const [selectedLegalArea, setSelectedLegalArea] = useState<string[]>([])
  const [selectedCity, setSelectedCity] = useState<string[]>([])
  const [selectedCourt, setSelectedCourt] = useState<string[]>([])
  const [selectedCourtType, setSelectedCourtType] = useState<string[]>([])
  const [selectedDateFrom, setSelectedDateFrom] = useState('')
  const [selectedDateTo, setSelectedDateTo] = useState('')
  const [selectedArticle, setSelectedArticle] = useState('')
  const [selectedActTitle, setSelectedActTitle] = useState('')
  const [selectedJudgmentType, setSelectedJudgmentType] = useState<string[]>([])
  const [selectedIsFinal, setSelectedIsFinal] = useState('')
  const [sortMode, setSortMode] = useState<SortMode>('newest')
  const [viewMode, setViewMode] = useState<ViewMode>('list')
  const [page, setPage] = useState(1)
  const [applyFiltersToAI, setApplyFiltersToAI] = useState(false)

  // ── browse list (no search query) ─────────────────────────────────────────
  const [browseList, setBrowseList] = useState<JudgmentResult[]>([])
  const [browseTotal, setBrowseTotal] = useState<number>(0)
  const [loadingBrowse, setLoadingBrowse] = useState(true)
  const [hasSearched, setHasSearched] = useState(false)
  const [folders, setFolders] = useState<Folder[]>([])
  const [foldersLoading, setFoldersLoading] = useState(false)

  const loadBrowseList = (opts: {
    year?: string
    source?: string[]
    court?: string[]
    court_type?: string[]
    legal_area?: string[]
    city?: string[]
    date_from?: string
    date_to?: string
    article?: string | string[]
    act_title?: string | string[]
    judgment_type?: string[]
    is_final?: string
  } = {}) => {
    setLoadingBrowse(true)
    const dateFrom = opts.date_from || (opts.year ? `${opts.year}-01-01` : undefined)
    const dateTo = opts.date_to || (opts.year ? `${opts.year}-12-31` : undefined)
    const params: Parameters<typeof judgmentsApi.list>[0] = {
      limit: 100,
      ...(opts.source?.length ? { source: opts.source } : {}),
      ...(opts.legal_area?.length ? { legal_area: opts.legal_area } : {}),
      ...(opts.city?.length ? { city: opts.city } : {}),
      ...(opts.court?.length ? { court: opts.court } : {}),
      ...(opts.court_type?.length ? { court_type: opts.court_type } : {}),
      ...(dateFrom ? { date_from: dateFrom } : {}),
      ...(dateTo ? { date_to: dateTo } : {}),
      ...(opts.article ? { article: opts.article } : {}),
      ...(opts.act_title ? { act_title: opts.act_title } : {}),
      ...(opts.judgment_type?.length ? { judgment_type: opts.judgment_type } : {}),
      ...(opts.is_final ? { is_final: opts.is_final } : {}),
    }
    judgmentsApi
      .list(params)
      .then((payload) => {
        setBrowseList(payload.judgments)
        setBrowseTotal(payload.total)
      })
      .catch(() => {
        setBrowseList([])
        setBrowseTotal(0)
      })
      .finally(() => setLoadingBrowse(false))
  }

  useEffect(() => {
    const timer = window.setTimeout(() => {
      loadBrowseList()
    }, 0)
    return () => window.clearTimeout(timer)
  }, [])

  useEffect(() => {
    if (!isAuthenticated) {
      const timer = window.setTimeout(() => {
        setFolders([])
      }, 0)
      return () => window.clearTimeout(timer)
    }
    const timer = window.setTimeout(() => {
      setFoldersLoading(true)
      foldersApi
        .list()
        .then((payload) => {
          setFolders(payload.folders)
        })
        .catch(() => {
          setFolders([])
        })
        .finally(() => setFoldersLoading(false))
    }, 0)
    return () => window.clearTimeout(timer)
  }, [isAuthenticated])

  // ── search hook ──────────────────────────────────────────────────────────
  const { filters, loadingFilters, searchResult, loadingSearch, searchError, runSearch, filterJudgments, resultsTotal } =
    useJudgmentsSearch()

  // ── active list ───────────────────────────────────────────────────────────
  const sortedJudgments = useMemo(() => {
    const activeJudgments: JudgmentResult[] = hasSearched
      ? (searchResult?.judgments ?? [])
      : browseList
    const list = [...activeJudgments]
    if (sortMode === 'newest')
      return list.sort((a, b) => String(b.date).localeCompare(String(a.date)))
    if (sortMode === 'oldest')
      return list.sort((a, b) => String(a.date).localeCompare(String(b.date)))
    if (hasSearched)
      return list.sort((a, b) => (b.similarity ?? 0) - (a.similarity ?? 0))
    return list
  }, [searchResult, browseList, sortMode, hasSearched])

  const totalPages = Math.max(1, Math.ceil(sortedJudgments.length / PAGE_SIZE))

  const safePage = Math.min(page, totalPages)

  const pagedJudgments = useMemo(() => {
    const start = (safePage - 1) * PAGE_SIZE
    return sortedJudgments.slice(start, start + PAGE_SIZE)
  }, [sortedJudgments, safePage])

  // ── handlers ─────────────────────────────────────────────────────────────
  const handleSearch = (e: FormEvent) => {
    e.preventDefault()
    if (!query.trim()) return
    setPage(1)
    setHasSearched(true)

    const shouldApplyFilters = applyFiltersToAI
    void runSearch({
      query,
      selectedSource: shouldApplyFilters ? selectedSource : [],
      selectedYear: shouldApplyFilters ? selectedYear : '',
      selectedLegalArea: shouldApplyFilters ? selectedLegalArea : [],
      selectedCity: shouldApplyFilters ? selectedCity : [],
      selectedCourt: shouldApplyFilters ? selectedCourt : [],
      selectedCourtType: shouldApplyFilters ? selectedCourtType : [],
      selectedDateFrom: shouldApplyFilters ? selectedDateFrom : '',
      selectedDateTo: shouldApplyFilters ? selectedDateTo : '',
      selectedArticle: shouldApplyFilters ? selectedArticle : '',
      selectedActTitle: shouldApplyFilters ? selectedActTitle : '',
    })
  }

  const handleApplyFilters = () => {
    setPage(1)
    const anyAdvanced = !!(
      selectedSource.length ||
      selectedYear ||
      selectedLegalArea.length ||
      selectedCity.length ||
      selectedCourt.length ||
      selectedCourtType.length ||
      selectedDateFrom ||
      selectedDateTo ||
      selectedArticle ||
      selectedActTitle ||
      selectedJudgmentType.length ||
      selectedIsFinal
    )

    if (!anyAdvanced && !query.trim()) {
      setHasSearched(false)
      loadBrowseList()
      return
    }

    setHasSearched(true)
    void filterJudgments({
      source: selectedSource.length ? selectedSource : undefined,
      legal_area: selectedLegalArea.length ? selectedLegalArea : undefined,
      city: selectedCity.length ? selectedCity : undefined,
      court: selectedCourt.length ? selectedCourt : undefined,
      court_type: selectedCourtType.length ? selectedCourtType : undefined,
      date_from: selectedDateFrom || (selectedYear ? `${selectedYear}-01-01` : undefined),
      date_to: selectedDateTo || (selectedYear ? `${selectedYear}-12-31` : undefined),
      article: selectedArticle || undefined,
      act_title: selectedActTitle || undefined,
      judgment_type: selectedJudgmentType.length ? selectedJudgmentType : undefined,
      is_final: selectedIsFinal || undefined,
    })
  }

  const handleClearFilters = () => {
    setSelectedSource([])
    setSelectedYear('')
    setSelectedLegalArea([])
    setSelectedCity([])
    setSelectedCourt([])
    setSelectedCourtType([])
    setSelectedDateFrom('')
    setSelectedDateTo('')
    setSelectedArticle('')
    setSelectedActTitle('')
    setSelectedJudgmentType([])
    setSelectedIsFinal('')
    setHasSearched(false)
    setPage(1)
    loadBrowseList()
  }

  const addToFolder = (folderId: number, judgment: JudgmentResult) => {
    if (!isAuthenticated) return
    void foldersApi.addJudgment(folderId, {
      judgment_id: judgment.id,
      case_number: judgment.case_number,
      court: judgment.court ?? null,
      date: judgment.date ?? null,
    })
  }

  const uiTotalCount = hasSearched
    ? (resultsTotal ?? sortedJudgments.length)
    : browseTotal

  const headerLabel = hasSearched
    ? `${uiTotalCount} wyników`
    : `Ostatnie orzeczenia (${uiTotalCount})`

  return (
    <Layout
      toolbar={
        <SearchBar
          query={query}
          onQueryChange={setQuery}
          loading={loadingSearch}
          onSubmit={handleSearch}
          placeholder="Wpisz pytanie prawne..."
          submitLabel="Szukaj inteligentnie"
          showFiltersCheckbox
          applyFiltersToAI={applyFiltersToAI}
          onApplyFiltersToAIChange={setApplyFiltersToAI}
        />
      }
      sidebar={
        <JudgmentFilters
          filters={filters}
          loading={loadingFilters}
          totalCount={uiTotalCount}
          selectedSource={selectedSource}     onSelectSource={setSelectedSource}
          selectedYear={selectedYear}         onSelectYear={setSelectedYear}
          selectedLegalArea={selectedLegalArea} onSelectLegalArea={setSelectedLegalArea}
          selectedCity={selectedCity}         onSelectCity={setSelectedCity}
          selectedCourt={selectedCourt}       onSelectCourt={setSelectedCourt}
          selectedCourtType={selectedCourtType} onSelectCourtType={setSelectedCourtType}
          selectedDateFrom={selectedDateFrom} onSelectDateFrom={setSelectedDateFrom}
          selectedDateTo={selectedDateTo}     onSelectDateTo={setSelectedDateTo}
          selectedArticle={selectedArticle}   onSelectArticle={setSelectedArticle}
          selectedActTitle={selectedActTitle} onSelectActTitle={setSelectedActTitle}
          selectedJudgmentType={selectedJudgmentType} onSelectJudgmentType={setSelectedJudgmentType}
          selectedIsFinal={selectedIsFinal}   onSelectIsFinal={setSelectedIsFinal}
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
          page={safePage}
          totalPages={totalPages}
          onPreviousPage={() => setPage((p) => Math.max(1, p - 1))}
          onNextPage={() => setPage((p) => Math.min(totalPages, p + 1))}
          loading={loadingSearch || (!hasSearched && loadingBrowse)}
          renderCardAction={(judgment) => (
            isAuthenticated ? (
              <div style={{ marginTop: 10, display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                {foldersLoading ? (
                  <span style={{ fontSize: 12, color: 'var(--color-text-muted)' }}>Ładowanie katalogów...</span>
                ) : folders.length === 0 ? (
                  <NavLink to={ROUTES.ORGANIZATION} className="ghost-btn" style={{ fontSize: 12 }}>
                    Utwórz katalog
                  </NavLink>
                ) : (
                  folders.map((folder) => (
                    <button
                      key={folder.id}
                      type="button"
                      className="ghost-btn"
                      style={{ fontSize: 12 }}
                      onClick={(e) => {
                        e.stopPropagation()
                        addToFolder(folder.id, judgment)
                      }}
                    >
                      + {folder.name}
                    </button>
                  ))
                )}
              </div>
            ) : (
              <div style={{ marginTop: 10 }}>
                <NavLink to={ROUTES.LOGIN} className="ghost-btn" style={{ fontSize: 12 }} onClick={(e) => e.stopPropagation()}>
                  Zaloguj się, aby dodać do katalogu
                </NavLink>
              </div>
            )
          )}
        />
      }
    />
  )
}
