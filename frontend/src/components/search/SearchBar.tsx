import type { FormEvent } from 'react'

interface SearchBarProps {
  query: string
  onQueryChange: (value: string) => void
  loading: boolean
  onSubmit: (event: FormEvent) => void
  placeholder?: string
  submitLabel?: string
  showFiltersCheckbox?: boolean
  applyFiltersToAI?: boolean
  onApplyFiltersToAIChange?: (value: boolean) => void
}

export function SearchBar({
  query, onQueryChange, loading, onSubmit,
  placeholder = 'Szukaj orzeczeń, tez i podstaw prawnych...',
  submitLabel = 'Szukaj',
  showFiltersCheckbox = false,
  applyFiltersToAI = false,
  onApplyFiltersToAIChange,
}: SearchBarProps) {
  return (
    <>
      <form className="search-form" onSubmit={onSubmit}>
        <input
          value={query}
          onChange={(e) => onQueryChange(e.target.value)}
          placeholder={placeholder}
        />
        <button type="submit" disabled={loading}>
          {loading ? 'Szukam...' : submitLabel}
        </button>
      </form>
      <div className="search-tools-row" style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
        {showFiltersCheckbox ? (
          <label style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 14, cursor: 'pointer', userSelect: 'none' }}>
            <input
              type="checkbox"
              checked={applyFiltersToAI}
              onChange={(e) => onApplyFiltersToAIChange?.(e.target.checked)}
              style={{ width: 16, height: 16, cursor: 'pointer' }}
            />
            Zastosuj aktywne filtry do wyszukiwania inteligentnego (RAG)
          </label>
        ) : (
          <button type="button" className="mode-pill">
            Wyszukiwanie inteligentne
          </button>
        )}
      </div>
    </>
  )
}
