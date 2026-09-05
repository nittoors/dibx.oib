import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

function jsonResponse(value: unknown, status = 200): Response {
  return new Response(JSON.stringify(value), {
    status,
    headers: { 'Content-Type': 'application/json' },
  })
}

beforeEach(() => {
  vi.resetModules()
  vi.unstubAllEnvs()
  sessionStorage.clear()
  localStorage.clear()
  window.history.replaceState({}, '', '/OIBReadiness/')
})

afterEach(() => {
  vi.unstubAllGlobals()
  vi.unstubAllEnvs()
})

describe('Cognito public-client boundary', () => {
  it('keeps local development token-free', async () => {
    const authentication = await import('./auth')

    expect(authentication.isCognitoMode()).toBe(false)
    expect(authentication.authorizationHeader()).toEqual({})
    await expect(authentication.completeSignIn()).resolves.toBeUndefined()
  })

  it('exchanges an authorization code with PKCE and retains the token in memory only', async () => {
    vi.stubEnv('VITE_AUTH_MODE', 'cognito')
    vi.stubEnv('VITE_COGNITO_DOMAIN', 'https://example.auth.us-east-1.amazoncognito.com')
    vi.stubEnv('VITE_COGNITO_CLIENT_ID', 'public-client')
    vi.stubEnv('VITE_COGNITO_REDIRECT_URI', 'https://app.example/OIBReadiness/')
    sessionStorage.setItem('oib.oauth.state', 'expected-state')
    sessionStorage.setItem('oib.pkce.verifier', 'pkce-verifier')
    window.history.replaceState({}, '', '/OIBReadiness/?code=authorization-code&state=expected-state')
    const fetchMock = vi.fn((...request: [RequestInfo | URL, RequestInit?]) => {
      expect(request).toHaveLength(2)
      return Promise.resolve(jsonResponse({ access_token: 'access-token' }))
    })
    vi.stubGlobal('fetch', fetchMock)
    const authentication = await import('./auth')

    await authentication.completeSignIn()

    expect(authentication.authorizationHeader()).toEqual({ Authorization: 'Bearer access-token' })
    expect(localStorage.length).toBe(0)
    expect(sessionStorage.length).toBe(0)
    expect(window.location.search).toBe('')
    const request = fetchMock.mock.calls[0]
    expect(request[0]).toBe('https://example.auth.us-east-1.amazoncognito.com/oauth2/token')
    expect(String(request[1]?.body)).toContain('code_verifier=pkce-verifier')
  })

  it('rejects an OAuth callback whose state cannot be validated', async () => {
    vi.stubEnv('VITE_AUTH_MODE', 'cognito')
    vi.stubEnv('VITE_COGNITO_DOMAIN', 'https://example.auth.us-east-1.amazoncognito.com')
    vi.stubEnv('VITE_COGNITO_CLIENT_ID', 'public-client')
    sessionStorage.setItem('oib.oauth.state', 'expected-state')
    sessionStorage.setItem('oib.pkce.verifier', 'pkce-verifier')
    window.history.replaceState({}, '', '/OIBReadiness/?code=code&state=wrong-state')
    const authentication = await import('./auth')

    await expect(authentication.completeSignIn()).rejects.toThrow(
      'The sign-in response could not be validated',
    )
  })

  it('refuses to start Cognito without a valid public-client configuration', async () => {
    vi.stubEnv('VITE_AUTH_MODE', 'cognito')
    const authentication = await import('./auth')

    await expect(authentication.beginSignIn()).rejects.toThrow('Cognito sign-in is not configured')
  })

  it('clears the in-memory token and ends the Cognito hosted session on sign-out', async () => {
    vi.stubEnv('VITE_AUTH_MODE', 'cognito')
    vi.stubEnv('VITE_COGNITO_DOMAIN', 'https://example.auth.us-east-1.amazoncognito.com')
    vi.stubEnv('VITE_COGNITO_CLIENT_ID', 'public-client')
    vi.stubEnv('VITE_COGNITO_REDIRECT_URI', 'https://app.example/OIBReadiness/')
    vi.stubEnv('VITE_COGNITO_LOGOUT_URI', 'https://app.example/OIBReadiness/')
    sessionStorage.setItem('oib.oauth.state', 'expected-state')
    sessionStorage.setItem('oib.pkce.verifier', 'pkce-verifier')
    window.history.replaceState({}, '', '/OIBReadiness/?code=authorization-code&state=expected-state')
    vi.stubGlobal('fetch', vi.fn(() => Promise.resolve(jsonResponse({ access_token: 'access-token' }))))
    const authentication = await import('./auth')
    await authentication.completeSignIn()
    sessionStorage.setItem('oib.oauth.state', 'stale-state')
    const navigate = vi.fn()

    authentication.signOut(navigate)

    expect(authentication.authorizationHeader()).toEqual({})
    expect(sessionStorage.length).toBe(0)
    expect(navigate).toHaveBeenCalledWith(
      'https://example.auth.us-east-1.amazoncognito.com/logout?client_id=public-client&logout_uri=https%3A%2F%2Fapp.example%2FOIBReadiness%2F',
    )
  })
})
