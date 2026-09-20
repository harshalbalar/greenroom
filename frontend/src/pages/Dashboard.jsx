import { useState, useEffect, useRef } from 'react'
import { jobs, apps, tasks, resumes, prefs } from '../api'
import Backstage, { CREW } from '../components/Backstage'
import SetupPanel from '../components/SetupPanel'
import SettingsPanel from '../components/SettingsPanel'

const COLORS = CREW.map(c => c.color)
const NAMES = CREW.map(c => c.id)

const TEMPLATES = [
  { id: 'modern', name: 'Modern', desc: 'Calibri, blue accents — tech & startups', color: '#3B5998' },
  { id: 'classic', name: 'Classic', desc: 'Georgia, traditional — banking & enterprise', color: '#8B6914' },
  { id: 'minimal', name: 'Minimal', desc: 'Arial, clean whitespace — design & creative', color: '#888' },
]

function agentFor(msg) {
  if (!msg) return 0
  const m = msg.toLowerCase()
  if (m.startsWith('scout')) return 0
  if (m.startsWith('analyst')) return 1
  if (m.startsWith('remy')) return 2
  if (m.startsWith('taylor')) return 3
  if (m.startsWith('quinn')) return 4
  if (m.includes('scan') || m.includes('found')) return 0
  if (m.includes('scor')) return 1
  if (m.includes('research')) return 2
  if (m.includes('tailor')) return 3
  if (m.includes('cover') || m.includes('interview')) return 4
  return 0
}

