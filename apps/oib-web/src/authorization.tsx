import { createContext, type ReactNode, useContext } from 'react'
import type { DepotCode } from './types'

const DEFAULT_DEPOTS = ['RRAD', 'ANAD', 'SIAD', 'WVA', 'Other']
const AuthorizedDepots = createContext<string[]>(DEFAULT_DEPOTS)

export function AuthorizationProvider({
  allowedDepots,
  children,
}: {
  allowedDepots: string[]
  children: ReactNode
}) {
  return <AuthorizedDepots value={allowedDepots}>{children}</AuthorizedDepots>
}

export function useAuthorizedDepots(): string[] {
  return useContext(AuthorizedDepots)
}

export function useAuthorizedScope(): DepotCode {
  const allowedDepots = useAuthorizedDepots()
  const operational = ['RRAD', 'ANAD', 'SIAD', 'WVA'] as const
  return operational.every((code) => allowedDepots.includes(code))
    ? 'ALL'
    : operational.find((code) => allowedDepots.includes(code)) ?? 'RRAD'
}
