const TONES = {
  emerald: 'bg-emerald-500/12 text-emerald-300 border-emerald-500/30',
  amber: 'bg-amber-500/12 text-amber-300 border-amber-500/30',
  rose: 'bg-rose-500/12 text-rose-300 border-rose-500/30',
  sky: 'bg-sky-500/12 text-sky-300 border-sky-500/30',
  violet: 'bg-violet-500/12 text-violet-300 border-violet-500/30',
  slate: 'bg-white/5 text-slate-300 border-white/10',
}

const BARS = {
  emerald: 'bg-emerald-400', amber: 'bg-amber-400', rose: 'bg-rose-400',
  sky: 'bg-sky-400', violet: 'bg-violet-400', slate: 'bg-slate-400',
}

export function Chip({ tone = 'slate', children, className = '', title }) {
  return (
    <span
      title={title}
      className={`inline-flex items-center gap-1 rounded-md border px-1.5 py-0.5
        text-[11px] font-medium leading-none ${TONES[tone] || TONES.slate} ${className}`}
    >
      {children}
    </span>
  )
}

export function Panel({ title, hint, right, children, className = '', bodyClass = '' }) {
  return (
    <section className={`panel ${className}`}>
      {(title || right) && (
        <header className="flex items-baseline justify-between gap-3 border-b
          border-white/5 px-4 py-2.5">
          <div>
            <h2 className="text-[13px] font-semibold tracking-tight">{title}</h2>
            {hint && <p className="text-[11px] text-mute">{hint}</p>}
          </div>
          {right}
        </header>
      )}
      <div className={`px-4 py-3 ${bodyClass}`}>{children}</div>
    </section>
  )
}

export function Stat({ label, value, sub, tone = 'slate', accent }) {
  return (
    <div className="panel card-hover px-4 py-3">
      <p className="text-[10px] uppercase tracking-[0.13em] text-mute">{label}</p>
      <p className={`num mt-1.5 text-2xl font-semibold leading-none
        ${accent || 'text-paper'}`}>{value}</p>
      {sub && (
        <p className="mt-1.5 text-[11px] text-mute">
          {tone !== 'slate' && (
            <span className={`mr-1 inline-block h-1.5 w-1.5 rounded-full
              ${BARS[tone]}`} />
          )}
          {sub}
        </p>
      )}
    </div>
  )
}

export function Meter({ segments, height = 8 }) {
  const total = segments.reduce((sum, s) => sum + (s.value || 0), 0) || 1
  return (
    <div className="flex overflow-hidden rounded-full bg-white/5"
         style={{ height }}>
      {segments.map((s) => (
        <div
          key={s.label}
          title={`${s.label}: ${s.value}`}
          className={`${BARS[s.tone] || BARS.slate} transition-all duration-500`}
          style={{ width: `${(s.value / total) * 100}%` }}
        />
      ))}
    </div>
  )
}

export function Bar({ value, max, tone = 'sky', label }) {
  const width = max ? Math.min(100, (value / max) * 100) : 0
  return (
    <div className="flex items-center gap-2">
      <div className="h-1.5 flex-1 overflow-hidden rounded-full bg-white/5">
        <div className={`h-full rounded-full ${BARS[tone]} transition-all duration-500`}
             style={{ width: `${width}%` }} />
      </div>
      <span className="num w-9 text-right text-[11px] text-mute">
        {label ?? value}
      </span>
    </div>
  )
}

export function Tick({ ok }) {
  return ok
    ? <span className="text-emerald-400">✓</span>
    : <span className="text-rose-400">✕</span>
}

export function Empty({ children }) {
  return (
    <p className="py-8 text-center text-[12px] text-mute">{children}</p>
  )
}

export function Button({ tone = 'slate', children, ...props }) {
  const styles = {
    emerald: 'bg-emerald-500/15 text-emerald-200 border-emerald-500/40 hover:bg-emerald-500/25',
    rose: 'bg-rose-500/15 text-rose-200 border-rose-500/40 hover:bg-rose-500/25',
    sky: 'bg-sky-500/15 text-sky-200 border-sky-500/40 hover:bg-sky-500/25',
    slate: 'bg-white/5 text-slate-200 border-white/10 hover:bg-white/10',
  }
  return (
    <button
      {...props}
      className={`rounded-lg border px-3 py-1.5 text-[12px] font-medium transition
        disabled:cursor-not-allowed disabled:opacity-40 ${styles[tone]}
        ${props.className || ''}`}
    >
      {children}
    </button>
  )
}
