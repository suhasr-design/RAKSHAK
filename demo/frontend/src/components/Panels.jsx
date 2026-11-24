import { useEffect, useRef, useState } from 'react'
import { Doc } from '../highlight.jsx'
import { OrchestrationDiagram } from './OrchestrationDiagram.jsx'
import { Timeline } from './Timeline.jsx'

// Forked from the VAJRA demo (prior work). New: PermissionDialog, TokenCard, ActivityLog,
// recipient checks against the user's own request.

const isAllowed = (to, scenario) =>
  (scenario.allowed_recipients?.length ? scenario.allowed_recipients : [scenario.user_email])
    .map((a) => a.toLowerCase())
    .includes(to.trim().toLowerCase())

export function ScenarioPicker({ scenarios, selected, onSelect, disabled }) {
  return (
    <div className="scenarios">
      {scenarios.map((s, i) => (
        <button
          key={s.id}
          className={`scenario ${s.id === selected ? 'selected' : ''}`}
          onClick={() => onSelect(s.id)}
          disabled={disabled}
        >
          <span className="scenario-num">Attack {i + 1}</span>
          <span className="scenario-title">{s.title}</span>
          <span className="scenario-attack">{s.attack}</span>
        </button>
      ))}
    </div>
  )
}

export function FileViewer({ scenario }) {
  const [tab, setTab] = useState(0)
  const box = useRef(null)
  const files = scenario.file_contents
  const file = files[Math.min(tab, files.length - 1)]
  const isPrivate = file.path.includes('inbox')

  // Bring the first injected line into view so the audience sees the payload immediately.
  useEffect(() => {
    const el = box.current
    const hit = el?.querySelector('.line-inj')
    if (el) el.scrollTop = hit ? Math.max(0, hit.offsetTop - el.offsetTop - 60) : 0
  }, [tab, scenario.id])
  return (
    <div className="files">
      <div className="tabs">
        {files.map((f, i) => (
          <button key={f.path} className={`tab ${i === tab ? 'active' : ''}`} onClick={() => setTab(i)}>
            {f.path.includes('inbox') ? '📥' : '📄'} {f.path.split('/').pop()}
          </button>
        ))}
      </div>
      <div className={`file-banner ${isPrivate ? 'secret' : 'poison'}`}>
        {isPrivate
          ? "The user's inbox: it also holds a bank reset code and confidential salary data"
          : 'Mock booby-trapped résumé. Highlighted lines are hidden white text: the prompt injection'}
      </div>
      <div ref={box} className="file-scroll">
        <Doc text={file.content} scenario={scenario} className="file-doc" />
      </div>
    </div>
  )
}

/** The plain-language permission screen. Nothing protected runs until the user approves. */
export function PermissionDialog({ screen, onDecide }) {
  if (!screen) return null
  return (
    <div className="modal-backdrop" role="dialog" aria-modal="true" aria-labelledby="perm-title">
      <div className="permission">
        <span className="perm-badge">Permission request</span>
        <h3 id="perm-title">Rakshak wants to help with: <b>“{screen.task}”</b></h3>
        <ul className="perm-list">
          {screen.allow.map((a) => <li key={a} className="perm allow"><span>ALLOW</span>{a}</li>)}
          {screen.block.map((b) => <li key={b} className="perm block"><span>BLOCK</span>{b}</li>)}
        </ul>
        <p className="muted">Valid for this task only, for {screen.minutes} minutes. You can revoke it at any time.</p>
        <div className="perm-actions">
          <button className="approve" onClick={() => onDecide(true)} autoFocus>Approve for this task</button>
          <button className="deny" onClick={() => onDecide(false)}>Deny</button>
        </div>
      </div>
    </div>
  )
}

function TokenCard({ token }) {
  if (!token) return null
  return (
    <div className="token">
      <h3>🔏 Signed task token</h3>
      <p className="muted">Minted from your approval · id <code>{token.id}</code> · expires in {token.minutes} min</p>
      <ul className="plain">{token.grants.map((g) => <li key={g}>{g}</li>)}</ul>
      <p className="muted">HMAC-SHA256 signature <code>{token.signature}</code>, verified on every call</p>
    </div>
  )
}

