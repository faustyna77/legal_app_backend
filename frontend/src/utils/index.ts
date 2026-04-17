export function formatDate(dateStr: string | undefined): string {
  if (!dateStr) return '—'
  return String(dateStr).slice(0, 10)
}

export function truncate(text: string | undefined, length = 280): string {
  if (!text) return 'Brak treści'
  return text.length > length ? `${text.slice(0, length)}…` : text
}

export function formatSimilarity(value: number | undefined): string {
  if (value === undefined) return ''
  return `${(value * 100).toFixed(1)}%`
}
