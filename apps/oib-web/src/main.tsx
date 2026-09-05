import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { BrowserRouter } from 'react-router-dom'
import App from './App'
import { completeSignIn } from './auth'
import './styles.css'

const queryClient = new QueryClient()

async function start() {
  try {
    await completeSignIn()
  } catch {
    // The session endpoint will fail closed and offer a fresh sign-in attempt.
  }
  createRoot(document.getElementById('root')!).render(
    <StrictMode>
      <QueryClientProvider client={queryClient}>
        <BrowserRouter basename="/OIBReadiness">
          <App />
        </BrowserRouter>
      </QueryClientProvider>
    </StrictMode>,
  )
}

void start()
