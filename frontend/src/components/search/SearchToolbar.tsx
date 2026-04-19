import { useState } from 'react'
import type { FormEvent } from 'react'

interface SearchToolbarProps {
  onSearch: (query: string) => void
  applyFilters: boolean
  onApplyFiltersChange: (value: boolean) => void
  isLoading: boolean
}

export function SearchToolbar({
  onSearch,
  applyFilters,
  onApplyFiltersChange,
  isLoading,
}: SearchToolbarProps) {
  const [query, setQuery] = useState('')

  const handleSubmit = (event: FormEvent) => {
    event.preventDefault()
    if (!query.trim()) return
    onSearch(query.trim())
  }

  return (
    <>
      <form className="search-form" onSubmit={handleSubmit}>
        <input
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          placeholder="Wpisz pytanie prawne..."
        />
        <button type="submit" disabled={isLoading}>
          {isLoading ? 'Szukam...' : 'Szukaj AI'}
        </button>
      </form>
      <div className="search-tools-row">
        <label style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 14, cursor: 'pointer', userSelect: 'none' }}>
          <input
            type="checkbox"
            checked={applyFilters}
            onChange={(event) => onApplyFiltersChange(event.target.checked)}
            style={{ width: 16, height: 16, cursor: 'pointer' }}
          />
          Zastosuj aktywne filtry do wyszukiwania AI
        </label>
      </div>
    </>
  )
}
