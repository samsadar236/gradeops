import React, { useEffect, useState } from 'react'
import { api } from '../api'
import {
  Button, Card, CardHeader, CardBody, Input, TextArea, Select,
  Field, Badge, EmptyState, PageHeader,
} from '../components/ui.jsx'

const DEFAULT_INSTRUCTIONS = `Base all scoring strictly on evidence visible in the student's handwritten work. If evidence is missing, assign zero — do not guess, infer, or hallucinate.
Award credit for intermediate steps only if they are explicitly written by the student. Do not infer non-trivial reasoning from a correct final answer except for trivial algebraic simplifications.
If the student's solution does not match the question being asked, assign a score of 0.`

const SAMPLE_RUBRIC = {
  title: 'Linear equation — sample',
  question_text: 'Solve for x and show all steps:\n\n2x + 5 = 15',
  max_marks: 10,
  course_instructions: DEFAULT_INSTRUCTIONS,
  criteria: [
    {
      name: 'Isolate the variable term',
      points: 5,
      conditions: 'Student subtracts 5 from both sides to obtain 2x = 10.',
      accept_alternatives: 'Equivalent algebraic rearrangements that arrive at 2x = 10.',
      do_not_deduct_for: 'Minor handwriting or notation differences.',
    },
    {
      name: 'Solve for x',
      points: 5,
      conditions: 'Student divides both sides by 2 and obtains x = 5.',
      accept_alternatives: 'Equivalent forms such as x=5 or x = 5.0.',
      do_not_deduct_for: 'Minor notation differences.',
    },
  ],
}

