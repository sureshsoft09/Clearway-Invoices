import { useCallback, useEffect, useState } from 'react'
import { api, usePoll } from './api'
import AlertsPanel from './components/AlertsPanel'
import CaseDetail from './components/CaseDetail'
import MetricsStrip from './components/MetricsStrip'
import PipelineBoard from './components/PipelineBoard'
import { Button, Chip } from './components/ui'

const TABS = [
  { key: 'board', label: 'Pipeline' },
  { key: 'alerts', label: 'Alerts' },
]

export default function App() {
  const [tab, setTab] = useState('board')
  const [selected, setSelected] = useState(null)
  const [caseFile, setCaseFile] = useState(null)
  const [mode, setMode] = useState('fixture')
  const [busy, setBusy] = useState(false)
  const [toast, setToast] = useState(null)

  const invoices = usePoll(api.invoices, 1500)
  const metrics = usePoll(api.metrics, 2000)
  const alerts = usePoll(api.alerts, 6000)
  const health = usePoll(api.health, 15000)

  const notify = useCallback((message, tone = 'sky') => {
    setToast({ message, tone })
    setTimeout(() => setToast(null), 3200)
  }, [])

  // Keep the open case fresh while the pipeline is still moving it along.
  useEffect(() => {
    if (!selected) { setCaseFile(null); return }
    let alive = true
    const load = () => api.invoice(selected)
      .then((data) => { if (alive) setCaseFile(data) })
      .catch(() => {})
    load()
    const handle = setInterval(load, 1500)
    return () => { alive = false; clearInterval(handle) }
  }, [selected])

  useEffect(() => {
    const onKey = (e) => { if (e.key === 'Escape') setSelected(null) }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [])

  const withBusy = async (fn, okMessage) => {
    setBusy(true)
    try {
      await fn()
      notify(okMessage, 'emerald')
      invoices.refresh()
      metrics.refresh()
    } catch (err) {
      notify(err.message, 'rose')
    } finally {
      setBusy(false)
    }
  }

  const list = invoices.data?.invoices || []
  const backendDown = invoices.error && !invoices.data

  return (
    <div className="min-h-full">
      <header className="sticky top-0 z-20 border-b border-white/8
        bg-gradient-to-r from-slate-900 to-indigo-900/80 backdrop-blur-xl">
        <div className="mx-auto flex max-w-[1600px] flex-wrap items-center gap-3
          px-5 py-3">
          <div className="min-w-0">
            <h1 className="text-[16px] font-semibold tracking-tight text-paper">
              Autonomous AP
              <span className="ml-2 font-normal text-sky-200/80">
                invoice control tower
              </span>
            </h1>
            <p className="text-[11px] text-mute">
              Document AI · BigQuery three-way match · ADK agents on Agent Engine ·
              Vertex AI Search
            </p>
          </div>

          <nav className="ml-auto flex rounded-lg border border-white/10 bg-white/5 p-0.5">
            {TABS.map((t) => (
              <button
                key={t.key}
                onClick={() => setTab(t.key)}
                className={`rounded-md px-3 py-1 text-[12px] font-medium transition
                  ${tab === t.key
                    ? 'bg-white/12 text-paper'
                    : 'text-mute hover:text-slate-200'}`}
              >
                {t.label}
                {t.key === 'alerts' && alerts.data?.total ? (
                  <span className="num ml-1.5 rounded bg-rose-500/25 px-1
                    text-[10px] text-rose-200">
                    {alerts.data.total}
                  </span>
                ) : null}
              </button>
            ))}
          </nav>

          <div className="flex items-center gap-2">
            <select
              value={mode}
              onChange={(e) => setMode(e.target.value)}
              className="rounded-lg border border-white/10 bg-black/30 px-2 py-1.5
                text-[12px] text-slate-200 outline-none"
              title="fixture replays pre-extracted JSON; docai runs the real processor"
            >
              <option value="fixture">fixture mode</option>
              <option value="docai">Document AI mode</option>
            </select>
            <Button
              tone="sky"
              disabled={busy}
              onClick={() => withBusy(
                () => api.replay({ limit: 100, mode, reset: true }),
                'Replaying 100 invoices',
              )}
            >
              Replay 100
            </Button>
            <Button
              disabled={busy}
              onClick={() => withBusy(
                () => api.runSync('INV-1010', mode),
                'INV-1010 processed',
              )}
              title="unit-of-measure case: extended value reconciles"
            >
              Run INV-1010
            </Button>
            <Button
              disabled={busy}
              onClick={() => withBusy(
                () => api.runSync('INV-1039', mode),
                'INV-1039 processed',
              )}
              title="price uplift above the contractual cap"
            >
              Run INV-1039
            </Button>
          </div>

          <div className="flex items-center gap-1.5 border-l border-white/10 pl-3">
            <span className={`live-dot h-2 w-2 rounded-full ${backendDown
              ? 'bg-rose-400' : 'bg-sky-400'}`} />
            <span className="text-[11px] text-mute">
              {backendDown ? 'backend offline' : 'live'}
            </span>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-[1600px] space-y-4 px-5 py-5">
        {backendDown && (
          <div className="panel border-rose-500/30 bg-rose-500/8 px-4 py-3
            text-[12px] text-rose-200">
            Cannot reach the backend. Start it with{' '}
            <code className="num rounded bg-black/40 px-1.5 py-0.5">
              uvicorn app.main:app --reload --port 8080
            </code>{' '}
            in Src/Backend.
          </div>
        )}

        {health.data?.settings && (
          <p className="num text-[10.5px] text-mute">
            {health.data.settings}
          </p>
        )}

        <MetricsStrip metrics={metrics.data} alerts={alerts.data} />

        {tab === 'board' ? (
          <PipelineBoard invoices={list} selected={selected} onSelect={setSelected} />
        ) : (
          <AlertsPanel alerts={alerts.data} onSelect={(id) => {
            setTab('board'); setSelected(id)
          }} />
        )}
      </main>

      {selected && (
        <>
          <div onClick={() => setSelected(null)}
               className="fixed inset-0 z-20 bg-black/50 backdrop-blur-sm" />
          <CaseDetail
            caseFile={caseFile}
            busy={busy}
            alerts={alerts.data}
            onClose={() => setSelected(null)}
            onApprove={(id) => withBusy(
              () => api.approve(id), `${id} posted to ERP`)}
            onReject={(id, reason) => withBusy(
              () => api.reject(id, reason), `${id} rejected`)}
          />
        </>
      )}

      {toast && (
        <div className={`pop fixed bottom-5 left-1/2 z-40 -translate-x-1/2 rounded-lg
          border px-4 py-2 text-[12px] ${toast.tone === 'rose'
            ? 'border-rose-500/40 bg-rose-500/15 text-rose-200'
            : toast.tone === 'emerald'
              ? 'border-emerald-500/40 bg-emerald-500/15 text-emerald-200'
              : 'border-sky-500/40 bg-sky-500/15 text-sky-200'}`}>
          {toast.message}
        </div>
      )}
    </div>
  )
}
