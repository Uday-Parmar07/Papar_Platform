import type {
  GenerateExamPayload,
  GenerateExamResponse,
  Question,
  TopicListResponse,
  SubjectListResponse,
  VerifyResponse,
} from '../types'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000/api/v1'

const jsonHeaders = {
  'Content-Type': 'application/json',
}

async function handleResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const detail = await response.text()
    throw new Error(detail || 'Request failed')
  }
  return response.json() as Promise<T>
}

export async function generateExam(payload: GenerateExamPayload): Promise<GenerateExamResponse> {
  const response = await fetch(`${API_BASE_URL}/exams/generate`, {
    method: 'POST',
    headers: jsonHeaders,
    body: JSON.stringify(payload),
  })
  return handleResponse<GenerateExamResponse>(response)
}

export async function fetchSubjects(): Promise<SubjectListResponse> {
  const response = await fetch(`${API_BASE_URL}/exams/subjects`)
  return handleResponse<SubjectListResponse>(response)
}

export async function fetchTopics(subjectId: string): Promise<TopicListResponse> {
  const response = await fetch(`${API_BASE_URL}/exams/subjects/${encodeURIComponent(subjectId)}/topics`)
  return handleResponse<TopicListResponse>(response)
}

export async function verifyQuestions(questions: Question[]): Promise<VerifyResponse> {
  const response = await fetch(`${API_BASE_URL}/exams/verify`, {
    method: 'POST',
    headers: jsonHeaders,
    body: JSON.stringify({ questions }),
  })
  return handleResponse<VerifyResponse>(response)
}

export async function downloadPdf(payload: { questions: Question[]; title: string }): Promise<Blob> {
  const response = await fetch(`${API_BASE_URL}/exams/pdf`, {
    method: 'POST',
    headers: jsonHeaders,
    body: JSON.stringify({
      metadata: { title: payload.title },
      questions: payload.questions,
    }),
  })

  if (!response.ok) {
    const detail = await response.text()
    throw new Error(detail || 'Unable to download PDF')
  }

  return response.blob()
}
