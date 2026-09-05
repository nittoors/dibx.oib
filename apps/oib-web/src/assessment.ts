import type { ConnectivityAssessment } from './types'

function csvCell(value: unknown): string {
  let safeValue = String(value ?? '')
  if (/^[\t\r ]*[=+\-@]/.test(safeValue)) safeValue = `'${safeValue}`
  return `"${safeValue.replaceAll('"', '""')}"`
}

export function assessmentsCsv(records: ConnectivityAssessment[]): string {
  if (!records.length) return ''
  const headers = Object.keys(records[0]) as Array<keyof ConnectivityAssessment>
  return [
    headers.map(csvCell).join(','),
    ...records.map((record) => headers.map((header) => csvCell(record[header])).join(',')),
  ].join('\n')
}

export function downloadText(name: string, text: string, type: string): void {
  const anchor = document.createElement('a')
  anchor.href = URL.createObjectURL(new Blob([text], { type }))
  anchor.download = name
  anchor.click()
  window.setTimeout(() => URL.revokeObjectURL(anchor.href), 500)
}
