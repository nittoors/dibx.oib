import { appConfig } from './config'

let accessToken: string | null = null

const AUTH_MODE = appConfig.authMode
const COGNITO_DOMAIN = appConfig.cognitoDomain.replace(/\/$/, '')
const CLIENT_ID = appConfig.cognitoClientId
const REDIRECT_URI = appConfig.cognitoRedirectUri
const LOGOUT_URI = appConfig.cognitoLogoutUri
const SCOPES = appConfig.cognitoScopes

function base64Url(bytes: ArrayBuffer): string {
  return btoa(String.fromCharCode(...new Uint8Array(bytes)))
    .replaceAll('+', '-')
    .replaceAll('/', '_')
    .replaceAll('=', '')
}

function randomValue(): string {
  return base64Url(crypto.getRandomValues(new Uint8Array(32)).buffer)
}

function requireCognitoConfiguration(): void {
  if (!COGNITO_DOMAIN.startsWith('https://') || !CLIENT_ID) {
    throw new Error('Cognito sign-in is not configured')
  }
}

export function isCognitoMode(): boolean {
  return AUTH_MODE === 'cognito'
}

export function authorizationHeader(): Record<string, string> {
  return accessToken ? { Authorization: `Bearer ${accessToken}` } : {}
}

export async function beginSignIn(): Promise<void> {
  requireCognitoConfiguration()
  const verifier = randomValue()
  const challenge = base64Url(await crypto.subtle.digest('SHA-256', new TextEncoder().encode(verifier)))
  const state = randomValue()
  sessionStorage.setItem('oib.pkce.verifier', verifier)
  sessionStorage.setItem('oib.oauth.state', state)
  const query = new URLSearchParams({
    response_type: 'code',
    client_id: CLIENT_ID,
    redirect_uri: REDIRECT_URI,
    scope: SCOPES,
    state,
    code_challenge_method: 'S256',
    code_challenge: challenge,
  })
  window.location.assign(`${COGNITO_DOMAIN}/oauth2/authorize?${query}`)
}

export async function completeSignIn(): Promise<void> {
  if (!isCognitoMode()) return
  const query = new URLSearchParams(window.location.search)
  const code = query.get('code')
  if (!code) return
  requireCognitoConfiguration()
  const expectedState = sessionStorage.getItem('oib.oauth.state')
  const verifier = sessionStorage.getItem('oib.pkce.verifier')
  if (!expectedState || query.get('state') !== expectedState || !verifier) {
    throw new Error('The sign-in response could not be validated')
  }
  sessionStorage.removeItem('oib.oauth.state')
  sessionStorage.removeItem('oib.pkce.verifier')
  const response = await fetch(`${COGNITO_DOMAIN}/oauth2/token`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body: new URLSearchParams({
      grant_type: 'authorization_code',
      client_id: CLIENT_ID,
      code,
      redirect_uri: REDIRECT_URI,
      code_verifier: verifier,
    }),
  })
  if (!response.ok) throw new Error('Cognito token exchange failed')
  const tokens = await response.json() as { access_token?: unknown }
  if (typeof tokens.access_token !== 'string') throw new Error('Cognito returned no access token')
  accessToken = tokens.access_token
  window.history.replaceState({}, document.title, window.location.pathname + window.location.hash)
}

export function signOut(navigate: (url: string) => void = (url) => window.location.assign(url)): void {
  accessToken = null
  sessionStorage.removeItem('oib.oauth.state')
  sessionStorage.removeItem('oib.pkce.verifier')
  if (!isCognitoMode()) {
    navigate(LOGOUT_URI)
    return
  }
  requireCognitoConfiguration()
  const query = new URLSearchParams({ client_id: CLIENT_ID, logout_uri: LOGOUT_URI })
  navigate(`${COGNITO_DOMAIN}/logout?${query}`)
}
