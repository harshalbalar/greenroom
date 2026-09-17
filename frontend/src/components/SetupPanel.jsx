import { useState } from 'react'
import { resumes, prefs } from '../api'

const SAMPLE_RESUME = `SARAH CHEN
san.chen@email.com | (555) 123-4567 | San Francisco, CA | github.com/sarahchen

SUMMARY
Full-stack software engineer with 4 years of experience building scalable web applications and data pipelines. Strong background in Python, React, and cloud infrastructure.

EXPERIENCE

Senior Software Engineer | DataFlow Inc. | Jan 2023 - Present
- Led backend team of 4 engineers rebuilding the data ingestion pipeline, reducing processing time by 65%
- Designed and implemented real-time analytics dashboard using React, D3.js, and WebSocket streaming
- Built CI/CD pipeline with GitHub Actions, reducing deployment time from 2 hours to 15 minutes
- Mentored 2 junior developers through structured code review and pair programming sessions

Software Engineer | CloudBase Systems | Jun 2021 - Dec 2022
- Developed RESTful APIs using FastAPI and PostgreSQL serving 500K daily requests
- Implemented event-driven architecture with Apache Kafka for inter-service communication
- Reduced API latency by 40% through Redis caching and query optimization

EDUCATION
B.S. Computer Science | UC Berkeley | 2020

SKILLS
Python, JavaScript/TypeScript, React, FastAPI, Django, Node.js, PostgreSQL, Redis, Apache Kafka, Docker, Kubernetes, AWS, GitHub Actions, CI/CD, REST APIs, WebSockets, GraphQL`

export default function SetupPanel({ onComplete }) {
  const [step, setStep] = useState(1)
  const [resumeText, setResumeText] = useState('')
  const [roles, setRoles] = useState('Senior Software Engineer, Senior Backend Engineer')
  const [locations, setLocations] = useState('Remote, San Francisco')
  const [salaryMin, setSalaryMin] = useState('150000')
  const [salaryMax, setSalaryMax] = useState('300000')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [parsedName, setParsedName] = useState('')
  const [parsedSkills, setParsedSkills] = useState(0)

  async function handleResumeUpload() {
    if (!resumeText.trim() || resumeText.trim().length < 50) {
      setError('Paste your resume text (at least 50 characters)')
      return
    }
    setLoading(true)
    setError('')
    try {
      const res = await resumes.upload(resumeText, 'resume.txt')
      const parsed = res.parsed_data || {}
      setParsedName(parsed.name || 'Unknown')
      setParsedSkills(parsed.skills?.length || 0)
      setStep(2)
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  async function handleSavePrefs() {
    setLoading(true)
    setError('')
    try {
      await prefs.save({
        target_roles: roles.split(',').map(r => r.trim()).filter(Boolean),
        locations: locations.split(',').map(l => l.trim()).filter(Boolean),
        salary_min: parseInt(salaryMin) || null,
        salary_max: parseInt(salaryMax) || null,
        remote_preference: 'any',
      })
      onComplete()
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div style={{
      position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.7)',
      display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 100,
    }}>
      <div style={{
        background: 'var(--surface)', border: '1px solid var(--border)',
        borderRadius: 16, padding: 28, width: 440, maxHeight: '80vh', overflowY: 'auto',
      }} className="fade-in">

        {step === 1 && (
          <>
            <div style={{ fontSize: 18, fontWeight: 600, marginBottom: 4 }}>
              Welcome to the <em style={{ color: 'var(--purple)', fontStyle: 'normal' }}>greenroom</em>
            </div>
            <div style={{ fontSize: 12, color: 'var(--muted)', marginBottom: 16 }}>
              First, let's get your resume. The crew needs it to find and prep your applications.
            </div>

            <label>Paste your resume text</label>
            <textarea
              value={resumeText}
              onChange={e => { setResumeText(e.target.value); setError('') }}
              placeholder="Paste your full resume here..."
              style={{ minHeight: 180, fontSize: 11, lineHeight: 1.5 }}
            />

            <button
              onClick={() => setResumeText(SAMPLE_RESUME)}
              style={{
                background: 'transparent', border: 'none', color: 'var(--purple)',
                fontSize: 10, cursor: 'pointer', padding: '4px 0', marginBottom: 12,
              }}
            >
              or load sample resume (Sarah Chen)
            </button>

            {error && <div className="form-error" style={{ marginBottom: 8 }}>{error}</div>}

            <button
              className="btn btn-primary"
              style={{ width: '100%', padding: 10, fontSize: 13 }}
              onClick={handleResumeUpload}
              disabled={loading}
            >
              {loading ? <><span className="spinner" style={{width:12,height:12}} /> parsing with gemini...</> : 'Upload and parse resume'}
            </button>
          </>
        )}

        {step === 2 && (
          <>
            <div style={{ fontSize: 18, fontWeight: 600, marginBottom: 4 }}>
              Resume parsed
            </div>
            <div style={{
              background: 'var(--card)', border: '1px solid var(--border)',
              borderRadius: 8, padding: 12, marginBottom: 16, fontSize: 12
            }}>
              <div><strong>{parsedName}</strong></div>
              <div style={{ color: 'var(--muted)', marginTop: 2 }}>{parsedSkills} skills detected</div>
            </div>

            <div style={{ fontSize: 12, color: 'var(--muted)', marginBottom: 14 }}>
              Now tell the crew what you're looking for.
            </div>

            <div className="form-group">
              <label>Target roles (comma-separated)</label>
              <input value={roles} onChange={e => setRoles(e.target.value)} />
            </div>

            <div className="form-group">
              <label>Preferred locations (comma-separated)</label>
              <input value={locations} onChange={e => setLocations(e.target.value)} />
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
              <div className="form-group">
                <label>Salary min ($)</label>
                <input type="number" value={salaryMin} onChange={e => setSalaryMin(e.target.value)} />
              </div>
              <div className="form-group">
                <label>Salary max ($)</label>
                <input type="number" value={salaryMax} onChange={e => setSalaryMax(e.target.value)} />
              </div>
            </div>

            {error && <div className="form-error" style={{ marginBottom: 8 }}>{error}</div>}

            <button
              className="btn btn-primary"
              style={{ width: '100%', padding: 10, fontSize: 13 }}
              onClick={handleSavePrefs}
              disabled={loading}
            >
              {loading ? <span className="spinner" style={{width:12,height:12}} /> : 'Save and start scanning'}
            </button>
          </>
        )}
      </div>
    </div>
  )
}
