import { useMemo, useState } from 'react'
import type { FiltersPayload } from '../../types'
import { Spinner } from '../ui/Spinner'

interface JudgmentFiltersProps {
  filters: FiltersPayload | null
  loading: boolean
  totalCount?: number
  selectedSource: string[]
  onSelectSource: (v: string[]) => void
  selectedYear: string
  onSelectYear: (v: string) => void
  selectedLegalArea: string[]
  onSelectLegalArea: (v: string[]) => void
  selectedCity: string[]
  onSelectCity: (v: string[]) => void
  selectedCourt: string[]
  onSelectCourt: (v: string[]) => void
  selectedCourtType: string[]
  onSelectCourtType: (v: string[]) => void
  selectedDateFrom: string
  onSelectDateFrom: (v: string) => void
  selectedDateTo: string
  onSelectDateTo: (v: string) => void
  selectedArticle: string
  onSelectArticle: (v: string) => void
  selectedActTitle: string
  onSelectActTitle: (v: string) => void
  onApplyFilters: () => void
  onClearFilters: () => void
}

function OptionSection({
  title,
  options,
  selected,
  onSelect,
  defaultOpen = false,
  limit = 10,
}: {
  title: string
  options: { value: string; count: number }[]
  selected: string[]
  onSelect: (v: string[]) => void
  defaultOpen?: boolean
  limit?: number
}) {
  if (!options.length) return null

  return (
    <details open={defaultOpen} style={{ borderBottom: '1px solid var(--color-border-light)', padding: '8px 0' }}>
      <summary style={{ cursor: 'pointer', fontWeight: 700, fontSize: 18, listStyle: 'none', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <span>{title}</span>
      </summary>
      <div style={{ maxHeight: 220, overflow: 'auto', marginTop: 8, display: 'flex', flexDirection: 'column', gap: 8 }}>
        {options.slice(0, limit).map((opt) => (
          <label key={opt.value} style={{ display: 'flex', alignItems: 'center', gap: 10, cursor: 'pointer' }}>
            <input
              type="checkbox"
              checked={selected.includes(String(opt.value))}
              onChange={() => {
                const value = String(opt.value)
                onSelect(
                  selected.includes(value)
                    ? selected.filter((v) => v !== value)
                    : [...selected, value],
                )
              }}
            />
            <span style={{ flex: 1 }}>{opt.value}</span>
            <span style={{ color: 'var(--color-text-muted)' }}>{opt.count.toLocaleString('pl-PL')}</span>
          </label>
        ))}
      </div>
    </details>
  )
}

function OptionSectionSingle({
  title,
  options,
  selected,
  onSelect,
  limit = 10,
}: {
  title: string
  options: { value: string; count: number }[]
  selected: string
  onSelect: (v: string) => void
  limit?: number
}) {
  if (!options.length) return null

  return (
    <details style={{ borderBottom: '1px solid var(--color-border-light)', padding: '8px 0' }}>
      <summary style={{ cursor: 'pointer', fontWeight: 700, fontSize: 18, listStyle: 'none', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <span>{title}</span>
      </summary>
      <div style={{ maxHeight: 220, overflow: 'auto', marginTop: 8, display: 'flex', flexDirection: 'column', gap: 8 }}>
        {options.slice(0, limit).map((opt) => (
          <label key={opt.value} style={{ display: 'flex', alignItems: 'center', gap: 10, cursor: 'pointer' }}>
            <input
              type="checkbox"
              checked={selected === String(opt.value)}
              onChange={() => onSelect(selected === String(opt.value) ? '' : String(opt.value))}
            />
            <span style={{ flex: 1 }}>{opt.value}</span>
            <span style={{ color: 'var(--color-text-muted)' }}>{opt.count.toLocaleString('pl-PL')}</span>
          </label>
        ))}
      </div>
    </details>
  )
}

export function JudgmentFilters({
  filters,
  loading,
  totalCount,
  selectedSource,
  onSelectSource,
  selectedYear,
  onSelectYear,
  selectedLegalArea,
  onSelectLegalArea,
  selectedCity,
  onSelectCity,
  selectedCourt,
  onSelectCourt,
  selectedCourtType,
  onSelectCourtType,
  selectedDateFrom,
  onSelectDateFrom,
  selectedDateTo,
  onSelectDateTo,
  selectedArticle,
  onSelectArticle,
  selectedActTitle,
  onSelectActTitle,
  onApplyFilters,
  onClearFilters,
}: JudgmentFiltersProps) {
  const [openDates, setOpenDates] = useState(true)
  const hasActiveFilter = !!(
    selectedSource.length ||
    selectedYear ||
    selectedLegalArea.length ||
    selectedCity.length ||
    selectedCourt.length ||
    selectedCourtType.length ||
    selectedDateFrom ||
    selectedDateTo ||
    selectedArticle ||
    selectedActTitle
  )

  const countLabel = useMemo(() => {
    if (typeof totalCount !== 'number') return null
    return `${totalCount.toLocaleString('pl-PL')} orzeczeń`
  }, [totalCount])

  return (
    <>
      <h3 style={{ margin: 0, fontSize: 30, fontWeight: 700 }}>Filtry</h3>
      {countLabel && <p style={{ margin: '10px 0 14px', fontSize: 20, fontWeight: 600 }}>{countLabel}</p>}

      {loading && <Spinner />}

      {!loading && filters && (
        <div style={{ display: 'grid', gap: 2 }}>
          <div style={{ marginBottom: 12, display: 'flex', flexDirection: 'column', gap: 8 }}>
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

          <details open={openDates} onToggle={(e) => setOpenDates((e.currentTarget as HTMLDetailsElement).open)} style={{ borderTop: '1px solid var(--color-border-light)', borderBottom: '1px solid var(--color-border-light)', padding: '10px 0' }}>
            <summary style={{ cursor: 'pointer', fontWeight: 700, fontSize: 18, listStyle: 'none' }}>Okres</summary>
            <div style={{ display: 'grid', gap: 10, marginTop: 10 }}>
              <label style={{ fontSize: 13, display: 'grid', gap: 6 }}>
                Data od
                <input type="date" value={selectedDateFrom} onChange={(e) => onSelectDateFrom(e.target.value)} style={{ width: '100%', height: 36, border: '1px solid var(--color-border)', borderRadius: 8, padding: '0 10px' }} />
              </label>
              <label style={{ fontSize: 13, display: 'grid', gap: 6 }}>
                Data do
                <input type="date" value={selectedDateTo} onChange={(e) => onSelectDateTo(e.target.value)} style={{ width: '100%', height: 36, border: '1px solid var(--color-border)', borderRadius: 8, padding: '0 10px' }} />
              </label>
            </div>
          </details>

          <OptionSection title="Źródło" options={filters.sources} selected={selectedSource} onSelect={onSelectSource} />
          <OptionSection title="Obszar prawa" options={filters.legal_areas} selected={selectedLegalArea} onSelect={onSelectLegalArea} defaultOpen />
          <OptionSection title="Typ sądu" options={filters.court_types} selected={selectedCourtType} onSelect={onSelectCourtType} />
          <OptionSection title="Sąd" options={filters.courts} selected={selectedCourt} onSelect={onSelectCourt} />
          <OptionSection title="Miasto" options={filters.cities} selected={selectedCity} onSelect={onSelectCity} />
          <OptionSectionSingle title="Rok" options={filters.years.map((y) => ({ value: String(y.value), count: y.count }))} selected={selectedYear} onSelect={onSelectYear} />

          <details style={{ borderBottom: '1px solid var(--color-border-light)', padding: '10px 0' }}>
            <summary style={{ cursor: 'pointer', fontWeight: 700, fontSize: 18, listStyle: 'none' }}>Artykuł</summary>
            <div style={{ display: 'grid', gap: 10, marginTop: 10 }}>
              <label style={{ fontSize: 13, display: 'grid', gap: 6 }}>
                Szukaj po artykule
                <input type="text" placeholder="np. art. 75c" value={selectedArticle} onChange={(e) => onSelectArticle(e.target.value)} style={{ width: '100%', height: 36, border: '1px solid var(--color-border)', borderRadius: 8, padding: '0 10px' }} />
              </label>
            </div>
          </details>

          <details style={{ borderBottom: '1px solid var(--color-border-light)', padding: '10px 0' }}>
            <summary style={{ cursor: 'pointer', fontWeight: 700, fontSize: 18, listStyle: 'none' }}>Ustawa</summary>
            <div style={{ display: 'grid', gap: 10, marginTop: 10 }}>
              <label style={{ fontSize: 13, display: 'grid', gap: 6 }}>
                Tytuł aktu
                <input type="text" placeholder="np. Prawo bankowe" value={selectedActTitle} onChange={(e) => onSelectActTitle(e.target.value)} style={{ width: '100%', height: 36, border: '1px solid var(--color-border)', borderRadius: 8, padding: '0 10px' }} />
              </label>
            </div>
          </details>

        </div>
      )}
    </>
  )
}
