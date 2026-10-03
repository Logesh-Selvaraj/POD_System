import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.tsx'
import ErrorBoundary from './components/ErrorBoundary.tsx'

/**
 * Root render — wraps the entire application in a top-level ErrorBoundary so
 * that any uncaught render error is caught and displayed as a user-friendly
 * recovery screen rather than a blank white page.
 *
 * StrictMode sits inside the boundary so that double-invocation in development
 * does not accidentally trigger the fallback for errors that only occur once.
 */
createRoot(document.getElementById('root')!).render(
  <ErrorBoundary>
    <StrictMode>
      <App />
    </StrictMode>
  </ErrorBoundary>,
)
