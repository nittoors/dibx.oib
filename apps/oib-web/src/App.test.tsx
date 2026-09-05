import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { cleanup, render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import App from './App'

const summary = {
  depot: 'ALL',
  command: {
    composite_readiness: 53.6,
    assets_elevated: 179,
    workforce_gap: 716,
    critical_supply: 170,
    plan_attainment: 88.3,
    open_ncr: 133,
    bottlenecks: 13,
  },
  assets: { count: 1600, average_health: 70.7, high_risk: 10, legacy_analog: 426 },
  workforce: {
    count: 2600,
    average_availability: 87.7,
    skill_families_at_risk: 27,
    training_due: 0,
  },
  flow: { plan_attainment: 88.3, bottlenecks: 13, queue_hours: 312.5, downtime_hours: 368.5 },
  quality: { inspections: 8935, average_defect_rate: 5.3, first_pass_yield: 92.7, open_ncr: 133 },
  supply: { parts: 1200, critical_risks: 170, single_source: 212, average_lead_time_days: 32, scope: 'GLOBAL' },
  assessment: { green: 64, yellow: 252, red: 84, ruleset: 'prototype-v1' },
  drivers: [
    { name: 'Workforce Capacity', value: 100 },
    { name: 'Supply Chain', value: 51 },
    { name: 'Asset Availability', value: 42 },
    { name: 'Production Flow', value: 12 },
    { name: 'Quality/Rework', value: 9 },
  ],
  observed_at: '2026-08-28T00:00:00Z',
  source_system: 'synthetic',
}

const pages: Record<string, unknown> = {
  '/assets': {
    items: [{ asset_id: 'CNC-014', depot: 'RRAD', asset_type: 'CNC', manufacturer: 'Example', model: 'M1', age_years: 12, criticality: 'High', connectivity_tier: 'Native Digital', protocol: 'MTConnect', health_score: 67.5, failure_risk_30d: 74, work_center: 'Machining', operating_hours: 4000, observed_at: '2026-08-28T00:00:00Z' }],
  },
  '/workforce/capacity': {
    items: [{ depot: 'RRAD', occupation_code: '51-4041', occupation: 'Machinists', assigned_workers: 12, available_workers: 9, required_workers: 14, capacity_gap: 5, training_due: 2, coverage_pct: 64, observed_at: '2026-08-28T00:00:00Z' }],
  },
  '/parts': {
    items: [{ part_id: 'P-001', fsc: '5305', part_name: 'Fastener', source_count: 1, lead_time_days: 90, on_hand: 2, projected_60d_demand: 12, criticality: 'High', supply_risk: 80, recommended_action: 'Expedite', scope: 'GLOBAL', observed_at: '2026-08-28T00:00:00Z' }],
  },
  '/production-flow': {
    items: [{ depot: 'RRAD', work_center: 'Machining', weekly_plan: 100, forecast_output: 81, plan_attainment_pct: 81, queue_hours: 24, downtime_hours: 10, labor_gap_pct: 8, constraint_driver: 'Labor', observed_at: '2026-08-28T00:00:00Z' }],
  },
  '/quality': {
    items: [{ depot: 'RRAD', work_center: 'Machining', inspections: 40, defect_rate_pct: 8, first_pass_yield_pct: 92, open_ncr: 3, repeat_ncr: 1, top_defect: 'Tolerance', ai_focus: 'Inspect tooling', observed_at: '2026-08-28T00:00:00Z' }],
  },
  '/connectivity-assessments': {
    items: [{ asset_id: 'SEED-001', depot: 'ANAD', asset_type: 'Crane', manufacturer: 'Example', connectivity: 'Legacy Analog', protocol: 'None', data_rights: 'No access', cyber_status: 'Not assessed', history: 'None', data_quality: 'Poor', readiness_score: 10, readiness_grade: 'Red', recommended_action: 'Retrofit/OEM engagement + data plan', observed_at: '2026-08-28T00:00:00Z' }],
  },
}

let activeSession = {
  subject: 'local-reviewer',
  roles: ['OIB-Admins'],
  allowed_depots: ['ANAD', 'Other', 'RRAD', 'SIAD', 'WVA'],
  authentication_mode: 'development',
}

function jsonResponse(value: unknown, status = 200): Response {
  return new Response(JSON.stringify(value), {
    status,
    headers: { 'Content-Type': 'application/json' },
  })
}

function successfulFetch(input: RequestInfo | URL, init?: RequestInit): Promise<Response> {
  const url = new URL(String(input), 'http://localhost')
  if (url.pathname.endsWith('/session')) {
    return Promise.resolve(jsonResponse(activeSession))
  }
  if (url.pathname.endsWith('/connectivity-assessments/submitted')) {
    return Promise.resolve(jsonResponse({ items: [], page: 1, size: 80, total: 0, pages: 0 }))
  }
  if (url.pathname.endsWith('/connectivity-assessments') && init?.method === 'POST') {
    const request = JSON.parse(String(init.body)) as Record<string, unknown>
    return Promise.resolve(jsonResponse({
      id: '70b3f84c-ea09-4aee-9896-048753bad6c2',
      ...request,
      readiness_score: 100,
      readiness_grade: 'Green',
      recommended_action: 'Direct connector + pilot',
      dimension_points: { connectivity: 28, protocol: 18, data_rights: 18, cyber_status: 16, history: 10, data_quality: 10 },
      ruleset: 'prototype-v1',
      assessed_at: '2026-09-04T10:00:00Z',
    }, 201))
  }
  if (url.pathname.endsWith('/readiness/summary')) {
    const depot = url.searchParams.get('depot') ?? 'ALL'
    return Promise.resolve(jsonResponse({
      ...summary,
      depot,
      command: {
        ...summary.command,
        composite_readiness: depot === 'RRAD' ? 51.3 : summary.command.composite_readiness,
      },
    }))
  }
  if (url.pathname.endsWith('/readiness/trend')) {
    return Promise.resolve(jsonResponse([
      { reporting_period: '2026-03-01', month: 'Mar', readiness: 49.1 },
      { reporting_period: '2026-04-01', month: 'Apr', readiness: 53.6 },
    ]))
  }
  const pageEntry = Object.entries(pages).find(([path]) => url.pathname.endsWith(path))
  if (pageEntry) {
    const body = pageEntry[1] as { items: unknown[] }
    return Promise.resolve(jsonResponse({ ...body, page: 1, size: 100, total: body.items.length, pages: 1 }))
  }
  return Promise.resolve(jsonResponse({ detail: 'Not found' }, 404))
}

function renderApp() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false, gcTime: Infinity } },
  })
  return render(
    <QueryClientProvider client={queryClient}>
      <App />
    </QueryClientProvider>,
  )
}

