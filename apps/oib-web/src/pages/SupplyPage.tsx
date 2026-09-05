import { useQuery } from '@tanstack/react-query'
import { api } from '../api'
import { useAuthorizedScope } from '../authorization'
import { ErrorState, KpiCard, LoadingState, RiskPill, formatNumber } from '../components'

export function SupplyPage() {
  const authorizedScope = useAuthorizedScope()
  const summaryQuery = useQuery({ queryKey: ['summary', authorizedScope], queryFn: () => api.summary(authorizedScope) })
  const rowsQuery = useQuery({ queryKey: ['parts'], queryFn: api.parts })
  if (summaryQuery.isPending || rowsQuery.isPending) return <LoadingState />
  if (summaryQuery.isError || rowsQuery.isError) {
    return <ErrorState retry={() => void Promise.all([summaryQuery.refetch(), rowsQuery.refetch()])} />
  }
  const kpis = summaryQuery.data.supply
  return <>
    <section className="grid g4">
      <KpiCard label="Parts Modeled" value={formatNumber(kpis.parts)} />
      <KpiCard label="Critical Risks" value={kpis.critical_risks} />
      <KpiCard label="Single-source Items" value={kpis.single_source} />
      <KpiCard label="Avg Lead Time" value={`${kpis.average_lead_time_days}d`} />
    </section>
    <section className="card section"><h3>Parts likely to constrain readiness</h3><div className="tablewrap"><table className="table">
      <thead><tr><th>Part</th><th>FSC</th><th>Description</th><th>Sources</th><th>Lead</th><th>On Hand</th><th>60d Demand</th><th>Risk</th><th>AI Action</th></tr></thead>
      <tbody>{rowsQuery.data.items.map((row) => <tr key={row.part_id}><td><b>{row.part_id}</b></td><td>{row.fsc}</td><td>{row.part_name}</td><td>{row.source_count}</td><td>{row.lead_time_days}d</td><td>{row.on_hand}</td><td>{row.projected_60d_demand}</td><td><RiskPill value={row.supply_risk} /></td><td>{row.recommended_action}</td></tr>)}</tbody>
    </table></div></section>
  </>
}
