import { describe, expect, it } from 'vitest'
import {
  acknowledgement,
  createTicket,
  parseReport,
  REPORT_EXAMPLE,
  transitionTicket,
  type NormalizedReport,
} from './domain'

const report: NormalizedReport = {
  building: 'A', floor: 2, type: 'LEAK', severity: 'HIGH', originalMessage: REPORT_EXAMPLE,
}

describe('parseReport', () => {
  it('normalizes the valid field format and preserves the original message', () => {
    const result = parseReport(REPORT_EXAMPLE)
    expect(result).toEqual({ ok: true, report })
  })

  it('rejects non-numeric floors instead of guessing', () => {
    const result = parseReport('ISSUE|BUILDING=A|FLOOR=second|TYPE=LEAK|SEVERITY=HIGH')
    expect(result.ok).toBe(false)
    if (!result.ok) expect(result.errors.join(' ')).toContain('numeric floor')
  })

  it('rejects missing, duplicate, and unsupported fields', () => {
    expect(parseReport('ISSUE|BUILDING=A|FLOOR=2|TYPE=LEAK')).toMatchObject({ ok: false })
    expect(parseReport('ISSUE|BUILDING=A|FLOOR=2|TYPE=LEAK|TYPE=HVAC|SEVERITY=HIGH')).toMatchObject({ ok: false })
    expect(parseReport('ISSUE|BUILDING=A|FLOOR=2|TYPE=ALIEN|SEVERITY=HIGH')).toMatchObject({ ok: false })
    expect(parseReport('ISSUE|BUILDING=A|FLOOR=2|TYPE=LEAK|SEVERITY=HIGH|NOTE=x')).toMatchObject({ ok: false })
  })
})

describe('ticket lifecycle', () => {
  it('allows the explicit lifecycle and derives acknowledgement from live state', () => {
    const fresh = createTicket(report, 'GL-001')
    const triaged = transitionTicket(fresh, 'TRIAGED')
    const assigned = transitionTicket(triaged, 'ASSIGNED', 'MAINTENANCE')
    expect(acknowledgement(fresh)).toBe('ACK|GL-001|STATUS=NEW')
    expect(acknowledgement(assigned)).toBe('ACK|GL-001|STATUS=ASSIGNED|TEAM=MAINTENANCE')
    expect(transitionTicket(assigned, 'RESOLVED')).toMatchObject({ status: 'RESOLVED', team: 'MAINTENANCE' })
  })

  it('rejects invalid jumps and assignment without a team', () => {
    const fresh = createTicket(report, 'GL-002')
    expect(() => transitionTicket(fresh, 'ASSIGNED', 'MAINTENANCE')).toThrow('Invalid transition')
    const triaged = transitionTicket(fresh, 'TRIAGED')
    expect(() => transitionTicket(triaged, 'ASSIGNED')).toThrow('Select a maintenance team')
    expect(() => transitionTicket(triaged, 'RESOLVED')).toThrow('Invalid transition')
  })
})
