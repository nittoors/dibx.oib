import { useQuery } from '@tanstack/react-query'
import { api } from '../api'
import { DepotSelector, DriverBar, ErrorState, KpiCard, LoadingState } from '../components'
import type { DepotCode } from '../types'

export function FlowPage({ depot, setDepot }: { depot: DepotCode; setDepot: (value: DepotCode) => void }) {
  const summaryQuery = useQuery({ queryKey: ['summary', depot], queryFn: () => api.summary(depot) })
  const rowsQuery = useQuery({ queryKey: ['flow', depot], queryFn: () => api.flow(depot) })
  if (summaryQuery.isPending || rowsQuery.isPending) return <LoadingState />
  if (summaryQuery.isError || rowsQuery.isError) {
    return <ErrorState retry={() => void Promise.all([summaryQuery.refetch(), rowsQuery.refetch()])} />
  }
  const kpis = summaryQuery.data.flow
  const rows = rowsQuery.data.items
  return <>
    <DepotSelector value={depot} onChange={setDepot} />
    <section className="grid g4">
      <KpiCard label="Plan Attainment" value={`${kpis.plan_attainment.toFixed(1)}%`} />
      <KpiCard label="Bottlenecks" value={kpis.bottlenecks} />
      <KpiCard label="Queue Hours" value={kpis.queue_hours.toFixed(0)} />
      <KpiCard label="Downtime Hours" value={kpis.downtime_hours.toFixed(0)} />
    </section>
    <section className="card section"><h3>Work-center flow</h3>{rows.map((row) => (
      <DriverBar key={`${row.depot}-${row.work_center}`} label={`${row.depot} • ${row.work_center}`} value={row.plan_attainment_pct} gold={row.plan_attainment_pct < 85} />
    ))}</section>
    <section className="card section"><h3>Constraint detail</h3><div className="tablewrap"><table className="table">
      <thead><tr><th>Depot</th><th>Center</th><th>Plan</th><th>Forecast</th><th>Attainment</th><th>Queue</th><th>Downtime</th><th>Labor Gap</th><th>Constraint</th></tr></thead>
      <tbody>{rows.map((row) => <tr key={`${row.depot}-${row.work_center}`}><td>{row.depot}</td><td>{row.work_center}</td><td>{row.weekly_plan}</td><td>{row.forecast_output}</td><td>{row.plan_attainment_pct}%</td><td>{row.queue_hours}h</td><td>{row.downtime_hours}h</td><td>{row.labor_gap_pct}%</td><td>{row.constraint_driver === 'None' ? <span className="pill green">Stable</span> : <span className="pill amber">{row.constraint_driver}</span>}</td></tr>)}</tbody>
    </table></div></section>
  </>
}
