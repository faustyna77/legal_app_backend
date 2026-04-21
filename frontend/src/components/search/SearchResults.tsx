import type { JudgmentResult, SortMode, ViewMode } from '../../types'
import type { ReactNode } from 'react'
import { JudgmentCard } from '../judgments/JudgmentCard'
import { AnswerBox } from './AnswerBox'
import { Spinner } from '../ui/Spinner'

interface SearchResultsProps {
  headerLabel: string
  latencyMs?: number
  sortMode: SortMode
  onSortChange: (mode: SortMode) => void
  viewMode: ViewMode
  onViewModeChange: (mode: ViewMode) => void
  results: JudgmentResult[]
  selectedJudgmentId?: number
  onSelectJudgment: (judgment: JudgmentResult) => void
  answer?: string
  error: string
  page: number
  totalPages: number
  onPreviousPage: () => void
  onNextPage: () => void
  loading?: boolean
  renderCardAction?: (judgment: JudgmentResult) => ReactNode
}

export function SearchResults({
  headerLabel, latencyMs, sortMode, onSortChange, viewMode, onViewModeChange,
  results, selectedJudgmentId, onSelectJudgment, answer, error,
  page, totalPages, onPreviousPage, onNextPage, loading, renderCardAction,
}: SearchResultsProps) {
  return (
    <>
      <div className="results-header">
        <h2 style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          {headerLabel}
          {loading && <Spinner size={18} />}
        </h2>
        <div className="results-controls">
          {latencyMs !== undefined && <span>{latencyMs} ms</span>}
          <select value={sortMode} onChange={(e) => onSortChange(e.target.value as SortMode)}>
            <option value="relevance">Trafność</option>
            <option value="newest">Najnowsze</option>
            <option value="oldest">Najstarsze</option>
          </select>
          <div className="view-toggle">
            <button
              type="button"
              className={`toggle-btn${viewMode === 'list' ? ' active' : ''}`}
              onClick={() => onViewModeChange('list')}
            >
              Lista
            </button>
            <button
              type="button"
              className={`toggle-btn${viewMode === 'grid' ? ' active' : ''}`}
              onClick={() => onViewModeChange('grid')}
            >
              Siatka
            </button>
          </div>
        </div>
      </div>

      {error && <div className="error-box">{error}</div>}
      {answer && <AnswerBox answer={answer} />}

      <div className={viewMode === 'grid' ? 'results-grid' : 'results-list'}>
        {results.map((judgment) => (
          <JudgmentCard
            key={judgment.id}
            judgment={judgment}
            isSelected={selectedJudgmentId === judgment.id}
            onClick={() => onSelectJudgment(judgment)}
            action={renderCardAction ? renderCardAction(judgment) : undefined}
          />
        ))}
      </div>

      {results.length > 0 && (
        <div className="pagination-row">
          <button type="button" onClick={onPreviousPage} disabled={page <= 1}>
            Poprzednia
          </button>
          <span>Strona {page} z {totalPages}</span>
          <button type="button" onClick={onNextPage} disabled={page >= totalPages}>
            Następna
          </button>
        </div>
      )}
    </>
  )
}
