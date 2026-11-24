import { useEffect, useRef, useState } from 'react'
import { FileViewer, PermissionDialog, RunPanel, ScenarioPicker } from './components/Panels.jsx'
import { useRun } from './useRun.js'

// Forked from the VAJRA demo UI (prior work, ImpactX'26).
// New for wHACKiest 2026: Rakshak branding, the permission dialog that must be approved before the
// protected run starts, the signed task token card and the hash-chained activity log.

const SPEEDS = { Slow: 1400, Normal: 750, Fast: 250 }

export default function App() {
  const [status, setStatus] = useState(null)
  const [scenarios, setScenarios] = useState([])
  const [selected, setSelected] = useState(null)
  const [provider, setProvider] = useState('scripted')
  const [model, setModel] = useState('')
  const [speed, setSpeed] = useState('Normal')
  const [paused, setPaused] = useState(false)
  const [loadError, setLoadError] = useState(null)
  const [asking, setAsking] = useState(false)
  const answer = useRef(null)
  const unprotected = useRun(SPEEDS[speed], paused)
  const protectedRun = useRun(SPEEDS[speed], paused)

  useEffect(() => {
    Promise.all([fetch('/api/status').then((r) => r.json()), fetch('/api/scenarios').then((r) => r.json())])
      .then(([st, sc]) => {
        setStatus(st)
        setScenarios(sc)
        setSelected(sc[0]?.id)
        if (st.groq_available) {
          setProvider('groq')
          setModel(st.groq_model)
        }
      })
      .catch(() => setLoadError('Cannot reach the demo backend. Start it with: python -m demo.backend'))
  }, [])

  const [query] = useState(() => new URLSearchParams(window.location.search))
  const scenario = scenarios.find((s) => s.id === selected)
  const busy = unprotected.phase === 'running' || protectedRun.phase === 'running' || asking
  const params = (mode) => ({ scenario: selected, mode, provider, ...(mode === 'protected' ? { approved: '1' } : {}) })
  const providerLabel = provider === 'groq' ? `Groq · ${model}` : 'offline gullible LLM'

  /** Shows the permission screen; resolves true only if the user presses Approve. */
  const askPermission = () =>
    new Promise((resolve) => {
      answer.current = resolve
      setAsking(true)
      if (query.get('approve') === 'auto') setTimeout(() => decide(true), 2500)
    })
  const decide = (ok) => {
    setAsking(false)
    answer.current?.(ok)
    answer.current = null
  }

  const runProtected = async () => {
    protectedRun.reset()
    if (await askPermission()) await protectedRun.start(params('protected'))
  }

  const selectScenario = (id) => {
    unprotected.reset()
    protectedRun.reset()
    setSelected(id)
  }
  const runBoth = async () => {
    protectedRun.reset()
    await unprotected.start(params('unprotected'))
    await runProtected()
  }

  // ?autorun=<scenario-id>&provider=scripted|groq&speed=Fast&approve=auto — hands-free replay for screen recording.
  useEffect(() => {
    const id = query.get('autorun')
    if (!id || !scenario || unprotected.phase !== 'idle') return
    const wantProvider = query.get('provider')
    const wantSpeed = query.get('speed')
    if (wantProvider && wantProvider !== provider) return setProvider(wantProvider)
    if (SPEEDS[wantSpeed] && wantSpeed !== speed) return setSpeed(wantSpeed)
    if (scenarios.some((s) => s.id === id) && id !== selected) return setSelected(id)
    query.delete('autorun')
    setTimeout(runBoth, 0)
  })

  const step = () => {
    unprotected.step()
    protectedRun.step()
  }

  if (loadError) return <div className="fatal">{loadError}</div>
  if (!scenario) return <div className="fatal muted">Loading…</div>

  return (
    <div className="app">
      <header className="hero">
        <div>
          <h1><span className="logo">🛡️</span> Rakshak</h1>
          <p className="tagline">
            Your everyday AI assistant, with nothing left to magic. Every action needs a <em>signed permission for
            this task only</em>, checked in code on top of the VAJRA zero-trust engine.
          </p>
        </div>
        <div className="controls">
          <label>
            LLM
            <select value={provider} onChange={(e) => setProvider(e.target.value)} disabled={busy}>
              <option value="groq" disabled={!status?.groq_available}>
                Groq (live){status?.groq_available ? '' : ': set GROQ_API_KEY'}
              </option>
              <option value="scripted">Offline: worst-case gullible LLM</option>
            </select>
          </label>
          <label>
            Replay speed
            <select value={speed} onChange={(e) => setSpeed(e.target.value)}>
              {Object.keys(SPEEDS).map((s) => <option key={s}>{s}</option>)}
            </select>
          </label>
          <button onClick={() => setPaused((p) => !p)}>{paused ? '▶ Resume' : '⏸ Pause'}</button>
          <button onClick={step} disabled={!paused}>⏭ Step</button>
        </div>
      </header>

      {scenarios.length > 1 && (
        <ScenarioPicker scenarios={scenarios} selected={selected} onSelect={selectScenario} disabled={busy} />
      )}

      <section className="scenario-detail">
        <div className="scenario-text">
          <h2>{scenario.title}</h2>
          <p className="attack-type">{scenario.attack}</p>
          <p>{scenario.summary}</p>
          <div className="task">
            <span className="task-label">User task</span>
            <p>“{scenario.task}”</p>
          </div>
          <button className="run-both" onClick={runBoth} disabled={busy}>
            ▶ Run both (plain assistant, then Rakshak)
          </button>
        </div>
        <FileViewer key={scenario.id} scenario={scenario} />
      </section>

      <div className="panels">
        <RunPanel
          mode="unprotected"
          run={unprotected}
          scenario={scenario}
          disabled={busy}
          providerLabel={providerLabel}
          onRun={() => unprotected.start(params('unprotected'))}
        />
        <RunPanel
          mode="protected"
          run={protectedRun}
          scenario={scenario}
          disabled={busy}
          providerLabel={providerLabel}
          onRun={runProtected}
        />
      </div>

      {asking && <PermissionDialog screen={scenario.permission_screen} onDecide={decide} />}

      <footer className="legend">
        <h3>How Rakshak keeps the assistant in line</h3>
        <ol>
          <li><b>You approve one task.</b> The permission screen lists, in plain words, what the assistant may do and what is blocked.</li>
          <li><b>Signed task token.</b> Your approval is minted into an HMAC-signed token: these actions, these people, this many times, for 15 minutes. It is verified on every call and revoked when the task ends.</li>
          <li><b>Checked in code, not by a model.</b> A hijacked AI can ask for anything; only calls inside your token reach your apps. The people you named are the only recipients allowed.</li>
          <li><b>Tamper-proof activity log.</b> Every allow and block is written in plain language, each entry chained to the previous one with SHA-256.</li>
          <li className="muted"><b>Prior work underneath:</b> VAJRA (ImpactX'26) labels outside data as untrusted, can withhold it behind opaque handles, and has a tool-less quarantine reader.</li>
        </ol>
      </footer>
    </div>
  )
}
