import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { type CSSProperties, type FormEvent, useState } from 'react'
import { ApiError, api } from '../api'
import { assessmentsCsv, downloadText } from '../assessment'
import { useAuthorizedDepots, useAuthorizedScope } from '../authorization'
import { ErrorState, GradePill, Hero, KpiCard, LoadingState } from '../components'
import type { ConnectivityAssessment, Page, SubmittedAssessmentInput } from '../types'

export function AssessmentPage({ showToast }: { showToast: (message: string) => void }) {
  const allowedDepots = useAuthorizedDepots()
  const scope = useAuthorizedScope()
  const summaryQuery = useQuery({ queryKey: ['summary', scope], queryFn: () => api.summary(scope) })
  const seedQuery = useQuery({ queryKey: ['assessments', scope], queryFn: () => api.assessments(scope) })
  const submittedQuery = useQuery({ queryKey: ['submitted-assessments', scope], queryFn: () => api.submittedAssessments(scope) })
  const queryClient = useQueryClient()
  const [result, setResult] = useState<ConnectivityAssessment | null>(null)
  const saveMutation = useMutation({
    mutationFn: ({ assessment, idempotencyKey }: { assessment: SubmittedAssessmentInput; idempotencyKey: string }) =>
      api.createAssessment(assessment, idempotencyKey),
    retry: (failureCount, error) => error instanceof ApiError && error.status >= 500 && failureCount < 2,
    onSuccess: (record) => {
      setResult(record)
      queryClient.setQueryData<Page<ConnectivityAssessment>>(['submitted-assessments', scope], (current) => ({
        items: [record, ...(current?.items ?? [])].slice(0, 80),
        page: 1,
        size: 80,
        total: (current?.total ?? 0) + 1,
        pages: Math.max(1, Math.ceil(((current?.total ?? 0) + 1) / 80)),
      }))
      showToast('Assessment saved')
    },
    onError: () => showToast('Assessment could not be saved'),
  })
  if (summaryQuery.isPending || seedQuery.isPending || submittedQuery.isPending) return <LoadingState />
  if (summaryQuery.isError || seedQuery.isError || submittedQuery.isError) {
    return <ErrorState retry={() => void Promise.all([summaryQuery.refetch(), seedQuery.refetch(), submittedQuery.refetch()])} />
  }
  const submitted = submittedQuery.data.items
  const all = [...submitted, ...seedQuery.data.items].slice(0, 80)
  const submittedCounts = { Green: 0, Yellow: 0, Red: 0 }
  submitted.forEach((record) => { submittedCounts[record.readiness_grade] += 1 })
  const base = summaryQuery.data.assessment

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const form = event.currentTarget
    const values = Object.fromEntries(new FormData(form).entries())
    const record: SubmittedAssessmentInput = {
      asset_id: String(values.asset_id), depot: String(values.depot), asset_type: String(values.asset_type),
      manufacturer: String(values.manufacturer), connectivity: String(values.connectivity), protocol: String(values.protocol),
      data_rights: String(values.data_rights), cyber_status: String(values.cyber_status), history: String(values.history),
      data_quality: String(values.data_quality), notes: String(values.notes),
    }
    saveMutation.mutate({ assessment: record, idempotencyKey: crypto.randomUUID() })
  }

  function exportCsv() {
    if (!submitted.length) return showToast('No assessments to export')
    downloadText('oib_connectivity_assessments.csv', assessmentsCsv(submitted), 'text/csv')
  }

  return <>
    <Hero title="OIB Data Readiness & Connectivity Assessment">Use this during a depot walk-through to determine whether equipment is ready for direct AI integration, requires an adapter/cyber action, or needs retrofit/OEM engagement.</Hero>
    <section className="grid g3 section">
      <KpiCard label="Green / Pilot Ready" value={base.green + submittedCounts.Green} />
      <KpiCard label="Yellow / Resolve Gaps" value={base.yellow + submittedCounts.Yellow} />
      <KpiCard label="Red / Retrofit or OEM" value={base.red + submittedCounts.Red} />
    </section>
    <section className="grid g2 section">
      <div className="card"><h3>Assess an asset</h3><form onSubmit={submit}><div className="formgrid">
        <div className="field"><label htmlFor="asset-id">Asset ID</label><input id="asset-id" required name="asset_id" placeholder="e.g., CNC-014" /></div>
        <div className="field"><label htmlFor="assessment-depot">Depot</label><select id="assessment-depot" name="depot">{['RRAD', 'ANAD', 'SIAD', 'WVA', 'Other'].filter((code) => allowedDepots.includes(code)).map((code) => <option key={code}>{code}</option>)}</select></div>
        <div className="field"><label htmlFor="asset-type">Asset Type</label><input id="asset-type" required name="asset_type" placeholder="CNC, crane, engine…" /></div>
        <div className="field"><label htmlFor="manufacturer">Manufacturer</label><input id="manufacturer" name="manufacturer" placeholder="Manufacturer" /></div>
        <SelectField label="Connectivity" name="connectivity" options={['Native Digital', 'Vendor Digital', 'Legacy Analog']} />
        <SelectField label="Protocol / Interface" name="protocol" options={['MTConnect', 'OPC UA', 'REST API', 'OEM Cloud API', 'Modbus', 'Serial/PLC', 'None']} />
        <SelectField label="Government Data Rights" name="data_rights" options={['Government usable', 'Limited license', 'Contract unclear', 'No access']} />
        <SelectField label="Cyber Status" name="cyber_status" options={['Approved', 'Isolated', 'Unknown', 'Not assessed']} />
        <SelectField label="Historical Data" name="history" options={['>24 months', '6-24 months', '<6 months', 'None']} />
        <SelectField label="Data Quality" name="data_quality" options={['Good', 'Mixed', 'Poor']} />
        <div className="field field-wide"><label htmlFor="notes">Notes</label><textarea id="notes" name="notes" placeholder="Controller, sensor, licensing, network, cybersecurity, or retrofit observations" /></div>
      </div><div className="actions"><button className="btn primary" type="submit" disabled={saveMutation.isPending}>Score &amp; Save Assessment</button><button className="btn ghost" type="button" onClick={exportCsv}>Export CSV</button><button className="btn ghost" type="button" onClick={() => downloadText('oib_connectivity_assessments.json', JSON.stringify(submitted, null, 2), 'application/json')}>Export JSON</button></div></form></div>
      <div className="card"><h3>Assessment logic</h3>{result ? <div className="scorebox"><div className="scorecircle" style={{ '--score': result.readiness_score } as CSSProperties}><strong>{result.readiness_score}</strong></div><div><h3 className="score-title"><GradePill grade={result.readiness_grade} /> Data Readiness</h3><p><b>Recommended action:</b> {result.recommended_action}</p><p className="assessment-disclaimer">This score is a prototype screening aid, not an authority-to-connect determination.</p></div></div> : <div className="empty">Complete the form to calculate readiness.</div>}<div className="callout"><b>Integration tiers:</b><br />Green = direct connector + pilot<br />Yellow = resolve access/cyber + adapter<br />Red = retrofit sensors, OEM engagement, and/or data-rights plan</div></div>
    </section>
    <section className="card section"><h3>Recent assessments</h3><div className="tablewrap"><table className="table"><thead><tr><th>Asset</th><th>Depot</th><th>Type</th><th>Connectivity</th><th>Protocol</th><th>Rights</th><th>Score</th><th>Grade</th><th>Action</th></tr></thead><tbody>{all.map((row, index) => <tr key={`${row.asset_id}-${row.assessed_at ?? row.observed_at ?? index}`}><td>{row.asset_id}</td><td>{row.depot}</td><td>{row.asset_type}</td><td>{row.connectivity}</td><td>{row.protocol}</td><td>{row.data_rights}</td><td>{row.readiness_score}</td><td><GradePill grade={row.readiness_grade} /></td><td>{row.recommended_action}</td></tr>)}</tbody></table></div></section>
  </>
}

function SelectField({ label, name, options }: { label: string; name: string; options: string[] }) {
  const id = `field-${name}`
  return <div className="field"><label htmlFor={id}>{label}</label><select id={id} name={name}>{options.map((option) => <option key={option}>{option}</option>)}</select></div>
}
