import { useEffect, useRef, useState } from 'react'
import type { FormEvent } from 'react'
import { Link, Navigate, useParams } from 'react-router-dom'
import { Layout } from '../../components/layout/Layout'
import { useAuthStore } from '../../contexts/authStore'
import { foldersApi } from '../../api'
import { ROUTES } from '../../config'
import type { Folder, FolderChatHistoryItem, FolderJudgmentItem } from '../../types'

interface ChatTurn {
  id: number
  question: string
  answer: string
  fromHistory?: boolean
}

export function FolderChatPage() {
  const { isAuthenticated } = useAuthStore()
  const { id } = useParams<{ id: string }>()
  const folderId = Number(id)

  const [folder, setFolder] = useState<Folder | null>(null)
  const [judgmentIds, setJudgmentIds] = useState<number[]>([])
  const [turns, setTurns] = useState<ChatTurn[]>([])
  const [question, setQuestion] = useState('')
  const [loading, setLoading] = useState(false)
  const [initLoading, setInitLoading] = useState(true)
  const [error, setError] = useState('')
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!isAuthenticated || !Number.isFinite(folderId)) return
    const timer = window.setTimeout(async () => {
      try {
        const [folderData, judgmentsData, historyData] = await Promise.all([
          foldersApi.getById(folderId),
          foldersApi.listJudgments(folderId),
          foldersApi.getChatHistory(folderId),
        ])
        setFolder(folderData)
        setJudgmentIds(judgmentsData.judgments.map((j: FolderJudgmentItem) => j.judgment_id))
        setTurns(
          (historyData.history as FolderChatHistoryItem[]).map((h) => ({
            id: h.id,
            question: h.question,
            answer: h.answer,
            fromHistory: true,
          })),
        )
      } catch {
        setError('Nie udało się załadować katalogu')
      } finally {
        setInitLoading(false)
      }
    }, 0)
    return () => window.clearTimeout(timer)
  }, [isAuthenticated, folderId])

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [turns])

  if (!isAuthenticated) {
    return <Navigate to={ROUTES.LOGIN} replace />
  }

  if (!Number.isFinite(folderId)) {
    return <Navigate to={ROUTES.ORGANIZATION} replace />
  }

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault()
    const q = question.trim()
    if (!q || loading || judgmentIds.length === 0) return

    setLoading(true)
    setError('')
    setQuestion('')

    try {
      const result = await foldersApi.chat(judgmentIds, q)
      const newTurn: ChatTurn = { id: Date.now(), question: q, answer: result.answer }
      setTurns((prev) => [...prev, newTurn])
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Nie udało się uzyskać odpowiedzi')
      setQuestion(q)
    } finally {
      setLoading(false)
    }
  }

  return (
    <Layout
      content={
        <div style={{ display: 'flex', flexDirection: 'column', height: '100%', minHeight: 0 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
            <div>
              <h2 style={{ marginTop: 0, marginBottom: 4 }}>
                Czat z katalogiem: {folder?.name ?? '…'}
              </h2>
              <p style={{ margin: 0, fontSize: 13, color: 'var(--color-text-muted)' }}>
                {judgmentIds.length} orzeczeń w katalogu
              </p>
            </div>
            <Link
              to={ROUTES.FOLDER_DETAIL.replace(':id', String(folderId))}
              className="ghost-btn"
            >
              Powrót do katalogu
            </Link>
          </div>

          {initLoading && (
            <p style={{ color: 'var(--color-text-muted)' }}>Ładowanie…</p>
          )}

          {!initLoading && judgmentIds.length === 0 && (
            <div className="error-box">
              Ten katalog jest pusty. Dodaj orzeczenia, aby móc zadawać pytania.
            </div>
          )}

          {!initLoading && judgmentIds.length > 0 && (
            <>
              <div
                style={{
                  flex: 1,
                  overflowY: 'auto',
                  display: 'flex',
                  flexDirection: 'column',
                  gap: 16,
                  marginBottom: 16,
                  padding: '8px 0',
                }}
              >
                {turns.length === 0 && (
                  <p style={{ color: 'var(--color-text-muted)', fontStyle: 'italic' }}>
                    Zadaj pytanie dotyczące orzeczeń w tym katalogu.
                  </p>
                )}
                {turns.map((turn) => (
                  <div key={turn.id}>
                    <div
                      style={{
                        background: 'var(--color-surface-alt, #f5f5f5)',
                        borderRadius: 'var(--radius-md)',
                        padding: '10px 14px',
                        marginBottom: 6,
                        fontWeight: 600,
                      }}
                    >
                      {turn.question}
                    </div>
                    <div
                      style={{
                        background: 'var(--color-surface)',
                        border: '1px solid var(--color-border-light)',
                        borderRadius: 'var(--radius-md)',
                        padding: '10px 14px',
                        whiteSpace: 'pre-wrap',
                        lineHeight: 1.6,
                      }}
                    >
                      {turn.answer}
                    </div>
                  </div>
                ))}
                {loading && (
                  <p style={{ color: 'var(--color-text-muted)', fontStyle: 'italic' }}>Generuję odpowiedź…</p>
                )}
                <div ref={bottomRef} />
              </div>

              {error && <div className="error-box" style={{ marginBottom: 8 }}>{error}</div>}

              <form onSubmit={handleSubmit} style={{ display: 'flex', gap: 10 }}>
                <input
                  value={question}
                  onChange={(e) => setQuestion(e.target.value)}
                  placeholder="Zadaj pytanie dotyczące orzeczeń w katalogu…"
                  style={{ flex: 1 }}
                  disabled={loading}
                />
                <button
                  type="submit"
                  disabled={loading || !question.trim()}
                  style={{
                    background: 'var(--color-primary)',
                    color: '#fff',
                    border: 'none',
                    borderRadius: 'var(--radius-md)',
                    padding: '0 20px',
                    fontWeight: 600,
                    cursor: 'pointer',
                  }}
                >
                  {loading ? '…' : 'Wyślij'}
                </button>
              </form>
            </>
          )}
        </div>
      }
    />
  )
}
