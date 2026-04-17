import { Layout } from '../../components/layout/Layout'

export function JudgmentListPage() {
  return (
    <Layout
      content={
        <div>
          <h2>Lista orzeczeń</h2>
          <p style={{ color: 'var(--color-text-muted)' }}>Wkrótce dostępna pełna lista orzeczeń z paginacją.</p>
        </div>
      }
    />
  )
}
