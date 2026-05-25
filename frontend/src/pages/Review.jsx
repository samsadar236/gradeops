import React, { useCallback, useContext, useEffect, useRef, useState } from 'react'
import { api } from '../api'
import {
  Button, Card, CardHeader, CardBody, Input, Field, Badge,
  EmptyState, PageHeader, Kbd,
} from '../components/ui.jsx'
import { RoleContext } from '../App.jsx'

export default function Review() {
  const { user } = useContext(RoleContext)
  const [queue, setQueue] = useState([])
  const [idx, setIdx] = useState(0)
  const [loading, setLoading] = useState(true)
  const [override, setOverride] = useState({ open: false, score: '', notes: '' })
  const overrideInputRef = useRef(null)

  const load = async () => {
    setLoading(true)
    try {
      const items = await api.reviewQueue()
      setQueue(items)
      setIdx(0)
    } finally {
      setLoading(false)
    }
  }
  useEffect(() => { load() }, [])

  const current = queue[idx]

  const submit = useCallback(async (action, finalScore, notes) => {
    if (!current) return
    await api.submitReview({
      crop_id: current.crop_id,
      action,
      final_score: finalScore,
      notes: notes || '',
      reviewer_id: user?.id,
    })
    setQueue(q => q.filter((_, i) => i !== idx))
    setIdx(i => Math.max(0, Math.min(i, queue.length - 2)))
    setOverride({ open: false, score: '', notes: '' })
  }, [current, idx, queue.length, user])

  const onApprove = () => current && submit('approve', current.aggregate.median, '')
  const onFlag    = () => current && submit('flag', current.aggregate.median, 'Flagged by reviewer')
  const openOverride = () => {
    if (!current) return
    setOverride({ open: true, score: String(current.aggregate.median), notes: '' })
    setTimeout(() => overrideInputRef.current?.focus(), 30)
  }
  const submitOverride = () => {
    const s = Number(override.score)
    if (isNaN(s)) return
    submit('override', s, override.notes)
  }

  // Keyboard shortcuts
  useEffect(() => {
    const handler = (e) => {
      if (override.open) {
        if (e.key === 'Escape') { setOverride({ open: false, score: '', notes: '' }); e.preventDefault() }
        if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) { submitOverride(); e.preventDefault() }
        return
      }
      if (['INPUT', 'TEXTAREA', 'SELECT'].includes(document.activeElement?.tagName)) return
      switch (e.key.toLowerCase()) {
        case 'enter': onApprove(); e.preventDefault(); break
        case 'o': openOverride(); e.preventDefault(); break
        case 'f': onFlag(); e.preventDefault(); break
        case 'j': case 'arrowright':
          setIdx(i => Math.min(i + 1, queue.length - 1)); e.preventDefault(); break
        case 'k': case 'arrowleft':
          setIdx(i => Math.max(i - 1, 0)); e.preventDefault(); break
      }
    }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [override.open, queue.length, current, idx]) // eslint-disable-line

  if (loading) {
    return (
      <div>
        <PageHeader title="Review queue" description="Loading…" />
      </div>
    )
  }

  if (queue.length === 0) {
    return (
      <div>
        <PageHeader
          title="Review queue"
          description="Answers awaiting human approval, sorted by AI uncertainty (highest variance first)."
          actions={<Button onClick={load}>Refresh</Button>}
        />
        <EmptyState
          title="Queue is clear"
          description="Either nothing has been graded yet, or every graded answer has been reviewed. Upload more answer sheets in the Grading tab."
          action={<Button onClick={load}>Refresh queue</Button>}
        />
      </div>
    )
  }

  return (
    <div>
      <PageHeader
        title="Review queue"
        description={`${queue.length} pending · sorted by AI uncertainty (highest variance first)`}
        actions={
          <>
            <div className="hidden md:flex items-center gap-3 text-label-sm text-ink-muted mr-2">
              <span className="flex items-center gap-1"><Kbd>↵</Kbd> approve</span>
              <span className="flex items-center gap-1"><Kbd>O</Kbd> override</span>
              <span className="flex items-center gap-1"><Kbd>F</Kbd> flag</span>
              <span className="flex items-center gap-1"><Kbd>J</Kbd>/<Kbd>K</Kbd> next/prev</span>
            </div>
            <Button onClick={load} variant="ghost">↻</Button>
          </>
        }
      />

      <div className="flex items-center justify-between mb-3">
        <span className="text-label-md text-ink-muted">Item {idx + 1} of {queue.length}</span>
        <div className="flex gap-1">
          <Button variant="ghost" size="sm" onClick={() => setIdx(i => Math.max(0, i - 1))} disabled={idx === 0}>← Prev</Button>
          <Button variant="ghost" size="sm" onClick={() => setIdx(i => Math.min(queue.length - 1, i + 1))} disabled={idx === queue.length - 1}>Next →</Button>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* LEFT: image + metadata */}
        <Card>
          <CardHeader
            title={current.student_anon_id}
            description={`${current.question_id} · ${current.rubric_title}`}
            action={
              <div className="flex items-center gap-2">
                {current.plagiarism_flagged && <Badge variant="danger">Similarity</Badge>}
                <span className="text-label-sm text-ink-subtle">#{current.crop_id}</span>
              </div>
            }
          />
          <div className="bg-surface-subtle p-3 border-t border-border">
            <img
              src={api.cropImageUrl(current.crop_id)}
              alt="student answer"
              className="w-full h-auto max-h-[64vh] object-contain bg-white rounded border border-border"
            />
          </div>
        </Card>

        {/* RIGHT: AI grade panels */}
        <div className="space-y-4">
          {/* Aggregate */}
          <Card>
            <CardHeader title={`AI grade · ${current.aggregate.n_passes} pass${current.aggregate.n_passes === 1 ? '' : 'es'}`} />
            <CardBody>
              <div className="grid grid-cols-4 gap-2">
                <ScoreBlock label="Median" value={current.aggregate.median} accent="text-brand" />
                <ScoreBlock label="Max" value={current.aggregate.max_score} />
                <ScoreBlock label="Min" value={current.aggregate.min_score} />
                <ScoreBlock
                  label="σ"
                  value={current.aggregate.std_dev.toFixed(2)}
                  accent={current.aggregate.std_dev > 1 ? 'text-warning-strong' : 'text-success-strong'}
                />
              </div>
              {current.gradings.length > 1 && (
                <div className="mt-3 flex gap-1.5">
                  {current.gradings.map(g => (
                    <div
                      key={g.id}
                      title={`Pass ${g.pass_num}: ${g.score}/${g.max_score}${g.critic_passed ? '' : ' (critic failed)'}`}
                      className="flex-1 h-7 rounded border border-border bg-surface-subtle flex items-center justify-center text-label-md text-ink"
                    >
                      {g.score}{!g.critic_passed && <span className="ml-1 text-warning">!</span>}
                    </div>
                  ))}
                </div>
              )}
            </CardBody>
          </Card>

          {/* Per-criterion */}
          <Card>
            <CardHeader title="Per-criterion" description="From the median pass" />
            <div className="divide-y divide-border">
              {pickMedianGrading(current).per_criterion.map((c, i) => (
                <div key={i} className="px-5 py-3">
                  <div className="flex items-center justify-between gap-3">
                    <span className="text-body-sm text-ink font-medium">
                      <span className="text-ink-subtle mr-2">#{i + 1}</span>{c.name}
                    </span>
                    <span className="text-body-sm text-ink font-medium">{c.awarded} / {c.max}</span>
                  </div>
                  <p className="text-label-sm text-ink-muted mt-0.5 pl-6">{c.reasoning}</p>
                </div>
              ))}
            </div>
          </Card>

          {/* Justification */}
          <Card>
            <CardHeader title="Justification" />
            <CardBody>
              <p className="text-body-sm text-ink leading-relaxed">
                {pickMedianGrading(current).justification}
              </p>
              {pickMedianGrading(current).flags?.length > 0 && (
                <div className="mt-3 flex gap-1.5 flex-wrap">
                  {pickMedianGrading(current).flags.map(f => (
                    <Badge key={f} variant="warning">{f}</Badge>
                  ))}
                </div>
              )}
            </CardBody>
          </Card>

          {/* Actions */}
          <Card className="border-brand/20 bg-brand-subtle/40">
            <CardBody>
              {!override.open ? (
                <div className="flex items-center gap-2">
                  <Button variant="primary" onClick={onApprove}>
                    <Kbd>↵</Kbd> Approve {current.aggregate.median}
                  </Button>
                  <Button onClick={openOverride}>
                    <Kbd>O</Kbd> Override
                  </Button>
                  <Button variant="danger" onClick={onFlag}>
                    <Kbd>F</Kbd> Flag
                  </Button>
                </div>
              ) : (
                <div className="space-y-3">
                  <div className="grid grid-cols-3 gap-3">
                    <Field label={`New score (0 — ${current.gradings[0]?.max_score || 0})`}>
                      <Input
                        ref={overrideInputRef} type="number" step="0.5" min="0"
                        max={current.gradings[0]?.max_score || 0}
                        value={override.score}
                        onChange={e => setOverride({ ...override, score: e.target.value })}
                      />
                    </Field>
                    <div className="col-span-2">
                      <Field label="Note (optional)">
                        <Input
                          value={override.notes}
                          onChange={e => setOverride({ ...override, notes: e.target.value })}
                          placeholder="Why you changed the score"
                        />
                      </Field>
                    </div>
                  </div>
                  <div className="flex gap-2 justify-end">
                    <Button onClick={() => setOverride({ open: false, score: '', notes: '' })}>
                      <Kbd>Esc</Kbd> Cancel
                    </Button>
                    <Button variant="success" onClick={submitOverride}>
                      <Kbd>⌘↵</Kbd> Save override
                    </Button>
                  </div>
                </div>
              )}
            </CardBody>
          </Card>
        </div>
      </div>

      {/* Transcript drawer */}
      <details className="mt-4 group">
        <summary className="list-none cursor-pointer rounded-lg border border-border bg-surface px-5 py-3 text-label-md text-ink-muted hover:text-ink hover:bg-surface-subtle transition-colors">
          <span className="inline-flex items-center gap-2">
            <span className="text-ink-faint group-open:rotate-90 transition-transform">›</span>
            OCR transcript
          </span>
        </summary>
        <pre className="mt-2 p-4 rounded-lg border border-border bg-surface text-body-sm text-ink whitespace-pre-wrap font-sans leading-relaxed">
{current.gradings[0]?.transcript || '(no transcript captured)'}
        </pre>
      </details>
    </div>
  )
}

function pickMedianGrading(item) {
  const sorted = [...item.gradings].sort(
    (a, b) => Math.abs(a.score - item.aggregate.median) - Math.abs(b.score - item.aggregate.median)
  )
  return sorted[0] || item.gradings[0]
}

function ScoreBlock({ label, value, accent }) {
  return (
    <div className="rounded border border-border bg-surface px-3 py-2.5">
      <div className="text-label-sm uppercase tracking-wide text-ink-subtle">{label}</div>
      <div className={`text-headline-md ${accent || 'text-ink'}`}>{value}</div>
    </div>
  )
}
