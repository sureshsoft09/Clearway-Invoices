import { Chip, Empty } from './ui'
import {
  CAUSE_LABEL, CHANNEL_ICON, COLUMNS, STATUS_TONE, ago, money, ms,
} from '../lib/format'

function Card({ invoice, selected, onSelect }) {
  const tone = STATUS_TONE[invoice.status] || 'slate'
  const held = invoice.route === 'hold'
  const cause = CAUSE_LABEL[invoice.variance_cause]

  return (
    <button
      onClick={() => onSelect(invoice.invoice_id)}
      className={`panel card-hover pop w-full border-l-2 px-3 py-2.5 text-left
        ${selected ? 'ring-1 ring-sky-400/50' : ''}
        ${held ? 'border-l-rose-400/70' : tone === 'emerald'
          ? 'border-l-emerald-400/70' : 'border-l-white/10'}`}
    >
      <div className="flex items-center justify-between gap-2">
        <span className="num text-[12px] font-semibold text-paper">
          {invoice.invoice_id}
        </span>
        <span className="num text-[12px] text-slate-300">
          {money(invoice.total, invoice.currency)}
        </span>
      </div>

      <p className="mt-0.5 truncate text-[11px] text-mute"
         title={invoice.vendor}>
        {invoice.vendor || 'Unresolved vendor'}
      </p>

      <div className="mt-2 flex flex-wrap items-center gap-1">
        <Chip tone="slate" title={`received via ${invoice.channel}`}>
          {CHANNEL_ICON[invoice.channel] || '•'} {invoice.channel}
        </Chip>
        {invoice.citation && <Chip tone="sky">cited</Chip>}
        {invoice.variance_cause && <Chip tone="violet">{CAUSE_LABEL[invoice.variance_cause]}</Chip>}
        {cause && <Chip tone="violet">{cause}</Chip>}
        {invoice.ms_total ? (
          <Chip tone="slate" className="ml-auto">{ms(invoice.ms_total)}</Chip>
        ) : null}
        
      </div>

      {held && invoice.reasons?.length > 0 && (
        <ul className="mt-2 space-y-0.5 border-t border-white/5 pt-1.5">
          {invoice.reasons.slice(0, 2).map((reason) => (
            <li key={reason} className="truncate text-[10.5px] text-rose-300/90"
                title={reason}>
              ▸ {reason}
            </li>
          ))}
          {invoice.reasons.length > 2 && (
            <li className="text-[10.5px] text-mute">
              +{invoice.reasons.length - 2} more
            </li>
          )}
        </ul>
      )}

      {!held && invoice.status === 'posted' && (
        <p className="mt-1.5 text-[10.5px] text-emerald-300/90">
          ▸ posted to ERP
        </p>
      )}
      <p className="mt-1 text-[10px] text-mute">{ago(invoice.updated_at)}</p>
    </button>
  )
}

export default function PipelineBoard({ invoices, selected, onSelect }) {
  const byColumn = COLUMNS.map((col) => ({
    ...col,
    items: invoices.filter((i) => col.statuses.includes(i.status)),
  }))
  const visible = byColumn.filter((c) => c.key !== 'rejected' || c.items.length > 0)

  if (invoices.length === 0) {
    return (
      <div className="panel">
        <Empty>
          No invoices yet. Hit <span className="text-sky-300">Replay 100</span> to
          start the run.
        </Empty>
      </div>
    )
  }

  return (
    <div className="grid gap-3"
         style={{ gridTemplateColumns: `repeat(${visible.length}, minmax(190px, 1fr))` }}>
      {visible.map((col) => (
        <div key={col.key} className="flex min-w-0 flex-col">
          <div className="mb-2 flex items-baseline justify-between gap-2 px-1">
            <div className="min-w-0">
              <h3 className="truncate text-[12px] font-semibold tracking-tight">
                {col.label}
              </h3>
              <p className="truncate text-[10px] text-mute">{col.hint}</p>
            </div>
            <span className="num shrink-0 rounded-md bg-white/5 px-1.5 py-0.5
              text-[11px] text-slate-300">
              {col.items.length}
            </span>
          </div>

          <div className="scroll-thin flex max-h-[calc(100vh-330px)] flex-col gap-2
            overflow-y-auto pr-1">
            {col.items.length === 0 ? (
              <p className="rounded-xl border border-dashed border-white/10 px-3 py-6
                text-center text-[11px] text-mute">
                empty
              </p>
            ) : (
              col.items.map((invoice) => (
                <Card
                  key={invoice.invoice_id}
                  invoice={invoice}
                  selected={selected === invoice.invoice_id}
                  onSelect={onSelect}
                />
              ))
            )}
          </div>
        </div>
      ))}
    </div>
  )
}
