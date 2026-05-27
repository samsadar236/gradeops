import React, { useEffect, useState } from 'react'
import { api } from '../api'
import {
  Button, Card, CardHeader, Badge, Stat, EmptyState, PageHeader,
} from '../components/ui.jsx'

export default function Audit() {
  const [stats, setStats] = useState(null)
  const [entries, setEntries] = useState([])
  const [plag, setPlag] = useState([])
  const [loading, setLoading] = useState(true)

  const load = async () => {
    setLoading(true)
    try {
      const [s, e, p] = await Promise.all([api.stats(), api.audit(), api.plagiarism()])
      setStats(s); setEntries(e); setPlag(p)
    } finally {
      setLoading(false)
    }
  }
  useEffect(() => { load() }, [])

  const pct = (n) => `${Math.round((n || 0) * 100)}%`

  return (
    <div>
      <PageHeader
        title="Audit & analytics"
        description="Immutable record of every grading and review decision. Each row is stamped with the rubric, prompt, and model versions in effect at the time."
        actions={<Button onClick={load}>Refresh</Button>}
      />

      {stats && (
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3 mb-6">
          <Stat label="Total answers" value={stats.total_crops} />
          <Stat label="Reviewed" value={stats.total_reviewed} />
          <Stat
            label="Override rate" value={pct(stats.override_rate)}
            accent={(stats.override_rate || 0) > 0.2 ? 'text-warning-strong' : 'text-ink'}
          />
          <Stat label="Flag rate" value={pct(stats.flag_rate)} />
          <Stat
            label="Mean σ" value={(stats.mean_std_dev || 0).toFixed(2)}
            accent={(stats.mean_std_dev || 0) > 1 ? 'text-warning-strong' : 'text-success-strong'}
          />
          <Stat
            label="Similarity pairs" value={stats.plagiarism_pairs}
            accent={stats.plagiarism_pairs > 0 ? 'text-danger-strong' : 'text-ink'}
          />
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <Card>
          <CardHeader title="Decision log" description="Newest first" />
          <div className="max-h-[64vh] overflow-auto">
            {loading ? (
              <p className="px-5 py-6 text-body-sm text-ink-muted">Loading…</p>
            ) : entries.length === 0 ? (
              <p className="px-5 py-6 text-body-sm text-ink-muted text-center">No audit entries yet.</p>
            ) : (
              <table className="w-full text-body-sm">
                <thead className="sticky top-0 bg-surface-subtle">
                  <tr className="text-left text-label-sm uppercase tracking-wide text-ink-subtle border-b border-border">
                    <th className="px-5 py-2 font-medium">When</th>
                    <th className="px-2 py-2 font-medium">Entity</th>
                    <th className="px-2 py-2 font-medium">Action</th>
                    <th className="px-2 py-2 font-medium">Versions</th>
                    <th className="px-5 py-2 font-medium">Detail</th>
                  </tr>
                </thead>
                <tbody>
                  {entries.map(e => (
                    <tr key={e.id} className="border-b border-border last:border-0 hover:bg-surface-subtle">
                      <td className="px-5 py-2.5 text-ink-muted whitespace-nowrap">
                        {new Date(e.created_at).toLocaleTimeString()}
                      </td>
                      <td className="px-2 py-2.5 text-ink">{e.entity_type}#{e.entity_id}</td>
                      <td className="px-2 py-2.5">
                        <Badge variant={actionVariant(e.action)}>{e.action}</Badge>
                      </td>
                      <td className="px-2 py-2.5 text-label-sm text-ink-subtle">
                        r:{e.rubric_version || '—'} · p:{e.prompt_version || '—'}
                      </td>
                      <td className="px-5 py-2.5 text-ink-muted truncate max-w-[200px]" title={JSON.stringify(e.after)}>
                        {summarizeDelta(e)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </Card>

        <Card>
          <CardHeader
            title="Similarity flags"
            description="Pairs of answers with highly similar reasoning"
          />
          <div className="max-h-[64vh] overflow-auto">
            {loading ? (
              <p className="px-5 py-6 text-body-sm text-ink-muted">Loading…</p>
            ) : plag.length === 0 ? (
              <p className="px-5 py-6 text-body-sm text-ink-muted text-center">No similarity pairs above the configured threshold.</p>
            ) : (
              <table className="w-full text-body-sm">
                <thead className="sticky top-0 bg-surface-subtle">
                  <tr className="text-left text-label-sm uppercase tracking-wide text-ink-subtle border-b border-border">
                    <th className="px-5 py-2 font-medium">Answer A</th>
                    <th className="px-2 py-2 font-medium">Answer B</th>
                    <th className="px-5 py-2 font-medium text-right">Similarity</th>
                  </tr>
                </thead>
                <tbody>
                  {plag.map(p => (
                    <tr key={`${p.crop_a_id}-${p.crop_b_id}`} className="border-b border-border last:border-0">
                      <td className="px-5 py-2.5 text-ink">#{p.crop_a_id}</td>
                      <td className="px-2 py-2.5 text-ink">#{p.crop_b_id}</td>
                      <td className="px-5 py-2.5 text-right">
                        <span className="text-danger-strong font-medium">{(p.similarity * 100).toFixed(1)}%</span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </Card>
      </div>
    </div>
  )
}

function actionVariant(action) {
  if (action === 'approve')  return 'success'
  if (action === 'override') return 'warning'
  if (action === 'flag')     return 'danger'
  return 'neutral'
}

function summarizeDelta(e) {
  const a = e.after || {}
  if (a.final_score !== undefined) return `→ ${a.final_score}`
  if (a.median !== undefined) return `median ${a.median} · σ ${(a.std_dev || 0).toFixed(2)}`
  if (a.title) return a.title
  return '—'
}
