import { useEffect, useMemo, useState, type FormEvent } from 'react'
import {
  acknowledgement,
  createTicket,
  parseReport,
  REPORT_EXAMPLE,
  transitionTicket,
  TEAMS,
  type ParseResult,
  type Team,
  type Ticket,
  type TicketStatus,
} from './domain'

const STORAGE_KEY = 'groundloop-tickets-v1'

const seedTickets: Ticket[] = [
  {
    id: 'GL-004', building: 'C', floor: 1, type: 'HVAC', severity: 'MEDIUM',
    originalMessage: 'ISSUE|BUILDING=C|FLOOR=1|TYPE=HVAC|SEVERITY=MEDIUM',
    createdAt: '2026-10-17T08:26:00.000Z', status: 'TRIAGED', source: 'DEMO DATA',
  },
  {
    id: 'GL-003', building: 'B', floor: 3, type: 'ELECTRICAL', severity: 'HIGH',
    originalMessage: 'ISSUE|BUILDING=B|FLOOR=3|TYPE=ELECTRICAL|SEVERITY=HIGH',
    createdAt: '2026-10-17T08:11:00.000Z', status: 'ASSIGNED', team: 'ELECTRICAL', source: 'DEMO DATA',
  },
  {
    id: 'GL-002', building: 'D', floor: 1, type: 'RESTROOM', severity: 'LOW',
    originalMessage: 'ISSUE|BUILDING=D|FLOOR=1|TYPE=RESTROOM|SEVERITY=LOW',
    createdAt: '2026-10-17T07:48:00.000Z', status: 'RESOLVED', team: 'CUSTODIAL', source: 'DEMO DATA',
  },
]

function Icon({ name, size = 18 }: { name: string; size?: number }) {
  const paths: Record<string, string> = {
    arrow: 'M5 12h14m-6-6 6 6-6 6',
    check: 'm5 12 4 4L19 6',
    chevron: 'm9 18 6-6-6-6',
    clipboard: 'M9 5h6m-8 3h10v11H7zM9 5a2 2 0 0 1 2-2h2a2 2 0 0 1 2 2',
    clock: 'M12 7v5l3 2m6-2a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z',
    close: 'M6 6l12 12M18 6 6 18',
    layers: 'M12 3 3 8l9 5 9-5-9-5Zm-9 9 9 5 9-5M3 16l9 5 9-5',
    location: 'M20 10c0 5-8 11-8 11S4 15 4 10a8 8 0 1 1 16 0Z M12 12.5a2.5 2.5 0 1 0 0-5 2.5 2.5 0 0 0 0 5Z',
    menu: 'M4 6h16M4 12h16M4 18h16',
    radio: 'M5 5a10 10 0 0 0 0 14M19 5a10 10 0 0 1 0 14M8 8a6 6 0 0 0 0 8M16 8a6 6 0 0 1 0 8M12 12h.01',
    send: 'M22 2 11 13M22 2l-7 20-4-9-9-4 20-7Z',
    settings: 'M12 15.5a3.5 3.5 0 1 0 0-7 3.5 3.5 0 0 0 0 7Zm0-12v2m0 13v2M4.22 4.22l1.42 1.42m12.72 12.72 1.42 1.42M1.5 12h2m17 0h2M4.22 19.78l1.42-1.42M18.36 5.64l1.42-1.42',
    shield: 'M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10Z',
    spark: 'm12 3 1.8 5.2L19 10l-5.2 1.8L12 17l-1.8-5.2L5 10l5.2-1.8L12 3Z',
  }
  return <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><path d={paths[name] ?? paths.spark} /></svg>
}

function statusLabel(status: TicketStatus) {
  return status[0] + status.slice(1).toLowerCase()
}

function formatTime(iso: string) {
  return new Intl.DateTimeFormat('en-US', { hour: 'numeric', minute: '2-digit' }).format(new Date(iso))
}

