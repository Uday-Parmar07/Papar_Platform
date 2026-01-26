export interface Question {
  concept: string
  difficulty: string
  question: string
}

export interface GenerateExamPayload {
  subject: string
  total_questions: number
  cutoff_year: number
}

export interface GenerateExamResponse {
  total_questions: number
  distribution: Record<string, number>
  questions: Question[]
  subject: string
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

export interface SubjectListResponse {
  subjects: string[]
}
