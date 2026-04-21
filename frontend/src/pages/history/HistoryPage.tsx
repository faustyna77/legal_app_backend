import { useEffect, useState } from 'react'
import { Navigate } from 'react-router-dom'
import { Layout } from '../../components/layout/Layout'
import { useAuthStore } from '../../contexts/authStore'
import { historyApi } from '../../api'
import { ROUTES } from '../../config'
import type { ChatHistoryItem, SearchHistoryItem } from '../../types'

export function HistoryPage() {
  const { isAuthenticated } = useAuthStore()
  const [searchHistory, setSearchHistory] = useState<SearchHistoryItem[]>([])
  const [chatHistory, setChatHistory] = useState<ChatHistoryItem[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const load = () => {
    setLoading(true)
    setError('')
    Promise.all([historyApi.listSearch(1, 30), historyApi.listChat(1, 30)])
      .then(([searchPayload, chatPayload]) => {
        setSearchHistory(searchPayload.history)
        setChatHistory(chatPayload.history)
      })
      .catch((e) => setError(e instanceof Error ? e.message : 'Nie udało się pobrać historii'))
      .finally(() => setLoading(false))
  }

  useEffect(() => {
    if (!isAuthenticated) return
    const timer = window.setTimeout(() => {
      load()
    }, 0)
    return () => window.clearTimeout(timer)
  }, [isAuthenticated])

  if (!isAuthenticated) {
    return <Navigate to={ROUTES.LOGIN} replace />
  }

  const removeSearch = (id: number) => {
    setLoading(true)
    setError('')
    historyApi
      .deleteSearch(id)
      .then(() => load())
      .catch((e) => setError(e instanceof Error ? e.message : 'Nie udało się usunąć wpisu'))
      .finally(() => setLoading(false))
  }

  const removeChat = (id: number) => {
    setLoading(true)
    setError('')
    historyApi
      .deleteChat(id)
      .then(() => load())
      .catch((e) => setError(e instanceof Error ? e.message : 'Nie udało się usunąć wpisu'))
      .finally(() => setLoading(false))
  }

  return (
    <Layout
      content={
        <div style={{ display: 'grid', gap: 28 }}>
          <section>
            <h2 style={{ marginTop: 0 }}>Historia wyszukiwania</h2>
            {error && <div className="error-box" style={{ marginBottom: 12 }}>{error}</div>}
            {searchHistory.length === 0 && !loading ? (
              <p style={{ color: 'var(--color-text-muted)' }}>Brak zapisanych zapytań.</p>
            ) : (
              <div className="results-list">
                {searchHistory.map((item) => (
                  <article key={item.id} className="result-card">
                    <div className="card-title-row">
                      <h3>{item.query}</h3>
                      <span style={{ fontSize: 12, color: 'var(--color-text-muted)' }}>
                        {new Date(item.created_at).toLocaleString()}
                      </span>
                    </div>
                    {item.answer && <p className="excerpt">{item.answer}</p>}
                    <button type="button" className="ghost-btn" onClick={() => removeSearch(item.id)}>
                      Usuń
                    </button>
                  </article>
                ))}
              </div>
            )}
          </section>

          <section>
            <h2 style={{ marginTop: 0 }}>Historia czatu</h2>
            {chatHistory.length === 0 && !loading ? (
              <p style={{ color: 'var(--color-text-muted)' }}>Brak zapisanych rozmów.</p>
            ) : (
              <div className="results-list">
                {chatHistory.map((item) => (
                  <article key={item.id} className="result-card">
                    <div className="card-title-row">
                      <h3>{item.case_number}</h3>
                      <span style={{ fontSize: 12, color: 'var(--color-text-muted)' }}>
                        {new Date(item.created_at).toLocaleString()}
                      </span>
                    </div>
                    <p className="meta">{item.question}</p>
                    <p className="excerpt">{item.answer}</p>
                    <button type="button" className="ghost-btn" onClick={() => removeChat(item.id)}>
                      Usuń
                    </button>
                  </article>
                ))}
              </div>
            )}
          </section>
        </div>
      }
    />
  )
}
