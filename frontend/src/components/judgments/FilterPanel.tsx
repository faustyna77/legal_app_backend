import type { CSSProperties } from 'react'
import type { FiltersPayload } from '../../types'
import { Spinner } from '../ui/Spinner'

interface FilterPanelProps {
  filters: FiltersPayload | null
  loading: boolean
  selectedSource: string
  onSelectSource: (v: string) => void
  selectedLegalArea: string
  onSelectLegalArea: (v: string) => void
  selectedCourt: string
  onSelectCourt: (v: string) => void
  selectedCourtType: string
  onSelectCourtType: (v: string) => void
  dateFrom: string
  onDateFromChange: (v: string) => void
  dateTo: string
  onDateToChange: (v: string) => void
  onApplyFilters: () => void
  onClearFilters: () => void
}

const selectStyle: CSSProperties = {
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

function FilterSelect({
  label, value, onChange, options, emptyLabel,
}: {
  label: string
  value: string
  onChange: (v: string) => void
  options: { value: string; count: number }[]
  emptyLabel: string
}) {
  if (!options.length) return null
  return (
    <div style={{ marginBottom: 14 }}>
      <label style={labelStyle}>{label}</label>
      <select style={selectStyle} value={value} onChange={(e) => onChange(e.target.value)}>
        <option value="">{emptyLabel}</option>
        {options.slice(0, 60).map((opt) => (
          <option key={opt.value} value={opt.value}>
            {opt.value} ({opt.count})
          </option>
        ))}
      </select>
    </div>
  )
}

export function FilterPanel({
  filters, loading,
  selectedSource, onSelectSource,
  selectedLegalArea, onSelectLegalArea,
  selectedCourt, onSelectCourt,
  selectedCourtType, onSelectCourtType,
  dateFrom, onDateFromChange,
  dateTo, onDateToChange,
  onApplyFilters,
  onClearFilters,
}: FilterPanelProps) {
  const hasActive = !!(selectedSource || selectedLegalArea || selectedCourt || selectedCourtType || dateFrom || dateTo)

  return (
    <>
      <h3 style={{ margin: '0 0 16px', fontSize: 16 }}>Filtry</h3>

      {loading && <Spinner />}

      {!loading && filters && (
        <>
          <FilterSelect
            label="Sąd"
            value={selectedCourt}
            onChange={onSelectCourt}
            options={filters.courts}
            emptyLabel="Wszystkie sądy"
          />

          <FilterSelect
            label="Typ sądu"
            value={selectedCourtType}
            onChange={onSelectCourtType}
            options={filters.court_types}
            emptyLabel="Wszystkie typy"
          />

          <FilterSelect
            label="Obszar prawa"
            value={selectedLegalArea}
            onChange={onSelectLegalArea}
            options={filters.legal_areas}
            emptyLabel="Wszystkie obszary"
          />

          <FilterSelect
            label="Źródło"
            value={selectedSource}
            onChange={onSelectSource}
            options={filters.sources}
            emptyLabel="Wszystkie źródła"
          />

          <div style={{ marginBottom: 14 }}>
            <label style={labelStyle}>Data od</label>
            <input
              type="date"
              value={dateFrom}
              onChange={(e) => onDateFromChange(e.target.value)}
              style={{ ...selectStyle, height: 38 }}
            />
          </div>

          <div style={{ marginBottom: 20 }}>
            <label style={labelStyle}>Data do</label>
            <input
              type="date"
              value={dateTo}
              onChange={(e) => onDateToChange(e.target.value)}
              style={{ ...selectStyle, height: 38 }}
            />
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            <button
              type="button"
              onClick={onApplyFilters}
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
              Filtruj
            </button>

            {hasActive && (
              <button
                type="button"
                className="ghost-btn"
                style={{ height: 36, fontSize: 13 }}
                onClick={onClearFilters}
              >
                Wyczyść
              </button>
            )}
          </div>
        </>
      )}
    </>
  )
}
