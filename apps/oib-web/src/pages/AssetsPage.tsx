import { useQuery } from '@tanstack/react-query'
import { api } from '../api'
import { DepotSelector, ErrorState, KpiCard, LoadingState, RiskPill, formatNumber } from '../components'
import type { DepotCode } from '../types'

export function AssetsPage({ depot, setDepot }: { depot: DepotCode; setDepot: (value: DepotCode) => void }) {
  const summaryQuery = useQuery({ queryKey: ['summary', depot], queryFn: () => api.summary(depot) })
  const rowsQuery = useQuery({ queryKey: ['assets', depot], queryFn: () => api.assets(depot) })
  if (summaryQuery.isPending || rowsQuery.isPending) return <LoadingState />
  if (summaryQuery.isError || rowsQuery.isError) {
    return <ErrorState retry={() => void Promise.all([summaryQuery.refetch(), rowsQuery.refetch()])} />
  }
  const kpis = summaryQuery.data.assets
  return (
    <>
      <DepotSelector value={depot} onChange={setDepot} />
      <section className="grid g4">
        <KpiCard label="Assets" value={formatNumber(kpis.count)} />
        <KpiCard label="Average Health" value={kpis.average_health.toFixed(1)} />
        <KpiCard label="High Risk" value={kpis.high_risk} />
        <KpiCard label="Legacy Analog" value={kpis.legacy_analog} />
      </section>
      <section className="card section">
        <h3>Highest-priority assets</h3>
        <div className="tablewrap">
          <table className="table">
            <thead><tr><th>Asset</th><th>Depot</th><th>Type</th><th>Manufacturer / Model</th><th>Health</th><th>30d Risk</th><th>Connectivity</th><th>Work Center</th></tr></thead>
            <tbody>{rowsQuery.data.items.map((row) => <tr key={row.asset_id}>
              <td><b>{row.asset_id}</b></td><td>{row.depot}</td><td>{row.asset_type}</td>
              <td>{row.manufacturer} {row.model}</td><td>{row.health_score.toFixed(1)}</td>
              <td><RiskPill value={row.failure_risk_30d} /></td>
              <td>{row.connectivity_tier}<br /><span className="muted">{row.protocol}</span></td>
              <td>{row.work_center}</td>
            </tr>)}</tbody>
          </table>
        </div>
      </section>
    </>
  )
}
