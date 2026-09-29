import type { Feedback, FeedbackResponse, MemoryOverview, UploadSummary } from './types'

const API_ROOT = import.meta.env.VITE_API_URL || (
  import.meta.env.PROD ? 'https://feedbackanalyzer-production-dd08.up.railway.app' : ''
)

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${API_ROOT}${path}`, {
    headers: { 'Content-Type': 'application/json', ...(options?.headers ?? {}) },
    ...options,
  })
  if (!response.ok) {
    const body = await response.json().catch(() => ({}))
    throw new Error(body.detail ?? `Request failed (${response.status})`)
  }
  return response.json() as Promise<T>
}

export async function fetchFeedback(params: Record<string, string | number | string[] | undefined> = {}) {
  const query = new URLSearchParams()
  Object.entries(params).forEach(([key, value]) => {
    if (Array.isArray(value)) value.forEach((item) => query.append(key, String(item)))
    else if (value !== undefined && value !== '') query.set(key, String(value))
  })
  return request<FeedbackResponse>(`/api/feedback?${query.toString()}`)
}

export async function submitFeedback(payload: Partial<Feedback> & { feedback_text: string }) {
  return request<Feedback>('/api/feedback', { method: 'POST', body: JSON.stringify(payload) })
}

export async function analyzeFeedback(id: string) {
  return request<Feedback>(`/api/feedback/${id}/analyze`, { method: 'POST' })
}

export async function uploadCsv(file: File, conversationId?: string) {
  const form = new FormData()
  form.append('file', file)
  const query = conversationId ? `?conversation_id=${encodeURIComponent(conversationId)}` : ''
  const response = await fetch(`${API_ROOT}/api/feedback/upload${query}`, { method: 'POST', body: form })
  if (!response.ok) {
    const body = await response.json().catch(() => ({})) as { detail?: string; message?: string }
    throw new Error(body.detail ?? body.message ?? `Upload failed (${response.status})`)
  }
  return response.json() as Promise<UploadSummary>
}

export async function deleteConversationFeedback(conversationId: string) {
  return request<{ conversation_id: string; deleted: number }>(`/api/feedback/conversation/${encodeURIComponent(conversationId)}`, { method: 'DELETE' })
}

export async function fetchMemory() {
  return request<MemoryOverview>('/api/memory')
}

export async function searchMemory(query: string, limit = 5) {
  return request<Array<Record<string, unknown>>>('/api/memory/search', {
    method: 'POST',
    body: JSON.stringify({ query, limit }),
  })
}

export async function reflectMemory(query: string, context?: string) {
  return request<Record<string, unknown>>('/api/memory/reflect', {
    method: 'POST',
    body: JSON.stringify({ query, context }),
  })
}

export async function retainMemory(payload: { content: string; context?: string; tags: string[]; memory_type: string }) {
  return request<Record<string, unknown>>('/api/memory/retain', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}
