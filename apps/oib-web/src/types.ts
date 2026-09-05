export type DepotCode = 'ALL' | 'RRAD' | 'ANAD' | 'SIAD' | 'WVA'
export type PageId =
  | 'command'
  | 'assets'
  | 'workforce'
  | 'supply'
  | 'flow'
  | 'quality'
  | 'connect'
  | 'training'
  | 'provenance'

export interface Page<T> {
  items: T[]
  page: number
  size: number
  total: number
  pages: number
}

export interface ReadinessSummary {
  depot: DepotCode
  command: {
    composite_readiness: number
    assets_elevated: number
    workforce_gap: number
    critical_supply: number
    plan_attainment: number
    open_ncr: number
    bottlenecks: number
  }
  assets: {
    count: number
    average_health: number
    high_risk: number
    legacy_analog: number
  }
  workforce: {
    count: number
    average_availability: number
    skill_families_at_risk: number
    training_due: number
  }
  flow: {
    plan_attainment: number
    bottlenecks: number
    queue_hours: number
    downtime_hours: number
  }
  quality: {
    inspections: number
    average_defect_rate: number
    first_pass_yield: number
    open_ncr: number
  }
  supply: {
    parts: number
    critical_risks: number
    single_source: number
    average_lead_time_days: number
    scope: 'GLOBAL'
  }
  assessment: {
    green: number
    yellow: number
    red: number
    ruleset: string
  }
  drivers: Array<{ name: string; value: number }>
  observed_at: string
  source_system: string
}

export interface ReadinessTrend {
  reporting_period: string
  month: string
  readiness: number
}

export interface Asset {
  asset_id: string
  depot: Exclude<DepotCode, 'ALL'>
  asset_type: string
  manufacturer: string
  model: string
  age_years: number
  criticality: string
  connectivity_tier: string
  protocol: string
  health_score: number
  failure_risk_30d: number
  work_center: string
  operating_hours: number
  observed_at: string
}

export interface WorkforceCapacity {
  depot: Exclude<DepotCode, 'ALL'>
  occupation_code: string
  occupation: string
  assigned_workers: number
  available_workers: number
  required_workers: number
  capacity_gap: number
  training_due: number
  coverage_pct: number
  observed_at: string
}

export interface Part {
  part_id: string
  fsc: string
  part_name: string
  source_count: number
  lead_time_days: number
  on_hand: number
  projected_60d_demand: number
  criticality: string
  supply_risk: number
  recommended_action: string
  scope: 'GLOBAL'
  observed_at: string
}

export interface ProductionFlow {
  depot: Exclude<DepotCode, 'ALL'>
  work_center: string
  weekly_plan: number
  forecast_output: number
  plan_attainment_pct: number
  queue_hours: number
  downtime_hours: number
  labor_gap_pct: number
  constraint_driver: string
  observed_at: string
}

export interface Quality {
  depot: Exclude<DepotCode, 'ALL'>
  work_center: string
  inspections: number
  defect_rate_pct: number
  first_pass_yield_pct: number
  open_ncr: number
  repeat_ncr: number
  top_defect: string
  ai_focus: string
  observed_at: string
}

export type ReadinessGrade = 'Green' | 'Yellow' | 'Red'

export interface ConnectivityAssessment {
  id?: string
  asset_id: string
  depot: string
  asset_type: string
  manufacturer: string
  connectivity: string
  protocol: string
  data_rights: string
  cyber_status: string
  history: string
  data_quality: string
  readiness_score: number
  readiness_grade: ReadinessGrade
  recommended_action: string
  dimension_points?: Record<string, number>
  ruleset?: string
  observed_at?: string
  notes?: string
  assessed_at?: string
}

export type SubmittedAssessmentInput = Pick<
  ConnectivityAssessment,
  | 'asset_id'
  | 'depot'
  | 'asset_type'
  | 'manufacturer'
  | 'connectivity'
  | 'protocol'
  | 'data_rights'
  | 'cyber_status'
  | 'history'
  | 'data_quality'
  | 'notes'
>

export interface Session {
  subject: string
  roles: string[]
  allowed_depots: string[]
  authentication_mode: 'development' | 'cognito'
}