export default function Rubrics() {
  const [exams, setExams] = useState([])
  const [examId, setExamId] = useState(null)
  const [rubrics, setRubrics] = useState([])
  const [editing, setEditing] = useState(null)
  const [loading, setLoading] = useState(true)

  const refresh = async (eid) => {
    setLoading(true)
    try {
      const es = await api.listExams()
      setExams(es)
      const useExam = eid ?? examId ?? (es[0]?.id || null)
      setExamId(useExam)
      setRubrics(useExam ? await api.listRubrics(useExam) : [])
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { refresh() }, []) // eslint-disable-line

  const createExam = async () => {
    const title = prompt('Name this exam')
    if (!title) return
    const e = await api.createExam({ title })
    await refresh(e.id)
  }

  const startBlank = () => {
    if (!examId) { alert('Create an exam first.'); return }
    setEditing({
      _new: true, exam_id: examId,
      title: '', question_text: '', max_marks: 10,
      course_instructions: DEFAULT_INSTRUCTIONS,
      criteria: [{ name: '', points: 1, conditions: '', accept_alternatives: '', do_not_deduct_for: '' }],
    })
  }

  const startSample = () => {
    if (!examId) { alert('Create an exam first.'); return }
    setEditing({ _new: true, exam_id: examId, ...SAMPLE_RUBRIC })
  }

  const save = async (r) => {
    const { _new, ...payload } = r
    await api.createRubric(payload)
    setEditing(null)
    await refresh()
  }

  if (editing) {
    return <RubricEditor initial={editing} onSave={save} onCancel={() => setEditing(null)} />
  }

  return (
    <div>
      <PageHeader
        title="Rubrics"
        description="Define grading criteria for each question. Criteria support alternatives and explicit do-not-deduct rules."
        actions={
          <>
            <ExamPicker exams={exams} value={examId} onChange={(id) => refresh(id)} />
            <Button onClick={createExam}>New exam</Button>
            <Button onClick={startSample}>Load sample</Button>
            <Button variant="primary" onClick={startBlank}>New rubric</Button>
          </>
        }
      />

      {loading ? (
        <Card><CardBody><p className="text-body-sm text-ink-muted">Loading…</p></CardBody></Card>
      ) : exams.length === 0 ? (
        <EmptyState
          title="No exams yet"
          description="Create an exam first, then add one or more rubrics to it. Each question on the exam needs its own rubric."
          action={<Button variant="primary" onClick={createExam}>Create your first exam</Button>}
        />
      ) : rubrics.length === 0 ? (
        <EmptyState
          title="No rubrics for this exam"
          description="Add a rubric to start grading. Use a blank rubric or load a sample to see the structure."
          action={
            <div className="flex gap-2 justify-center">
              <Button onClick={startSample}>Load sample</Button>
              <Button variant="primary" onClick={startBlank}>New rubric</Button>
            </div>
          }
        />
      ) : (
        <div className="grid gap-4">
          {rubrics.map(r => <RubricCard key={r.id} rubric={r} />)}
        </div>
      )}
    </div>
  )
}

function ExamPicker({ exams, value, onChange }) {
  return (
    <Select value={value || ''} onChange={e => onChange(Number(e.target.value))} className="!w-auto min-w-[200px]">
      {exams.length === 0 && <option value="">No exams</option>}
      {exams.map(e => <option key={e.id} value={e.id}>{e.title}</option>)}
    </Select>
  )
}

function RubricCard({ rubric }) {
  return (
    <Card>
      <div className="px-5 py-4">
        <div className="flex items-start justify-between gap-4">
          <div className="min-w-0">
            <div className="flex items-center gap-2 mb-1">
              <h3 className="text-headline-sm text-ink truncate">{rubric.title}</h3>
              <Badge variant="brand">{rubric.version}</Badge>
              <Badge>{rubric.max_marks} pts</Badge>
              <Badge>{rubric.criteria.length} criteria</Badge>
            </div>
            <p className="text-body-sm text-ink-muted whitespace-pre-line">{rubric.question_text}</p>
          </div>
          <span className="text-label-sm text-ink-faint shrink-0">#{rubric.id}</span>
        </div>

        <div className="mt-4 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-2">
          {rubric.criteria.map((c, i) => (
            <div key={i} className="rounded border border-border bg-surface-subtle px-3 py-2.5">
              <div className="flex items-center justify-between mb-0.5">
                <span className="text-label-sm uppercase tracking-wide text-ink-subtle">#{i + 1}</span>
                <span className="text-label-sm font-medium text-ink">{c.points} pts</span>
              </div>
              <p className="text-body-sm text-ink font-medium truncate">{c.name}</p>
              <p className="text-label-sm text-ink-muted line-clamp-2 mt-0.5">{c.conditions}</p>
            </div>
          ))}
        </div>
      </div>
    </Card>
  )
}

// ===========================================================================
// Editor
// ===========================================================================
function RubricEditor({ initial, onSave, onCancel }) {
  const [r, setR] = useState(initial)
  const [submitted, setSubmitted] = useState(false)

  const update = (patch) => setR({ ...r, ...patch })
  const updateCrit = (i, patch) => update({
    criteria: r.criteria.map((c, idx) => idx === i ? { ...c, ...patch } : c),
  })
  const addCrit = () => update({
    criteria: [...r.criteria, { name: '', points: 1, conditions: '', accept_alternatives: '', do_not_deduct_for: '' }],
  })
  const removeCrit = (i) => update({ criteria: r.criteria.filter((_, idx) => idx !== i) })

  const total = r.criteria.reduce((s, c) => s + (Number(c.points) || 0), 0)
  const mismatch = total !== Number(r.max_marks)
  const allCritsNamed = r.criteria.every(c => c.name.trim())
  const canSave = r.title.trim() && r.question_text.trim() && r.criteria.length > 0 && allCritsNamed

  const onSaveClick = () => {
    setSubmitted(true)
    if (canSave) onSave(r)
  }

  return (
    <div>
      <PageHeader
        title={initial._new ? 'New rubric' : 'Edit rubric'}
        description="Fine-grained criteria with explicit conditions, alternatives, and do-not-deduct rules give the grader the least room for misinterpretation."
        actions={
          <>
            <Button onClick={onCancel}>Cancel</Button>
            <Button variant="primary" onClick={onSaveClick} disabled={!canSave}>Save rubric</Button>
          </>
        }
      />

      {submitted && !canSave && (
        <div className="mb-4 px-4 py-3 rounded-lg border border-danger/30 bg-danger-subtle text-body-sm text-danger-strong">
          Fill in the rubric title, question text, and a name for every criterion before saving.
        </div>
      )}

      <Card className="mb-4">
        <CardHeader title="Basics" />
        <CardBody>
          <div className="grid grid-cols-3 gap-4 mb-4">
            <div className="col-span-2">
              <Field label="Title" required>
                <Input
                  value={r.title}
                  onChange={e => update({ title: e.target.value })}
                  placeholder="Short, descriptive name"
                  invalid={submitted && !r.title.trim()}
                />
              </Field>
            </div>
            <Field label="Max marks">
              <Input
                type="number" min={0}
                value={r.max_marks}
                onChange={e => update({ max_marks: Number(e.target.value) || 0 })}
              />
            </Field>
          </div>

          <Field label="Question text" required hint="Exactly as the question appears on the exam.">
            <TextArea
              rows={3}
              value={r.question_text}
              onChange={e => update({ question_text: e.target.value })}
              invalid={submitted && !r.question_text.trim()}
            />
          </Field>
        </CardBody>
      </Card>

      <Card className="mb-4">
        <CardHeader
          title="Grading instructions"
          description="Course-level anti-hallucination guardrails passed to the grader on every call."
        />
        <CardBody>
          <TextArea
            rows={5}
            value={r.course_instructions}
            onChange={e => update({ course_instructions: e.target.value })}
          />
        </CardBody>
      </Card>

      <Card>
        <CardHeader
          title="Criteria"
          description={`${total} / ${r.max_marks} pts allocated${mismatch ? '  •  totals do not match' : ''}`}
          action={<Button onClick={addCrit}>Add criterion</Button>}
        />
        <div className="divide-y divide-border">
          {r.criteria.map((c, i) => (
            <CriterionRow
              key={i}
              index={i}
              criterion={c}
              showError={submitted && !c.name.trim()}
              onChange={(patch) => updateCrit(i, patch)}
              onRemove={() => removeCrit(i)}
              canRemove={r.criteria.length > 1}
            />
          ))}
        </div>
      </Card>
    </div>
  )
}

function CriterionRow({ index, criterion, showError, onChange, onRemove, canRemove }) {
  return (
    <div className="px-5 py-4">
      {/* Top row: index + name + points + remove. Uses GRID with explicit
          column widths so the name field cannot get visually squashed. */}
      <div className="grid items-center gap-3 mb-3"
           style={{ gridTemplateColumns: '32px minmax(0,1fr) 96px auto' }}>
        <span className="text-label-md font-medium text-ink-subtle">#{index + 1}</span>
        <Input
          value={criterion.name}
          onChange={e => onChange({ name: e.target.value })}
          placeholder="Criterion name"
          invalid={showError}
        />
        <div className="flex items-center gap-1.5">
          <Input
            type="number" min={0} step="0.5"
            value={criterion.points}
            onChange={e => onChange({ points: Number(e.target.value) || 0 })}
            className="text-right"
          />
          <span className="text-label-sm text-ink-muted">pts</span>
        </div>
        <Button
          variant="ghost" size="icon" onClick={onRemove} disabled={!canRemove}
          aria-label="Remove criterion"
        >
          <span aria-hidden="true">×</span>
        </Button>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-3 pl-11">
        <Field label="Conditions">
          <TextArea rows={3}
            value={criterion.conditions}
            onChange={e => onChange({ conditions: e.target.value })}
            placeholder="What must the student show to earn these points?"
          />
        </Field>
        <Field label="Accept also">
          <TextArea rows={3}
            value={criterion.accept_alternatives}
            onChange={e => onChange({ accept_alternatives: e.target.value })}
            placeholder="Equivalent forms or alternative paths"
          />
        </Field>
        <Field label="Do not deduct for">
          <TextArea rows={3}
            value={criterion.do_not_deduct_for}
            onChange={e => onChange({ do_not_deduct_for: e.target.value })}
            placeholder="Surface issues to ignore"
          />
        </Field>
      </div>
    </div>
  )
}
