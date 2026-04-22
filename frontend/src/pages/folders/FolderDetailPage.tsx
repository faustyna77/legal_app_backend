import { useEffect, useState } from 'react'
import { Link, Navigate, useNavigate, useParams } from 'react-router-dom'
import { Layout } from '../../components/layout/Layout'
import { useAuthStore } from '../../contexts/authStore'
import { foldersApi } from '../../api'
import { ROUTES } from '../../config'
import type { Folder, FolderJudgmentItem } from '../../types'

export function FolderDetailPage() {
  const { isAuthenticated } = useAuthStore()
  const { id } = useParams<{ id: string }>()
  const folderId = Number(id)
  const navigate = useNavigate()

  const [folder, setFolder] = useState<Folder | null>(null)
  const [items, setItems] = useState<FolderJudgmentItem[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const loadFolder = () => {
    if (!Number.isFinite(folderId)) return
    foldersApi.getById(folderId).then(setFolder).catch(() => {})
  }

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
      loadFolder()
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
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
            <div>
              <h2 style={{ marginTop: 0, marginBottom: 4 }}>{folder?.name ?? 'Katalog'}</h2>
              {folder?.description && (
                <p style={{ margin: 0, color: 'var(--color-text-muted)', fontSize: 14 }}>{folder.description}</p>
              )}
            </div>
            <div style={{ display: 'flex', gap: 8 }}>
              {items.length > 0 && (
                <button
                  type="button"
                  onClick={() => navigate(ROUTES.FOLDER_CHAT.replace(':id', String(folderId)))}
                  style={{
                    background: 'var(--color-primary)',
                    color: '#fff',
                    border: 'none',
                    borderRadius: 'var(--radius-md)',
                    padding: '8px 16px',
                    fontWeight: 600,
                    fontSize: 14,
                    cursor: 'pointer',
                  }}
                >
                  Czat z katalogiem
                </button>
              )}
              <Link to={ROUTES.ORGANIZATION} className="ghost-btn">Powrót do katalogów</Link>
            </div>
          </div>

          {error && <div className="error-box" style={{ marginBottom: 12 }}>{error}</div>}

          {items.length === 0 && !loading ? (
            <p style={{ color: 'var(--color-text-muted)' }}>
              Ten katalog nie ma jeszcze orzeczeń. Dodaj orzeczenia w{' '}
              <Link to={ROUTES.SEARCH}>wyszukiwarce</Link>.
            </p>
          ) : (
            <div className="results-list">
              {items.map((item) => (
                <article key={item.judgment_id} className="result-card">
                  <div className="card-title-row">
                    <h3>
                      <Link to={`/judgments/${item.judgment_id}`} style={{ color: 'inherit' }}>
                        {item.case_number}
                      </Link>
                    </h3>
                    <span style={{ fontSize: 13, color: 'var(--color-text-muted)' }}>{item.court ?? '—'}</span>
                  </div>
                  <p className="meta">Data: {item.date ?? '—'}</p>
                  {item.note && <p className="excerpt">{item.note}</p>}
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
