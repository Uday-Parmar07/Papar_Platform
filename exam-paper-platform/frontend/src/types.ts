export interface Question {
  concept: string
  difficulty: string
  question: string
}

export interface GenerateExamResponse {
  total_questions: number
  distribution: Record<string, number>
  questions: Question[]
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
