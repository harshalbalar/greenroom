import { useState } from 'react'
import { auth, setToken } from '../api'

export default function Login({ onAuth }) {
  const [mode, setMode] = useState('login')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [name, setName] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  async function handleSubmit(e) {
    e.preventDefault()
    setError('')
    setLoading(true)

    try {
      let res
      if (mode === 'register') {
        res = await auth.register(email, password, name)
      } else {
        res = await auth.login(email, password)
      }

      setToken(res.access_token)
      const user = await auth.me()
      onAuth(res.access_token, user)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="login-page">
      <div className="login-card fade-in">
        <div className="login-title"><em>green</em>room</div>
        <div className="login-sub">your applications, prepped and ready</div>

        <form onSubmit={handleSubmit}>
          {mode === 'register' && (
            <div className="form-group">
              <label>Name</label>
              <input
                type="text"
                placeholder="Sarah Chen"
                value={name}
                onChange={e => setName(e.target.value)}
              />
            </div>
          )}

          <div className="form-group">
            <label>Email</label>
            <input
              type="email"
              placeholder="you@example.com"
              value={email}
              onChange={e => setEmail(e.target.value)}
              required
            />
          </div>

          <div className="form-group">
            <label>Password</label>
            <input
              type="password"
              placeholder="min 6 characters"
              value={password}
              onChange={e => setPassword(e.target.value)}
              required
              minLength={6}
            />
          </div>

          {error && <div className="form-error">{error}</div>}

          <button
            type="submit"
            className="btn btn-primary"
            style={{ width: '100%', padding: '10px', fontSize: 13, marginTop: 8 }}
            disabled={loading}
          >
            {loading ? <span className="spinner" /> : mode === 'login' ? 'Enter the greenroom' : 'Join the crew'}
          </button>
        </form>

        <div className="form-footer">
          {mode === 'login' ? (
            <>New here? <a onClick={() => { setMode('register'); setError('') }}>Create an account</a></>
          ) : (
            <>Already have an account? <a onClick={() => { setMode('login'); setError('') }}>Sign in</a></>
          )}
        </div>
      </div>
    </div>
  )
}
