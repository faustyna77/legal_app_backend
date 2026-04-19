import { useState } from 'react'
import type { FormEvent } from 'react'
import type { ChatTurn, JudgmentResult, SummaryPayload } from '../../types'
import { formatDate } from '../../utils'
import { Spinner } from '../ui/Spinner'
import { ChatMessage } from './ChatMessage'

interface ChatPanelProps {
  selectedJudgment: JudgmentResult | null
  loadingSummary: boolean
  summaryError: string
  summaryObject: SummaryPayload | null
  chatTurns: ChatTurn[]
  loadingChat: boolean
  chatError: string
  onSendQuestion: (question: string) => void
}

const SUMMARY_FIELDS: [keyof SummaryPayload, string][] = [
  ['teza', 'Teza'],
  ['stan_faktyczny', 'Stan faktyczny'],
  ['rozstrzygniecie', 'Rozstrzygnięcie'],
  ['podstawa_prawna', 'Podstawa prawna'],
]

export function ChatPanel({
  selectedJudgment,
  loadingSummary,
  summaryError,
  summaryObject,
  chatTurns,
  loadingChat,
  chatError,
  onSendQuestion,
}: ChatPanelProps) {
  const [chatInput, setChatInput] = useState('')

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault()
    if (!chatInput.trim()) return
    onSendQuestion(chatInput.trim())
    setChatInput('')
  }

  if (!selectedJudgment) {
    return (
      <p style={{ color: 'var(--color-text-muted)', marginTop: 24, textAlign: 'center' }}>
        Wybierz orzeczenie z listy po lewej.-----
      </p>
    )
  }

  const refsOut = selectedJudgment.references_out ?? []
  const refsIn = selectedJudgment.references_in ?? []

  return (
    <>
      <h3>{selectedJudgment.case_number}</h3>
      <p className="meta">
        {selectedJudgment.court} • {formatDate(selectedJudgment.date)}
      </p>

      {/* ── Podsumowanie ── */}
      <div className="detail-block">
        <h4>Podsumowanie</h4>
        {loadingSummary && <Spinner />}
        {summaryError && <div className="error-box">{summaryError}</div>}
        {summaryObject && (
          <div className="summary-grid">
            {SUMMARY_FIELDS.map(([key, label]) => (
              <div key={key}>
                <h5>{label}</h5>
                <p>{summaryObject[key] || '—'}</p>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* ── Asystent AI ── */}
      <div className="detail-block">
        <h4>Asystent AI</h4>
        <form className="chat-form" onSubmit={handleSubmit}>
          <input
            value={chatInput}
            onChange={(e) => setChatInput(e.target.value)}
            placeholder="Zadaj pytanie o to orzeczenie"
          />
          <button type="submit" disabled={loadingChat}>
            {loadingChat ? 'Wysyłam...' : 'Wyślij'}
          </button>
        </form>
        {chatError && <div className="error-box">{chatError}</div>}
        <div className="chat-list">
          {chatTurns.map((turn) => (
            <ChatMessage key={turn.id} turn={turn} />
          ))}
        </div>
      </div>

      {/* ── Powiązania ── */}
      <div className="detail-block">
        <h4>Powiązania</h4>
        {refsOut.length > 0 && (
          <div style={{ marginBottom: 10 }}>
            <p className="meta" style={{ marginBottom: 4 }}>
              Cytuje ({refsOut.length}):
            </p>
            <ul style={{ margin: 0, paddingLeft: 16 }}>
              {refsOut.slice(0, 5).map((ref, i) => (
                <li key={i} style={{ fontSize: 13, marginBottom: 2 }}>
                  {ref.referenced_case_number}
                  {ref.court && ` · ${ref.court}`}
                  {ref.referenced_judgment_id === null && (
                    <span style={{ color: 'var(--color-text-subtle)', fontSize: 11 }}> (poza bazą)</span>
                  )}
                </li>
              ))}
              {refsOut.length > 5 && (
                <li style={{ fontSize: 12, color: 'var(--color-text-subtle)' }}>
                  +{refsOut.length - 5} więcej
                </li>
              )}
            </ul>
          </div>
        )}
        {refsIn.length > 0 && (
          <div>
            <p className="meta" style={{ marginBottom: 4 }}>
              Cytowane przez ({refsIn.length}):
            </p>
            <ul style={{ margin: 0, paddingLeft: 16 }}>
              {refsIn.slice(0, 5).map((ref, i) => (
                <li key={i} style={{ fontSize: 13, marginBottom: 2 }}>
                  {ref.case_number}
                  {ref.court && ` · ${ref.court}`}
                </li>
              ))}
              {refsIn.length > 5 && (
                <li style={{ fontSize: 12, color: 'var(--color-text-subtle)' }}>
                  +{refsIn.length - 5} więcej
                </li>
              )}
            </ul>
          </div>
        )}
        {refsOut.length === 0 && refsIn.length === 0 && (
          <p style={{ color: 'var(--color-text-muted)', fontSize: 13 }}>Brak powiązań.</p>
        )}
      </div>
    </>
  )
}
