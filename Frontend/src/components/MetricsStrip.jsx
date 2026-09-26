import { Bar, Meter, Panel, Stat } from './ui'
import { compact, ms, pct } from '../lib/format'

export default function MetricsStrip({ metrics, alerts }) {
  const m = metrics || {}
  const processed = m.processed || 0
  const touchless = m.touchless || 0
  const escalated = m.escalated || 0
  const reasons = Object.entries(m.exceptions_by_reason || {}).slice(0, 5)
  const worst = reasons.length ? reasons[0][1] : 0

  return (
    <div className="grid grid-cols-2 gap-3 lg:grid-cols-6">
      <Stat
        label="Touchless rate"
        value={pct(m.touchless_rate)}
        tone="emerald"
        accent="text-emerald-300"
        sub={`${touchless} of ${processed} processed`}
      />
      <Stat
        label="Escalated"
        value={escalated}
        tone="amber"
        accent="text-amber-300"
        sub={`${m.agent_invoked || 0} needed an agent`}
      />
      <Stat
        label="Avg cycle"
        value={ms(m.avg_cycle_ms)}
        sub="ingest to decision"
      />
      <Stat
        label="Cost per invoice"
        value={`$${(m.cost_per_invoice_usd ?? 0).toFixed(2)}`}
        tone="emerald"
        sub={`manual $${(m.manual_cost_per_invoice_usd ?? 0).toFixed(2)}`}
      />
      <Stat
        label="Saved this run"
        value={compact(m.cost_saved_usd, 'USD')}
        tone="emerald"
        accent="text-emerald-300"
        sub={`${m.hours_saved ?? 0} analyst hours`}
      />
      <Stat
        label="Value at risk"
        value={compact(alerts?.value_at_risk, 'INR')}
        tone="rose"
        accent="text-rose-300"
        sub={`${alerts?.total ?? 0} fraud signals`}
      />

      <Panel
        title="Routing split"
        hint="deterministic clears the bulk, agents handle the rest"
        className="col-span-2 lg:col-span-3"
      >
        <Meter
          height={10}
          segments={[
            { label: 'Touchless', value: touchless, tone: 'emerald' },
            { label: 'Escalated', value: escalated, tone: 'amber' },
            { label: 'In flight', value: m.in_flight || 0, tone: 'sky' },
          ]}
        />
        <ul className="mt-3 flex flex-wrap gap-x-5 gap-y-1 text-[11px]">
          <li className="text-emerald-300">● Touchless {touchless}</li>
          <li className="text-amber-300">● Escalated {escalated}</li>
          <li className="text-sky-300">● In flight {m.in_flight || 0}</li>
        </ul>
      </Panel>

      <Panel
        title="Exceptions by reason"
        hint="what actually stops an invoice"
        className="col-span-2 lg:col-span-3"
      >
        {reasons.length === 0 ? (
          <p className="py-3 text-[12px] text-mute">
            No exceptions held yet.
          </p>
        ) : (
          <ul className="space-y-1.5">
            {reasons.map(([reason, count]) => (
              <li key={reason} className="grid grid-cols-[1fr_auto] items-center gap-3">
                <span className="truncate text-[12px] text-slate-300" title={reason}>
                  {reason}
                </span>
                <div className="w-28">
                  <Bar value={count} max={worst} tone="amber" />
                </div>
              </li>
            ))}
          </ul>
        )}
      </Panel>
    </div>
  )
}