function formatDate(iso: string) {
  return new Intl.DateTimeFormat('en-US', { month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit' }).format(new Date(iso))
}

function readTickets() {
  try {
    const saved = window.localStorage.getItem(STORAGE_KEY)
    if (saved) return JSON.parse(saved) as Ticket[]
  } catch {
    // The UI still works when storage is unavailable.
  }
  return seedTickets
}

function App() {
  const [tickets, setTickets] = useState<Ticket[]>(readTickets)
  const [selectedId, setSelectedId] = useState('GL-004')
  const [message, setMessage] = useState('')
  const [validation, setValidation] = useState<ParseResult | null>(null)
  const [selectedTeam, setSelectedTeam] = useState<Team>('MAINTENANCE')
  const [notice, setNotice] = useState('')

  useEffect(() => {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(tickets))
  }, [tickets])

  const selected = tickets.find((ticket) => ticket.id === selectedId) ?? tickets[0]
  const counts = useMemo(() => ({
    all: tickets.length,
    new: tickets.filter((ticket) => ticket.status === 'NEW').length,
    active: tickets.filter((ticket) => ticket.status === 'TRIAGED' || ticket.status === 'ASSIGNED').length,
    resolved: tickets.filter((ticket) => ticket.status === 'RESOLVED').length,
  }), [tickets])

  function loadSample() {
    setMessage(REPORT_EXAMPLE)
    setValidation(parseReport(REPORT_EXAMPLE))
    setNotice('Sample loaded — ready to send.')
  }

  function submitReport(event: FormEvent) {
    event.preventDefault()
    const result = parseReport(message)
    setValidation(result)
    if (!result.ok) {
      setNotice('Report held — correct the highlighted fields before sending.')
      return
    }
    const nextNumber = Math.max(0, ...tickets.map((ticket) => Number(ticket.id.replace('GL-', '')))) + 1
    const ticket = createTicket(result.report, `GL-${String(nextNumber).padStart(3, '0')}`)
    setTickets((current) => [ticket, ...current])
    setSelectedId(ticket.id)
    setNotice(`${ticket.id} created and visible to operations.`)
    setMessage('')
  }

  function updateTicket(nextStatus: TicketStatus) {
    if (!selected) return
    try {
      const updated = transitionTicket(selected, nextStatus, nextStatus === 'ASSIGNED' ? selectedTeam : selected.team)
      setTickets((current) => current.map((ticket) => ticket.id === updated.id ? updated : ticket))
      setNotice(`${updated.id} moved to ${statusLabel(updated.status)}.`)
    } catch (error) {
      setNotice(error instanceof Error ? error.message : 'That transition is not available.')
    }
  }

  function resetDemo() {
    setTickets(seedTickets)
    setSelectedId('GL-004')
    setNotice('Demo data restored.')
  }

  return (
    <div className="app-shell">
      <header className="topbar">
        <div className="brand"><span className="brand-mark"><Icon name="layers" size={18} /></span><span>GROUND<span>LOOP</span></span></div>
        <div className="topbar-center"><span className="topbar-dot" /> Campus operations bridge <span className="topbar-divider" /> <span className="muted">Workspace / Demo</span></div>
        <div className="topbar-actions"><span className="local-pill"><span className="pulse-dot" /> Local transport</span><button className="icon-button" aria-label="Settings"><Icon name="settings" size={17} /></button><button className="profile">OP</button></div>
      </header>

      <main className="page-content">
        <div className="intro-row">
          <div><p className="eyebrow"><span className="eyebrow-line" /> FIELD SIGNAL → WORK ORDER</p><h1>Make every report<br /><em>actionable.</em></h1><p className="intro-copy">GroundLoop turns compact field messages into accountable campus work orders — with a clear loop back to the person who reported it.</p></div>
          <div className="intro-aside"><div className="stat-orbit"><span className="orbit-ring" /><strong>24<span>h</span></strong></div><div><strong>One shared loop</strong><p>From signal to resolution</p></div></div>
        </div>

        <section className="workspace-grid">
          <aside className="reporter-card">
            <div className="card-topline"><div className="section-kicker"><span className="icon-bubble amber"><Icon name="radio" size={16} /></span><span><small>01 / INTAKE</small><strong>Field reporter</strong></span></div><span className="demo-label">SIMULATED</span></div>
            <div className="phone-frame">
              <div className="phone-speaker" />
              <div className="phone-header"><div className="phone-brand"><span className="mini-mark"><Icon name="layers" size={12} /></span>groundloop</div><span className="phone-signal"><span className="pulse-dot" /> connected</span></div>
              <div className="phone-body">
                <div className="phone-greeting"><span className="avatar">JS</span><div><strong>Good morning, Jordan</strong><span>Report a campus issue</span></div></div>
                <div className="field-label-row"><label htmlFor="report-message">Message payload</label><button type="button" className="text-button" onClick={loadSample}>Load sample <Icon name="arrow" size={13} /></button></div>
                <form onSubmit={submitReport}>
                  <div className={`message-input ${validation && !validation.ok ? 'has-error' : ''} ${validation?.ok ? 'has-success' : ''}`}><textarea id="report-message" value={message} onChange={(event) => { setMessage(event.target.value); setValidation(null); setNotice('') }} placeholder="ISSUE|BUILDING=A|FLOOR=2|..." rows={4} spellCheck={false} /><span className="input-counter">{message.length}/120</span></div>
                  <p className="format-hint"><Icon name="shield" size={13} /> Strict format · no guessing or auto-correction</p>
                  <button className="send-button" type="submit"><span>Validate &amp; send report</span><span className="send-icon"><Icon name="send" size={15} /></span></button>
                </form>
                {validation && !validation.ok && <div className="validation-box error-box"><div className="validation-heading"><span className="status-icon error-icon"><Icon name="close" size={13} /></span><strong>Needs correction</strong></div><ul>{validation.errors.map((error) => <li key={error}>{error}</li>)}</ul></div>}
                {validation?.ok && <div className="validation-box success-box"><div className="validation-heading"><span className="status-icon success-icon"><Icon name="check" size={13} /></span><strong>Payload validated</strong></div><p>Ready to create a new work order in operations.</p></div>}
              </div>
              <div className="phone-footer"><span className="footer-lock"><Icon name="shield" size={12} /> deterministic parser</span><span>v1.0</span></div>
            </div>
            <div className="transport-callout"><span className="callout-icon"><Icon name="radio" size={15} /></span><div><strong>Local transport active</strong><p>Simulation only · no external message sent</p></div><span className="callout-check"><Icon name="check" size={14} /></span></div>
          </aside>

          <section className="operations-card">
            <div className="operations-heading"><div className="section-kicker"><span className="icon-bubble green"><Icon name="clipboard" size={16} /></span><span><small>02 / OPERATIONS</small><strong>Command center</strong></span></div><div className="ops-heading-right"><span className="live-chip"><span className="pulse-dot" /> LIVE VIEW</span><button className="reset-button" onClick={resetDemo}>Reset demo</button></div></div>
            <div className="metric-grid"><div className="metric-card accent"><span className="metric-label">All reports</span><strong>{counts.all}</strong><span className="metric-note"><span className="trend">↑</span> intake this shift</span></div><div className="metric-card"><span className="metric-label">Needs action</span><strong>{counts.active + counts.new}</strong><span className="metric-note">across {counts.active + counts.new === 1 ? '1 status' : '3 statuses'}</span></div><div className="metric-card"><span className="metric-label">In progress</span><strong>{counts.active}</strong><span className="metric-note">triaged or assigned</span></div><div className="metric-card"><span className="metric-label">Resolved</span><strong>{counts.resolved}</strong><span className="metric-note good-note"><Icon name="check" size={12} /> closed loop</span></div></div>

            <div className="ops-content"><div className="ticket-list-panel"><div className="list-header"><div><h2>Incoming work orders</h2><p>Sorted by most recent activity</p></div><span className="list-count">{tickets.length} total</span></div><div className="ticket-list">{tickets.map((ticket) => <button key={ticket.id} className={`ticket-row ${selected?.id === ticket.id ? 'selected' : ''}`} onClick={() => setSelectedId(ticket.id)}><div className={`ticket-severity ${ticket.severity.toLowerCase()}`} /><div className="ticket-row-main"><div className="ticket-row-top"><strong>{ticket.id}</strong><span className={`status-chip ${ticket.status.toLowerCase()}`}>{statusLabel(ticket.status)}</span></div><span className="ticket-title">{ticket.type} issue <span>·</span> Building {ticket.building}</span><span className="ticket-meta"><Icon name="location" size={12} /> Floor {ticket.floor} <span className="meta-divider" /> {formatTime(ticket.createdAt)}</span></div><Icon name="chevron" size={16} /></button>)}</div></div>

              {selected && <div className="detail-panel"><div className="detail-header"><div><span className="detail-id">{selected.id} <span className="source-tag">{selected.source}</span></span><h2>{selected.type} issue<span className="detail-building"> · Building {selected.building}</span></h2></div><span className={`big-status ${selected.status.toLowerCase()}`}><span className="big-status-dot" /> {statusLabel(selected.status)}</span></div><div className="detail-facts"><div><span>LOCATION</span><strong>Building {selected.building} · Floor {selected.floor}</strong></div><div><span>SEVERITY</span><strong className={`severity-text ${selected.severity.toLowerCase()}`}><i /> {selected.severity}</strong></div><div><span>REPORTED</span><strong>{formatDate(selected.createdAt)}</strong></div><div><span>ASSIGNED TEAM</span><strong>{selected.team ?? 'Awaiting assignment'}</strong></div></div><div className="original-message"><div><span className="code-label"><Icon name="radio" size={13} /> ORIGINAL FIELD MESSAGE</span><span className="preserved-label">preserved</span></div><code>{selected.originalMessage}</code></div><div className="lifecycle"><div className="lifecycle-head"><span>WORK ORDER LIFECYCLE</span><span>{selected.status === 'RESOLVED' ? 'Complete' : 'Next action available'}</span></div><div className="steps">{(['NEW', 'TRIAGED', 'ASSIGNED', 'RESOLVED'] as TicketStatus[]).map((status, index) => { const isDone = ['NEW', 'TRIAGED', 'ASSIGNED', 'RESOLVED'].indexOf(selected.status) >= index; const isCurrent = selected.status === status; return <div key={status} className={`step ${isDone ? 'done' : ''} ${isCurrent ? 'current' : ''}`}><span className="step-dot">{isDone && !isCurrent ? <Icon name="check" size={11} /> : index + 1}</span><span>{statusLabel(status)}</span>{index < 3 && <i />}</div> })}</div></div><div className="action-area">{selected.status === 'NEW' && <button className="primary-action" onClick={() => updateTicket('TRIAGED')}>Mark as triaged <Icon name="arrow" size={15} /></button>}{selected.status === 'TRIAGED' && <div className="assign-control"><label htmlFor="team">Assign maintenance team</label><div className="assign-row"><select id="team" value={selectedTeam} onChange={(event) => setSelectedTeam(event.target.value as Team)}>{TEAMS.map((team) => <option key={team}>{team}</option>)}</select><button className="primary-action" onClick={() => updateTicket('ASSIGNED')}>Assign <Icon name="arrow" size={15} /></button></div></div>}{selected.status === 'ASSIGNED' && <button className="primary-action" onClick={() => updateTicket('RESOLVED')}>Mark resolved <Icon name="check" size={15} /></button>}{selected.status === 'RESOLVED' && <div className="resolved-note"><span className="status-icon success-icon"><Icon name="check" size={13} /></span><strong>Work order resolved</strong><span>Closed by {selected.team}</span></div>}</div><div className="acknowledgement"><div className="ack-heading"><span><Icon name="arrow" size={13} /> RETURN ACKNOWLEDGEMENT</span><span>derived from live state</span></div><code>{acknowledgement(selected)}</code><button className="copy-button" onClick={() => navigator.clipboard?.writeText(acknowledgement(selected))} aria-label="Copy acknowledgement">Copy</button></div></div>}
            </div>
          </section>
        </section>
        <div className={`toast ${notice ? 'visible' : ''}`}><span className="toast-icon"><Icon name={notice.includes('held') ? 'close' : 'check'} size={14} /></span>{notice}</div>
        <footer className="page-footer"><span><span className="footer-brand-mark"><Icon name="layers" size={12} /></span> GroundLoop <span className="footer-muted">· Campus operations bridge</span></span><span className="footer-muted"><Icon name="shield" size={12} /> Local demo environment</span></footer>
      </main>
    </div>
  )
}

export default App
