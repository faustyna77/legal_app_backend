import { useState } from 'react'
import type { FormEvent } from 'react'
import { Link } from 'react-router-dom'
import { ROUTES } from '../../config'

export function RegisterPage() {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [info, setInfo] = useState('')

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault()
    setInfo('Rejestracja wkrótce dostępna. Użyj konta testowego: admin@test.pl / password')
    void email; void password
  }

  return (
    <div style={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', background: 'var(--color-bg)' }}>
      <div style={{ background: 'var(--color-surface)', border: '1px solid var(--color-border)', borderRadius: 'var(--radius-lg)', padding: '32px', width: '100%', maxWidth: '400px' }}>
        <div className="brand-wrap" style={{ marginBottom: 24 }}>
          <div className="brand-mark" />
          <span className="brand-text">Lexedit</span>
        </div>

        <h2 style={{ margin: '0 0 20px' }}>Zarejestruj się</h2>

        {info && <div className="answer-box" style={{ marginBottom: 12, fontSize: 14 }}>{info}</div>}

        <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          <input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="E-mail"
            required
          />
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="Hasło"
            required
          />
          <button type="submit">Zarejestruj się</button>
        </form>

        <p style={{ marginTop: 16, textAlign: 'center', fontSize: 14, color: 'var(--color-text-muted)' }}>
          Masz już konto? <Link to={ROUTES.LOGIN}>Zaloguj się</Link>
        </p>
      </div>
    </div>
  )
}
