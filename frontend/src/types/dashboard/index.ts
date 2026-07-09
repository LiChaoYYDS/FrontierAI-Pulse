export interface OverviewStats {
  total_articles:        number
  total_sources:         number
  total_knowledge_nodes: number
  total_unique_tags:     number
  read_count:            number
  favorite_count:        number
  today_new:             number
}

export interface DailyCount {
  date:  string  // "07-01"
  count: number
}

export interface ReadFunnel {
  total_articles: number
  ai_processed:   number
  user_read:      number
  user_favorite:  number
  has_insight:    number
}

export interface AIAccuracy {
  high_score_total: number
  high_score_read:  number
  read_rate:        number  // 高分文章被读率（%）
  read_total:       number
  read_high_score:  number
  quality_rate:     number  // 已读文章高分占比（%）
}

export interface SourceContribution {
  source_id:     number
  source_name:   string
  article_count: number
  avg_score:     number
}

export interface TagCount {
  tag:   string
  count: number
}

export interface DashboardData {
  overview:         OverviewStats
  growth_trend:     DailyCount[]
  funnel:           ReadFunnel
  ai_accuracy:      AIAccuracy
  top_sources:      SourceContribution[]
  tag_distribution: TagCount[]
}

/** 向后兼容旧代码 */
export type DashboardSummary = DashboardData
