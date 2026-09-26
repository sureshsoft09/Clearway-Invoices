import { useCallback, useEffect, useRef, useState } from 'react'

const BASE = import.meta.env.VITE_API_BASE || ''

async function request(path, options) {
  const res = await fetch(`${BASE}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  })
  if (!res.ok) {
    let detail = res.statusText
    try {
      const body = await res.json()
      detail = body.detail || JSON.stringify(body)
    } catch { /* non-JSON error body */ }
    throw new Error(`${res.status} ${detail}`)
  }
  return res.json()
}

const post = (path, body) =>
  request(path, { method: 'POST', body: JSON.stringify(body ?? {}) })

export const api = {
  health: () => request('/api/health'),
  invoices: () => request('/api/invoices'),
  invoice: (id) => request(`/api/invoices/${id}`),
  checks: (id) => request(`/api/checks/${id}`),
  metrics: () => request('/api/metrics'),
  alerts: () => request('/api/alerts'),
  ingest: (id, mode = 'fixture') => post(`/api/invoices/${id}/ingest?mode=${mode}`),
  runSync: (id, mode = 'fixture') => post(`/api/invoices/${id}/run?mode=${mode}`),
  replay: ({ limit = 100, mode = 'fixture', reset = true } = {}) =>
    post(`/api/batch/replay?limit=${limit}&mode=${mode}&reset=${reset}`),
  approve: (id, actor = 'ap.reviewer', note) =>
    post(`/api/invoices/${id}/approve`, { actor, note }),
  reject: (id, override_reason, actor = 'ap.reviewer') =>
    post(`/api/invoices/${id}/reject`, { actor, override_reason }),
}

/**
 * Poll an async function on an interval.
 *
 * Swap this for a Firestore onSnapshot subscription on `cases` and every consumer
 * keeps working unchanged - the shape it returns is the contract.
 */
export function usePoll(fn, intervalMs = 1500, { enabled = true } = {}) {
  const [data, setData] = useState(null)
  const [error, setError] = useState(null)
  const [loading, setLoading] = useState(true)
  const alive = useRef(true)
  const fnRef = useRef(fn)
  fnRef.current = fn

  const tick = useCallback(async () => {
    try {
      const result = await fnRef.current()
      if (alive.current) {
        setData(result)
        setError(null)
      }
    } catch (err) {
      if (alive.current) setError(err.message)
    } finally {
      if (alive.current) setLoading(false)
    }
  }, [])

  useEffect(() => {
    alive.current = true
    if (!enabled) return () => { alive.current = false }
    tick()
    const handle = setInterval(tick, intervalMs)
    return () => {
      alive.current = false
      clearInterval(handle)
    }
  }, [enabled, intervalMs, tick])

  return { data, error, loading, refresh: tick }
}
