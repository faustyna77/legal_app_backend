import type { JudgmentResult } from '../../types'

interface AnswerBoxProps {
  answer: string
  sources?: JudgmentResult[]
  latencyMs?: number
}

export function AnswerBox({ answer, sources, latencyMs }: AnswerBoxProps) {
  return (
    <div className="answer-box" style={{ marginBottom: 16 }}>
      <div style={{
        display: 'flex',
        alignItems: 'center',
        gap: 8,
        marginBottom: 10,
        paddingBottom: 8,
        borderBottom: '1px solid var(--color-info-border)',
      }}>
        <span style={{ fontSize: 18 }}>&#x1F4A1;</span>
        <strong style={{ fontSize: 15, color: 'var(--color-text)' }}>Odpowiedź AI</strong>
        {latencyMs !== undefined && (
          <span style={{ marginLeft: 'auto', fontSize: 12, color: 'var(--color-text-subtle)' }}>
            Czas odpowiedzi: {(latencyMs / 1000).toFixed(1)}s
          </span>
        )}
      </div>

      <p style={{ margin: '0 0 10px', fontSize: 14, lineHeight: 1.6 }}>{answer}</p>

      {sources && sources.length > 0 && (
        <div style={{ fontSize: 13, color: 'var(--color-text-muted)' }}>
          <span style={{ fontWeight: 600 }}>Źródła: </span>
          {sources.map((s, i) => (
            <span key={s.id}>
              {i > 0 && ', '}
              <span style={{ color: '#2563eb', fontWeight: 500 }}>{s.case_number}</span>
            </span>
          ))}
        </div>
      )}
    </div>
  )
}
