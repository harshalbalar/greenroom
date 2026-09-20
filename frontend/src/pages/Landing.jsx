const CREW = [
  { emoji: '🔭', name: 'Scout', role: 'Scans job boards and finds matches based on your profile' },
  { emoji: '📊', name: 'Analyst', role: 'Scores every job against your resume across 5 dimensions' },
  { emoji: '🔍', name: 'Remy', role: 'Researches the company — funding, products, culture, news' },
  { emoji: '✂️', name: 'Taylor', role: 'Rewrites your resume to emphasize what each job needs' },
  { emoji: '✍️', name: 'Quinn', role: 'Writes personalized cover letters and interview prep' },
]

export default function Landing({ onGetStarted }) {

  return (
    <div style={{ background: '#0a0a14', color: '#e8e6e0', fontFamily: "'Inter',system-ui,sans-serif", minHeight: '100vh', overflowX: 'hidden', overflowY: 'auto', height: '100vh' }}>

      {/* Nav */}
      <nav style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '16px 40px', maxWidth: 1100, margin: '0 auto' }}>
        <div style={{ fontSize: 20, fontWeight: 700, letterSpacing: 0.5 }}>
          <span style={{ color: '#7B6CF6' }}>green</span>room
        </div>
        <div style={{ display: 'flex', gap: 8 }}>
          <button onClick={() => onGetStarted('login')} style={{ padding: '8px 20px', borderRadius: 8, border: '1px solid rgba(255,255,255,0.1)', background: 'transparent', color: '#e8e6e0', cursor: 'pointer', fontSize: 13 }}>
            Sign in
          </button>
          <button onClick={() => onGetStarted('register')} style={{ padding: '8px 20px', borderRadius: 8, border: 'none', background: '#7B6CF6', color: '#fff', cursor: 'pointer', fontSize: 13, fontWeight: 500 }}>
            Get started
          </button>
        </div>
      </nav>

      {/* Hero */}
      <section style={{ textAlign: 'center', padding: '80px 40px 60px', maxWidth: 800, margin: '0 auto' }}>
        <div style={{ display: 'inline-block', padding: '4px 14px', borderRadius: 20, background: 'rgba(123,108,246,0.12)', border: '1px solid rgba(123,108,246,0.2)', fontSize: 12, color: '#7B6CF6', marginBottom: 24 }}>
          Open-source AI job application agent
        </div>
        <h1 style={{ fontSize: 52, fontWeight: 700, lineHeight: 1.1, margin: '0 0 20px', letterSpacing: -1 }}>
          Stop spending hours<br />on every application
        </h1>
        <p style={{ fontSize: 18, color: 'rgba(255,255,255,0.5)', lineHeight: 1.6, maxWidth: 560, margin: '0 auto 36px' }}>
          Upload your resume. Set your preferences. Greenroom scans job boards, scores matches,
          tailors your resume, writes cover letters, and preps you for interviews — automatically.
        </p>
        <div style={{ display: 'flex', gap: 12, justifyContent: 'center' }}>
          <button onClick={() => onGetStarted('register')} style={{ padding: '14px 32px', borderRadius: 10, border: 'none', background: 'linear-gradient(135deg, #7B6CF6, #E966A0)', color: '#fff', cursor: 'pointer', fontSize: 15, fontWeight: 600, transition: 'transform 0.2s' }}>
            Get started — it's free
          </button>
          <button onClick={() => document.getElementById('how-it-works')?.scrollIntoView({ behavior: 'smooth' })} style={{ padding: '14px 32px', borderRadius: 10, border: '1px solid rgba(255,255,255,0.12)', background: 'transparent', color: '#e8e6e0', cursor: 'pointer', fontSize: 15 }}>
            See how it works
          </button>
        </div>
        <p style={{ fontSize: 12, color: 'rgba(255,255,255,0.25)', marginTop: 16 }}>
          100% free. Open source on GitHub.
        </p>
      </section>

      {/* Time saved bar */}
      <section style={{ maxWidth: 900, margin: '0 auto', padding: '0 40px 80px' }}>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 1, background: 'rgba(255,255,255,0.04)', borderRadius: 14, overflow: 'hidden' }}>
          {[
            { n: '30+', unit: 'min', label: 'saved per application' },
            { n: '5', unit: 'agents', label: 'working for you' },
            { n: '82%', unit: 'avg', label: 'match score accuracy' },
            { n: '2', unit: 'min', label: 'to get started' },
          ].map((s, i) => (
            <div key={i} style={{ padding: '28px 20px', textAlign: 'center', background: '#0d0b1e' }}>
              <div style={{ fontSize: 32, fontWeight: 700, color: ['#1D9E75','#7B6CF6','#EF9F27','#E966A0'][i] }}>
                {s.n}<span style={{ fontSize: 14, fontWeight: 400, opacity: 0.6, marginLeft: 3 }}>{s.unit}</span>
              </div>
              <div style={{ fontSize: 11, color: 'rgba(255,255,255,0.35)', marginTop: 4 }}>{s.label}</div>
            </div>
          ))}
        </div>
      </section>

      {/* How it works — the crew */}
      <section id="how-it-works" style={{ maxWidth: 900, margin: '0 auto', padding: '0 40px 80px' }}>
        <h2 style={{ fontSize: 14, color: 'rgba(255,255,255,0.3)', letterSpacing: 3, textTransform: 'uppercase', marginBottom: 32, textAlign: 'center' }}>
          Meet the crew
        </h2>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5, 1fr)', gap: 12 }}>
          {CREW.map((c, i) => (
            <div key={i} style={{ background: '#12102a', border: '1px solid rgba(255,255,255,0.06)', borderRadius: 14, padding: '24px 16px', textAlign: 'center', position: 'relative', overflow: 'hidden' }}>
              <div style={{ position: 'absolute', top: 0, left: 0, right: 0, height: 2, background: `linear-gradient(90deg, ${['#1D9E75','#EF9F27','#7B6CF6','#F06449','#E966A0'][i]}, transparent)` }} />
              <div style={{ fontSize: 28, marginBottom: 10 }}>{c.emoji}</div>
              <div style={{ fontSize: 14, fontWeight: 600, marginBottom: 4, color: ['#1D9E75','#EF9F27','#7B6CF6','#F06449','#E966A0'][i] }}>{c.name}</div>
              <div style={{ fontSize: 11, color: 'rgba(255,255,255,0.4)', lineHeight: 1.5 }}>{c.role}</div>
            </div>
          ))}
        </div>
      </section>

      {/* Pipeline flow */}
      <section style={{ maxWidth: 700, margin: '0 auto', padding: '0 40px 80px' }}>
        <h2 style={{ fontSize: 14, color: 'rgba(255,255,255,0.3)', letterSpacing: 3, textTransform: 'uppercase', marginBottom: 32, textAlign: 'center' }}>
          What you get for each application
        </h2>
        {[
          { icon: '📄', title: 'Tailored resume', desc: 'Rewritten to emphasize the skills and experience each specific job is looking for. ATS-optimized, downloadable as Word.' },
          { icon: '✉️', title: 'Personalized cover letter', desc: 'References the company\'s actual products, recent news, and culture — not a generic template.' },
          { icon: '🏢', title: 'Company research brief', desc: 'Funding, industry, recent news, products, and culture — everything you need to sound informed.' },
          { icon: '🎯', title: 'Interview prep', desc: 'Likely technical, behavioral, and company-specific questions with talking points tailored to your background.' },
        ].map((item, i) => (
          <div key={i} style={{ display: 'flex', gap: 16, padding: '20px 0', borderBottom: i < 3 ? '1px solid rgba(255,255,255,0.04)' : 'none' }}>
            <div style={{ fontSize: 22, flexShrink: 0, marginTop: 2 }}>{item.icon}</div>
            <div>
              <div style={{ fontSize: 15, fontWeight: 600, marginBottom: 4 }}>{item.title}</div>
              <div style={{ fontSize: 13, color: 'rgba(255,255,255,0.4)', lineHeight: 1.6 }}>{item.desc}</div>
            </div>
          </div>
        ))}
      </section>

      {/* Tech Stack */}
      <section style={{ maxWidth: 900, margin: '0 auto', padding: '0 40px 80px' }}>
        <h2 style={{ fontSize: 14, color: 'rgba(255,255,255,0.3)', letterSpacing: 3, textTransform: 'uppercase', marginBottom: 8, textAlign: 'center' }}>
          Built with
        </h2>
        <p style={{ fontSize: 14, color: 'rgba(255,255,255,0.35)', textAlign: 'center', marginBottom: 32 }}>
          Open source. Self-hostable. No paid tiers — every feature is free.
        </p>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 16 }}>
          {[
            { name: 'AI Pipeline', color: '#7B6CF6', items: ['Google Gemini 3.6 Flash', 'LangGraph state machine', 'Tavily web search', '6-node agent pipeline'] },
            { name: 'Backend', color: '#1D9E75', items: ['Python + FastAPI', 'PostgreSQL + SQLAlchemy', 'APScheduler automation', 'Resend email notifications'] },
            { name: 'Frontend', color: '#E966A0', items: ['React 18 + Vite', 'Theater-themed dark UI', 'Real-time crew activity', 'Kanban application board'] },
          ].map((t, i) => (
            <div key={i} style={{ background: '#12102a', border: '1px solid rgba(255,255,255,0.06)', borderRadius: 16, padding: '28px 24px' }}>
              <div style={{ fontSize: 18, fontWeight: 600, color: t.color, marginBottom: 16 }}>{t.name}</div>
              {t.items.map((f, fi) => (
                <div key={fi} style={{ display: 'flex', gap: 8, alignItems: 'center', padding: '6px 0', fontSize: 13, color: 'rgba(255,255,255,0.5)' }}>
                  <div style={{ width: 16, height: 16, borderRadius: '50%', background: `${t.color}18`, display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 10, color: t.color, flexShrink: 0 }}>✓</div>
                  {f}
                </div>
              ))}
            </div>
          ))}
        </div>
        <div style={{ textAlign: 'center', marginTop: 24 }}>
          <a href="https://github.com/harshalbalar/greenroom" target="_blank" rel="noopener noreferrer" style={{ display: 'inline-flex', alignItems: 'center', gap: 8, padding: '10px 24px', borderRadius: 10, border: '1px solid rgba(255,255,255,0.12)', background: 'transparent', color: 'rgba(255,255,255,0.5)', textDecoration: 'none', fontSize: 13 }}>
            ⭐ Star on GitHub
          </a>
        </div>
      </section>

      {/* Final CTA */}
      <section style={{ textAlign: 'center', padding: '60px 40px 80px' }}>
        <h2 style={{ fontSize: 32, fontWeight: 700, marginBottom: 12 }}>Ready to stop grinding?</h2>
        <p style={{ fontSize: 15, color: 'rgba(255,255,255,0.4)', marginBottom: 28 }}>
          The crew is standing by. Upload your resume and let them work.
        </p>
        <button onClick={() => onGetStarted('register')} style={{ padding: '14px 36px', borderRadius: 10, border: 'none', background: 'linear-gradient(135deg, #7B6CF6, #E966A0)', color: '#fff', cursor: 'pointer', fontSize: 15, fontWeight: 600 }}>
          Get started free
        </button>
      </section>

      {/* Footer */}
      <footer style={{ borderTop: '1px solid rgba(255,255,255,0.06)', padding: '24px 40px', display: 'flex', justifyContent: 'space-between', alignItems: 'center', maxWidth: 1100, margin: '0 auto' }}>
        <div style={{ fontSize: 13, color: 'rgba(255,255,255,0.2)' }}>
          <span style={{ color: '#7B6CF6' }}>green</span>room — your applications, prepped and ready
        </div>
        <div style={{ fontSize: 11, color: 'rgba(255,255,255,0.15)' }}>
          Built with LangGraph, Gemini, and FastAPI
        </div>
      </footer>
    </div>
  )
}