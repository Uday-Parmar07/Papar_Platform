export interface GeneratePaperRequest {
  subject: string
  topics: string[]
  cutoff_year: number
  num_questions: number
}

export interface GeneratePaperQuestion {
  question: string
  topic: string
}

export interface GeneratePaperResponse {
  subject: string
  questions: GeneratePaperQuestion[]
}

export interface SubjectsResponse {
  subjects: string[]
}

export interface TopicsResponse {
  subject: string
  topics: string[]
}