import { describe, expect, it } from 'vitest'
import { assessmentsCsv } from './assessment'

describe('connectivity assessment rules', () => {
  it('neutralizes spreadsheet formulas in CSV exports', () => {
    const csv = assessmentsCsv([{
      asset_id: '=HYPERLINK("https://example.test")',
      depot: 'RRAD',
      asset_type: 'CNC',
      manufacturer: 'Example',
      connectivity: 'Native Digital',
      protocol: 'MTConnect',
      data_rights: 'Government usable',
      cyber_status: 'Approved',
      history: '>24 months',
      data_quality: 'Good',
      readiness_score: 100,
      readiness_grade: 'Green',
      recommended_action: 'Direct connector + pilot',
    }])
    expect(csv).toContain("'=")
    expect(csv).not.toContain('"=HYPERLINK')
  })
})
