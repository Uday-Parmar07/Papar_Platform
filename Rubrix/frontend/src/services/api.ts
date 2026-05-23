import type { GeneratePaperRequest, GeneratePaperResponse, SubjectsResponse, TopicsResponse } from '../types'

const CONFIGURED_BASE_URL = import.meta.env.VITE_API_BASE_URL

const API_BASE_URLS = Array.from(
  new Set(
    [
      CONFIGURED_BASE_URL,
      'http://127.0.0.1:8001',
      'http://127.0.0.1:8000',
      'http://localhost:8001',
      'http://localhost:8000',
    ].filter((value): value is string => Boolean(value && value.trim())),
  ),
)

async function extractErrorMessage(response: Response): Promise<string> {
  const raw = await response.text()
  try {
    const parsed = JSON.parse(raw) as { detail?: unknown }
    if (typeof parsed.detail === 'string' && parsed.detail.trim()) {
      return parsed.detail
    }
  } catch {
    // Fall back to raw body.
  }
  return raw || 'Request failed'
}

async function handleResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const detail = await extractErrorMessage(response)
    throw new Error(detail)
  }
  return response.json() as Promise<T>
}

async function requestWithFallback(path: string, init?: RequestInit): Promise<Response> {
  const errors: string[] = []

  for (const baseUrl of API_BASE_URLS) {
    try {
      const response = await fetch(`${baseUrl}${path}`, init)

      if (response.status === 404) {
        const detail = await extractErrorMessage(response)
        if (detail.toLowerCase().includes('not found')) {
          errors.push(`${baseUrl}: ${detail}`)
          continue
        }
      }

      return response
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Network error'
      errors.push(`${baseUrl}: ${message}`)
    }
  }

  throw new Error(errors.join(' | ') || 'Unable to reach backend API')
}

export async function fetchSubjects(): Promise<SubjectsResponse> {
  const response = await requestWithFallback('/subjects')
  return handleResponse<SubjectsResponse>(response)
}

export async function fetchTopics(subject: string): Promise<TopicsResponse> {
  const response = await requestWithFallback(`/topics/${encodeURIComponent(subject)}`)
  return handleResponse<TopicsResponse>(response)
}

export async function generatePaper(payload: GeneratePaperRequest): Promise<GeneratePaperResponse> {
  const response = await requestWithFallback('/generate-paper', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(payload),
  })
  return handleResponse<GeneratePaperResponse>(response)
}