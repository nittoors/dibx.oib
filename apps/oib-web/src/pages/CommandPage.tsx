import { useQuery } from '@tanstack/react-query'
import { api } from '../api'
import { useAuthorizedScope } from '../authorization'
import {
  DepotSelector,
  DriverBar,
  ErrorState,
  Hero,
  KpiCard,
  LoadingState,
  MetricLine,
  ReadinessChart,
  formatNumber,
} from '../components'
import type { DepotCode } from '../types'

export function CommandPage({ depot, setDepot }: { depot: DepotCode; setDepot: (value: DepotCode) => void }) {
  const authorizedScope = useAuthorizedScope()
  const summaryQuery = useQuery({ queryKey: ['summary', depot], queryFn: () => api.summary(depot) })
  const globalQuery = useQuery({ queryKey: ['summary', authorizedScope], queryFn: () => api.summary(authorizedScope) })
  const trendQuery = useQuery({ queryKey: ['trend', depot], queryFn: () => api.trend(depot) })

  if (summaryQuery.isPending || globalQuery.isPending || trendQuery.isPending) return <LoadingState />
  if (summaryQuery.isError || globalQuery.isError || trendQuery.isError) {
    return <ErrorState retry={() => void Promise.all([summaryQuery.refetch(), globalQuery.refetch(), trendQuery.refetch()])} />
  }

  const summary = summaryQuery.data
  const global = globalQuery.data
  return (
    <>
      <DepotSelector value={depot} onChange={setDepot} />
      <Hero title="Mission readiness before the constraint becomes a crisis.">
        One operational view connecting asset health, workforce capacity, parts risk, production flow,
        quality, and data connectivity. All values in this prototype are synthetic.
      </Hero>
      <section className="grid g4 section">
        <KpiCard label="Composite Readiness" value={summary.command.composite_readiness.toFixed(1)} sub="0–100 synthetic score" />
        <KpiCard label="Assets at Elevated Risk" value={summary.command.assets_elevated} sub="30-day failure risk ≥50" />
        <KpiCard label="Workforce Capacity Gap" value={formatNumber(summary.command.workforce_gap)} sub="Synthetic worker equivalents" />
        <KpiCard label="Critical Supply Risks" value={formatNumber(summary.command.critical_supply)} sub="Parts with risk ≥70" />
      </section>
      <section className="grid g2 section">
        <div className="card">
          <h3>Readiness Trend</h3>
          <ReadinessChart rows={trendQuery.data} />
        </div>
        <div className="card">
          <h3>Why readiness is at risk</h3>
          {summary.drivers.map((driver) => (
            <DriverBar key={driver.name} label={driver.name} value={driver.value} gold suffix="" />
          ))}
          <div className="callout command-callout">
            <b>AI command recommendation:</b> prioritize the top two constraints, then re-run the readiness
            outlook to measure recovery impact.
          </div>
        </div>
      </section>
      <section className="grid g3 section">
        <div className="card">
          <h3>Production</h3>
          <MetricLine label="Plan attainment" value={`${summary.flow.plan_attainment.toFixed(1)}%`} />
          <MetricLine label="Open quality NCRs" value={formatNumber(summary.quality.open_ncr)} />
          <MetricLine label="Bottleneck work centers" value={summary.flow.bottlenecks} />
        </div>
        <div className="card">
          <h3>AI Actions</h3>
          <MetricLine label="Inspect high-risk assets" value={summary.assets.high_risk} />
          <MetricLine label="Close critical skill gaps" value={summary.workforce.skill_families_at_risk} />
          <MetricLine label="Expedite / source parts" value={summary.supply.critical_risks} />
        </div>
        <div className="card">
          <h3>Data Readiness</h3>
          <MetricLine label="Green" value={global.assessment.green} />
          <MetricLine label="Yellow" value={global.assessment.yellow} />
          <MetricLine label="Red" value={global.assessment.red} />
        </div>
      </section>
    </>
  )
}
