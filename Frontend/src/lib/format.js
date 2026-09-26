export const SYMBOL = { INR: '₹', EUR: '€', USD: '$' }

export function money(value, currency = 'INR') {
  const n = Number(value ?? 0)
  return `${SYMBOL[currency] || ''}${n.toLocaleString('en-IN', {
    minimumFractionDigits: 2, maximumFractionDigits: 2,
  })}`
}

export function compact(value, currency = 'USD') {
  const n = Number(value ?? 0)
  return `${SYMBOL[currency] || ''}${n.toLocaleString('en-US', {
    notation: 'compact', maximumFractionDigits: 1,
  })}`
}

export function ms(value) {
  const n = Number(value ?? 0)
  if (!n) return '—'
  return n < 1000 ? `${n} ms` : `${(n / 1000).toFixed(1)} s`
}

export function pct(value, digits = 0) {
  return `${(Number(value ?? 0) * 100).toFixed(digits)}%`
}

export function ago(iso) {
  if (!iso) return '—'
  const secs = Math.max(0, (Date.now() - new Date(iso).getTime()) / 1000)
  if (secs < 60) return `${Math.floor(secs)}s ago`
  if (secs < 3600) return `${Math.floor(secs / 60)}m ago`
  return `${Math.floor(secs / 3600)}h ago`
}

export function clock(iso) {
  if (!iso) return ''
  return new Date(iso).toLocaleTimeString('en-GB', {
    hour: '2-digit', minute: '2-digit', second: '2-digit',
  })
}

/** Pipeline board columns. Status values come from the backend pipeline. */
export const COLUMNS = [
  { key: 'ingest', label: 'Ingest', hint: 'Document AI', statuses: ['received', 'extracting'] },
  { key: 'match', label: 'Three-way match', hint: 'BigQuery', statuses: ['matching'] },
  { key: 'agents', label: 'Agent review', hint: 'Agent Engine', statuses: ['agent_review'] },
  { key: 'queue', label: 'Human queue', hint: 'awaiting approval', statuses: ['awaiting_approval'] },
  { key: 'cleared', label: 'Cleared', hint: 'touchless + posted', statuses: ['posted_pending_approval', 'posted'] },
  { key: 'rejected', label: 'Rejected', hint: 'overridden or failed', statuses: ['rejected', 'failed'] },
]

export const STATUS_TONE = {
  received: 'sky', extracting: 'sky', matching: 'violet', agent_review: 'amber',
  awaiting_approval: 'amber', posted_pending_approval: 'emerald', posted: 'emerald',
  rejected: 'rose', failed: 'rose',
}

export const STATUS_LABEL = {
  received: 'Received', extracting: 'Extracting', matching: 'Matching',
  agent_review: 'Agent review', awaiting_approval: 'Needs approval',
  posted_pending_approval: 'Ready to post', posted: 'Posted',
  rejected: 'Rejected', failed: 'Failed',
}

export const CAUSE_LABEL = {
  short_shipment: 'Short shipment',
  overbilled_vs_receipt: 'Billed above receipt',
  uom_difference: 'Unit of measure',
  price_escalation: 'Price escalation',
  freight_billed_separately: 'Freight separate',
  tax_or_rounding: 'Tax or rounding',
  duplicate_submission: 'Duplicate',
  wrong_po_referenced: 'Wrong PO',
  no_variance: 'No variance',
  unexplained: 'Unexplained',
}

export const CHANNEL_ICON = { email: '✉', portal: '⌾', edi: '⇄', scan: '▤' }

export function confidenceTone(value) {
  const n = Number(value ?? 0)
  if (n >= 0.95) return 'emerald'
  if (n >= 0.85) return 'sky'
  if (n >= 0.75) return 'amber'
  return 'rose'
}
