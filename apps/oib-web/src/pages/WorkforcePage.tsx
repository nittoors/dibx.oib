import { useQuery } from '@tanstack/react-query'
import { api } from '../api'
import { DepotSelector, DriverBar, ErrorState, KpiCard, LoadingState, MetricLine, formatNumber } from '../components'
import type { DepotCode } from '../types'

export function WorkforcePage({ depot, setDepot }: { depot: DepotCode; setDepot: (value: DepotCode) => void }) {
  const summaryQuery = useQuery({ queryKey: ['summary', depot], queryFn: () => api.summary(depot) })
  const rowsQuery = useQuery({ queryKey: ['workforce', depot], queryFn: () => api.workforce(depot) })
  if (summaryQuery.isPending || rowsQuery.isPending) return <LoadingState />
  if (summaryQuery.isError || rowsQuery.isError) {
    return <ErrorState retry={() => void Promise.all([summaryQuery.refetch(), rowsQuery.refetch()])} />
  }
  const kpis = summaryQuery.data.workforce
  const rows = rowsQuery.data.items
  return (
    <>
      <DepotSelector value={depot} onChange={setDepot} />
      <section className="grid g4">
        <KpiCard label="Synthetic Workforce" value={formatNumber(kpis.count)} />
        <KpiCard label="Avg Availability" value={`${kpis.average_availability.toFixed(1)}%`} />
        <KpiCard label="Skill Families at Risk" value={kpis.skill_families_at_risk} />
        <KpiCard label="Training Due" value={kpis.training_due} />
      </section>
      <section className="grid g2 section">
        <div className="card"><h3>Capacity by occupation</h3>{rows.slice(0, 12).map((row) => (
          <DriverBar key={`${row.depot}-${row.occupation_code}`} label={row.occupation} value={row.coverage_pct} />
        ))}</div>
        <div className="card"><h3>OpEx + AI workforce actions</h3>
          <MetricLine label="Cross-train constrained roles" value={`${rows.filter((row) => row.coverage_pct < 85).length} skill families`} />
          <MetricLine label="Prioritize expiring training" value={`${kpis.training_due} workers`} />
          <MetricLine label="Rebalance shifts" value="Model by workload / certification" />
          <div className="callout card-callout"><b>OpEx layer:</b> map actual work, eliminate avoidable handoffs, standardize skill demand and certification logic, then use AI for forecasting and surge decisions.</div>
        </div>
      </section>
      <section className="card section"><h3>Lowest coverage skill families</h3><div className="tablewrap"><table className="table">
        <thead><tr><th>Depot</th><th>Occupation</th><th>Assigned</th><th>Available</th><th>Required</th><th>Gap</th><th>Coverage</th></tr></thead>
        <tbody>{rows.map((row) => <tr key={`${row.depot}-${row.occupation_code}`}><td>{row.depot}</td><td>{row.occupation}</td><td>{row.assigned_workers}</td><td>{row.available_workers}</td><td>{row.required_workers}</td><td>{row.capacity_gap}</td><td><span className={`pill ${row.coverage_pct < 80 ? 'red' : 'green'}`}>{row.coverage_pct}%</span></td></tr>)}</tbody>
      </table></div></section>
    </>
  )
}
