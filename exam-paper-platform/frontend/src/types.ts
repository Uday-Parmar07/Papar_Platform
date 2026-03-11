export interface Question {
  concept: string
  difficulty: string
  question: string
}

export interface SubjectOption {
  id: string
  name: string
}

export interface SubjectListResponse {
  subjects: SubjectOption[]
}

export interface TopicListResponse {
  topics: string[]
}

export interface GeneratePaperPayload {
  subject: string
  total_questions: number
  cutoff_year: number
  topics?: string[]
}

export interface GenerateExamResult {
  total_questions: number
  distribution: Record<string, number>
  questions: Question[]
  subject_id: string
  subject_name: string
  topics: string[]
}

export interface GeneratePaperResponse {
  paper_id: number
  result: GenerateExamResult
}

export interface RegisterPayload {
  name: string
  email: string
  password: string
}

export interface LoginPayload {
  email: string
  password: string
}

export interface TokenResponse {
  access_token: string
  token_type: string
}

export interface DashboardPaperItem {
  paper_id: number
  subject: string
  topics: string[]
  total_questions: number
  created_at: string
}

export interface DashboardResponse {
  papers_generated: number
  total_questions_solved: number
  recent_papers: DashboardPaperItem[]
  weak_topics: string[]
}

export interface PaperHistoryItem {
  paper_id: number
  subject: string
  topics: string[]
  total_questions: number
  created_at: string
}

export interface PaperDetail {
  paper_id: number
  subject: string
  topics: string[]
  questions: Question[]
  created_at: string
}

export interface ExplainPayload {
  question: string
  topic: string
  difficulty: 'easy' | 'medium' | 'exam'
}

export interface ExplainResponse {
  concept: string
  formula: string
  steps: string
  answer: string
  exam_tip: string
  cached: boolean
  created_at: string | null
}

export interface GenerateExamPayload {
  subject: string
  total_questions: number
  cutoff_year: number
  topics?: string[]
}

export interface GenerateExamResponse {
  total_questions: number
  distribution: Record<string, number>
  questions: Question[]
  subject_id: string
  subject_name: string
  topics: string[]
}

export interface VerifyResult extends Question {
  valid: boolean
  reason: string
}

export interface VerifyResponse {
  total: number
  valid: number
  invalid: number
  results: VerifyResult[]
}

export interface AnswerResult {
  concept: string
  difficulty: string
  question: string
  answer: string
  context_retrieved: boolean
}

export interface GenerateAnswersResponse {
  total: number
  namespace: string
  answers: AnswerResult[]
}
