import type { CSSProperties } from 'react'
import type { Filters } from '../../hooks/useJudgmentsSearch'
import type { FiltersPayload } from '../../types'

interface FiltersSidebarProps {
  filters: Filters
  options: FiltersPayload | null
  optionsLoading: boolean
  onFiltersChange: (filters: Filters) => void
  onFilter: () => void
  onClear: () => void
  isLoading: boolean
}

const controlStyle: CSSProperties = {
  width: '100%',
  height: 38,
  border: '1px solid var(--color-border-light)',
  borderRadius: 'var(--radius-sm)',
  padding: '0 8px',
  fontSize: 14,
  fontFamily: 'inherit',
  background: 'var(--color-surface)',
  color: 'var(--color-text)',
}

const labelStyle: CSSProperties = {
  display: 'block',
  fontSize: 12,
  fontWeight: 600,
  color: 'var(--color-text-muted)',
  marginBottom: 4,
  textTransform: 'uppercase',
  letterSpacing: '0.04em',
}

export function FiltersSidebar({
  filters,
  options,
  optionsLoading,
  onFiltersChange,
  onFilter,
  onClear,
  isLoading,
}: FiltersSidebarProps) {
  const hasActive = !!(
    filters.court ||
    filters.court_type ||
    filters.legal_area ||
    filters.source ||
    filters.date_from ||
    filters.date_to
  )

  return (
    <>
      <h3 style={{ margin: '0 0 16px', fontSize: 16 }}>Filtry</h3>

      <div style={{ marginBottom: 14 }}>
        <label style={labelStyle}>Sąd</label>
        <input
          type="text"
          value={filters.court ?? ''}
          onChange={(event) => onFiltersChange({ ...filters, court: event.target.value })}
          style={controlStyle}
          placeholder="Np. Sąd Najwyższy"
        />
      </div>

      <div style={{ marginBottom: 14 }}>
        <label style={labelStyle}>Typ sądu</label>
        <select
          style={controlStyle}
          value={filters.court_type ?? ''}
          onChange={(event) => onFiltersChange({ ...filters, court_type: event.target.value })}
          disabled={optionsLoading}
        >
          <option value="">Wszystkie typy</option>
          {(options?.court_types ?? []).map((opt) => (
            <option key={opt.value} value={opt.value}>{opt.value}</option>
          ))}
        </select>
      </div>

      <div style={{ marginBottom: 14 }}>
        <label style={labelStyle}>Obszar prawa</label>
        <select
          style={controlStyle}
          value={filters.legal_area ?? ''}
          onChange={(event) => onFiltersChange({ ...filters, legal_area: event.target.value })}
          disabled={optionsLoading}
        >
          <option value="">Wszystkie obszary</option>
          {(options?.legal_areas ?? []).map((opt) => (
            <option key={opt.value} value={opt.value}>{opt.value}</option>
          ))}
        </select>
      </div>

      <div style={{ marginBottom: 14 }}>
        <label style={labelStyle}>Źródło</label>
        <select
          style={controlStyle}
          value={filters.source ?? ''}
          onChange={(event) => onFiltersChange({ ...filters, source: event.target.value })}
          disabled={optionsLoading}
        >
          <option value="">Wszystkie źródła</option>
          {(options?.sources ?? []).map((opt) => (
            <option key={opt.value} value={opt.value}>{opt.value}</option>
          ))}
        </select>
      </div>

      <div style={{ marginBottom: 14 }}>
        <label style={labelStyle}>Data od</label>
        <input
          type="date"
          value={filters.date_from ?? ''}
          onChange={(event) => onFiltersChange({ ...filters, date_from: event.target.value })}
          style={controlStyle}
        />
      </div>

      <div style={{ marginBottom: 20 }}>
        <label style={labelStyle}>Data do</label>
        <input
          type="date"
          value={filters.date_to ?? ''}
          onChange={(event) => onFiltersChange({ ...filters, date_to: event.target.value })}
          style={controlStyle}
        />
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
        <button
          type="button"
          onClick={onFilter}
          disabled={isLoading}
          style={{
            background: '#2563eb',
            color: '#fff',
            border: 'none',
            borderRadius: 'var(--radius-md)',
            height: 40,
            fontWeight: 600,
            fontSize: 14,
            cursor: 'pointer',
          }}
        >
          {isLoading ? 'Filtrowanie...' : 'Filtruj'}
        </button>

        {hasActive && (
          <button
            type="button"
            className="ghost-btn"
            style={{ height: 36, fontSize: 13 }}
            onClick={onClear}
            disabled={isLoading}
          >
            Wyczyść
          </button>
        )}
      </div>
    </>
  )
}
