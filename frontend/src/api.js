const BASE = '/api'

async function request(path, options = {}) {
  const token = localStorage.getItem('token')
  const headers = { ...(options.headers || {}) }
  if (token) headers['Authorization'] = `Bearer ${token}`
  if (!(options.body instanceof FormData)) {
    headers['Content-Type'] = 'application/json'
  }
  const res = await fetch(`${BASE}${path}`, { ...options, headers })
  if (res.status === 401) {
    localStorage.removeItem('token')
    window.location.reload()
    throw new Error('Session expired')
  }
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(err.detail || 'Request failed')
  }
  if (res.status === 204) return null
  return res.json()
}

export const auth = {
  register: (email, password, name) =>
    request('/auth/register', { method: 'POST', body: JSON.stringify({ email, password, name }) }),
  login: async (email, password) => {
    const data = await request('/auth/login', { method: 'POST', body: JSON.stringify({ email, password }) })
    if (data.access_token) localStorage.setItem('token', data.access_token)
    return data
  },
  me: () => request('/auth/me'),
  logout: () => { localStorage.removeItem('token') },
  updateProfile: (data) => request('/auth/profile', { method: 'PATCH', body: JSON.stringify(data) }),
  deleteAccount: () => request('/auth/account', { method: 'DELETE' }),
}

export const resumes = {
  upload: (raw_text, filename = 'resume.txt') =>
    request('/resumes', { method: 'POST', body: JSON.stringify({ raw_text, filename }) }),
  uploadFile: (file) => {
    const formData = new FormData()
    formData.append('file', file)
    return request('/resumes/upload', { method: 'POST', body: formData })
  },
  list: () => request('/resumes'),
  active: () => request('/resumes/active'),
  activate: (id) => request(`/resumes/${id}/activate`, { method: 'PATCH' }),
}

export const prefs = {
  get: () => request('/preferences'),
  save: (data) => request('/preferences', { method: 'PUT', body: JSON.stringify(data) }),
}

export const jobs = {
  list: (query = '') => request(`/jobs?${query}`),
  get: (id) => request(`/jobs/${id}`),
  scan: (score = true) => request('/jobs/scan', { method: 'POST', body: JSON.stringify({ score_results: score }) }),
}

export const apps = {
  list: () => request('/applications'),
  create: (jobId, runPipeline = true) =>
    request('/applications', { method: 'POST', body: JSON.stringify({ job_id: jobId, run_pipeline: runPipeline }) }),
  get: (id) => request(`/applications/${id}`),
  update: (id, data) => request(`/applications/${id}`, { method: 'PATCH', body: JSON.stringify(data) }),
  stats: () => request('/applications/stats'),
}

export const tasks = {
  status: (id) => request(`/events/${id}/status`),
}

export const notifications = {
  list: (unreadOnly = false) => request(`/notifications?unread_only=${unreadOnly}`),
  unreadCount: () => request('/notifications/unread-count'),
  markRead: (id) => request(`/notifications/${id}/read`, { method: 'POST' }),
  markAllRead: () => request('/notifications/read-all', { method: 'POST' }),
}

export function setToken(t) { localStorage.setItem('token', t) }
export function getToken() { return localStorage.getItem('token') }