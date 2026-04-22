import { useEffect, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { useJudgmentUpdates } from '../../hooks/useJudgmentUpdates'

export function UpdatesBell() {
  const { updates, unseenCount, open, openDropdown, closeDropdown } = useJudgmentUpdates()
  const ref = useRef<HTMLDivElement>(null)
  const navigate = useNavigate()

  useEffect(() => {
    if (!open) return
    function handleClick(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) closeDropdown()
    }
    document.addEventListener('mousedown', handleClick)
    return () => document.removeEventListener('mousedown', handleClick)
  }, [open, closeDropdown])

  return (
    <div className="updates-bell-wrap" ref={ref}>
      <button
        className="updates-bell-btn"
        type="button"
        aria-label="Powiadomienia o aktualizacjach orzeczeń"
        onClick={open ? closeDropdown : openDropdown}
      >
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9" />
          <path d="M13.73 21a2 2 0 0 1-3.46 0" />
        </svg>
        {unseenCount > 0 && (
          <span className="updates-bell-badge">{unseenCount > 99 ? '99+' : unseenCount}</span>
        )}
      </button>

      {open && (
        <div className="updates-dropdown">
          <div className="updates-dropdown-header">
            <span>Nowe uzasadnienia (ostatnie 7 dni)</span>
          </div>
          {updates.length === 0 ? (
            <p className="updates-empty">Brak nowych uzasadnień.</p>
          ) : (
            <ul className="updates-list">
              {updates.map((u) => (
                <li key={u.id} className="updates-item">
                  <button
                    type="button"
                    className="updates-item-btn"
                    onClick={() => {
                      closeDropdown()
                      navigate(`/judgments/${u.id}`)
                    }}
                  >
                    <span className="updates-case">{u.case_number}</span>
                    <span className="updates-court">{u.court}</span>
                    <span className="updates-date">
                      {new Date(u.content_updated_at).toLocaleDateString('pl-PL')}
                    </span>
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
    </div>
  )
}
