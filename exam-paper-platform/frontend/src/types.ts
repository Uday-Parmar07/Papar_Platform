export interface Question {
  concept: string
  difficulty: string
  question: string
}

export interface AnswerResult {
  concept: string
  difficulty: string
  question: string
  answer: string
  context_retrieved: boolean
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

export interface GenerateAnswersResponse {
  total: number
  namespace: string
  answers: AnswerResult[]
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
