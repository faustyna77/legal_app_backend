import type { JudgmentResult } from '../../types'
import { formatDate, formatSimilarity, truncate } from '../../utils'
import { Badge } from '../ui/Badge'

interface JudgmentCardProps {
  judgment: JudgmentResult
  isSelected: boolean
  onClick: () => void
}

export function JudgmentCard({ judgment, isSelected, onClick }: JudgmentCardProps) {
  return (
    <article
      className={`result-card${isSelected ? ' active' : ''}`}
      onClick={onClick}
      role="button"
      tabIndex={0}
      onKeyDown={(e) => e.key === 'Enter' && onClick()}
    >
      <div className="card-title-row">
        <h3>{judgment.case_number}</h3>
        <time dateTime={judgment.date}>{formatDate(judgment.date)}</time>
      </div>
      <p className="meta">{judgment.court}</p>
      {(judgment.thesis ?? judgment.content) && (
        <p className="excerpt">{truncate(judgment.thesis ?? judgment.content)}</p>
      )}
      <div className="tags-row">
        {judgment.source && <Badge>{judgment.source}</Badge>}
        {judgment.similarity !== undefined && (
          <Badge>trafność {formatSimilarity(judgment.similarity)}</Badge>
        )}
      </div>
    </article>
  )
}
