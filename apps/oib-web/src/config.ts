export interface OibRuntimeConfig {
  apiBaseUrl: string
  authMode: string
  cognitoDomain: string
  cognitoClientId: string
  cognitoRedirectUri: string
  cognitoLogoutUri: string
  cognitoScopes: string
}

const runtime = window.__OIB_CONFIG__ ?? {}

export const appConfig: OibRuntimeConfig = {
  apiBaseUrl: runtime.apiBaseUrl || import.meta.env.VITE_API_BASE_URL || '/api/v1',
  authMode: runtime.authMode || import.meta.env.VITE_AUTH_MODE || 'development',
  cognitoDomain: runtime.cognitoDomain || import.meta.env.VITE_COGNITO_DOMAIN || '',
  cognitoClientId: runtime.cognitoClientId || import.meta.env.VITE_COGNITO_CLIENT_ID || '',
  cognitoRedirectUri:
    runtime.cognitoRedirectUri ||
    import.meta.env.VITE_COGNITO_REDIRECT_URI ||
    `${window.location.origin}/OIBReadiness/`,
  cognitoLogoutUri:
    runtime.cognitoLogoutUri ||
    import.meta.env.VITE_COGNITO_LOGOUT_URI ||
    `${window.location.origin}/OIBReadiness/`,
  cognitoScopes:
    runtime.cognitoScopes || import.meta.env.VITE_COGNITO_SCOPES || 'openid email profile',
}
