"""
仪表盘结构化数据 Schema

六个模块：
  1. 数据总览
  2. 内容增长趋势（7/30/90天）
  3. 阅读漏斗（新增→AI处理→已读→收藏→洞察）
  4. AI 推荐命中率
  5. 来源贡献排行（Top 10）
  6. 内容标签分布（Top 10）
"""
from pydantic import BaseModel


class OverviewStats(BaseModel):
    total_articles:       int
    total_sources:        int     # 活跃来源数
    total_knowledge_nodes: int
    total_unique_tags:    int
    read_count:           int
    favorite_count:       int
    today_new:            int


class DailyCount(BaseModel):
    date:  str   # "07-01"
    count: int


class ReadFunnel(BaseModel):
    total_articles: int
    ai_processed:   int   # process_status='done'
    user_read:      int   # is_read=True
    user_favorite:  int   # is_favorite=True
    has_insight:    int   # insight IS NOT NULL


class AIAccuracy(BaseModel):
    high_score_total:  int    # importance_score >= 80
    high_score_read:   int    # importance_score >= 80 AND is_read=True
    read_rate:         float  # 高分文章被读率
    read_total:        int    # 已读文章总数
    read_high_score:   int    # 已读文章中高分占数
    quality_rate:      float  # 已读文章中高分占比


class SourceContribution(BaseModel):
    source_id:     int
    source_name:   str
    article_count: int
    avg_score:     float


class TagCount(BaseModel):
    tag:   str
    count: int


class DashboardData(BaseModel):
    overview:         OverviewStats
    growth_trend:     list[DailyCount]        # 按 days 参数决定长度
    funnel:           ReadFunnel
    ai_accuracy:      AIAccuracy
    top_sources:      list[SourceContribution]
    tag_distribution: list[TagCount]
