import type {
  Asset,
  ConnectivityAssessment,
  DepotCode,
  Page,
  Part,
  ProductionFlow,
  Quality,
  ReadinessSummary,
  ReadinessTrend,
  Session,
  SubmittedAssessmentInput,
  WorkforceCapacity,
} from './types'
import { authorizationHeader } from './auth'
import { appConfig } from './config'

const API_BASE = appConfig.apiBaseUrl.replace(/\/$/, '')

export class ApiError extends Error {
  constructor(public status: number) {
    super(`Request failed (${status})`)
  }
}

async function getJson<T>(path: string): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: { Accept: 'application/json', ...authorizationHeader() },
  })
  if (!response.ok) {
    throw new ApiError(response.status)
  }
  return (await response.json()) as T
}

async function postJson<T>(path: string, value: unknown, idempotencyKey: string): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    method: 'POST',
    headers: {
      Accept: 'application/json',
      'Content-Type': 'application/json',
      'Idempotency-Key': idempotencyKey,
      ...authorizationHeader(),
    },
    body: JSON.stringify(value),
  })
  if (!response.ok) throw new ApiError(response.status)
  return (await response.json()) as T
}

function depotParam(depot: DepotCode): string {
  return encodeURIComponent(depot)
}

export const api = {
  session: () => getJson<Session>('/session'),
  summary: (depot: DepotCode) =>
    getJson<ReadinessSummary>(`/readiness/summary?depot=${depotParam(depot)}`),
  trend: (depot: DepotCode) =>
    getJson<ReadinessTrend[]>(`/readiness/trend?depot=${depotParam(depot)}`),
  assets: (depot: DepotCode) =>
    getJson<Page<Asset>>(`/assets?depot=${depotParam(depot)}&size=80&sort=risk_desc`),
  workforce: (depot: DepotCode) =>
    getJson<Page<WorkforceCapacity>>(`/workforce/capacity?depot=${depotParam(depot)}&size=60`),
  parts: () => getJson<Page<Part>>('/parts?size=100&sort=risk_desc'),
  flow: (depot: DepotCode) =>
    getJson<Page<ProductionFlow>>(`/production-flow?depot=${depotParam(depot)}&size=100`),
  quality: (depot: DepotCode) =>
    getJson<Page<Quality>>(`/quality?depot=${depotParam(depot)}&size=100`),
  assessments: (depot: DepotCode = 'ALL') =>
    getJson<Page<ConnectivityAssessment>>(`/connectivity-assessments?size=80&depot=${depotParam(depot)}`),
  submittedAssessments: (depot: DepotCode = 'ALL') =>
    getJson<Page<ConnectivityAssessment>>(`/connectivity-assessments/submitted?size=80&depot=${depotParam(depot)}`),
  createAssessment: (assessment: SubmittedAssessmentInput, idempotencyKey: string) =>
    postJson<ConnectivityAssessment>('/connectivity-assessments', assessment, idempotencyKey),
}
