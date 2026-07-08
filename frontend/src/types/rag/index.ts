import type { Article } from '@/types/article'

export interface HistoryItem {
  role: 'user' | 'assistant'
  content: string
}

export interface AskResponse {
  answer: string
  layer: string
  layer_desc: string
  sources: Article[]
}

export interface EmbedStatus {
  total: number
  embedded: number
  pending: number
  coverage_pct: number
  job_running: boolean
}

export interface ChatMsg {
  role: 'user' | 'assistant'
  content: string
  layer?: string
  layer_desc?: string
  sources?: Article[]
}
