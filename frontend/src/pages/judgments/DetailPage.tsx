import { useState } from 'react'
import type { FormEvent } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { Layout } from '../../components/layout/Layout'
import { ChatMessage } from '../../components/chat/ChatMessage'
import { Spinner } from '../../components/ui/Spinner'
import { JudgmentCard } from '../../components/judgments/JudgmentCard'
import { useJudgmentDetail } from '../../hooks/useJudgmentDetail'
import { formatDate } from '../../utils'

const SUMMARY_FIELDS = [
  ['teza', 'Teza'],
  ['stan_faktyczny', 'Stan faktyczny'],
  ['rozstrzygniecie', 'Rozstrzygnięcie'],
  ['podstawa_prawna', 'Podstawa prawna'],
] as const

export function JudgmentDetailPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const numId = Number(id)

  const {
    judgment, loading, error,
    summaryObject, loadingSummary, summaryError,
    similar,
    references, regulations,
    chatTurns, loadingChat, chatError, askQuestion,
  } = useJudgmentDetail(numId)

  const [chatInput, setChatInput] = useState('')

  const handleChat = (e: FormEvent) => {
    e.preventDefault()
    if (!chatInput.trim()) return
    void askQuestion(chatInput.trim())
    setChatInput('')
  }

  if (loading) {
    return (
      <Layout
        content={
          <div style={{ display: 'flex', justifyContent: 'center', padding: 60 }}>
            <Spinner size={36} />
          </div>
        }
      />
    )
  }

  if (error) {
    return (
      <Layout
        content={
          <div>
            <button className="ghost-btn" onClick={() => navigate(-1)} style={{ marginBottom: 16, fontSize: 13 }}>
              ← Wróć
            </button>
            <div className="error-box">{error}</div>
          </div>
        }
      />
    )
  }

  if (!judgment) return null

  // ── Main content (left / wider column) ───────────────────────────────────
  const mainContent = (
    <div>
      <button
        className="ghost-btn"
        type="button"
        onClick={() => navigate(-1)}
        style={{ marginBottom: 20, fontSize: 13 }}
      >
        ← Wróć do listy
      </button>

      {/* Header */}
      <h2 style={{ margin: '0 0 6px', fontSize: 22 }}>{judgment.case_number}</h2>
      <p className="meta" style={{ margin: '0 0 12px' }}>
        {judgment.court} • {formatDate(judgment.date)}
      </p>

      {/* Link to original */}
      {judgment.source_url && (
        <a
          href={judgment.source_url}
          target="_blank"
          rel="noopener noreferrer"
          style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: 6,
            marginBottom: 20,
            color: 'var(--color-primary)',
            fontSize: 14,
            textDecoration: 'none',
            border: '1px solid var(--color-info-border)',
            background: 'var(--color-info-bg)',
            borderRadius: 'var(--radius-md)',
            padding: '8px 14px',
          }}
        >
          ↗ Otwórz oryginalne orzeczenie
        </a>
      )}

      {/* AI Summary */}
      <div className="detail-block" style={{ borderTop: 'none', paddingTop: 0 }}>
        <h4 style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          Podsumowanie AI
          {loadingSummary && <Spinner size={16} />}
        </h4>
        {summaryError && <div className="error-box">{summaryError}</div>}
        {!loadingSummary && !summaryObject && !summaryError && (
          <p style={{ color: 'var(--color-text-muted)', fontSize: 14 }}>Generowanie podsumowania...</p>
        )}
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

      {/* Similar judgments */}
      {similar.length > 0 && (
        <div className="detail-block">
          <h4>Podobne orzeczenia</h4>
          <div className="results-list">
            {similar.map((j) => (
              <JudgmentCard
                key={j.id}
                judgment={j}
                isSelected={false}
                onClick={() => navigate(`/judgments/${j.id}`)}
              />
            ))}
          </div>
        </div>
      )}

      {/* Related judgments (references) */}
      {references && (references.references_out.length > 0 || references.references_in.length > 0) && (
        <div className="detail-block">
          <h4>Powiązane orzeczenia</h4>
          {references.references_out.length > 0 && (
            <>
              <h5 style={{ marginBottom: 6 }}>Cytowane przez to orzeczenie</h5>
              <ul style={{ margin: '0 0 12px', paddingLeft: 20, fontSize: 14, lineHeight: 1.8 }}>
                {references.references_out.map((ref) => (
                  <li key={ref.case_number}>
                    {ref.in_database && ref.judgment_id ? (
                      <button
                        type="button"
                        className="link-btn"
                        onClick={() => navigate(`/judgments/${ref.judgment_id}`)}
                        style={{ color: 'var(--color-primary)', background: 'none', border: 'none', cursor: 'pointer', padding: 0, fontSize: 'inherit' }}
                      >
                        {ref.case_number}
                      </button>
                    ) : (
                      <span>{ref.case_number}</span>
                    )}
                    {ref.court && <span style={{ color: 'var(--color-text-muted)' }}> — {ref.court}</span>}
                    {ref.date && <span style={{ color: 'var(--color-text-muted)' }}> ({ref.date})</span>}
                    {!ref.in_database && <span style={{ color: 'var(--color-text-muted)', fontSize: 12 }}> [brak w bazie]</span>}
                  </li>
                ))}
              </ul>
            </>
          )}
          {references.references_in.length > 0 && (
            <>
              <h5 style={{ marginBottom: 6 }}>Cytowane przez inne orzeczenia</h5>
              <ul style={{ margin: 0, paddingLeft: 20, fontSize: 14, lineHeight: 1.8 }}>
                {references.references_in.map((ref) => (
                  <li key={ref.judgment_id}>
                    <button
                      type="button"
                      className="link-btn"
                      onClick={() => navigate(`/judgments/${ref.judgment_id}`)}
                      style={{ color: 'var(--color-primary)', background: 'none', border: 'none', cursor: 'pointer', padding: 0, fontSize: 'inherit' }}
                    >
                      {ref.case_number}
                    </button>
                    {ref.court && <span style={{ color: 'var(--color-text-muted)' }}> — {ref.court}</span>}
                    {ref.date && <span style={{ color: 'var(--color-text-muted)' }}> ({ref.date})</span>}
                  </li>
                ))}
              </ul>
            </>
          )}
        </div>
      )}

      {/* Referenced regulations */}
      {regulations && regulations.regulations.length > 0 && (
        <div className="detail-block">
          <h4>Powołane przepisy</h4>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            {regulations.regulations.map((reg, i) => (
              <div key={i} style={{ fontSize: 14 }}>
                <span style={{ fontWeight: 600 }}>{reg.act_title}</span>
                {reg.act_year && <span style={{ color: 'var(--color-text-muted)' }}> ({reg.act_year})</span>}
                {reg.articles.length > 0 && (
                  <div style={{ color: 'var(--color-text-muted)', marginTop: 2, fontSize: 13 }}>
                    {reg.articles.join(', ')}
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Official content */}
      {judgment.content && (
        <div className="detail-block">
          <h4>Treść orzeczenia</h4>
          <div
            style={{
              background: '#f8fafc',
              border: '1px solid var(--color-border)',
              borderRadius: 'var(--radius-md)',
              padding: '16px 20px',
              maxHeight: 520,
              overflowY: 'auto',
              fontSize: 14,
              lineHeight: 1.7,
              whiteSpace: 'pre-wrap',
              fontFamily: 'Georgia, "Times New Roman", serif',
              color: '#1e293b',
            }}
          >
            {judgment.content}
          </div>
        </div>
      )}
    </div>
  )

  // ── Chat (right column) ───────────────────────────────────────────────────
  const chatContent = (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      <h3 style={{ margin: '0 0 14px' }}>Asystent AI</h3>

      <form className="chat-form" onSubmit={handleChat}>
        <input
          value={chatInput}
          onChange={(e) => setChatInput(e.target.value)}
          placeholder="Zadaj pytanie o to orzeczenie..."
        />
        <button type="submit" disabled={loadingChat}>
          {loadingChat ? 'Wysyłam...' : 'Wyślij'}
        </button>
      </form>

      {chatError && <div className="error-box" style={{ marginTop: 8 }}>{chatError}</div>}

      <div className="chat-list" style={{ marginTop: 14, flex: 1, overflowY: 'auto' }}>
        {chatTurns.length === 0 && (
          <p style={{ color: 'var(--color-text-muted)', fontSize: 14, textAlign: 'center', marginTop: 32 }}>
            Możesz zadawać pytania dotyczące<br />tego orzeczenia.
          </p>
        )}
        {chatTurns.map((turn) => (
          <ChatMessage key={turn.id} turn={turn} />
        ))}
      </div>
    </div>
  )

  return <Layout content={mainContent} details={chatContent} />
}
