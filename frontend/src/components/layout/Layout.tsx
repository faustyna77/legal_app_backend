import type { ReactNode } from 'react'
import { Navbar } from './Navbar'

interface LayoutProps {
  toolbar?: ReactNode
  sidebar?: ReactNode
  content: ReactNode
  details?: ReactNode
}

export function Layout({ toolbar, sidebar, content, details }: LayoutProps) {
  const cols = sidebar && details ? '280px 1fr 420px'
    : sidebar               ? '280px 1fr'
    : details               ? '1fr 420px'
    : '1fr'

  const dataCols = sidebar && details ? '3' : sidebar || details ? '2' : '1'

  return (
    <div className="app-shell">
      <Navbar />
      {toolbar && <section className="search-zone">{toolbar}</section>}
      <main className="layout" style={{ gridTemplateColumns: cols }} data-cols={dataCols}>
        {sidebar && <aside className="filters-panel">{sidebar}</aside>}
        <section className="results-panel">{content}</section>
        {details && <section className="details-panel">{details}</section>}
      </main>
    </div>
  )
}
