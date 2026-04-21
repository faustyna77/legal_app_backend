import { useEffect, useState } from 'react'
import type { FormEvent } from 'react'
import { Navigate } from 'react-router-dom'
import { Layout } from '../../components/layout/Layout'
import { useAuthStore } from '../../contexts/authStore'
import { foldersApi } from '../../api'
import { ROUTES } from '../../config'
import type { Folder } from '../../types'

export function FoldersPage() {
  const { isAuthenticated } = useAuthStore()
  const [folders, setFolders] = useState<Folder[]>([])
  const [name, setName] = useState('')
  const [description, setDescription] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const loadFolders = () => {
    setLoading(true)
    setError('')
    foldersApi
      .list()
      .then((payload) => setFolders(payload.folders))
      .catch((e) => setError(e instanceof Error ? e.message : 'Nie udało się pobrać katalogów'))
      .finally(() => setLoading(false))
  }

  useEffect(() => {
    if (!isAuthenticated) return
    const timer = window.setTimeout(() => {
      loadFolders()
    }, 0)
    return () => window.clearTimeout(timer)
  }, [isAuthenticated])

  if (!isAuthenticated) {
    return <Navigate to={ROUTES.LOGIN} replace />
  }

  const handleCreate = (e: FormEvent) => {
    e.preventDefault()
    if (!name.trim()) return
    setLoading(true)
    setError('')
    foldersApi
      .create({ name: name.trim(), description: description.trim() || undefined })
      .then(() => {
        setName('')
        setDescription('')
        loadFolders()
      })
      .catch((e) => setError(e instanceof Error ? e.message : 'Nie udało się utworzyć katalogu'))
      .finally(() => setLoading(false))
  }

  return (
    <Layout
      content={
        <div>
          <h2 style={{ marginTop: 0 }}>Moje katalogi orzeczeń</h2>
          <form onSubmit={handleCreate} style={{ display: 'grid', gap: 12, marginBottom: 24, maxWidth: 560 }}>
            <input
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Nazwa katalogu"
              required
            />
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Opis (opcjonalnie)"
              rows={3}
              style={{ padding: 10, border: '1px solid var(--color-border)', borderRadius: 'var(--radius-md)' }}
            />
            <button type="submit" disabled={loading} style={{ width: 'fit-content' }}>
              {loading ? 'Tworzenie...' : 'Utwórz katalog'}
            </button>
          </form>

          {error && <div className="error-box" style={{ marginBottom: 12 }}>{error}</div>}

          {folders.length === 0 && !loading ? (
            <p style={{ color: 'var(--color-text-muted)' }}>Brak katalogów. Utwórz pierwszy katalog powyżej.</p>
          ) : (
            <div className="results-list">
              {folders.map((folder) => (
                <article key={folder.id} className="result-card">
                  <div className="card-title-row">
                    <h3>{folder.name}</h3>
                    <span style={{ fontSize: 13, color: 'var(--color-text-muted)' }}>
                      {folder.judgment_count ?? 0} orzeczeń
                    </span>
                  </div>
                  {folder.description && <p className="excerpt">{folder.description}</p>}
                </article>
              ))}
            </div>
          )}
        </div>
      }
    />
  )
}
