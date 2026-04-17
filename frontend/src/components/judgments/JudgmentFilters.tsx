import type { FiltersPayload } from '../../types'
import { Spinner } from '../ui/Spinner'

interface JudgmentFiltersProps {
  filters: FiltersPayload | null
  loading: boolean
  selectedSource: string
  onSelectSource: (v: string) => void
  selectedYear: string
  onSelectYear: (v: string) => void
  selectedLegalArea: string
  onSelectLegalArea: (v: string) => void
  selectedCity: string
  onSelectCity: (v: string) => void
  selectedCourt: string
  onSelectCourt: (v: string) => void
  selectedCourtType: string
  onSelectCourtType: (v: string) => void
  onApplyFilters: () => void
  onClearFilters: () => void
}

function FilterGroup({
  label,
  options,
  selected,
  onSelect,
  limit = 8,
}: {
  label: string
  options: { value: string; count: number }[]
  selected: string
  onSelect: (v: string) => void
  limit?: number
}) {
  if (!options.length) return null
  return (
    <div className="filter-group">
      <label>{label}</label>
      <div className="option-list">
        {options.slice(0, limit).map((opt) => (
          <button
            key={opt.value}
            type="button"
            className={`filter-pill${selected === String(opt.value) ? ' selected' : ''}`}
            onClick={() => onSelect(selected === String(opt.value) ? '' : String(opt.value))}
          >
            {opt.value} ({opt.count})
          </button>
        ))}
      </div>
    </div>
  )
}

export function JudgmentFilters({
  filters, loading,
  selectedSource, onSelectSource,
  selectedYear, onSelectYear,
  selectedLegalArea, onSelectLegalArea,
  selectedCity, onSelectCity,
  selectedCourt, onSelectCourt,
  selectedCourtType, onSelectCourtType,
  onApplyFilters,
  onClearFilters,
}: JudgmentFiltersProps) {
  const hasActiveFilter = !!(
    selectedSource || selectedYear || selectedLegalArea ||
    selectedCity || selectedCourt || selectedCourtType
  )

  return (
    <>
      <h3>Filtry</h3>
      {loading && <Spinner />}

      {!loading && filters && (
        <>
          <FilterGroup label="Źródło"        options={filters.sources}     selected={selectedSource}    onSelect={onSelectSource} />
          <FilterGroup label="Typ sądu"      options={filters.court_types} selected={selectedCourtType} onSelect={onSelectCourtType} limit={6} />
          <FilterGroup label="Sąd"           options={filters.courts}      selected={selectedCourt}     onSelect={onSelectCourt} limit={10} />
          <FilterGroup label="Rok"           options={filters.years.map((y) => ({ value: String(y.value), count: y.count }))} selected={selectedYear} onSelect={onSelectYear} limit={10} />
          <FilterGroup label="Obszar prawa"  options={filters.legal_areas} selected={selectedLegalArea} onSelect={onSelectLegalArea} />
          <FilterGroup label="Miasto"        options={filters.cities}      selected={selectedCity}      onSelect={onSelectCity} limit={10} />
          <FilterGroup label="Prawomocność"  options={filters.finality}    selected=""                  onSelect={() => {}} />

          <div style={{ marginTop: 20, display: 'flex', flexDirection: 'column', gap: 8 }}>
            <button
              type="button"
              onClick={onApplyFilters}
              style={{
                background: 'var(--color-primary)',
                color: '#fff',
                border: 'none',
                borderRadius: 'var(--radius-md)',
                height: 40,
                fontWeight: 600,
                fontSize: 14,
                cursor: 'pointer',
              }}
            >
              Zastosuj filtry
            </button>

            {hasActiveFilter && (
              <button
                type="button"
                className="ghost-btn"
                style={{ height: 36, fontSize: 13 }}
                onClick={onClearFilters}
              >
                Wyczyść filtry
              </button>
            )}
          </div>
        </>
      )}
    </>
  )
}
