import { useQuery } from '@tanstack/react-query'
import { api } from '../api'
import { DepotSelector, ErrorState, KpiCard, LoadingState, formatNumber } from '../components'
import type { DepotCode } from '../types'

export function QualityPage({ depot, setDepot }: { depot: DepotCode; setDepot: (value: DepotCode) => void }) {
  const summaryQuery = useQuery({ queryKey: ['summary', depot], queryFn: () => api.summary(depot) })
  const rowsQuery = useQuery({ queryKey: ['quality', depot], queryFn: () => api.quality(depot) })
  if (summaryQuery.isPending || rowsQuery.isPending) return <LoadingState />
  if (summaryQuery.isError || rowsQuery.isError) {
    return <ErrorState retry={() => void Promise.all([summaryQuery.refetch(), rowsQuery.refetch()])} />
  }
  const kpis = summaryQuery.data.quality
  return <>
    <DepotSelector value={depot} onChange={setDepot} />
    <section className="grid g4">
      <KpiCard label="Inspections" value={formatNumber(kpis.inspections)} />
      <KpiCard label="Avg Defect Rate" value={`${kpis.average_defect_rate.toFixed(1)}%`} />
      <KpiCard label="First Pass Yield" value={`${kpis.first_pass_yield.toFixed(1)}%`} />
      <KpiCard label="Open NCR" value={formatNumber(kpis.open_ncr)} />
    </section>
    <section className="card section"><h3>Quality risk by work center</h3><div className="tablewrap"><table className="table">
      <thead><tr><th>Depot</th><th>Center</th><th>Inspections</th><th>Defect Rate</th><th>FPY</th><th>Open NCR</th><th>Repeat NCR</th><th>Top Defect</th><th>AI Focus</th></tr></thead>
      <tbody>{rowsQuery.data.items.map((row) => <tr key={`${row.depot}-${row.work_center}`}><td>{row.depot}</td><td>{row.work_center}</td><td>{row.inspections}</td><td>{row.defect_rate_pct > 7 ? <span className="pill red">{row.defect_rate_pct}%</span> : `${row.defect_rate_pct}%`}</td><td>{row.first_pass_yield_pct}%</td><td>{row.open_ncr}</td><td>{row.repeat_ncr}</td><td>{row.top_defect}</td><td>{row.ai_focus}</td></tr>)}</tbody>
    </table></div></section>
  </>
}