beforeEach(() => {
  activeSession = {
    subject: 'local-reviewer',
    roles: ['OIB-Admins'],
    allowed_depots: ['ANAD', 'Other', 'RRAD', 'SIAD', 'WVA'],
    authentication_mode: 'development',
  }
  vi.stubGlobal('fetch', vi.fn(successfulFetch))
})

afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
})

describe('Depot Readiness React UI', () => {
  it('preserves the command screen, navigation order, and approved baseline data', async () => {
    renderApp()

    expect(await screen.findByRole('heading', { name: 'Mission readiness before the constraint becomes a crisis.' })).toBeInTheDocument()
    expect(screen.getByText('53.6')).toBeInTheDocument()
    expect(screen.getByText('716')).toBeInTheDocument()
    expect(screen.getByText('Prototype v5.1 • Army + Red Cedar Theme • Port 8899')).toBeInTheDocument()
    const navigation = screen.getByRole('navigation', { name: 'Primary navigation' })
    expect(within(navigation).getAllByRole('button').map((button) => button.textContent)).toEqual([
      '◈Readiness Command',
      '⚙Asset Reliability AI',
      '♟Workforce AI',
      '▣Supply AI',
      '⇄Production Flow AI',
      '✓Quality AI',
      '⌁Data Readiness Assessment',
      '?User Guide + Help',
      'iData Provenance',
    ])
  })

  it('retains the selected depot while moving between operational modules', async () => {
    const user = userEvent.setup()
    renderApp()
    const selector = await screen.findByRole('combobox', { name: 'Depot' })
    await user.selectOptions(selector, 'RRAD')
    expect(await screen.findByText('51.3')).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: /Asset Reliability AI/ }))
    expect(await screen.findByRole('heading', { name: 'Highest-priority assets' })).toBeInTheDocument()
    expect(screen.getByRole('combobox', { name: 'Depot' })).toHaveValue('RRAD')
    expect(screen.getByText('CNC-014')).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: /Production Flow AI/ }))
    expect(await screen.findByRole('heading', { name: 'Work-center flow' })).toBeInTheDocument()
    expect(screen.getByRole('combobox', { name: 'Depot' })).toHaveValue('RRAD')
  })

  it('keeps every legacy module reachable from the same navigation flow', async () => {
    const user = userEvent.setup()
    renderApp()
    await screen.findByRole('heading', { name: 'Mission readiness before the constraint becomes a crisis.' })
    const modules: Array<[RegExp, string]> = [
      [/Workforce AI/, 'Capacity by occupation'],
      [/Supply AI/, 'Parts likely to constrain readiness'],
      [/Quality AI/, 'Quality risk by work center'],
      [/Data Readiness Assessment/, 'Assess an asset'],
      [/User Guide \+ Help/, 'Interactive guided tour'],
      [/Data Provenance/, 'Important boundary'],
    ]
    for (const [buttonName, heading] of modules) {
      await user.click(screen.getByRole('button', { name: buttonName }))
      expect(await screen.findByRole('heading', { name: heading })).toBeInTheDocument()
    }
  })

  it('saves an assessment through the authoritative API without browser-side scoring', async () => {
    const user = userEvent.setup()
    renderApp()
    await screen.findByRole('heading', { name: 'Mission readiness before the constraint becomes a crisis.' })
    await user.click(screen.getByRole('button', { name: /Data Readiness Assessment/ }))
    await screen.findByRole('heading', { name: 'Assess an asset' })
    await user.type(screen.getByLabelText('Asset ID'), 'CNC-999')
    await user.type(screen.getByLabelText('Asset Type'), 'CNC')
    await user.click(screen.getByRole('button', { name: 'Score & Save Assessment' }))

    expect(await screen.findAllByText('Direct connector + pilot')).toHaveLength(2)
    expect(screen.getByText('Assessment saved')).toBeInTheDocument()
    expect(localStorage.getItem('dra_assessments')).toBeNull()
    const fetchMock = vi.mocked(fetch)
    const write = fetchMock.mock.calls.find(([, options]) => options?.method === 'POST')
    expect(write).toBeDefined()
    expect(write?.[1]?.headers).toMatchObject({ 'Idempotency-Key': expect.any(String) })
    const request = JSON.parse(String(write?.[1]?.body)) as Record<string, unknown>
    expect(request).toMatchObject({ asset_id: 'CNC-999', connectivity: 'Native Digital' })
    expect(request).not.toHaveProperty('readiness_score')
    expect(request).not.toHaveProperty('readiness_grade')
  })

  it('offers a recoverable error state when the API is unavailable', async () => {
    const fetchMock = vi.mocked(fetch)
    fetchMock.mockImplementation(() => Promise.resolve(jsonResponse({ detail: 'Unavailable' }, 503)))
    const user = userEvent.setup()
    renderApp()
    expect(await screen.findByRole('alert')).toHaveTextContent('Prototype data could not load')

    fetchMock.mockImplementation(successfulFetch)
    await user.click(screen.getByRole('button', { name: 'Try again' }))
    expect(await screen.findByRole('heading', { name: 'Mission readiness before the constraint becomes a crisis.' })).toBeInTheDocument()
  })

  it('keeps the eight-step guide and opens the selected module', async () => {
    const user = userEvent.setup()
    renderApp()
    await screen.findByRole('heading', { name: 'Mission readiness before the constraint becomes a crisis.' })
    await user.click(screen.getByRole('button', { name: /User Guide \+ Help/ }))
    expect(await screen.findByText('Step 1 of 8')).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Next' }))
    expect(screen.getByRole('heading', { name: '2. Investigate asset risk' })).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Open this module' }))
    expect(await screen.findByRole('heading', { name: 'Highest-priority assets' })).toBeInTheDocument()
  })

  it('opens and closes the same sidebar through the mobile menu control', async () => {
    const user = userEvent.setup()
    const { container } = renderApp()
    const menu = await screen.findByRole('button', { name: 'Toggle navigation' })
    expect(menu).toHaveAttribute('aria-expanded', 'false')
    await user.click(menu)
    expect(menu).toHaveAttribute('aria-expanded', 'true')
    expect(container.querySelector('.side')).toHaveClass('open')
    await user.click(screen.getByRole('button', { name: /Quality AI/ }))
    expect(menu).toHaveAttribute('aria-expanded', 'false')
    expect(container.querySelector('.side')).not.toHaveClass('open')
  })

  it('limits depot controls and requests to the authenticated depot scope', async () => {
    activeSession = {
      subject: 'limited-assessor',
      roles: ['OIB-Assessors'],
      allowed_depots: ['ANAD'],
      authentication_mode: 'cognito',
    }
    const user = userEvent.setup()
    renderApp()

    await screen.findByRole('heading', { name: 'Mission readiness before the constraint becomes a crisis.' })
    const depot = screen.getByRole('combobox', { name: 'Depot' })
    expect(depot).toHaveValue('ANAD')
    expect(within(depot).getAllByRole('option').map((option) => option.textContent)).toEqual(['ANAD'])
    expect(screen.getByRole('button', { name: 'Sign out' })).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: /Data Readiness Assessment/ }))
    await screen.findByRole('heading', { name: 'Assess an asset' })
    expect(within(screen.getByRole('combobox', { name: 'Depot' })).getAllByRole('option').map((option) => option.textContent)).toEqual(['ANAD'])
    const fetchMock = vi.mocked(fetch)
    const scopedRequests = fetchMock.mock.calls
      .map(([input]) => new URL(String(input), 'http://localhost'))
      .filter((url) => url.pathname.includes('readiness/summary') || url.pathname.includes('connectivity-assessments'))
    expect(scopedRequests.length).toBeGreaterThan(0)
    expect(scopedRequests.every((url) => url.searchParams.get('depot') === 'ANAD')).toBe(true)
  })
})
