import { useState } from 'react'
import { Button, Chip, Empty, Panel, Tick } from './ui'
import {
  CAUSE_LABEL, STATUS_LABEL, STATUS_TONE, clock, confidenceTone, money, ms, pct,
} from '../lib/format'

function Field({ label, value, confidence }) {
  return (
    <div className="border-b border-white/5 py-1.5 last:border-0">
      <p className="text-[10px] uppercase tracking-[0.1em] text-mute">
        {label}
      </p>
      <div className="mt-0.5 flex items-center justify-between gap-2">
        <span className="num truncate text-[12px] text-paper" title={String(value ?? '')}>
          {value ?? '—'}
        </span>
        {confidence != null && (
          <Chip tone={confidenceTone(confidence)} title="extraction confidence">
            {pct(confidence, 1)}
          </Chip>
        )}
      </div>
    </div>
  )
}

function ChecksTable({ checks }) {
  const groups = [
    ['hard', 'Hard stops', 'fail routes straight to a human'],
    ['soft', 'Soft checks', 'fail sends it to the agents'],
    ['info', 'Context', 'never routes on its own'],
  ]
  return (
    <div className="space-y-3">
      {groups.map(([severity, title, hint]) => {
        const rows = checks.filter((c) => c.severity === severity)
        if (rows.length === 0) return null
        return (
          <div key={severity}>
            <p className="mb-1 text-[11px] font-semibold text-slate-300">
              {title}{' '}
              <span className="font-normal text-mute">— {hint}</span>
            </p>
            <table className="w-full border-collapse text-[11.5px]">
              <tbody>
                {rows.map((c) => (
                  <tr key={c.check_name}
                      className={`border-b border-white/5 last:border-0
                        ${c.status === 'fail' ? 'bg-rose-500/5' : ''}`}>
                    <td className="w-5 py-1.5 align-top">
                      <Tick ok={c.status === 'pass'} />
                    </td>
                    <td className="py-1.5 pr-2 align-top text-slate-300">
                      {c.check_name.replace(/_/g, ' ')}
                    </td>
                    <td className="num py-1.5 pr-2 align-top text-mute">
                      {c.expected}
                    </td>
                    <td className={`num py-1.5 text-right align-top
                      ${c.status === 'fail' ? 'text-rose-300' : 'text-slate-400'}`}>
                      {c.actual}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )
      })}
    </div>
  )
}

function LineComparison({ invoiceLines, poAndGrn, currency }) {
  const po = poAndGrn?.po_lines || []
  const grn = poAndGrn?.goods_receipts || []
  const find = (list, code) => list.find((x) => x.item_code === code)

  if (invoiceLines.length === 0) return <Empty>No invoice lines.</Empty>

  return (
    <div className="scroll-thin overflow-x-auto">
      <table className="w-full min-w-[540px] border-collapse text-[11.5px]">
        <thead>
          <tr className="border-b border-white/10 text-[10px] uppercase
            tracking-[0.08em] text-mute">
            <th className="py-1.5 text-left font-medium">Item</th>
            <th className="py-1.5 text-right font-medium">Inv qty</th>
            <th className="py-1.5 text-right font-medium">PO qty</th>
            <th className="py-1.5 text-right font-medium">Recd</th>
            <th className="py-1.5 text-right font-medium">Inv price</th>
            <th className="py-1.5 text-right font-medium">PO price</th>
            <th className="py-1.5 text-right font-medium">Line total</th>
          </tr>
        </thead>
        <tbody>
          {invoiceLines.map((line) => {
            const p = find(po, line.item_code)
            const g = find(grn, line.item_code)
            const qtyOff = p && Number(line.qty) !== Number(p.qty_ordered)
            const priceOff = p && Number(line.unit_price) !== Number(p.unit_price)
            const valueOk = p &&
              Math.abs(Number(line.line_total) - Number(p.line_total)) < 0.02
            return (
              <tr key={line.line_no} className="border-b border-white/5 last:border-0">
                <td className="py-1.5 pr-2">
                  <span className="num text-slate-200">{line.item_code}</span>
                  <span className="ml-1.5 text-[10px] text-mute">
                    {line.uom}
                  </span>
                  {!p && <Chip tone="amber" className="ml-1.5">not on PO</Chip>}
                  {valueOk && (qtyOff || priceOff) && (
                    <Chip tone="emerald" className="ml-1.5"
                          title="extended value matches the PO despite the difference">
                      value ok
                    </Chip>
                  )}
                </td>
                <td className={`num py-1.5 text-right
                  ${qtyOff ? 'text-amber-300' : 'text-slate-300'}`}>
                  {line.qty}
                </td>
                <td className="num py-1.5 text-right text-mute">
                  {p?.qty_ordered ?? '—'}
                </td>
                <td className={`num py-1.5 text-right
                  ${g && Number(g.qty_received) < Number(line.qty)
                    ? 'text-rose-300' : 'text-mute'}`}>
                  {g?.qty_received ?? '—'}
                </td>
                <td className={`num py-1.5 text-right
                  ${priceOff ? 'text-amber-300' : 'text-slate-300'}`}>
                  {line.unit_price}
                </td>
                <td className="num py-1.5 text-right text-mute">
                  {p?.unit_price ?? '—'}
                </td>
                <td className="num py-1.5 text-right text-slate-200">
                  {money(line.line_total, currency)}
                </td>
              </tr>
            )
          })}
        </tbody>
      </table>
      {grn.some((g) => g.note) && (
        <p className="mt-2 rounded-lg bg-white/5 px-2.5 py-1.5 text-[11px]
          text-slate-300">
          <span className="text-mute">Receiving note: </span>
          {grn.filter((g) => g.note).map((g) => g.note).join('; ')}
        </p>
      )}
    </div>
  )
}

function AgentTrace({ trace, result }) {
  const finding = result?.matching_finding
  const verdict = result?.policy_verdict

  return (
    <div className="space-y-3">
      {trace?.length > 0 && (
        <ol className="relative space-y-2 border-l border-white/10 pl-4">
          {trace.map((step, i) => (
            <li key={`${step.agent}-${i}`} className="relative">
              <span className="absolute -left-[21px] top-1 h-2 w-2 rounded-full
                bg-violet-400" />
              <p className="text-[11.5px] text-slate-200">{step.label}</p>
              <p className="text-[10px] text-mute">
                <span className="num">{step.agent}</span>
                {step.elapsed_ms != null && ` · ${ms(step.elapsed_ms)}`}
              </p>
            </li>
          ))}
        </ol>
      )}

      {finding && (
        <div className="rounded-xl border border-violet-500/25 bg-violet-500/5 p-3">
          <div className="flex items-center justify-between gap-2">
            <Chip tone="violet">
              {CAUSE_LABEL[finding.variance_cause] || finding.variance_cause}
            </Chip>
            <Chip tone={confidenceTone(finding.confidence)}>
              confidence {pct(finding.confidence, 0)}
            </Chip>
          </div>
          <p className="mt-2 text-[12px] leading-relaxed text-slate-200">
            {finding.explanation}
          </p>
          {finding.quantitative_basis?.length > 0 && (
            <ul className="mt-2 space-y-0.5">
              {finding.quantitative_basis.map((b, i) => (
                <li key={i} className="num text-[11px] text-mute">▸ {b}</li>
              ))}
            </ul>
          )}
          <div className="mt-2 flex flex-wrap gap-1.5">
            {finding.value_reconciles && (
              <Chip tone="emerald">extended value reconciles</Chip>
            )}
            <Chip tone="slate">
              recommends {String(finding.recommended_action).replace(/_/g, ' ')}
            </Chip>
          </div>
        </div>
      )}

      {verdict && (
        <div className={`rounded-xl border p-3 ${verdict.permitted
          ? 'border-emerald-500/25 bg-emerald-500/5'
          : 'border-rose-500/25 bg-rose-500/5'}`}>
          <div className="flex items-center justify-between gap-2">
            <Chip tone={verdict.permitted ? 'emerald' : 'rose'}>
              {verdict.permitted ? 'permitted by contract' : 'not permitted'}
            </Chip>
            {verdict.clause_reference && (
              <Chip tone="sky">
                {verdict.contract_id} clause {verdict.clause_reference}
              </Chip>
            )}
          </div>

          {verdict.quote ? (
            <blockquote className="mt-2 border-l-2 border-sky-400/50 pl-3
              text-[12px] italic leading-relaxed text-slate-200">
              “{verdict.quote}”
            </blockquote>
          ) : (
            <p className="mt-2 text-[12px] text-amber-300">
              No clause found in the corpus — routed to a human rather than guessing.
            </p>
          )}

          {(verdict.limit_applied || verdict.observed_value) && (
            <div className="mt-2 grid grid-cols-2 gap-2 text-[11px]">
              <div className="rounded-lg bg-black/20 px-2 py-1.5">
                <p className="text-[10px] text-mute">Contract limit</p>
                <p className="num text-slate-200">{verdict.limit_applied || '—'}</p>
              </div>
              <div className="rounded-lg bg-black/20 px-2 py-1.5">
                <p className="text-[10px] text-mute">Observed</p>
                <p className="num text-slate-200">{verdict.observed_value || '—'}</p>
              </div>
            </div>
          )}
          <p className="mt-2 text-[11px] text-mute">{verdict.reasoning}</p>
        </div>
      )}
    </div>
  )
}

export default function CaseDetail({ caseFile, onClose, onApprove, onReject, busy, alerts }) {
  const [reason, setReason] = useState('')
  const [showReject, setShowReject] = useState(false)

  if (!caseFile) return null
  const header = caseFile.header || {}
  const extracted = caseFile.extracted || {}
  const conf = extracted.field_confidence || {}
  const match = caseFile.match || {}
  const decision = caseFile.decision || {}
  const currency = header.currency || 'INR'
  const canAct = ['awaiting_approval', 'posted_pending_approval'].includes(caseFile.status)

  // Alerts-based flags (near-duplicate, bank-change)
  const isDuplicate = alerts?.duplicates?.some((d) => d.invoice_id === caseFile.invoice_id)
  const bankChange = alerts?.bank_changes?.some((b) => b.invoice_id === caseFile.invoice_id)

  return (
    <aside className="slide-in fixed inset-y-0 right-0 z-30 flex w-full max-w-[720px]
      flex-col border-l border-white/10 bg-ink-900/97 backdrop-blur-xl">
      <header className="flex items-start justify-between gap-3 border-b
        border-white/10 px-5 py-3.5">
        <div className="min-w-0">
          <div className="flex items-center gap-2">
            <h2 className="num text-[15px] font-semibold">{caseFile.invoice_id}</h2>
            <Chip tone={STATUS_TONE[caseFile.status] || 'slate'}>
              {STATUS_LABEL[caseFile.status] || caseFile.status}
            </Chip>
            {extracted._extraction_mode === 'docai' && (
              <Chip tone="sky">Document AI</Chip>
            )}
          </div>
          <p className="mt-0.5 truncate text-[12px] text-mute">
            {header.vendor_name_raw} · {header.po_ref || 'no PO'} ·{' '}
            <span className="num text-slate-300">
              {money(header.total, currency)}
            </span>
          </p>
        </div>
        <button onClick={onClose}
                className="rounded-lg border border-white/10 px-2 py-1 text-[12px]
                  text-slate-300 hover:bg-white/10">
          Close
        </button>
      </header>

      <div className="mx-5 mt-3 flex items-center gap-2">
        <Chip tone="slate">{header.source_channel || 'ingest'}</Chip>
        {extracted._extraction_mode === 'docai' && (
          <Chip tone="sky">Document AI</Chip>
        )}
        {isDuplicate && <Chip tone="rose">near-duplicate</Chip>}
        {bankChange && <Chip tone="amber">bank-change</Chip>}
        {caseFile.decision?.citation && <Chip tone="sky">cited</Chip>}
        <div className="ml-auto text-[12px] text-mute">{caseFile.status}</div>
      </div>

      <div className="scroll-thin flex-1 space-y-3 overflow-y-auto px-5 py-4">
        {decision.route && (
          <div className={`rounded-xl border px-3.5 py-3 ${decision.route === 'post'
            ? 'border-emerald-500/30 bg-emerald-500/8'
            : 'border-amber-500/30 bg-amber-500/8'}`}>
            <p className="text-[10px] uppercase tracking-[0.12em] text-mute">
              Gate decision
            </p>
            <p className={`mt-0.5 text-[14px] font-semibold ${decision.route === 'post'
              ? 'text-emerald-300' : 'text-amber-300'}`}>
              {decision.route === 'post'
                ? 'Clear to post — touchless'
                : 'Held for human approval'}
            </p>
            {decision.reasons?.length > 0 && (
              <ul className="mt-1.5 space-y-0.5">
                {decision.reasons.map((r) => (
                  <li key={r} className="text-[11.5px] text-slate-300">▸ {r}</li>
                ))}
              </ul>
            )}
            {decision.citation && (
              <p className="mt-1.5 text-[11px] text-sky-300">
                Basis: {decision.citation}
              </p>
            )}
          </div>
        )}

        <div className="grid gap-3 md:grid-cols-2">
          <Panel title="Extracted" hint="Document AI fields and confidence">
            <Field label="Invoice no" value={extracted.invoice_no}
                   confidence={conf.invoice_no} />
            <Field label="Invoice date" value={extracted.invoice_date}
                   confidence={conf.invoice_date} />
            <Field label="Vendor (as printed)" value={extracted.vendor_name_raw}
                   confidence={conf.vendor_name} />
            <Field label="PO reference" value={extracted.po_ref}
                   confidence={conf.po_ref} />
            <Field label="Total" value={money(extracted.total, currency)}
                   confidence={conf.total} />
            <Field label="Remittance account" value={extracted.bank_account}
                   confidence={conf.bank_account} />
          </Panel>

          <Panel title="Three-way match" hint={`route: ${match.route_hint || '—'}`}>
            {match.checks?.length
              ? <ChecksTable checks={match.checks} />
              : <Empty>No checks yet.</Empty>}
          </Panel>
        </div>

        <Panel title="Invoice vs PO vs goods receipt"
               hint="the comparison the deterministic match ran">
          <LineComparison invoiceLines={caseFile.invoice_lines || []}
                          poAndGrn={caseFile.po_and_grn} currency={currency} />
        </Panel>

        {(caseFile.agent_trace?.length > 0 || caseFile.agent_result) && (
          <Panel title="Agent analysis"
                 hint="ADK pipeline on Vertex AI Agent Engine"
                 right={caseFile.agent_result?.elapsed_ms ? (
                   <Chip tone="violet">{ms(caseFile.agent_result.elapsed_ms)}</Chip>
                 ) : null}>
            <AgentTrace trace={caseFile.agent_trace}
                        result={caseFile.agent_result} />
          </Panel>
        )}

        <Panel title="Event timeline" hint="every state change, in order">
          <ol className="space-y-1.5">
            {(caseFile.timeline || []).map((e, i) => (
              <li key={i} className="grid grid-cols-[62px_150px_1fr] items-baseline
                gap-2 text-[11px]">
                <span className="num text-mute">{clock(e.ts)}</span>
                <span className="num text-slate-300">{e.event}</span>
                <span className="truncate text-mute" title={e.detail}>
                  {e.detail}
                </span>
              </li>
            ))}
          </ol>
        </Panel>

        {caseFile.error && (
          <div className="rounded-xl border border-rose-500/30 bg-rose-500/8 px-3 py-2
            text-[11.5px] text-rose-200">
            {caseFile.error}
          </div>
        )}
      </div>

      <footer className="border-t border-white/10 px-5 py-3">
        {showReject ? (
          <div className="space-y-2">
            <input
              autoFocus
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              placeholder="Why are you overriding? This feeds the learning loop."
              className="w-full rounded-lg border border-white/10 bg-black/30 px-3
                py-2 text-[12px] text-paper outline-none
                placeholder:text-mute focus:border-sky-400/50"
            />
            <div className="flex gap-2">
              <Button tone="rose" disabled={!reason.trim() || busy}
                      onClick={() => onReject(caseFile.invoice_id, reason.trim())}>
                Confirm rejection
              </Button>
              <Button onClick={() => setShowReject(false)}>Cancel</Button>
            </div>
          </div>
        ) : (
          <div className="flex items-center gap-2">
            <Button tone="emerald" disabled={!canAct || busy}
                    onClick={() => onApprove(caseFile.invoice_id)}>
              Approve and post
            </Button>
            <Button tone="rose" disabled={!canAct || busy}
                    onClick={() => setShowReject(true)}>
              Reject
            </Button>
            {caseFile.erp?.doc_no && (
              <Chip tone="emerald" className="ml-auto">
                ERP {caseFile.erp.doc_no}
              </Chip>
            )}
            {!canAct && !caseFile.erp && (
              <span className="ml-auto text-[11px] text-mute">
                no action available at this stage
              </span>
            )}
          </div>
        )}
      </footer>
    </aside>
  )
}
