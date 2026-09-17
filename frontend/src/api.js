const BASE = '/api'

let token = localStorage.getItem('greenroom_token') || null

export function setToken(t) {
  token = t
  if (t) localStorage.setItem('greenroom_token', t)
  else localStorage.removeItem('greenroom_token')
}

export function getToken() {
  return token
}

async function request(method, path, body = null) {
  const headers = { 'Content-Type': 'application/json' }
  if (token) headers['Authorization'] = `Bearer ${token}`

  const opts = { method, headers }
  if (body) opts.body = JSON.stringify(body)

  const res = await fetch(`${BASE}${path}`, opts)

  if (res.status === 401) {
    setToken(null)
    window.location.href = '/login'
    throw new Error('Unauthorized')
  }

  if (res.status === 204) return null

  const data = await res.json()
  if (!res.ok) throw new Error(data.detail || 'Request failed')
  return data
}

// Auth
export const auth = {
  register: (email, password, name) =>
    request('POST', '/auth/register', { email, password, name }),
  login: (email, password) =>
    request('POST', '/auth/login', { email, password }),
  me: () => request('GET', '/auth/me'),
}

// Resumes
export const resumes = {
  upload: (raw_text, filename) =>
    request('POST', '/resumes', { raw_text, filename }),
  list: () => request('GET', '/resumes'),
  active: () => request('GET', '/resumes/active'),
}

// Preferences
export const prefs = {
  get: () => request('GET', '/preferences'),
  save: (data) => request('PUT', '/preferences', data),
}

// Jobs
export const jobs = {
  scan: (score_results = false) =>
    request('POST', '/jobs/scan', { score_results }),
  list: (params = '') => request('GET', `/jobs${params ? '?' + params : ''}`),
  get: (id) => request('GET', `/jobs/${id}`),
}

// Applications
export const apps = {
  create: (job_id, run_pipeline = true) =>
    request('POST', '/applications', { job_id, run_pipeline }),
  batch: (job_ids) =>
    request('POST', '/applications/batch', { job_ids }),
  list: (params = '') =>
    request('GET', `/applications${params ? '?' + params : ''}`),
  stats: () => request('GET', '/applications/stats'),
  update: (id, data) => request('PATCH', `/applications/${id}`, data),
  remove: (id) => request('DELETE', `/applications/${id}`),
}

// Task polling
export const tasks = {
  status: (taskId) =>
    fetch(`${BASE}/events/${taskId}/status`).then(r => r.json()),
}

// SSE stream
export function streamTask(taskId, onEvent) {
  const source = new EventSource(`${BASE}/events/${taskId}`)
  source.onmessage = (e) => {
    const data = JSON.parse(e.data)
    onEvent(data)
    if (data.status === 'completed' || data.status === 'failed') {
      source.close()
    }
  }
  source.onerror = () => source.close()
  return source
}
