import { useState, useEffect, forwardRef, useImperativeHandle, useRef } from 'react'

const CREW = [
  { id: 'scout', name: 'Scout', role: 'finder', color: '#1D9E75', glow: 'rgba(29,158,117,0.3)', icon: '🔭' },
  { id: 'analyst', name: 'Analyst', role: 'scorer', color: '#EF9F27', glow: 'rgba(239,159,39,0.3)', icon: '📊' },
  { id: 'remy', name: 'Remy', role: 'researcher', color: '#7B6CF6', glow: 'rgba(123,108,246,0.3)', icon: '🔍' },
  { id: 'taylor', name: 'Taylor', role: 'tailor', color: '#F06449', glow: 'rgba(240,100,73,0.3)', icon: '✂️' },
  { id: 'quinn', name: 'Quinn', role: 'writer', color: '#E966A0', glow: 'rgba(233,102,160,0.3)', icon: '✍️' },
]

function Avatar({ crew, size = 56, active, speaking }) {
  return (
    <div style={{
      width: size, height: size, borderRadius: '50%',
      background: `linear-gradient(135deg, ${crew.color}, ${crew.color}88)`,
      display: 'flex', alignItems: 'center', justifyContent: 'center',
      fontSize: size * 0.4, position: 'relative',
      boxShadow: active ? `0 0 20px ${crew.glow}, 0 0 40px ${crew.glow}` : `0 4px 12px rgba(0,0,0,0.3)`,
      transition: 'box-shadow 0.4s, transform 0.3s',
      transform: speaking ? 'scale(1.08)' : active ? 'scale(1.02)' : 'scale(1)',
      animation: active ? 'float 2s ease-in-out infinite' : 'none',
    }}>
      {crew.icon}
    </div>
  )
}