export default function Dashboard({ user, onLogout }) {
  const [jobList, setJobList] = useState([])
  const [appList, setAppList] = useState([])
  const [statData, setStatData] = useState({})
  const [feed, setFeed] = useState([])
  const [selJob, setSelJob] = useState(null)
  const [selAppId, setSelAppId] = useState(null)
  const [tab, setTab] = useState('resume')
  const [scanning, setScanning] = useState(false)
  const [prepping, setPrepping] = useState(false)
  const [hasResume, setHasResume] = useState(false)
  const [hasPrefs, setHasPrefs] = useState(false)
  const [showSetup, setShowSetup] = useState(false)
  const [scanProg, setScanProg] = useState('')
  const [copied, setCopied] = useState('')
  const [showSettings, setShowSettings] = useState(false)
  const [selectedTemplate, setSelectedTemplate] = useState('modern')
  const [showTemplatePicker, setShowTemplatePicker] = useState(false)
  const bsRef = useRef()
  const lastProgRef = useRef('')
  const lastFeedRef = useRef('')
  const feedKeys = useRef(new Set())

  useEffect(() => { load() }, [])

  async function load() {
    try {
      const [j, a, s] = await Promise.all([jobs.list('limit=50').catch(() => []), apps.list().catch(() => []), apps.stats().catch(() => ({}))])
      setJobList(j); setAppList(a); setStatData(s)
      try { await resumes.active(); setHasResume(true) } catch { setHasResume(false) }
      try { await prefs.get(); setHasPrefs(true) } catch { setHasPrefs(false) }
      setShowSetup(true)
    } catch {}
  }

  function addFeed(agent, text) {
    let clean = text.replace(/^(scout|analyst|remy|taylor|quinn)[:\s]+/i, '')
    if (feedKeys.current.has(clean)) return
    feedKeys.current.add(clean)
    setFeed(prev => [{
      agent,
      text: clean,
      time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    }, ...prev].slice(0, 10))
  }

  async function copyToClipboard(text, label) {
    try {
      await navigator.clipboard.writeText(text)
      setCopied(label)
      setTimeout(() => setCopied(''), 2000)
    } catch {}
  }

  function downloadDoc(appId, docType) {
    const token = localStorage.getItem('token')
    const url = `/api/applications/${appId}/download?doc_type=${docType}&template=${selectedTemplate}`
    fetch(url, { headers: { Authorization: `Bearer ${token}` } })
      .then(res => {
        if (!res.ok) throw new Error('Download failed')
        return res.blob()
      })
      .then(blob => {
        const a = document.createElement('a')
        a.href = URL.createObjectURL(blob)
        a.download = docType === 'bundle'
          ? `Greenroom_${selJob?.company || 'Application'}.zip`
          : `${docType}_${selJob?.company || 'document'}.docx`
        a.click()
        URL.revokeObjectURL(a.href)
      })
      .catch(e => console.error(e))
  }

  function pickJob(j) { setSelJob(j); setSelAppId(null); setTab('resume') }
  function pickApp(a) { setSelJob({ id: a.job_id, title: a.job_title, company: a.job_company, url: a.job_url }); setSelAppId(a.id); setTab('resume') }

  const selApp = selAppId ? appList.find(a => a.id === selAppId) : selJob ? appList.find(a => a.job_id === selJob.id) : null

  function content(t) {
    if (!selApp) return ''
    if (t === 'resume') return selApp.tailored_resume || ''
    if (t === 'letter') return selApp.cover_letter || ''
    if (t === 'prep') return selApp.interview_prep || ''
    if (t === 'research') {
      const r = selApp.company_research
      if (!r || typeof r !== 'object') return ''
      return Object.entries(r).filter(([,v]) => v && v !== 'Not found' && v !== '' && !(Array.isArray(v) && !v.length))
        .map(([k,v]) => `${k.replace(/_/g,' ').toUpperCase()}\n${Array.isArray(v) ? v.join('\n') : v}`).join('\n\n')
    }
    return ''
  }

  async function scan() {
    setScanning(true); setScanProg('starting...'); feedKeys.current.clear(); lastProgRef.current = ''
    addFeed(0, 'scanning all job sources...')
    bsRef.current?.say(0, 'scanning!', 3000)
    try {
      const r = await jobs.scan(false); const tid = r.task_id
      if (!tid) { setScanning(false); return }
      const p = setInterval(async () => {
        try {
          const s = await tasks.status(tid)
          if (s.progress && s.progress !== lastProgRef.current) { lastProgRef.current = s.progress; setScanProg(s.progress.slice(0,28)); bsRef.current?.say(agentFor(s.progress), s.progress.slice(0,35), 2500); addFeed(agentFor(s.progress), s.progress) }
          if (s.status === 'completed') { clearInterval(p); const x = s.result||{}; addFeed(0, `found ${x.new_jobs||0} new jobs!`); bsRef.current?.say(0, `${x.new_jobs||0} new jobs!`, 3000); setScanning(false); setScanProg(''); lastProgRef.current = ''; await load() }
          if (s.status === 'failed') { clearInterval(p); addFeed(0, 'scan failed'); setScanning(false); setScanProg('') }
        } catch {}
      }, 2500)
    } catch (e) { addFeed(0, e.message); setScanning(false); setScanProg('') }
  }

  async function prep(jobId) {
    const job = jobList.find(j => j.id === jobId)
    if (!job || appList.some(a => a.job_id === jobId)) { addFeed(0, 'already prepped'); return }
    setPrepping(true); feedKeys.current.clear(); lastProgRef.current = ''
    addFeed(0, `prepping ${job.title} @ ${job.company}`)
    bsRef.current?.say(0, `prepping ${job.company}`, 3000)
    bsRef.current?.moveDoc(0)
    try {
      const r = await apps.create(jobId, true); const tid = r.task_id
      if (!tid) { addFeed(0, r.message || 'error'); setPrepping(false); bsRef.current?.hideDoc(); return }
      await load()
      const p = setInterval(async () => {
        try {
          const s = await tasks.status(tid)
          if (s.progress && s.progress !== lastProgRef.current) {
            lastProgRef.current = s.progress; const a = agentFor(s.progress)
            bsRef.current?.say(a, s.progress.slice(0,35), 2500)
            addFeed(a, s.progress)
            bsRef.current?.moveDoc(a)
          }
          if (s.status === 'completed') { clearInterval(p); bsRef.current?.hideDoc(); bsRef.current?.say(4, 'prepped and ready!', 3000); addFeed(4, `${job.company} application ready!`); setPrepping(false); lastProgRef.current = ''; await load() }
          if (s.status === 'failed') { clearInterval(p); bsRef.current?.hideDoc(); addFeed(0, 'prep failed'); setPrepping(false) }
        } catch {}
      }, 3000)
    } catch (e) { addFeed(0, e.message); setPrepping(false); bsRef.current?.hideDoc() }
  }

  const wings = jobList.filter(j => (j.is_worth_applying || j.is_worth_applying === null) && !appList.some(a => a.job_id === j.id)).slice(0, 8)
  const rehearsal = appList.filter(a => a.status === 'queued' || a.status === 'processing')
  const ready = appList.filter(a => a.status === 'ready')
  const onStage = appList.filter(a => ['applied','interviewing','offered','rejected','ghosted'].includes(a.status))
  const tabs = [['resume','Resume'],['letter','Cover letter'],['prep','Interview prep'],['research','Research']]

  const statCards = [
    { n: jobList.length, l: 'discovered', c: '#1D9E75' },
    { n: wings.length, l: 'worth applying', c: '#7B6CF6' },
    { n: ready.length, l: 'ready to send', c: '#EF9F27' },
    { n: statData.applied||0, l: 'applied', c: '#5DCF5D' },
    { n: statData.interviewing||0, l: 'interviews', c: '#F06449' },
  ]

  const currentTpl = TEMPLATES.find(t => t.id === selectedTemplate)

  return (
    <div style={{ height: '100vh', display: 'flex', flexDirection: 'column', background: '#0a0a14', color: '#e8e6e0', fontFamily: "'Inter',system-ui,sans-serif", fontSize: 13 }}>
      {/* Topbar */}
      <div style={{ display: 'flex', alignItems: 'center', padding: '0 20px', height: 52, borderBottom: '1px solid rgba(255,255,255,0.06)', flexShrink: 0, background: '#0d0b1e' }}>
        <div style={{ fontSize: 18, fontWeight: 700, letterSpacing: 0.5 }}><span style={{ color: '#7B6CF6' }}>green</span>room</div>
        <div style={{ display: 'flex', gap: 8, marginLeft: 20 }}>
          <button onClick={scan} disabled={scanning} style={{ padding: '6px 16px', borderRadius: 8, border: '1px solid rgba(255,255,255,0.1)', background: 'transparent', color: '#e8e6e0', cursor: 'pointer', fontSize: 12, display: 'flex', alignItems: 'center', gap: 6, transition: 'all 0.2s' }}>
            {scanning ? <><span style={{ width: 10, height: 10, border: '2px solid rgba(255,255,255,0.2)', borderTopColor: '#7B6CF6', borderRadius: '50%', animation: 'spin 0.6s linear infinite', display: 'inline-block' }} />{scanProg || 'scanning...'}</> : '🔭 scan jobs'}
          </button>
          <button onClick={() => wings[0] && prep(wings[0].id)} disabled={prepping || !wings.length} style={{ padding: '6px 16px', borderRadius: 8, border: 'none', background: 'linear-gradient(135deg, #7B6CF6, #E966A0)', color: '#fff', cursor: 'pointer', fontSize: 12, fontWeight: 500, display: 'flex', alignItems: 'center', gap: 6, transition: 'all 0.2s', opacity: prepping || !wings.length ? 0.5 : 1 }}>
            {prepping ? 'prepping...' : '✨ prep next job'}
          </button>
        </div>
        <div style={{ flex: 1 }} />
        <div onClick={() => setShowSettings(true)} title="Settings" style={{ width: 32, height: 32, borderRadius: '50%', background: 'linear-gradient(135deg, #7B6CF6, #E966A0)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 12, fontWeight: 600, cursor: 'pointer' }}>{user.name?.slice(0,2).toUpperCase()}</div>
      </div>

      {/* Content */}
      <div style={{ flex: 1, overflowY: 'auto' }}>
        <Backstage ref={bsRef} stats={{ jobs: jobList.length, wings: wings.length, ready: ready.length, applied: statData.applied || 0 }} />

        {/* Stats */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5,1fr)', gap: 10, padding: '16px 20px' }}>
          {statCards.map((s,i) => (
            <div key={i} style={{ background: '#12102a', border: '1px solid rgba(255,255,255,0.06)', borderRadius: 12, padding: '14px 16px', position: 'relative', overflow: 'hidden' }}>
              <div style={{ position: 'absolute', top: 0, left: 0, right: 0, height: 2, background: `linear-gradient(90deg, ${s.c}, transparent)` }} />
              <div style={{ fontSize: 28, fontWeight: 700, color: s.c, lineHeight: 1, textShadow: `0 0 20px ${s.c}44` }}>{s.n}</div>
              <div style={{ fontSize: 9, color: 'rgba(255,255,255,0.35)', marginTop: 4, textTransform: 'uppercase', letterSpacing: 1 }}>{s.l}</div>
            </div>
          ))}
        </div>

        {/* Kanban */}
        <div style={{ padding: '0 20px', display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 10 }}>
          <div style={{ fontSize: 10, color: 'rgba(255,255,255,0.25)', letterSpacing: 2, textTransform: 'uppercase' }}>production board</div>
          <button onClick={load} style={{ fontSize: 10, padding: '3px 10px', borderRadius: 6, border: '1px solid rgba(255,255,255,0.08)', background: 'transparent', color: 'rgba(255,255,255,0.4)', cursor: 'pointer' }}>refresh</button>
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4,1fr)', gap: 10, padding: '0 20px 16px' }}>
          {[
            { label: 'in the wings', color: '#1D9E75', items: wings, type: 'job' },
            { label: 'in rehearsal', color: '#7B6CF6', items: rehearsal, type: 'app' },
            { label: 'ready for stage', color: '#EF9F27', items: ready, type: 'app' },
            { label: 'on stage', color: '#5DCF5D', items: onStage, type: 'app' },
          ].map((col, ci) => (
            <div key={ci} style={{ background: '#12102a', border: '1px solid rgba(255,255,255,0.06)', borderRadius: 12, padding: 10, minHeight: 120 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 6, paddingBottom: 8, marginBottom: 8, borderBottom: '1px solid rgba(255,255,255,0.04)', fontSize: 10, color: 'rgba(255,255,255,0.3)', letterSpacing: 0.5, textTransform: 'uppercase' }}>
                <div style={{ width: 6, height: 6, borderRadius: '50%', background: col.color }} />
                {col.label}
                <span style={{ marginLeft: 'auto', background: 'rgba(255,255,255,0.05)', padding: '1px 6px', borderRadius: 8, fontSize: 9 }}>{col.items.length}</span>
              </div>
              {col.items.map(item => {
                const isApp = col.type === 'app'
                const id = isApp ? item.id : item.id
                const title = isApp ? item.job_title : item.title
                const company = isApp ? item.job_company : item.company
                const selected = isApp ? selAppId === item.id : selJob?.id === item.id
                return (
                  <div key={id} onClick={() => isApp ? pickApp(item) : pickJob(item)} style={{
                    background: selected ? `${col.color}15` : 'rgba(255,255,255,0.02)',
                    border: `1px solid ${selected ? col.color + '66' : 'rgba(255,255,255,0.04)'}`,
                    borderRadius: 8, padding: '8px 10px', marginBottom: 6, cursor: 'pointer', transition: 'all 0.15s',
                  }}>
                    {!isApp && item.overall_score && <span style={{ float: 'right', fontSize: 10, padding: '1px 6px', borderRadius: 6, background: `${col.color}22`, color: col.color, fontWeight: 600 }}>{item.overall_score}</span>}
                    <div style={{ fontSize: 12, fontWeight: 500 }}>{title}</div>
                    <div style={{ fontSize: 10, color: 'rgba(255,255,255,0.3)', marginTop: 2 }}>
                      {company}
                      {!isApp && item.source && <span style={{ marginLeft: 6, opacity: 0.5 }}>via {item.source}</span>}
                      {isApp && item.status && !['queued','processing','ready'].includes(item.status) && <span style={{ marginLeft: 6, color: item.status === 'applied' ? '#5DCF5D' : item.status === 'interviewing' ? '#EF9F27' : item.status === 'rejected' ? '#E24B4A' : 'rgba(255,255,255,0.2)' }}>{item.status}</span>}
                    </div>
                    {!isApp && item.url && (
                      <a href={item.url} target="_blank" rel="noopener noreferrer" onClick={e => e.stopPropagation()}
                         style={{ fontSize: 10, color: '#7B6CF6', textDecoration: 'none', marginTop: 3, display: 'inline-block' }}>Apply →</a>
                    )}
                  </div>
                )
              })}
              {!col.items.length && (
                <div style={{ fontSize: 11, color: 'rgba(255,255,255,0.15)', padding: 12, textAlign: 'center' }}>
                  {ci === 0 ? 'scan to find jobs' : ci === 1 && prepping ? 'crew is working...' : ''}
                </div>
              )}
            </div>
          ))}
        </div>

        {/* Detail panel */}
        {selJob && (
          <div style={{ padding: '0 20px 20px', animation: 'fadeIn 0.3s' }}>
            <div style={{ background: '#12102a', border: '1px solid rgba(255,255,255,0.06)', borderRadius: 16, padding: 24 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 16 }}>
                <div>
                  <div style={{ fontSize: 22, fontWeight: 700 }}>{selJob.title}</div>
                  <div style={{ fontSize: 14, color: 'rgba(255,255,255,0.35)', marginTop: 4 }}>
                    {selJob.company}
                    {selApp?.score_data?.overall_score ? <span style={{ marginLeft: 8, color: '#7B6CF6', fontWeight: 600 }}>{selApp.score_data.overall_score}/100 match</span> : selJob.overall_score ? <span style={{ marginLeft: 8, color: '#1D9E75', fontWeight: 600 }}>{selJob.overall_score}/100 match</span> : ''}
                    {selJob.source && <span style={{ marginLeft: 8, opacity: 0.4, fontSize: 12 }}>via {selJob.source}</span>}
                  </div>
                  {selJob.url && (
                    <a href={selJob.url} target="_blank" rel="noopener noreferrer"
                       style={{ fontSize: 12, color: '#7B6CF6', textDecoration: 'none', marginTop: 6, display: 'inline-block' }}>🔗 View original posting →</a>
                  )}
                </div>
                <div style={{ display: 'flex', gap: 8 }}>
                  {!appList.some(a => a.job_id === selJob.id) && <button onClick={() => prep(selJob.id)} disabled={prepping} style={{ padding: '8px 18px', borderRadius: 8, border: 'none', background: 'linear-gradient(135deg, #7B6CF6, #E966A0)', color: '#fff', cursor: 'pointer', fontSize: 12, fontWeight: 500 }}>✨ prep this job</button>}
                  {selApp?.status === 'ready' && (
                    <>
                      {selJob.url && <a href={selJob.url} target="_blank" rel="noopener noreferrer" style={{ padding: '8px 18px', borderRadius: 8, border: '1px solid #7B6CF6', background: 'transparent', color: '#7B6CF6', cursor: 'pointer', fontSize: 12, textDecoration: 'none', display: 'flex', alignItems: 'center' }}>apply now →</a>}
                      <button onClick={async () => { await apps.update(selApp.id, { status: 'applied' }); addFeed(4, 'marked applied!'); load() }} style={{ padding: '8px 18px', borderRadius: 8, border: '1px solid #5DCF5D', background: 'transparent', color: '#5DCF5D', cursor: 'pointer', fontSize: 12 }}>mark applied</button>
                    </>
                  )}
                  {selApp?.status === 'applied' && <button onClick={async () => { await apps.update(selApp.id, { status: 'interviewing' }); load() }} style={{ padding: '8px 18px', borderRadius: 8, border: '1px solid #EF9F27', background: 'transparent', color: '#EF9F27', cursor: 'pointer', fontSize: 12 }}>got interview!</button>}
                  {/* Re-prep: regenerate content */}
                  {selApp && selApp.status === 'ready' && (
                    <button onClick={async () => {
                      if (!window.confirm('Regenerate all content for this application?')) return
                      const r = await apps.reprep(selApp.id)
                      if (r.task_id) {
                        addFeed(0, `re-prepping ${selJob.company}...`)
                        // Poll like normal prep
                        const p = setInterval(async () => {
                          try {
                            const s = await tasks.status(r.task_id)
                            if (s.status === 'completed') { clearInterval(p); addFeed(4, 're-prep done!'); await load() }
                            if (s.status === 'failed') { clearInterval(p); addFeed(0, 're-prep failed') }
                          } catch {}
                        }, 3000)
                      }
                    }} style={{ padding: '8px 14px', borderRadius: 8, border: '1px solid rgba(123,108,246,0.3)', background: 'transparent', color: '#7B6CF6', cursor: 'pointer', fontSize: 11 }}>
                      🔄 re-prep
                    </button>
                  )}
 
                  {/* Delete application */}
                  {selApp && (
                    <button onClick={async () => {
                      if (!window.confirm(`Delete ${selJob.title} application? This removes all prepped content.`)) return
                      await apps.delete(selApp.id)
                      addFeed(0, `deleted ${selJob.company} application`)
                      setSelJob(null)
                      setSelAppId(null)
                      await load()
                    }} style={{ padding: '8px 14px', borderRadius: 8, border: '1px solid rgba(239,100,73,0.3)', background: 'transparent', color: '#EF6449', cursor: 'pointer', fontSize: 11 }}>
                      🗑
                    </button>
                  )}
                  <button onClick={() => setSelJob(null)} style={{ padding: '8px 12px', borderRadius: 8, border: '1px solid rgba(255,255,255,0.08)', background: 'transparent', color: 'rgba(255,255,255,0.3)', cursor: 'pointer', fontSize: 12 }}>✕</button>
                </div>
              </div>
              <div style={{ display: 'flex', gap: 0, marginBottom: 16, background: 'rgba(255,255,255,0.03)', borderRadius: 10, padding: 3, maxWidth: 500 }}>
                {tabs.map(([key, label]) => (
                  <button key={key} onClick={() => setTab(key)} style={{ flex: 1, padding: '8px 0', borderRadius: 8, border: 'none', fontSize: 11, fontWeight: tab === key ? 600 : 400, cursor: 'pointer', transition: 'all 0.15s', background: tab === key ? 'linear-gradient(135deg, #7B6CF6, #E966A0)' : 'transparent', color: tab === key ? '#fff' : 'rgba(255,255,255,0.35)' }}>{label}</button>
                ))}
              </div>

              {/* Action bar */}
              {content(tab) && (
                <div style={{ display: 'flex', gap: 6, marginBottom: 8, justifyContent: 'flex-end', alignItems: 'center', flexWrap: 'wrap' }}>
                  {/* Template selector */}
                  {selApp && (
                    <div style={{ position: 'relative', marginRight: 'auto' }}>
                      <button onClick={() => setShowTemplatePicker(!showTemplatePicker)}
                        style={{ padding: '5px 12px', borderRadius: 6, fontSize: 11, border: '1px solid rgba(255,255,255,0.1)', background: 'rgba(255,255,255,0.03)', color: 'rgba(255,255,255,0.5)', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 5 }}>
                        <span style={{ width: 8, height: 8, borderRadius: '50%', background: currentTpl?.color || '#7B6CF6' }} />
                        {currentTpl?.name || 'Modern'} template
                        <span style={{ fontSize: 8, opacity: 0.5 }}>▼</span>
                      </button>
                      {showTemplatePicker && (
                        <div style={{ position: 'absolute', top: '100%', left: 0, marginTop: 4, background: '#1a1830', border: '1px solid rgba(255,255,255,0.1)', borderRadius: 10, padding: 6, zIndex: 50, width: 240, boxShadow: '0 8px 24px rgba(0,0,0,0.4)' }}>
                          {TEMPLATES.map(t => (
                            <div key={t.id} onClick={() => { setSelectedTemplate(t.id); setShowTemplatePicker(false) }}
                              style={{
                                padding: '10px 12px', borderRadius: 8, cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 10,
                                background: selectedTemplate === t.id ? 'rgba(123,108,246,0.12)' : 'transparent',
                                border: selectedTemplate === t.id ? '1px solid rgba(123,108,246,0.3)' : '1px solid transparent',
                              }}>
                              <span style={{ width: 10, height: 10, borderRadius: '50%', background: t.color, flexShrink: 0 }} />
                              <div>
                                <div style={{ fontSize: 12, fontWeight: 500, color: selectedTemplate === t.id ? '#e8e6e0' : 'rgba(255,255,255,0.5)' }}>{t.name}</div>
                                <div style={{ fontSize: 9, color: 'rgba(255,255,255,0.25)', marginTop: 1 }}>{t.desc}</div>
                              </div>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  )}

                  <button onClick={() => copyToClipboard(content(tab), tab)}
                    style={{ padding: '5px 12px', borderRadius: 6, fontSize: 11, border: '1px solid rgba(255,255,255,0.1)', background: copied === tab ? 'rgba(93,207,93,0.15)' : 'transparent', color: copied === tab ? '#5DCF5D' : 'rgba(255,255,255,0.4)', cursor: 'pointer', transition: 'all 0.2s' }}>
                    {copied === tab ? '✓ copied' : '📋 copy'}
                  </button>
                  {selApp && (tab === 'resume' || tab === 'letter') && (
                    <button onClick={() => downloadDoc(selApp.id, tab === 'resume' ? 'resume' : 'cover_letter')}
                      style={{ padding: '5px 12px', borderRadius: 6, fontSize: 11, border: '1px solid rgba(123,108,246,0.3)', background: 'rgba(123,108,246,0.08)', color: '#7B6CF6', cursor: 'pointer', transition: 'all 0.2s' }}>
                      📄 download .docx
                    </button>
                  )}
                  {selApp && (
                    <button onClick={() => downloadDoc(selApp.id, 'bundle')}
                      style={{ padding: '5px 12px', borderRadius: 6, fontSize: 11, border: '1px solid rgba(233,102,160,0.3)', background: 'rgba(233,102,160,0.08)', color: '#E966A0', cursor: 'pointer', transition: 'all 0.2s' }}>
                      📦 download all (.zip)
                    </button>
                  )}
                </div>
              )}

              {/* Content */}
              <div style={{ background: 'rgba(0,0,0,0.3)', border: '1px solid rgba(255,255,255,0.04)', borderRadius: 12, padding: 20, minHeight: 200, maxHeight: 450, overflowY: 'auto', fontSize: 13, lineHeight: 1.8, color: 'rgba(255,255,255,0.55)', whiteSpace: 'pre-wrap' }}>
                {content(tab) || (selApp ? '⏳ Content empty — Gemini was rate limited during prep. Enable billing at aistudio.google.com or wait for quota reset, then re-prep this job.' : 'Click "prep this job" to generate a tailored resume, cover letter, interview prep, and company research.')}
              </div>
            </div>
          </div>
        )}

        {/* Crew feed */}
        <div style={{ padding: '0 20px 24px' }}>
          <div style={{ fontSize: 10, color: 'rgba(255,255,255,0.25)', letterSpacing: 2, textTransform: 'uppercase', marginBottom: 8 }}>crew activity</div>
          {feed.length === 0 && <div style={{ fontSize: 11, color: 'rgba(255,255,255,0.15)', padding: 8 }}>The crew is standing by. Scan or prep a job to see activity.</div>}
          {feed.map((f, i) => (
            <div key={`${f.agent}-${i}`} style={{ display: 'flex', gap: 10, alignItems: 'flex-start', padding: '7px 0', borderBottom: '1px solid rgba(255,255,255,0.03)', animation: 'fadeIn 0.3s' }}>
              <div style={{ width: 8, height: 8, borderRadius: '50%', background: COLORS[f.agent], flexShrink: 0, marginTop: 5, boxShadow: `0 0 6px ${COLORS[f.agent]}44` }} />
              <div style={{ fontSize: 12, color: 'rgba(255,255,255,0.45)', lineHeight: 1.5 }}>
                <strong style={{ color: COLORS[f.agent], fontWeight: 600 }}>{NAMES[f.agent]}</strong> {f.text}
              </div>
              <div style={{ fontSize: 9, color: 'rgba(255,255,255,0.15)', marginLeft: 'auto', flexShrink: 0 }}>{f.time}</div>
            </div>
          ))}
        </div>
      </div>

      {showSetup && (!hasResume || !hasPrefs) && <SetupPanel onComplete={() => { setShowSetup(false); setHasResume(true); setHasPrefs(true); load() }} />}

      {showSettings && (
        <SettingsPanel user={user} onClose={() => setShowSettings(false)}
          onUpdate={(updatedUser) => { if (updatedUser) { user.name = updatedUser.name; user.email = updatedUser.email }; load() }} />
      )}

      <style>{`
        @keyframes spin { to { transform: rotate(360deg) } }
        @keyframes fadeIn { from { opacity: 0; transform: translateY(6px) } to { opacity: 1; transform: none } }
        button:hover { filter: brightness(1.1) }
        *::-webkit-scrollbar { width: 6px }
        *::-webkit-scrollbar-track { background: transparent }
        *::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.08); border-radius: 3px }
      `}</style>
    </div>
  )
}