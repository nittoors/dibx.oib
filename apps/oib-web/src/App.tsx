import { useQuery } from '@tanstack/react-query'
import { useEffect, useState } from 'react'
import { ApiError, api } from './api'
import { beginSignIn, isCognitoMode, signOut } from './auth'
import { AuthorizationProvider } from './authorization'
import { LoadingState } from './components'
import { AssessmentPage } from './pages/AssessmentPage'
import { AssetsPage } from './pages/AssetsPage'
import { CommandPage } from './pages/CommandPage'
import { FlowPage } from './pages/FlowPage'
import { ProvenancePage } from './pages/ProvenancePage'
import { QualityPage } from './pages/QualityPage'
import { SupplyPage } from './pages/SupplyPage'
import { TrainingPage } from './pages/TrainingPage'
import { WorkforcePage } from './pages/WorkforcePage'
import { redCedarLogo } from './resources'
import type { DepotCode, PageId } from './types'

const NAVIGATION: Array<{ id: PageId; icon: string; label: string; subtitle: string }> = [
  { id: 'command', icon: '◈', label: 'Readiness Command', subtitle: 'Integrated readiness picture' },
  { id: 'assets', icon: '⚙', label: 'Asset Reliability AI', subtitle: 'Equipment health and failure risk' },
  { id: 'workforce', icon: '♟', label: 'Workforce AI', subtitle: 'Skills, capacity and surge' },
  { id: 'supply', icon: '▣', label: 'Supply AI', subtitle: 'Parts and source risk' },
  { id: 'flow', icon: '⇄', label: 'Production Flow AI', subtitle: 'Bottlenecks and plan attainment' },
  { id: 'quality', icon: '✓', label: 'Quality AI', subtitle: 'Defects, yield and NCR signals' },
  { id: 'connect', icon: '⌁', label: 'Data Readiness Assessment', subtitle: 'Connectivity and data-access scoring' },
  { id: 'training', icon: '?', label: 'User Guide + Help', subtitle: 'Interactive guide and resources' },
  { id: 'provenance', icon: 'i', label: 'Data Provenance', subtitle: 'Synthetic data sources and boundaries' },
]

export default function App() {
  const sessionQuery = useQuery({ queryKey: ['session'], queryFn: api.session, retry: false })
  if (sessionQuery.isPending) return <div className="content"><LoadingState /></div>
  if (sessionQuery.isError) {
    const authenticationRequired = isCognitoMode()
      && sessionQuery.error instanceof ApiError
      && sessionQuery.error.status === 401
    if (authenticationRequired) {
      return <main className="content"><section className="hero"><h3>Depot Readiness AI</h3><p>Sign in with your authorized account to continue.</p><div className="actions"><button className="btn primary" type="button" onClick={() => void beginSignIn()}>Sign in</button></div></section></main>
    }
    return <main className="content"><div className="card error-state" role="alert"><h3>Prototype data could not load</h3><p>The API is unavailable or authentication is not configured.</p><button className="btn primary" type="button" onClick={() => void sessionQuery.refetch()}>Try again</button></div></main>
  }
  return <AuthorizationProvider allowedDepots={sessionQuery.data.allowed_depots}><ApplicationShell allowedDepots={sessionQuery.data.allowed_depots} publicReadOnly={sessionQuery.data.authentication_mode === 'public_readonly'} showSignOut={sessionQuery.data.authentication_mode === 'cognito'} /></AuthorizationProvider>
}

function ApplicationShell({ allowedDepots, publicReadOnly, showSignOut }: { allowedDepots: string[]; publicReadOnly: boolean; showSignOut: boolean }) {
  const [page, setPage] = useState<PageId>('command')
  const [depot, setDepot] = useState<DepotCode>(() => {
    const operational = ['RRAD', 'ANAD', 'SIAD', 'WVA'] as const
    return operational.every((code) => allowedDepots.includes(code))
      ? 'ALL'
      : operational.find((code) => allowedDepots.includes(code)) ?? 'RRAD'
  })
  const [menuOpen, setMenuOpen] = useState(false)
  const [toast, setToast] = useState('')
  const current = NAVIGATION.find((item) => item.id === page) ?? NAVIGATION[0]

  useEffect(() => {
    window.scrollTo({ top: 0, behavior: 'instant' })
  }, [page])

  useEffect(() => {
    if (!toast) return
    const timeout = window.setTimeout(() => setToast(''), 1800)
    return () => window.clearTimeout(timeout)
  }, [toast])

  function openPage(nextPage: PageId) {
    setPage(nextPage)
    setMenuOpen(false)
  }

  let content
  if (page === 'command') content = <CommandPage depot={depot} setDepot={setDepot} />
  else if (page === 'assets') content = <AssetsPage depot={depot} setDepot={setDepot} />
  else if (page === 'workforce') content = <WorkforcePage depot={depot} setDepot={setDepot} />
  else if (page === 'supply') content = <SupplyPage />
  else if (page === 'flow') content = <FlowPage depot={depot} setDepot={setDepot} />
  else if (page === 'quality') content = <QualityPage depot={depot} setDepot={setDepot} />
  else if (page === 'connect') content = <AssessmentPage publicReadOnly={publicReadOnly} showToast={setToast} />
  else if (page === 'training') content = <TrainingPage openPage={openPage} />
  else content = <ProvenancePage />

  return (
    <div className="app">
      <aside className={`side${menuOpen ? ' open' : ''}`}>
        <div className="brand">
          <img src={redCedarLogo} alt="Red Cedar logo" />
          <div><h1>Depot Readiness AI</h1><small>OIB Decision Support Prototype</small></div>
        </div>
        <nav className="nav" aria-label="Primary navigation">
          {NAVIGATION.map((item) => (
            <button key={item.id} type="button" className={item.id === page ? 'active' : ''} aria-current={item.id === page ? 'page' : undefined} onClick={() => openPage(item.id)}>
              <span className="ico" aria-hidden="true">{item.icon}</span><span>{item.label}</span>
            </button>
          ))}
        </nav>
        <div className="sidefoot">Synthetic demonstration environment. No operational Army data is included.</div>
      </aside>
      <div className="main">
        <header className="topbar">
          <div className="topbar-title">
            <button className="btn ghost mobile-menu" type="button" aria-label="Toggle navigation" aria-expanded={menuOpen} onClick={() => setMenuOpen((value) => !value)}>☰</button>
            <div><h2>{current.label}</h2><div className="meta">{current.subtitle}</div></div>
          </div>
          <div className="topbar-actions">
            <div className="meta topbar-version">Prototype v5.1 • Army + Red Cedar Theme • Port 8899</div>
            {showSignOut && <button className="btn ghost sign-out" type="button" onClick={() => signOut()}>Sign out</button>}
          </div>
        </header>
        <main className="content">{content}</main>
      </div>
      <div className={`toast${toast ? ' show' : ''}`} role="status">{toast}</div>
    </div>
  )
}
