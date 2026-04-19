import { useMemo, useState } from 'react'
import { Layout } from '../../components/layout/Layout'
import { SearchToolbar } from '../../components/search/SearchToolbar'
import { FiltersSidebar } from '../../components/search/FiltersSidebar'
import { SearchResultsPanel } from '../../components/search/SearchResultsPanel'
import { useJudgmentsSearch } from '../../hooks/useJudgmentsSearch'

const PAGE_SIZE = 8

export function JudgmentsPage() {
  const [page, setPage] = useState(1)

  const {
    mode,
    ragAnswer,
    ragLatencyMs,
    loadingSearch,
    loadingFilters,
    filters,
    searchError,
    applyFiltersToRAG,
    setApplyFiltersToRAG,
    activeFilters,
    setActiveFilters,
    results,
    searchRAG,
    filterJudgments,
  } = useJudgmentsSearch()

  const totalPages = Math.max(1, Math.ceil(results.length / PAGE_SIZE))

  const pagedResults = useMemo(() => {
    const start = (page - 1) * PAGE_SIZE
    return results.slice(start, start + PAGE_SIZE)
  }, [results, page])

  const handleSearch = (query: string) => {
    setPage(1)
    void searchRAG(query)
  }

  const handleFilter = () => {
    setPage(1)
    void filterJudgments()
  }

  const handleClear = () => {
    setPage(1)
    setActiveFilters({})
    void filterJudgments({})
  }

  return (
    <Layout
      toolbar={
        <SearchToolbar
          onSearch={handleSearch}
          applyFilters={applyFiltersToRAG}
          onApplyFiltersChange={setApplyFiltersToRAG}
          isLoading={loadingSearch}
        />
      }
      sidebar={
        <FiltersSidebar
          filters={activeFilters}
          options={filters}
          optionsLoading={loadingFilters}
          onFiltersChange={setActiveFilters}
          onFilter={handleFilter}
          onClear={handleClear}
          isLoading={loadingSearch}
        />
      }
      content={
        <div>
          {searchError && <div className="error-box">{searchError}</div>}
          <SearchResultsPanel
            mode={mode}
            ragAnswer={ragAnswer}
            ragLatencyMs={ragLatencyMs}
            results={pagedResults}
            totalCount={results.length}
            isLoading={loadingSearch}
            page={page}
            totalPages={totalPages}
            onPreviousPage={() => setPage((prev) => Math.max(1, prev - 1))}
            onNextPage={() => setPage((prev) => Math.min(totalPages, prev + 1))}
          />
        </div>
      }
    />
  )
}
