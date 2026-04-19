import { useNavigate } from 'react-router-dom'
import { JudgmentCard } from '../judgments/JudgmentCard'
import { AnswerBox } from './AnswerBox'
import { Spinner } from '../ui/Spinner'
import type { JudgmentResult } from '../../types'

interface SearchResultsPanelProps {
  mode: 'rag' | 'filter'
  ragAnswer: string | null
  ragLatencyMs?: number
  results: JudgmentResult[]
  totalCount: number
  isLoading: boolean
  page: number
  totalPages: number
  onPreviousPage: () => void
  onNextPage: () => void
}

export function SearchResultsPanel({
  mode,
  ragAnswer,
  ragLatencyMs,
  results,
  totalCount,
  isLoading,
  page,
  totalPages,
  onPreviousPage,
  onNextPage,
}: SearchResultsPanelProps) {
  const navigate = useNavigate()

  if (isLoading) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', padding: 40 }}>
        <Spinner size={32} />
      </div>
    )
  }

  return (
    <>
      {mode === 'rag' && ragAnswer && (
        <AnswerBox answer={ragAnswer} sources={results.slice(0, 5)} latencyMs={ragLatencyMs} />
      )}

      {mode === 'filter' && (
        <div className="results-header" style={{ marginBottom: 12 }}>
          <h2 style={{ margin: 0 }}>Znaleziono {totalCount} orzeczeń</h2>
        </div>
      )}

      <div className="results-list">
        {results.map((judgment) => (
          <JudgmentCard
            key={judgment.id}
            judgment={judgment}
            isSelected={false}
            onClick={() => navigate(`/judgments/${judgment.id}`)}
          />
        ))}
      </div>

      {totalCount > 0 && totalPages > 1 && (
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
