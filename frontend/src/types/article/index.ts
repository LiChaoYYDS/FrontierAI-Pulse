export interface Article {
  id: number
  title: string
  url: string
  content: string | null
  summary: string | null
  author: string | null
  published_at: string | null
  source_id: number | null
  source_type: string | null
  tags: string[]
  importance_score: number
  is_read: boolean
  is_favorite: boolean
  is_liked: boolean
  notes: string | null
  insight: string | null
  process_status: string | null
  created_at: string | null
  read_at: string | null
}

export interface ArticleParams {
  page?: number
  page_size?: number
  tags?: string[]
  source_id?: number
  is_read?: boolean
  is_favorite?: boolean
  is_liked?: boolean
  sort_by?: 'time' | 'score'
  source_type?: string         // 仅返回该 source_type（如 'github'）
  exclude_source_type?: string // 排除该 source_type（如 'github'）
}

export interface ArticleResponse {
  items: Article[]
  total: number
  page: number
  page_size: number
  total_pages: number
}

export interface ArticleUpdate {
  is_read?: boolean
  is_favorite?: boolean
  is_liked?: boolean
  notes?: string | null
}
