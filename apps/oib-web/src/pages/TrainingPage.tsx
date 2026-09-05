import { useState } from 'react'
import { Hero, MetricLine } from '../components'
import {
  architectureUrl,
  assessmentGuideUrl,
  demoGuideUrl,
  quickStartUrl,
  userGuideMontage,
  userGuideUrl,
} from '../resources'
import type { PageId } from '../types'

const GUIDE_STEPS: Array<{ title: string; text: string; page: PageId }> = [
  { title: '1. Start with Readiness Command', text: 'Use the command page to see the integrated readiness picture across asset health, workforce capacity, supply risk, production flow, and quality.', page: 'command' },
  { title: '2. Investigate asset risk', text: 'Open Asset Reliability AI to review equipment health, failure probability, lifecycle condition, and maintenance priorities.', page: 'assets' },
  { title: '3. Check workforce capacity', text: 'Use Workforce AI to identify skill or certification gaps, training due, and areas where OpEx and cross-training can improve capacity.', page: 'workforce' },
  { title: '4. Check parts and supplier risk', text: 'Use Supply AI to identify low inventory, long lead time, source concentration, and predicted parts constraints.', page: 'supply' },
  { title: '5. Find production bottlenecks', text: 'Use Production Flow AI to compare planned and forecast output and identify work centers constraining mission throughput.', page: 'flow' },
  { title: '6. Review quality signals', text: 'Use Quality AI to examine yield, defect patterns, nonconformance signals, and recurring quality risk.', page: 'quality' },
  { title: '7. Assess real-data readiness', text: 'Use the OIB Data Readiness & Connectivity Assessment during a depot walk-through. Score connectivity, protocol, data rights, cyber status, history, and data quality.', page: 'connect' },
  { title: '8. Confirm data provenance', text: 'Use Data Provenance to explain what is public-source-informed, what is synthetic, and what would be replaced by authorized Army or OEM data in production.', page: 'provenance' },
]

export function TrainingPage({ openPage }: { openPage: (page: PageId) => void }) {
  const [index, setIndex] = useState(0)
  const step = GUIDE_STEPS[index]
  return <>
    <Hero title="User Guide & Help Center">No audio or video required. Learn the system through an interactive guided tour, task-based quick starts, and downloadable reference material.</Hero>
    <section className="grid g2 section">
      <div className="card"><h3>Interactive guided tour</h3><div className="callout"><h3 className="guide-title">{step.title}</h3><p className="guide-text">{step.text}</p></div><div className="actions"><button className="btn ghost" type="button" disabled={index === 0} onClick={() => setIndex((value) => value - 1)}>Previous</button><button className="btn primary" type="button" disabled={index === GUIDE_STEPS.length - 1} onClick={() => setIndex((value) => value + 1)}>Next</button><button className="btn gold" type="button" onClick={() => openPage(step.page)}>Open this module</button></div><div className="guide-count">Step {index + 1} of {GUIDE_STEPS.length}</div></div>
      <div className="card"><h3>Quick-start paths</h3><MetricLine label="Command / leadership view" value="Readiness Command → drivers → actions" /><MetricLine label="Depot walk-through" value="Data Readiness Assessment → score → export" /><MetricLine label="Maintenance planning" value="Asset Reliability → Supply → Workforce" /><MetricLine label="Throughput improvement" value="Production Flow → Workforce → Quality" /><div className="callout card-callout"><b>Recommended first demo:</b> start on Readiness Command, investigate one red/amber driver, then show how the Data Readiness Assessment determines whether real equipment can be connected.</div></div>
    </section>
    <section className="grid g2 section">
      <div className="card"><h3>Downloadable guides</h3>
        <MetricLine label="PowerPoint User Guide" value={<a href={userGuideUrl}>Open / download</a>} />
        <MetricLine label="Quick Start Guide" value={<a href={quickStartUrl} target="_blank" rel="noreferrer">Open / print</a>} />
        <MetricLine label="Demo Guide" value={<a href={demoGuideUrl} target="_blank" rel="noreferrer">Open</a>} />
        <MetricLine label="Connectivity Assessment Guide" value={<a href={assessmentGuideUrl} target="_blank" rel="noreferrer">Open</a>} />
        <MetricLine label="Architecture" value={<a href={architectureUrl} target="_blank" rel="noreferrer">Open</a>} />
      </div>
      <div className="card"><h3>Slide-based visual reference</h3><p className="muted body-copy">Use the PowerPoint for instructor-led training or as a leave-behind. The montage below gives users a quick visual index.</p><img className="slide-preview" src={userGuideMontage} alt="User guide slide montage" /></div>
    </section>
  </>
}