function ActivityLog({ entries, final }) {
  if (!entries.length) return null
  const icon = { approve: '👤', allow: '✅', block: '⛔', end: '🔚', info: 'ℹ️' }
  return (
    <div className="activity">
      <h3>
        📜 Activity log (what the user reads)
        {final && (
          <span className={`chain ${final.verified ? 'ok' : 'bad'}`}>
            {final.verified ? '🔗 hash chain verified' : '⚠ chain broken'}
          </span>
        )}
      </h3>
      <ol>
        {entries.map((e) => (
          <li key={e.seq} className={`log-${e.kind}`}>
            <span className="log-icon">{icon[e.kind] || '•'}</span>
            <span className="log-text">{e.text}</span>
            <code className="log-hash" title={`prev ${e.prev}`}>{e.hash.slice(0, 10)}…</code>
          </li>
        ))}
      </ol>
    </div>
  )
}

function Outbox({ emails, scenario }) {
  if (!emails) return null
  return (
    <div className="outbox">
      <h3>📤 Outbox: what actually left the system</h3>
      {!emails.length && <p className="muted">No email was sent.</p>}
      {emails.map((m, i) => {
        const attacker = !isAllowed(m.to, scenario)
        return (
          <div key={i} className={`email ${attacker ? 'attacker' : 'legit'}`}>
            <div className="email-head">
              <span className="email-tag">{attacker ? '🚨 attacker' : '✓ legitimate'}</span>
              <span>To: <b>{m.to}</b></span>
              <span className="muted">Subject: {m.subject}</span>
            </div>
            <Doc text={m.body} scenario={scenario} maxLines={10} />
          </div>
        )
      })}
    </div>
  )
}

function Verdict({ events, phase, mode }) {
  const verdict = events.find((e) => e.type === 'verdict')
  const error = events.find((e) => e.type === 'error')
  const blocks = events.filter((e) => e.type === 'proxy.block').length
  if (error && !verdict) return <div className="verdict error">💥 Run failed: {error.message}</div>
  if (!verdict) {
    if (phase === 'running') return <div className="verdict pending"><span className="spinner" /> Assistant running…</div>
    return <div className="verdict idle">Press “Run” to start the {mode === 'protected' ? 'Rakshak' : 'plain'} assistant.</div>
  }
  if (verdict.status === 'compromised') {
    return (
      <div className="verdict compromised">
        🚨 COMPROMISED: email sent to <b>{verdict.foreign_recipients.join(', ')}</b>
        {verdict.secrets_leaked && <> · <b>bank code and salary data leaked</b></>}
      </div>
    )
  }
  if (blocks) return <div className="verdict safe">🛡️ SAFE: Rakshak blocked {blocks} action{blocks > 1 ? 's' : ''} outside your approved task; only Priya got a reply</div>
  if (verdict.status === 'safe') return <div className="verdict safe">🛡️ SAFE: only the people you named received mail</div>
  return <div className="verdict idle">No email was sent (the model chose not to act).</div>
}

export function RunPanel({ mode, run, scenario, onRun, disabled, providerLabel }) {
  const P = mode === 'protected'
  const outbox = run.events.find((e) => e.type === 'outbox')
  const token = run.events.find((e) => e.type === 'rakshak.token')
  const logEntries = run.events.filter((e) => e.type === 'rakshak.audit')
  const logFinal = run.events.find((e) => e.type === 'rakshak.log')
  return (
    <section className={`panel ${mode}`}>
      <header className="panel-head">
        <div>
          <h2>{P ? '🛡️ With Rakshak' : '⚠️ Plain AI assistant'}</h2>
          <p className="muted">
            {P
              ? 'You approve the task → signed token → every call checked in code (on top of VAJRA) → MCP server.'
              : 'The assistant talks to the mail server directly. Whatever it reads, it may act on.'}
          </p>
        </div>
        <button className={`run-btn ${mode}`} onClick={onRun} disabled={disabled}>
          {run.phase === 'running' ? 'Running…' : 'Run'}
        </button>
      </header>
      <p className="expect"><b>Expected:</b> {scenario.expectation[mode]}</p>
      <OrchestrationDiagram mode={mode} events={run.events} scenario={scenario} providerLabel={providerLabel} />
      <Verdict events={run.events} phase={run.phase} mode={mode} />
      {P && <TokenCard token={token} />}
      {P && <ActivityLog entries={logEntries} final={logFinal} />}
      <Timeline events={run.events} scenario={scenario} mode={mode} />
      <Outbox emails={outbox?.emails} scenario={scenario} />
    </section>
  )
}
