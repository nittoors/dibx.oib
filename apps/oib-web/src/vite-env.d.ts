/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_API_BASE_URL?: string
  readonly VITE_AUTH_MODE?: string
  readonly VITE_COGNITO_DOMAIN?: string
  readonly VITE_COGNITO_CLIENT_ID?: string
  readonly VITE_COGNITO_REDIRECT_URI?: string
  readonly VITE_COGNITO_LOGOUT_URI?: string
  readonly VITE_COGNITO_SCOPES?: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}

interface Window {
  __OIB_CONFIG__?: {
    apiBaseUrl?: string
    authMode?: string
    cognitoDomain?: string
    cognitoClientId?: string
    cognitoRedirectUri?: string
    cognitoLogoutUri?: string
    cognitoScopes?: string
  }
}
