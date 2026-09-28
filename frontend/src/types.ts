export type View = 'overview' | 'feedback' | 'memory' | 'assistant' | 'files' | 'conversations'

export interface Analysis {
  id: string
  feedback_id: string
  topic: string
  urgency: string
  issue_type: string
  is_recurring: boolean
  short_summary: string
  entities: string[]
  created_at: string
}

export interface Feedback {
  id: string
  conversation_id?: string | null
  product_id: string
  customer_id?: string | null
  customer_name: string
  source: string
  feedback_text: string
  rating?: number | null
  feedback_date: string
  category: string
  sentiment: string
  sentiment_score: number
  created_at: string
  analysis_result?: Analysis | null
}

export interface FeedbackResponse {
  items: Feedback[]
  total: number
  page: number
  limit: number
  pages: number
}

export interface MemoryOverview {
  bank_id: string
  is_live_service: boolean
  total_memories: number
  memory_types: Record<string, number>
  memories: Array<Record<string, unknown>>
}

export interface UploadSummary {
  conversation_id: string
  uploaded: number
  processed: number
  successful: number
  failed: number
  errors: string[]
  message: string
}

export interface ImportedFile {
  id: string
  conversationId: string
  name: string
  uploadedAt: string
  uploaded: number
  successful: number
  failed: number
}

export interface ConversationMessage {
  role: 'user' | 'agent'
  content: string
  createdAt: string
}

export interface Conversation {
  id: string
  title: string
  createdAt: string
  pinned: boolean
  workspace?: 'assistant' | 'memory'
  datasetIds?: string[]
  messages: ConversationMessage[]
}
