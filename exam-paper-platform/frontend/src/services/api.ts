import type {
  GenerateAnswersResponse,
  GenerateExamPayload,
  GenerateExamResponse,
  Question,
  VerifyResponse,
  DashboardResponse,
  ExplainPayload,
  ExplainResponse,
  GeneratePaperPayload,
  GeneratePaperResponse,
  LoginPayload,
  PaperDetail,
  PaperHistoryItem,
  RegisterPayload,
  SubjectListResponse,
  TokenResponse,
  TopicListResponse,
} from '../types'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000/api/v1'
const TOKEN_KEY = 'exam_platform_token'

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

function authHeaders(): Record<string, string> {
  const token = localStorage.getItem(TOKEN_KEY)
  return token ? { Authorization: `Bearer ${token}` } : {}
}

export function setToken(token: string): void {
  localStorage.setItem(TOKEN_KEY, token)
}

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY)
}

export function clearToken(): void {
  localStorage.removeItem(TOKEN_KEY)
}

export async function register(payload: RegisterPayload): Promise<void> {
  const response = await fetch(`${API_BASE_URL}/auth/register`, {
    method: 'POST',
    headers: jsonHeaders,
    body: JSON.stringify(payload),
  })
  if (!response.ok) {
    const detail = await response.text()
    throw new Error(detail || 'Registration failed')
  }
}

export async function login(payload: LoginPayload): Promise<TokenResponse> {
  const response = await fetch(`${API_BASE_URL}/auth/login`, {
    method: 'POST',
    headers: jsonHeaders,
    body: JSON.stringify(payload),
  })
  return handleResponse<TokenResponse>(response)
}

export async function fetchDashboard(): Promise<DashboardResponse> {
  const response = await fetch(`${API_BASE_URL}/dashboard`, {
    headers: { ...authHeaders() },
  })
  return handleResponse<DashboardResponse>(response)
}

export async function fetchSubjects(): Promise<SubjectListResponse> {
  const response = await fetch(`${API_BASE_URL}/exams/subjects`)
  return handleResponse<SubjectListResponse>(response)
}

export async function fetchTopics(subjectId: string): Promise<TopicListResponse> {
  const response = await fetch(`${API_BASE_URL}/exams/subjects/${encodeURIComponent(subjectId)}/topics`)
  return handleResponse<TopicListResponse>(response)
}

export async function generateExam(payload: GenerateExamPayload): Promise<GenerateExamResponse> {
  const response = await fetch(`${API_BASE_URL}/exams/generate`, {
    method: 'POST',
    headers: {
      ...jsonHeaders,
      ...authHeaders(),
    },
    body: JSON.stringify(payload),
  })
  return handleResponse<GenerateExamResponse>(response)
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

export async function generateAnswers(payload: {
  questions: Question[]
  namespace?: string
}): Promise<GenerateAnswersResponse> {
  const body: Record<string, unknown> = { questions: payload.questions }
  if (payload.namespace && payload.namespace.trim().length > 0) {
    body.namespace = payload.namespace
  }

  const response = await fetch(`${API_BASE_URL}/exams/answers`, {
    method: 'POST',
    headers: jsonHeaders,
    body: JSON.stringify(body),
  })
  return handleResponse<GenerateAnswersResponse>(response)
}

export async function generatePaper(payload: GeneratePaperPayload): Promise<GeneratePaperResponse> {
  const response = await fetch(`${API_BASE_URL}/generate-paper`, {
    method: 'POST',
    headers: {
      ...jsonHeaders,
      ...authHeaders(),
    },
    body: JSON.stringify(payload),
  })
  return handleResponse<GeneratePaperResponse>(response)
}

export async function fetchHistory(): Promise<PaperHistoryItem[]> {
  const response = await fetch(`${API_BASE_URL}/papers/history`, {
    headers: { ...authHeaders() },
  })
  return handleResponse<PaperHistoryItem[]>(response)
}

export async function fetchPaper(paperId: number): Promise<PaperDetail> {
  const response = await fetch(`${API_BASE_URL}/papers/${paperId}`, {
    headers: { ...authHeaders() },
  })
  return handleResponse<PaperDetail>(response)
}

export async function explainQuestion(payload: ExplainPayload): Promise<ExplainResponse> {
  const response = await fetch(`${API_BASE_URL}/explain-question`, {
    method: 'POST',
    headers: {
      ...jsonHeaders,
      ...authHeaders(),
    },
    body: JSON.stringify(payload),
  })
  return handleResponse<ExplainResponse>(response)
}
