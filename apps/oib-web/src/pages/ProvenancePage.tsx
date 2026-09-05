import { Hero } from '../components'
import { dataDictionaryUrl, dataProvenanceUrl } from '../resources'

export function ProvenancePage() {
  return <>
    <Hero title="Built for a credible synthetic-data demonstration">The prototype separates public reference structures, public-data-informed simulation assumptions, and purely synthetic Army demonstration records.</Hero>
    <section className="grid g3 section">
      <div className="card"><h3>1 • Public reference structures</h3><p>DLA PUB LOG / FLIS patterns for parts logistics; O*NET occupational and skills structures; NASA/PHM predictive-maintenance concepts; public Army OIB modernization framing.</p></div>
      <div className="card"><h3>2 • Public-informed synthetic values</h3><p>Lead-time distributions, health degradation, skill coverage, work-center capacity, defect patterns, and connectivity readiness are simulated for demonstration.</p></div>
      <div className="card"><h3>3 • Purely synthetic Army demo data</h3><p>Asset IDs, worker IDs, inventory quantities, readiness scores, failure probabilities, schedules, quality events, and all operational records are fictional.</p></div>
    </section>
    <section className="card section"><h3>Important boundary</h3><div className="callout">The prototype does not represent actual RRAD, ANAD, SIAD, WVA, Caterpillar, or other OEM performance. Production deployment would replace synthetic adapters with authorized Army/OEM data connectors and validated mission-specific models.</div><div className="actions"><a className="btn ghost" href={dataProvenanceUrl}>Read full provenance notes</a><a className="btn ghost" href={dataDictionaryUrl}>Read data dictionary</a></div></section>
  </>
}
