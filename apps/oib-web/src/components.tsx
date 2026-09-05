import type { ReactNode } from 'react'
import { useAuthorizedDepots } from './authorization'
import type { DepotCode, ReadinessGrade, ReadinessTrend } from './types'

export function DepotSelector({
  value,
  onChange,
}: {
  value: DepotCode
  onChange: (depot: DepotCode) => void
}) {
  const allowedDepots = useAuthorizedDepots()
  const allOperational = ['RRAD', 'ANAD', 'SIAD', 'WVA'].every((code) => allowedDepots.includes(code))
  return (
    <div className="toolbar">
      <label htmlFor="depot-select">Depot</label>
      <select
        id="depot-select"
        value={value}
        onChange={(event) => onChange(event.target.value as DepotCode)}
      >
        {allOperational ? <option value="ALL">All OIB Demo Sites</option> : null}
        {(['RRAD', 'ANAD', 'SIAD', 'WVA'] as const).filter((code) => allowedDepots.includes(code)).map((code) => <option key={code} value={code}>{code}</option>)}
      </select>
    </div>
  )
}

export function Hero({ children, title }: { children: ReactNode; title: string }) {
  return (
    <section className="hero">
      <h3>{title}</h3>
      <p>{children}</p>
    </section>
  )
}

export function KpiCard({ label, value, sub }: { label: string; value: ReactNode; sub?: string }) {
  return (
    <div className="card kpi">
      <div className="label">{label}</div>
      <div className="val">{value}</div>
      {sub ? <div className="sub">{sub}</div> : null}
    </div>
  )
}

export function RiskPill({ value }: { value: number }) {
  const className = value >= 70 ? 'red' : value >= 50 ? 'amber' : 'green'
  const label = value >= 70 ? 'HIGH' : value >= 50 ? 'WATCH' : 'LOW'
  return <span className={`pill ${className}`}>{`${label} ${value.toFixed(0)}`}</span>
}

export function GradePill({ grade }: { grade: ReadinessGrade }) {
  const className = grade === 'Green' ? 'green' : grade === 'Yellow' ? 'amber' : 'red'
  return <span className={`pill ${className}`}>{grade}</span>
}

export function DriverBar({
  label,
  value,
  gold = false,
  suffix = '%',
}: {
  label: string
  value: number
  gold?: boolean
  suffix?: string
}) {
  return (
    <div className="driver">
      <b>{label}</b>
      <div className={`bar${gold ? ' gold' : ''}`}>
        <span style={{ width: `${Math.min(100, value)}%` }} />
      </div>
      <span>{value.toFixed(0)}{suffix}</span>
    </div>
  )
}

export function ReadinessChart({ rows }: { rows: ReadinessTrend[] }) {
  const values = rows.map((row) => row.readiness)
  const width = 650
  const height = 180
  const padding = 24
  const minimum = Math.min(...values, 40) - 3
  const maximum = Math.max(...values, 80) + 3
  const range = maximum - minimum || 1
  const x = (index: number) =>
    padding + (index * (width - 2 * padding)) / Math.max(1, values.length - 1)
  const y = (value: number) => height - padding - ((value - minimum) * (height - 2 * padding)) / range
  const points = values.map((value, index) => `${x(index)},${y(value)}`).join(' ')

  return (
    <svg className="mini-chart" viewBox={`0 0 ${width} ${height}`} role="img" aria-label="Readiness trend">
      <line x1={padding} y1={height - padding} x2={width - padding} y2={height - padding} stroke="#d8ddd2" />
      <polyline fill="none" stroke="#4b5320" strokeWidth="4" points={points} />
      {values.map((value, index) => (
        <g key={`${rows[index].reporting_period}-${rows[index].month}`}>
          <circle cx={x(index)} cy={y(value)} r="5" fill="#d4a72c" />
          <text x={x(index)} y={height - 5} textAnchor="middle" fontSize="11" fill="#667064">
            {rows[index].month}
          </text>
        </g>
      ))}
    </svg>
  )
}

export function LoadingState() {
  return <div className="card empty">Loading prototype…</div>
}

export function ErrorState({ retry }: { retry: () => void }) {
  return (
    <div className="card error-state" role="alert">
      <h3>Prototype data could not load</h3>
      <p>The local API is unavailable or has not been seeded.</p>
      <button className="btn primary" type="button" onClick={retry}>Try again</button>
    </div>
  )
}

export function MetricLine({ label, value }: { label: ReactNode; value: ReactNode }) {
  return (
    <div className="metricline">
      <b>{label}</b>
      <span>{value}</span>
    </div>
  )
}

export function formatNumber(value: number): string {
  return value.toLocaleString()
}
