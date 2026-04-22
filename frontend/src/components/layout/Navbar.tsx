import { NavLink } from 'react-router-dom'
import { ROUTES } from '../../config'
import { useAuthStore } from '../../contexts/authStore'
import { useAuth } from '../../hooks/useAuth'
import { UpdatesBell } from './UpdatesBell'

export function Navbar() {
  const { isAuthenticated } = useAuthStore()
  const { logout } = useAuth()

  return (
    <header className="topbar">
      <div className="brand-wrap">
        <div className="brand-mark" />
        <span className="brand-text">LexSearch Taxenbach </span>
      </div>

      <nav className="topnav">
        <NavLink to={ROUTES.SEARCH}>Orzecznictwo</NavLink>
        <NavLink to={ROUTES.JUDGMENTS}>Asystent AI</NavLink>
        <NavLink to={ROUTES.ORGANIZATION}>Organizacja</NavLink>
      </nav>

      <div className="topbar-actions">
        <UpdatesBell />
        {isAuthenticated ? (
          <button className="ghost-btn" type="button" onClick={() => void logout()}>
            Wyloguj
          </button>
        ) : (
          <NavLink to={ROUTES.LOGIN} className="dark-btn">Konto</NavLink>
        )}
      </div>
    </header>
  )
}
