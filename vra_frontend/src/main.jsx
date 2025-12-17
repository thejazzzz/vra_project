//File: src/main.jsx
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.jsx'

const rootElement = document.getElementById('root')

if (!rootElement) {
  throw new Error(
    'Failed to find the root element. Ensure your HTML contains a <div id="root"></div>'
  )
}

createRoot(rootElement).render(
  <StrictMode>
    <App />
  </StrictMode>
)
