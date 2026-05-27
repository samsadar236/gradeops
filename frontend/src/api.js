import axios from 'axios'

// 1. Generate or retrieve a unique, invisible session ID for this browser
const getSessionId = () => {
  let sessionId = localStorage.getItem('gradeops_session_id');
  if (!sessionId) {
    // Fallback included just in case crypto isn't supported
    sessionId = typeof crypto !== 'undefined' && crypto.randomUUID 
      ? crypto.randomUUID() 
      : 'sess_' + Math.random().toString(36).substr(2, 9);
    localStorage.setItem('gradeops_session_id', sessionId);
  }
  return sessionId;
};

// 2. Attach the Session ID to the Axios client headers
const client = axios.create({
  baseURL: '/api', // <--- FIXED: Now ALWAYS uses /api for every environment
  timeout: 600_000,
  headers: {
    'X-Session-ID': getSessionId() 
  }
})

export const api = {
  health: () => client.get('/health').then(r => r.data),
  users:  () => client.get('/users').then(r => r.data),

  // Exams
  createExam: (payload) => client.post('/exams', payload).then(r => r.data),
  listExams:  () => client.get('/exams').then(r => r.data),

  // Rubrics
  createRubric: (payload) => client.post('/rubrics', payload).then(r => r.data),
  listRubrics:  (examId) => client.get('/rubrics', { params: examId ? { exam_id: examId } : {} }).then(r => r.data),

  // Papers / upload
  uploadPaper: (examId, rubricId, file, anonId) => {
    const fd = new FormData()
    fd.append('exam_id', examId)
    fd.append('rubric_id', rubricId)
    if (anonId) fd.append('student_anon_id', anonId)
    fd.append('file', file)
    return client.post('/papers/upload', fd, {
      headers: { 'Content-Type': 'multipart/form-data' },
    }).then(r => r.data)
  },

  // Review queue
  reviewQueue: (examId) => client.get('/review/queue', { params: examId ? { exam_id: examId } : {} }).then(r => r.data),
  submitReview: (payload) => client.post('/reviews', payload).then(r => r.data),

  // Audit + stats
  audit: () => client.get('/audit').then(r => r.data),
  plagiarism: () => client.get('/plagiarism').then(r => r.data),
  stats: () => client.get('/stats').then(r => r.data),

  // Crop image URL
  cropImageUrl: (cropId) => `/api/crops/${cropId}/image`,
}