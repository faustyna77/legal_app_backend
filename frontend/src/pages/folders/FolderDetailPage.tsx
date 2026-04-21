import { useEffect, useState } from 'react'
import { Link, Navigate, useParams } from 'react-router-dom'
import { Layout } from '../../components/layout/Layout'
import { useAuthStore } from '../../contexts/authStore'
import { foldersApi } from '../../api'
import { ROUTES } from '../../config'
import type { FolderJudgmentItem } from '../../types'

export function FolderDetailPage() {
  const { isAuthenticated } = useAuthStore()
  const { id } = useParams<{ id: string }>()
  const folderId = Number(id)
  const [items, setItems] = useState<FolderJudgmentItem[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const loadItems = () => {
    if (!Number.isFinite(folderId)) return
    setLoading(true)
    setError('')
    foldersApi
      .listJudgments(folderId)
      .then((payload) => setItems(payload.judgments))
      .catch((e) => setError(e instanceof Error ? e.message : 'Nie udało się pobrać orzeczeń'))
      .finally(() => setLoading(false))
  }

  useEffect(() => {
    if (!isAuthenticated || !Number.isFinite(folderId)) return
    const timer = window.setTimeout(() => {
      loadItems()
    }, 0)
    return () => window.clearTimeout(timer)
  }, [isAuthenticated, folderId])

  if (!isAuthenticated) {
    return <Navigate to={ROUTES.LOGIN} replace />
  }

  if (!Number.isFinite(folderId)) {
    return <Navigate to={ROUTES.ORGANIZATION} replace />
  }

  const handleRemove = (judgmentId: number) => {
    setLoading(true)
    setError('')
    foldersApi
      .removeJudgment(folderId, judgmentId)
      .then(() => loadItems())
      .catch((e) => setError(e instanceof Error ? e.message : 'Nie udało się usunąć orzeczenia'))
      .finally(() => setLoading(false))
  }

  return (
    <Layout
      content={
        <div>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <h2 style={{ marginTop: 0 }}>Orzeczenia w katalogu</h2>
            <Link to={ROUTES.ORGANIZATION} className="ghost-btn">Powrót do katalogów</Link>
          </div>

          {error && <div className="error-box" style={{ marginBottom: 12 }}>{error}</div>}

          {items.length === 0 && !loading ? (
            <p style={{ color: 'var(--color-text-muted)' }}>Ten katalog nie ma jeszcze orzeczeń.</p>
          ) : (
            <div className="results-list">
              {items.map((item) => (
                <article key={item.judgment_id} className="result-card">
                  <div className="card-title-row">
                    <h3>{item.case_number}</h3>
                    <span style={{ fontSize: 13, color: 'var(--color-text-muted)' }}>{item.court ?? '—'}</span>
                  </div>
                  <p className="meta">Data: {item.date ?? '—'}</p>
                  <div style={{ marginTop: 8 }}>
                    <button type="button" className="ghost-btn" onClick={() => handleRemove(item.judgment_id)}>
                      Usuń z katalogu
                    </button>
                  </div>
                </article>
              ))}
            </div>
          )}
        </div>
      }
    />
  )
}
