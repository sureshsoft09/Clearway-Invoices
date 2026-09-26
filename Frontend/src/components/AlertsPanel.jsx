import { Chip, Empty, Panel } from './ui'
import { money } from '../lib/format'

export default function AlertsPanel({ alerts, onSelect }) {
  const dups = alerts?.duplicates || []
  const banks = alerts?.bank_changes || []

  return (
    <div className="grid gap-3 lg:grid-cols-2">
      <Panel
        title="Duplicate submissions"
        hint="same vendor, PO and amount as an invoice already received"
        right={<Chip tone="rose">{dups.length}</Chip>}
      >
        {dups.length === 0 ? (
          <Empty>No duplicates detected.</Empty>
        ) : (
          <ul className="space-y-2">
            {dups.map((d) => (
              <li key={d.invoice_id}>
                <button
                  onClick={() => onSelect(d.invoice_id)}
                  className="panel card-hover w-full border-l-2 border-l-rose-400/70
                    px-3 py-2 text-left"
                >
                  <div className="flex items-center justify-between gap-2">
                    <span className="num text-[12px] font-semibold">
                      {d.invoice_id}
                    </span>
                    <span className="num text-[12px] text-rose-300">
                      {money(d.total, d.currency)}
                    </span>
                  </div>
                  <p className="mt-0.5 truncate text-[11px] text-mute">
                    {d.vendor_name_raw} · {d.po_ref}
                  </p>
                  <p className="mt-1 text-[11px] text-rose-300/90">
                    ▸ duplicate of{' '}
                    <span className="num">{d.duplicate_of}</span>
                  </p>
                </button>
              </li>
            ))}
          </ul>
        )}
      </Panel>

      <Panel
        title="Unverified bank changes"
        hint="remittance account changed shortly before the invoice arrived"
        right={<Chip tone="rose">{banks.length}</Chip>}
      >
        {banks.length === 0 ? (
          <Empty>No unverified bank changes.</Empty>
        ) : (
          <ul className="space-y-2">
            {banks.map((b) => (
              <li key={`${b.invoice_id}-${b.new_bank_account}`}>
                <button
                  onClick={() => onSelect(b.invoice_id)}
                  className="panel card-hover w-full border-l-2 border-l-rose-400/70
                    px-3 py-2 text-left"
                >
                  <div className="flex items-center justify-between gap-2">
                    <span className="num text-[12px] font-semibold">
                      {b.invoice_id}
                    </span>
                    <span className="num text-[12px] text-rose-300">
                      {money(b.total, b.currency)}
                    </span>
                  </div>
                  <p className="mt-0.5 truncate text-[11px] text-mute">
                    {b.vendor_name_raw}
                  </p>

                  <div className="mt-1.5 space-y-0.5 text-[10.5px]">
                    <p className="num text-mute">
                      <span className="text-slate-400">was </span>
                      <span className="line-through">{b.old_bank_account}</span>
                    </p>
                    <p className="num text-rose-300">
                      <span className="text-slate-400">now </span>
                      {b.new_bank_account}
                    </p>
                  </div>

                  <div className="mt-1.5 flex flex-wrap gap-1">
                    <Chip tone="rose">
                      {b.days_before_invoice}d before invoice
                    </Chip>
                    <Chip tone="amber">{b.channel}</Chip>
                    <Chip tone="slate">{b.changed_by}</Chip>
                  </div>
                </button>
              </li>
            ))}
          </ul>
        )}
      </Panel>
    </div>
  )
}
