import { NavLink } from 'react-router-dom'
import { ROUTES } from '../../config'
import { useAuthStore } from '../../contexts/authStore'

export function Navbar() {
  const { isAuthenticated, clearAuth } = useAuthStore()

  return (
    <header className="topbar">
      <div className="brand-wrap">
        <div className="brand-mark" />
        <span className="brand-text">LexSearch Taxenbach </span>
      </div>

      <nav className="topnav">
        <NavLink to={ROUTES.SEARCH}>Orzecznictwo</NavLink>
        <NavLink to={ROUTES.JUDGMENTS}>Asystent AI</NavLink>
        <NavLink to={ROUTES.ADMIN}>Raporty</NavLink>
      </nav>

      <div className="topbar-actions">
        {isAuthenticated ? (
          <button className="ghost-btn" type="button" onClick={clearAuth}>
            Wyloguj
          </button>
        ) : (
          <>
            <button className="ghost-btn" type="button">Organizacja</button>
            <NavLink to={ROUTES.LOGIN} className="dark-btn">Konto</NavLink>
          </>
        )}
      </div>
    </header>
  )
}
