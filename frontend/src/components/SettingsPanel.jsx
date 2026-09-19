import { useState, useEffect, useRef } from 'react'
import { auth, resumes, prefs } from '../api'

export default function SettingsPanel({ user, onClose, onUpdate }) {
  const [activeTab, setActiveTab] = useState('profile')
  const [loading, setLoading] = useState(false)
  const [success, setSuccess] = useState('')
  const [error, setError] = useState('')

  // Profile
  const [name, setName] = useState(user?.name || '')
  const [email, setEmail] = useState(user?.email || '')

  // Resume
  const [currentResume, setCurrentResume] = useState(null)
  const [uploadedFile, setUploadedFile] = useState(null)
  const [resumeText, setResumeText] = useState('')
  const fileInputRef = useRef()

  // Preferences
  const [roles, setRoles] = useState('')
  const [locations, setLocations] = useState('')
  const [salaryMin, setSalaryMin] = useState('')
  const [salaryMax, setSalaryMax] = useState('')
  const [remotePref, setRemotePref] = useState('any')

  useEffect(() => {
    loadData()
  }, [])

  async function loadData() {
    try {
      const r = await resumes.active().catch(() => null)
      if (r) setCurrentResume(r)
    } catch {}
    try {
      const p = await prefs.get().catch(() => null)
      if (p) {
        setRoles((p.target_roles || []).join(', '))
        setLocations((p.locations || []).join(', '))
        setSalaryMin(p.salary_min || '')
        setSalaryMax(p.salary_max || '')
        setRemotePref(p.remote_preference || 'any')
      }
    } catch {}
  }

  function showSuccess(msg) {
    setSuccess(msg); setError('')
    setTimeout(() => setSuccess(''), 3000)
  }

  async function saveProfile() {
    setLoading(true); setError('')
    try {
      const updated = await auth.updateProfile({ name, email })
      showSuccess('Profile updated')
      onUpdate?.(updated)
    } catch (e) { setError(e.message) }
    finally { setLoading(false) }
  }

  function handleFileSelect(e) {
    const file = e.target.files?.[0]
    if (!file) return
    const ext = file.name.split('.').pop().toLowerCase()
    if (!['pdf', 'docx', 'txt', 'doc'].includes(ext)) {
      setError('Supported formats: PDF, DOCX, TXT')
      return
    }
    setUploadedFile(file)
    setResumeText('')
    setError('')
  }

  async function uploadResume() {
    setLoading(true); setError('')
    try {
      let res
      if (uploadedFile) {
        res = await resumes.uploadFile(uploadedFile)
      } else if (resumeText.trim().length >= 50) {
        res = await resumes.upload(resumeText, 'resume.txt')
      } else {
        setError('Upload a file or paste at least 50 characters')
        setLoading(false)
        return
      }
      setCurrentResume(res)
      setUploadedFile(null)
      setResumeText('')
      showSuccess(`Resume updated — ${res.parsed_data?.name || 'parsed'}, ${res.parsed_data?.skills?.length || 0} skills`)
    } catch (e) { setError(e.message) }
    finally { setLoading(false) }
  }

  async function savePreferences() {
    setLoading(true); setError('')
    try {
      await prefs.save({
        target_roles: roles.split(',').map(r => r.trim()).filter(Boolean),
        locations: locations.split(',').map(l => l.trim()).filter(Boolean),
        salary_min: parseInt(salaryMin) || null,
        salary_max: parseInt(salaryMax) || null,
        remote_preference: remotePref,
      })
      showSuccess('Preferences saved')
    } catch (e) { setError(e.message) }
    finally { setLoading(false) }
  }

  const tabs = [
    { id: 'profile', label: '👤 Profile' },
    { id: 'resume', label: '📄 Resume' },
    { id: 'prefs', label: '🎯 Preferences' },
  ]

  return (
    <div style={{
      position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.7)',
      display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 100,
    }} onClick={e => e.target === e.currentTarget && onClose()}>
      <div style={{
        background: '#12102a', border: '1px solid rgba(255,255,255,0.08)',
        borderRadius: 16, padding: 0, width: 480, maxHeight: '80vh', overflow: 'hidden',
        display: 'flex', flexDirection: 'column',
      }}>
        {/* Header */}
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '16px 20px', borderBottom: '1px solid rgba(255,255,255,0.06)' }}>
          <div style={{ fontSize: 16, fontWeight: 600 }}>Settings</div>
          <button onClick={onClose} style={{ background: 'none', border: 'none', color: 'rgba(255,255,255,0.3)', cursor: 'pointer', fontSize: 16 }}>✕</button>
        </div>

        {/* Tabs */}
        <div style={{ display: 'flex', gap: 0, padding: '12px 20px 0', borderBottom: '1px solid rgba(255,255,255,0.06)' }}>
          {tabs.map(t => (
            <button key={t.id} onClick={() => { setActiveTab(t.id); setError(''); setSuccess('') }}
              style={{
                padding: '8px 16px', fontSize: 12, cursor: 'pointer',
                background: 'none', border: 'none', borderBottom: activeTab === t.id ? '2px solid #7B6CF6' : '2px solid transparent',
                color: activeTab === t.id ? '#e8e6e0' : 'rgba(255,255,255,0.35)',
                fontWeight: activeTab === t.id ? 600 : 400, transition: 'all 0.15s',
              }}>{t.label}</button>
          ))}
        </div>

        {/* Content */}
        <div style={{ padding: 20, overflowY: 'auto', flex: 1 }}>
          {/* Messages */}
          {success && <div style={{ background: 'rgba(93,207,93,0.1)', border: '1px solid rgba(93,207,93,0.2)', borderRadius: 8, padding: '8px 12px', marginBottom: 12, fontSize: 12, color: '#5DCF5D' }}>✓ {success}</div>}
          {error && <div style={{ background: 'rgba(239,100,73,0.1)', border: '1px solid rgba(239,100,73,0.2)', borderRadius: 8, padding: '8px 12px', marginBottom: 12, fontSize: 12, color: '#EF6449' }}>{error}</div>}

          {/* Profile Tab */}
          {activeTab === 'profile' && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
              <div>
                <label style={{ fontSize: 10, color: 'rgba(255,255,255,0.35)', textTransform: 'uppercase', letterSpacing: 1, display: 'block', marginBottom: 4 }}>Name</label>
                <input value={name} onChange={e => setName(e.target.value)}
                  style={{ width: '100%', padding: '10px 12px', borderRadius: 8, border: '1px solid rgba(255,255,255,0.08)', background: 'rgba(255,255,255,0.03)', color: '#e8e6e0', fontSize: 13, outline: 'none', boxSizing: 'border-box' }} />
              </div>
              <div>
                <label style={{ fontSize: 10, color: 'rgba(255,255,255,0.35)', textTransform: 'uppercase', letterSpacing: 1, display: 'block', marginBottom: 4 }}>Email</label>
                <input value={email} onChange={e => setEmail(e.target.value)} type="email"
                  style={{ width: '100%', padding: '10px 12px', borderRadius: 8, border: '1px solid rgba(255,255,255,0.08)', background: 'rgba(255,255,255,0.03)', color: '#e8e6e0', fontSize: 13, outline: 'none', boxSizing: 'border-box' }} />
              </div>
              <button onClick={saveProfile} disabled={loading}
                style={{ padding: '10px 0', borderRadius: 8, border: 'none', background: 'linear-gradient(135deg, #7B6CF6, #E966A0)', color: '#fff', cursor: 'pointer', fontSize: 13, fontWeight: 500, opacity: loading ? 0.6 : 1 }}>
                {loading ? 'Saving...' : 'Save profile'}
              </button>
              <button onClick={() => { auth.logout(); window.location.reload() }}
                style={{ padding: '10px 0', borderRadius: 8, border: '1px solid rgba(239,100,73,0.3)', background: 'transparent', color: '#EF6449', cursor: 'pointer', fontSize: 12, marginTop: 8 }}>
                Log out
              </button>
              <button onClick={async () => {
                if (window.confirm('This will permanently delete your account and all data. Are you sure?')) {
                  if (window.confirm('This cannot be undone. Really delete everything?')) {
                    try {
                      await auth.deleteAccount()
                      auth.logout()
                      window.location.reload()
                    } catch (e) { setError(e.message) }
                  }
                }
              }} style={{ padding: '10px 0', borderRadius: 8, border: '1px solid rgba(239,100,73,0.5)', background: 'rgba(239,100,73,0.08)', color: '#EF6449', cursor: 'pointer', fontSize: 12, width: '100%' }}>
                Delete account permanently
              </button>
            </div>
          )}

          {/* Resume Tab */}
          {activeTab === 'resume' && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
              {currentResume && (
                <div style={{ background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.06)', borderRadius: 10, padding: 14 }}>
                  <div style={{ fontSize: 12, fontWeight: 500 }}>Current resume</div>
                  <div style={{ fontSize: 11, color: 'rgba(255,255,255,0.4)', marginTop: 4 }}>
                    {currentResume.parsed_data?.name || 'Unknown'} — {currentResume.parsed_data?.skills?.length || 0} skills — {currentResume.filename || 'text input'}
                  </div>
                </div>
              )}

              <div
                onClick={() => fileInputRef.current?.click()}
                style={{
                  border: `2px dashed ${uploadedFile ? '#7B6CF6' : 'rgba(255,255,255,0.1)'}`,
                  borderRadius: 10, padding: '16px', textAlign: 'center', cursor: 'pointer',
                  background: uploadedFile ? 'rgba(123,108,246,0.06)' : 'transparent',
                }}>
                <input ref={fileInputRef} type="file" accept=".pdf,.docx,.txt,.doc" onChange={handleFileSelect} style={{ display: 'none' }} />
                {uploadedFile ? (
                  <div style={{ fontSize: 12, color: '#7B6CF6' }}>📄 {uploadedFile.name} <span style={{ fontSize: 10, opacity: 0.5 }}>click to change</span></div>
                ) : (
                  <div>
                    <div style={{ fontSize: 12 }}>📄 Upload new resume</div>
                    <div style={{ fontSize: 10, color: 'rgba(255,255,255,0.3)', marginTop: 2 }}>PDF, DOCX, or TXT</div>
                  </div>
                )}
              </div>

              <div style={{ fontSize: 10, color: 'rgba(255,255,255,0.2)', textAlign: 'center' }}>— or paste text —</div>

              <textarea
                value={resumeText}
                onChange={e => { setResumeText(e.target.value); setUploadedFile(null) }}
                placeholder="Paste resume text..."
                disabled={!!uploadedFile}
                style={{ minHeight: 80, padding: '10px 12px', borderRadius: 8, border: '1px solid rgba(255,255,255,0.08)', background: 'rgba(255,255,255,0.03)', color: '#e8e6e0', fontSize: 11, outline: 'none', resize: 'vertical', fontFamily: 'inherit' }}
              />

              <button onClick={uploadResume} disabled={loading || (!uploadedFile && resumeText.trim().length < 50)}
                style={{ padding: '10px 0', borderRadius: 8, border: 'none', background: 'linear-gradient(135deg, #7B6CF6, #E966A0)', color: '#fff', cursor: 'pointer', fontSize: 13, fontWeight: 500, opacity: loading || (!uploadedFile && resumeText.trim().length < 50) ? 0.5 : 1 }}>
                {loading ? 'Parsing with Gemini...' : 'Upload and parse'}
              </button>
            </div>
          )}

          {/* Preferences Tab */}
          {activeTab === 'prefs' && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
              <div>
                <label style={{ fontSize: 10, color: 'rgba(255,255,255,0.35)', textTransform: 'uppercase', letterSpacing: 1, display: 'block', marginBottom: 4 }}>Target roles (comma-separated)</label>
                <input value={roles} onChange={e => setRoles(e.target.value)}
                  style={{ width: '100%', padding: '10px 12px', borderRadius: 8, border: '1px solid rgba(255,255,255,0.08)', background: 'rgba(255,255,255,0.03)', color: '#e8e6e0', fontSize: 13, outline: 'none', boxSizing: 'border-box' }} />
              </div>
              <div>
                <label style={{ fontSize: 10, color: 'rgba(255,255,255,0.35)', textTransform: 'uppercase', letterSpacing: 1, display: 'block', marginBottom: 4 }}>Preferred locations (comma-separated)</label>
                <input value={locations} onChange={e => setLocations(e.target.value)}
                  style={{ width: '100%', padding: '10px 12px', borderRadius: 8, border: '1px solid rgba(255,255,255,0.08)', background: 'rgba(255,255,255,0.03)', color: '#e8e6e0', fontSize: 13, outline: 'none', boxSizing: 'border-box' }} />
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
                <div>
                  <label style={{ fontSize: 10, color: 'rgba(255,255,255,0.35)', textTransform: 'uppercase', letterSpacing: 1, display: 'block', marginBottom: 4 }}>Salary min</label>
                  <input type="number" value={salaryMin} onChange={e => setSalaryMin(e.target.value)}
                    style={{ width: '100%', padding: '10px 12px', borderRadius: 8, border: '1px solid rgba(255,255,255,0.08)', background: 'rgba(255,255,255,0.03)', color: '#e8e6e0', fontSize: 13, outline: 'none', boxSizing: 'border-box' }} />
                </div>
                <div>
                  <label style={{ fontSize: 10, color: 'rgba(255,255,255,0.35)', textTransform: 'uppercase', letterSpacing: 1, display: 'block', marginBottom: 4 }}>Salary max</label>
                  <input type="number" value={salaryMax} onChange={e => setSalaryMax(e.target.value)}
                    style={{ width: '100%', padding: '10px 12px', borderRadius: 8, border: '1px solid rgba(255,255,255,0.08)', background: 'rgba(255,255,255,0.03)', color: '#e8e6e0', fontSize: 13, outline: 'none', boxSizing: 'border-box' }} />
                </div>
              </div>
              <div>
                <label style={{ fontSize: 10, color: 'rgba(255,255,255,0.35)', textTransform: 'uppercase', letterSpacing: 1, display: 'block', marginBottom: 4 }}>Remote preference</label>
                <div style={{ display: 'flex', gap: 6 }}>
                  {['any', 'remote', 'hybrid', 'onsite'].map(opt => (
                    <button key={opt} onClick={() => setRemotePref(opt)}
                      style={{
                        flex: 1, padding: '8px 0', borderRadius: 8, fontSize: 11, cursor: 'pointer',
                        border: remotePref === opt ? '1px solid #7B6CF6' : '1px solid rgba(255,255,255,0.08)',
                        background: remotePref === opt ? 'rgba(123,108,246,0.15)' : 'transparent',
                        color: remotePref === opt ? '#7B6CF6' : 'rgba(255,255,255,0.35)',
                      }}>{opt}</button>
                  ))}
                </div>
              </div>
              <button onClick={savePreferences} disabled={loading}
                style={{ padding: '10px 0', borderRadius: 8, border: 'none', background: 'linear-gradient(135deg, #7B6CF6, #E966A0)', color: '#fff', cursor: 'pointer', fontSize: 13, fontWeight: 500, opacity: loading ? 0.6 : 1 }}>
                {loading ? 'Saving...' : 'Save preferences'}
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
