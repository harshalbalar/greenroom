import { useState, useEffect } from 'react'
import { auth, setToken, getToken } from './api'
import Landing from './pages/Landing'
import Login from './pages/Login'
import Dashboard from './pages/Dashboard'

export default function App() {
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(true)
  const [view, setView] = useState('landing')

  useEffect(() => {
    if (getToken()) {
      auth.me()
        .then(setUser)
        .catch(() => setToken(null))
        .finally(() => setLoading(false))
    } else {
      setLoading(false)
    }
  }, [])

  function handleAuth(token, userData) {
    setToken(token)
    setUser(userData)
  }

  function handleLogout() {
    setToken(null)
    setUser(null)
    setView('landing')
  }

  if (loading) {
    return (
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100vh', background: '#0d0a12' }}>
        <div className="spinner" style={{ width: 24, height: 24 }} />
      </div>
    )
  }

  if (user) return <Dashboard user={user} onLogout={handleLogout} />

  if (view === 'login' || view === 'register') {
    return <Login onAuth={handleAuth} initialMode={view} onBack={() => setView('landing')} />
  }

  return <Landing onGetStarted={(mode) => setView(mode)} />
}