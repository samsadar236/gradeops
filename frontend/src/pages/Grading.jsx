import React, { useEffect, useState } from 'react'
import { api } from '../api'
import {
  Button, Card, CardHeader, CardBody, Select, Field, Badge,
  EmptyState, PageHeader,
} from '../components/ui.jsx'

export default function Grading() {
  const [exams, setExams] = useState([])
  const [examId, setExamId] = useState(null)
  const [rubrics, setRubrics] = useState([])
  const [rubricId, setRubricId] = useState(null)
  const [files, setFiles] = useState([])
  const [batch, setBatch] = useState([])
  const [running, setRunning] = useState(false)

  const refresh = async () => {
    const es = await api.listExams()
    setExams(es)
    const eid = examId ?? es[0]?.id ?? null
    setExamId(eid)
    if (eid) {
      const rs = await api.listRubrics(eid)
      setRubrics(rs)
      if (!rubricId && rs[0]) setRubricId(rs[0].id)
    }
  }
  useEffect(() => { refresh() }, []) // eslint-disable-line
  useEffect(() => { if (examId) api.listRubrics(examId).then(setRubrics) }, [examId])

  const onPickFiles = (e) => setFiles(Array.from(e.target.files || []))

  const runBatch = async () => {
    if (!examId || !rubricId || !files.length) return
    setRunning(true)
    const fresh = files.map((f, i) => ({
      id: `${Date.now()}_${i}`,
      name: f.name,
      status: 'queued',
    }))
    setBatch(fresh)
    for (let i = 0; i < files.length; i++) {
      const f = files[i]
      setBatch(b => b.map((x, idx) => idx === i ? { ...x, status: 'grading' } : x))
      try {
        const res = await api.uploadPaper(examId, rubricId, f)
        setBatch(b => b.map((x, idx) => idx === i ? {
          ...x, status: 'done',
          paperId: res.paper_id, anonId: res.student_anon_id,
          cropIds: res.crop_ids,
        } : x))
      } catch (err) {
        setBatch(b => b.map((x, idx) => idx === i ? {
          ...x, status: 'failed',
          error: err?.response?.data?.detail || err.message,
        } : x))
      }
    }
    setRunning(false)
    setFiles([])
  }

const handleDelete = async (paperId) => {
    if (!window.confirm('Delete this exam and all its grades? This cannot be undone.')) return;
    try {
      // Note: If you don't have api.delete in your api.js, you can use standard fetch:
      // await fetch(`http://localhost:8000/papers/${paperId}`, { method: 'DELETE' })
      // Or if your API object has an axios instance, adjust accordingly.
      await api.deletePaper ? await api.deletePaper(paperId) : await fetch(`/papers/${paperId}`, { method: 'DELETE' });
      
      // Remove it from the batch UI so you know it's gone
      setBatch((prevBatch) => prevBatch.filter((item) => item.paperId !== paperId));
    } catch (err) {
      alert(err?.response?.data?.detail || 'Failed to delete the paper.');
    }
  };

  const rubric = rubrics.find(r => r.id === rubricId)
  const anyDone = batch.some(b => b.status === 'done')

  return (
    <div>
      <PageHeader
        title="Grading"
        description="Upload scanned answer sheets. The system extracts each answer region, transcribes the handwriting, and grades against the selected rubric."
      />

      {exams.length === 0 ? (
        <EmptyState
          title="Create an exam and a rubric first"
          description="Go to the Rubrics tab, create an exam, and add at least one rubric. Then come back here to upload answer sheets."
        />
      ) : (
        <>
          <Card className="mb-4">
            <CardBody>
              <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
                <Field label="Exam">
                  <Select value={examId || ''} onChange={e => setExamId(Number(e.target.value))}>
                    {exams.map(e => <option key={e.id} value={e.id}>{e.title}</option>)}
                  </Select>
                </Field>
                <Field label="Rubric">
                  <Select value={rubricId || ''} onChange={e => setRubricId(Number(e.target.value))}>
                    {rubrics.length === 0 && <option value="">No rubrics in this exam</option>}
                    {rubrics.map(r => <option key={r.id} value={r.id}>{r.title} ({r.version})</option>)}
                  </Select>
                </Field>
                <Field label="Answer sheets" hint="PDF or image. One student per file.">
                  <label className="cursor-pointer">
                    <input type="file" accept="application/pdf,image/*" multiple
                           onChange={onPickFiles} className="sr-only" />
                    <span className="block w-full h-9 px-3 rounded border border-dashed border-border bg-surface-subtle text-body-sm text-ink-muted flex items-center hover:border-brand hover:bg-brand-subtle hover:text-brand transition-colors">
                      {files.length > 0
                        ? `${files.length} file${files.length === 1 ? '' : 's'} selected`
                        : 'Click to choose files'}
                    </span>
                  </label>
                </Field>
              </div>

              {rubric && (
                <div className="mt-4 rounded border border-border bg-surface-subtle px-4 py-3">
                  <div className="flex items-center gap-2 mb-1">
                    <Badge variant="brand">{rubric.version}</Badge>
                    <span className="text-label-md text-ink font-medium">{rubric.title}</span>
                    <span className="text-label-sm text-ink-muted">· {rubric.max_marks} pts · {rubric.criteria.length} criteria</span>
                  </div>
                  <p className="text-body-sm text-ink-muted whitespace-pre-line line-clamp-2">{rubric.question_text}</p>
                </div>
              )}

              <div className="mt-4 flex items-center justify-between">
                <span className="text-label-md text-ink-muted">
                  {files.length} file{files.length === 1 ? '' : 's'} queued
                </span>
                <Button
                  variant="primary" onClick={runBatch}
                  disabled={!rubricId || !files.length || running}
                >
                  {running ? 'Grading…' : `Run grading on ${files.length || 0}`}
                </Button>
              </div>
            </CardBody>
          </Card>

          {batch.length > 0 && (
            <Card>
              <CardHeader title="Batch progress" />
              <div className="divide-y divide-border">
                {batch.map(item => <BatchRow key={item.id} item={item} onDelete={handleDelete} />)}
              </div>
            </Card>
          )}

          {anyDone && (
            <p className="mt-6 text-body-sm text-ink-muted">
              Done. Open the <span className="text-brand font-medium">Review</span> tab to see grades and approve, override, or flag each answer.
            </p>
          )}
        </>
      )}
    </div>
  )
}

function BatchRow({ item, onDelete }) {
  return (
    <div className="flex items-center gap-3 px-5 py-3">
      <span className="flex-1 text-body-sm text-ink truncate">{item.name}</span>
      {item.status === 'queued'  && <Badge>queued</Badge>}
      {item.status === 'grading' && <Badge variant="info">Grading…</Badge>}
      {item.status === 'done'    && (
        <>
          <Badge variant="success">✓ {item.cropIds?.length || 0} answer{item.cropIds?.length === 1 ? '' : 's'}</Badge>
          <span className="text-label-sm text-ink-subtle">{item.anonId}</span>
          
          <button
            onClick={() => onDelete(item.paperId)}
            className="text-sm font-medium text-red-600 hover:text-red-800 transition-colors px-2 py-1 border border-transparent hover:border-red-200 rounded-md"
          >
            Delete
          </button>
        </>
      )}
      {item.status === 'failed'  && (
        <Badge variant="danger" title={item.error}>Failed</Badge>
      )}
    </div> 
  )
}
