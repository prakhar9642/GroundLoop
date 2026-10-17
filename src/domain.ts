export const REPORT_EXAMPLE = 'ISSUE|BUILDING=A|FLOOR=2|TYPE=LEAK|SEVERITY=HIGH'

export const ISSUE_TYPES = ['LEAK', 'ELECTRICAL', 'HVAC', 'PLUMBING', 'RESTROOM', 'DAMAGE', 'LIGHTING'] as const
export const SEVERITIES = ['LOW', 'MEDIUM', 'HIGH'] as const
export const TICKET_STATUSES = ['NEW', 'TRIAGED', 'ASSIGNED', 'RESOLVED'] as const
export const TEAMS = ['MAINTENANCE', 'ELECTRICAL', 'HVAC', 'CUSTODIAL'] as const

export type IssueType = (typeof ISSUE_TYPES)[number]
export type Severity = (typeof SEVERITIES)[number]
export type TicketStatus = (typeof TICKET_STATUSES)[number]
export type Team = (typeof TEAMS)[number]

export type NormalizedReport = {
  building: string
  floor: number
  type: IssueType
  severity: Severity
  originalMessage: string
}

export type Ticket = NormalizedReport & {
  id: string
  createdAt: string
  status: TicketStatus
  team?: Team
  source: 'FIELD REPORT' | 'DEMO DATA'
}

export type ParseResult = { ok: true; report: NormalizedReport } | { ok: false; errors: string[] }

const REQUIRED_FIELDS = ['BUILDING', 'FLOOR', 'TYPE', 'SEVERITY'] as const

export function parseReport(message: string): ParseResult {
  const errors: string[] = []
  if (!message.trim()) return { ok: false, errors: ['Enter a field report to validate.'] }

  const parts = message.split('|')
  if (parts[0] !== 'ISSUE') errors.push('Message must start with ISSUE.')
  if (parts.length !== 5) errors.push('Use exactly 5 segments: ISSUE plus BUILDING, FLOOR, TYPE, and SEVERITY.')

  const fields: Record<string, string> = {}
  for (const part of parts.slice(1)) {
    const separator = part.indexOf('=')
    if (separator <= 0 || separator === part.length - 1) {
      errors.push(`Malformed segment "${part || '(empty)'}". Use FIELD=VALUE.`)
      continue
    }
    const key = part.slice(0, separator)
    const value = part.slice(separator + 1)
    if (!REQUIRED_FIELDS.includes(key as (typeof REQUIRED_FIELDS)[number])) {
      errors.push(`Unknown field ${key}. Allowed fields: ${REQUIRED_FIELDS.join(', ')}.`)
    } else if (key in fields) {
      errors.push(`Duplicate field ${key}. Each field may appear once.`)
    } else {
      fields[key] = value
    }
  }

  for (const field of REQUIRED_FIELDS) {
    if (!(field in fields)) errors.push(`Missing required field ${field}.`)
  }

  const building = fields.BUILDING
  if (building && !/^[A-Z]$/.test(building)) errors.push('BUILDING must be a single uppercase letter (A–Z).')

  const floor = fields.FLOOR ? Number(fields.FLOOR) : NaN
  if (fields.FLOOR && (!/^\d+$/.test(fields.FLOOR) || !Number.isInteger(floor) || floor < 1 || floor > 12)) {
    errors.push('FLOOR must be a numeric floor from 1 to 12 (for example, FLOOR=2).')
  }

  if (fields.TYPE && !ISSUE_TYPES.includes(fields.TYPE as IssueType)) {
    errors.push(`Unsupported TYPE ${fields.TYPE}. Try ${ISSUE_TYPES.slice(0, 4).join(', ')}.`)
  }
  if (fields.SEVERITY && !SEVERITIES.includes(fields.SEVERITY as Severity)) {
    errors.push(`Unsupported SEVERITY ${fields.SEVERITY}. Use LOW, MEDIUM, or HIGH.`)
  }

  if (errors.length) return { ok: false, errors }
  return {
    ok: true,
    report: {
      building,
      floor,
      type: fields.TYPE as IssueType,
      severity: fields.SEVERITY as Severity,
      originalMessage: message,
    },
  }
}

const NEXT_STATUS: Record<TicketStatus, TicketStatus | null> = {
  NEW: 'TRIAGED',
  TRIAGED: 'ASSIGNED',
  ASSIGNED: 'RESOLVED',
  RESOLVED: null,
}

export function transitionTicket(ticket: Ticket, nextStatus: TicketStatus, team?: Team): Ticket {
  const expected = NEXT_STATUS[ticket.status]
  if (expected !== nextStatus) throw new Error(`Invalid transition: ${ticket.status} → ${nextStatus}.`)
  if (nextStatus === 'ASSIGNED' && !team) throw new Error('Select a maintenance team before assigning this ticket.')
  return { ...ticket, status: nextStatus, ...(team ? { team } : {}) }
}

export function acknowledgement(ticket: Ticket): string {
  return `ACK|${ticket.id}|STATUS=${ticket.status}${ticket.team ? `|TEAM=${ticket.team}` : ''}`
}

export function createTicket(report: NormalizedReport, id: string, source: Ticket['source'] = 'FIELD REPORT'): Ticket {
  return { ...report, id, createdAt: new Date().toISOString(), status: 'NEW', source }
}