const Backstage = forwardRef(function Backstage({ stats = {} }, ref) {
  const [bubbles, setBubbles] = useState({})
  const [activeSet, setActiveSet] = useState(new Set())
  const [docPos, setDocPos] = useState(-1)
  const [chatBubble, setChatBubble] = useState(null)
  const chatIdxRef = useRef(0)

  function say(i, msg, dur = 3500) {
    setBubbles(prev => ({ ...prev, [i]: msg }))
    setActiveSet(prev => new Set([...prev, i]))
    setTimeout(() => {
      setBubbles(prev => ({ ...prev, [i]: null }))
      setTimeout(() => setActiveSet(prev => { const s = new Set(prev); s.delete(i); return s }), 1000)
    }, dur)
  }

  function moveDoc(step) { setDocPos(step) }
  function hideDoc() { setDocPos(-1) }

  useImperativeHandle(ref, () => ({ say, moveDoc, hideDoc }))

  useEffect(() => {
    const iv = setInterval(() => {
      const j = stats.jobs || 0
      const w = stats.wings || 0
      const r = stats.ready || 0
      const a = stats.applied || 0

      const dynamic = [
        { from: 0, to: 1, msg: j ? `hey analyst, ${j} jobs tracked so far` : "hey analyst, no jobs yet — hit scan" },
        { from: 1, to: 0, msg: w ? `scout, ${w} worth applying — nice finds` : "scout, waiting for matches to score" },
        { from: 2, to: 4, msg: "quinn, checking latest company news for you" },
        { from: 4, to: 2, msg: r ? `thanks remy, ${r} letters ready for review` : "remy, no letters queued yet" },
        { from: 3, to: 4, msg: r ? "quinn, resume tailored and heading your way" : "quinn, standing by for the next job" },
        { from: 0, to: 1, msg: "analyst, should i run another scan?" },
        { from: 1, to: 3, msg: w > 0 ? "taylor, top match is looking strong — get ready" : "taylor, need more jobs to score" },
        { from: 4, to: 0, msg: a ? `scout, ${a} applications out there already` : "scout, ready to write when you are" },
        { from: 2, to: 3, msg: "taylor, found some good intel for the resume" },
        { from: 3, to: 2, msg: "thanks remy, weaving it into the skills section" },
      ]

      const chat = dynamic[chatIdxRef.current % dynamic.length]
      chatIdxRef.current++
      setChatBubble(chat)
      setActiveSet(prev => new Set([...prev, chat.from, chat.to]))
      setTimeout(() => {
        setChatBubble(null)
        setActiveSet(prev => { const s = new Set(prev); s.delete(chat.from); s.delete(chat.to); return s })
      }, 4500)
    }, 8000)
    return () => clearInterval(iv)
  }, [stats])

  const positions = ['10%', '25%', '45%', '65%', '82%']

  return (
    <div style={{
      height: '55vh', minHeight: 360, position: 'relative', overflow: 'hidden',
      background: 'linear-gradient(180deg, #08061a 0%, #0d0b1e 50%, #12102a 100%)',
    }}>
      {/* Ambient glow orbs */}
      <div style={{ position: 'absolute', top: '20%', left: '15%', width: 200, height: 200, borderRadius: '50%', background: 'radial-gradient(circle, rgba(29,158,117,0.06), transparent 70%)', pointerEvents: 'none' }} />
      <div style={{ position: 'absolute', top: '30%', right: '20%', width: 180, height: 180, borderRadius: '50%', background: 'radial-gradient(circle, rgba(123,108,246,0.06), transparent 70%)', pointerEvents: 'none' }} />
      <div style={{ position: 'absolute', bottom: '20%', left: '50%', width: 250, height: 250, borderRadius: '50%', background: 'radial-gradient(circle, rgba(233,102,160,0.04), transparent 70%)', pointerEvents: 'none' }} />

      {/* Floor line */}
      <div style={{ position: 'absolute', bottom: 90, left: '5%', right: '5%', height: 1, background: 'linear-gradient(90deg, transparent, rgba(255,255,255,0.06), transparent)' }} />

      {/* Connection lines between stations */}
      <svg style={{ position: 'absolute', bottom: 115, left: 0, right: 0, height: 4, overflow: 'visible', pointerEvents: 'none' }}>
        <line x1="12%" y1="2" x2="84%" y2="2" stroke="rgba(255,255,255,0.04)" strokeWidth="2" strokeDasharray="6 4" />
      </svg>

      {/* Document sprite */}
      {docPos >= 0 && (
        <div style={{
          position: 'absolute', bottom: 170, left: positions[docPos],
          transform: 'translateX(-50%)',
          width: 28, height: 34, background: '#fff', borderRadius: 4,
          boxShadow: '0 4px 16px rgba(123,108,246,0.4), 0 0 30px rgba(123,108,246,0.2)',
          transition: 'left 1.2s cubic-bezier(0.34, 1.56, 0.64, 1)', zIndex: 20,
          display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: 2,
        }}>
          <div style={{ width: 16, height: 2, background: '#bbb', borderRadius: 1 }} />
          <div style={{ width: 16, height: 2, background: '#ddd', borderRadius: 1 }} />
          <div style={{ width: 12, height: 2, background: '#ddd', borderRadius: 1 }} />
        </div>
      )}

      {/* Characters */}
      {CREW.map((c, i) => {
        const isSpeaker = !!bubbles[i] || chatBubble?.from === i
        const isReceiver = chatBubble?.to === i
        const isActive = activeSet.has(i)

        return (
          <div key={c.id} style={{
            position: 'absolute', bottom: 95, left: positions[i], transform: 'translateX(-50%)',
            textAlign: 'center', zIndex: 10,
          }}>
            {/* Speech bubble for speaker */}
            {isSpeaker && (
              <div style={{
                position: 'absolute', bottom: '100%', left: '50%', transform: 'translateX(-50%)',
                background: 'rgba(0,0,0,0.85)', backdropFilter: 'blur(8px)',
                border: `1px solid ${c.color}44`, padding: '6px 14px', fontSize: 12,
                whiteSpace: 'nowrap', borderRadius: '12px 12px 12px 4px', marginBottom: 10,
                color: '#e8e6e0', animation: 'bubblePop 0.3s ease-out', boxShadow: `0 4px 20px ${c.glow}`,
              }}>
                {bubbles[i] || chatBubble?.msg}
              </div>
            )}

            {/* Reaction for receiver */}
            {isReceiver && !isSpeaker && (
              <div style={{
                position: 'absolute', bottom: '100%', left: '50%', transform: 'translateX(-50%)',
                background: 'rgba(0,0,0,0.7)', border: `1px solid ${c.color}33`,
                padding: '4px 10px', fontSize: 14, borderRadius: '10px 10px 10px 4px',
                marginBottom: 10, animation: 'bubblePop 0.3s ease-out 0.3s both',
              }}>
                👋
              </div>
            )}

            <Avatar crew={c} active={isActive} speaking={isSpeaker} />
            <div style={{ fontSize: 13, fontWeight: 600, color: c.color, marginTop: 8, letterSpacing: 0.3 }}>{c.name}</div>
            <div style={{ fontSize: 9, color: 'rgba(255,255,255,0.25)', letterSpacing: 1.5, textTransform: 'uppercase' }}>{c.role}</div>
          </div>
        )
      })}

      {/* Top label */}
      <div style={{
        position: 'absolute', top: 12, left: '50%', transform: 'translateX(-50%)',
        fontSize: 10, color: 'rgba(255,255,255,0.12)', letterSpacing: 6, textTransform: 'uppercase',
      }}>the greenroom</div>

      <style>{`
        @keyframes float { 0%,100%{transform:scale(1.02) translateY(0)} 50%{transform:scale(1.02) translateY(-4px)} }
        @keyframes bubblePop { from{opacity:0;transform:translateX(-50%) scale(0.9) translateY(6px)} to{opacity:1;transform:translateX(-50%) scale(1) translateY(0)} }
      `}</style>
    </div>
  )
})

export default Backstage
export { CREW }