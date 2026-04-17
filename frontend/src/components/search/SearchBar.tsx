import type { FormEvent } from 'react'

interface SearchBarProps {
  query: string
  onQueryChange: (value: string) => void
  loading: boolean
  onSubmit: (event: FormEvent) => void
}

export function SearchBar({ query, onQueryChange, loading, onSubmit }: SearchBarProps) {
  return (
    <>
      <form className="search-form" onSubmit={onSubmit}>
        <input
          value={query}
          onChange={(e) => onQueryChange(e.target.value)}
          placeholder="Szukaj orzeczeń, tez i podstaw prawnych..."
        />
        <button type="submit" disabled={loading}>
          {loading ? 'Szukam...' : 'Szukaj'}
        </button>
      </form>
      <div className="search-tools-row">
        <button type="button" className="mode-pill">
          Wyszukiwanie inteligentne
        </button>
      </div>
    </>
  )
}
