export interface WeeklyOverview {
  total_articles: number
  read_count: number
  read_minutes: number
  knowledge_points: number
}

export interface TrendItem {
  tag: string
  count: number
  change: number
  direction: 'up_strong' | 'up' | 'down' | 'stable'
  summary: string
}

export interface ArticleItem {
  id: number
  title: string
  url: string
  summary: string
  tags: string[]
  score: number
  read_minutes: number
}

export interface InsightItem {
  title: string
  url: string
  insight: string
}

export interface ActionItem {
  title: string
  detail: string
  time_estimate: string
  reference_url: string
}

export interface DailyCount {
  date: string   // "07-01"
  count: number
}

export interface TagCount {
  tag: string
  count: number
}

export interface WeeklyReportData {
  period: string
  overview: WeeklyOverview
  top_trends: TrendItem[]
  curated_articles: ArticleItem[]
  insights: InsightItem[]
  action_items: ActionItem[]
  next_week_focus: string[]
  daily_reads: DailyCount[]
  tag_distribution: TagCount[]
}
