"""
周报结构化数据 Schema

将周报从单一 Markdown 字符串改为结构化 JSON，
前端按模块独立渲染，支持图表、卡片等富展示。
"""
from pydantic import BaseModel


class WeeklyOverview(BaseModel):
    total_articles: int       # 本周新增文章数
    read_count: int           # 已读文章数
    read_minutes: int         # 估算阅读时长（中文约300字/分钟）
    knowledge_points: int     # 本周出现的不重复标签数


class TrendItem(BaseModel):
    tag: str
    count: int                # 本周出现次数
    change: int               # 相较上周变化量（正/负/零）
    direction: str            # "up" | "down" | "stable"
    summary: str              # LLM 生成的一句话趋势描述


class ArticleItem(BaseModel):
    id: int
    title: str
    url: str
    summary: str              # AI 生成摘要
    tags: list[str]
    score: int                # importance_score
    read_minutes: int         # 估算阅读时长


class InsightItem(BaseModel):
    title: str
    url: str
    insight: str              # article.insight 字段（AI 个人关联洞察）


class ActionItem(BaseModel):
    title: str                # 行动项标题
    detail: str               # 具体步骤
    time_estimate: str        # 预计时间（如"2小时"）
    reference_url: str = ""   # 关联文章链接（可选）


class DailyCount(BaseModel):
    date: str                 # "07-01"
    count: int                # 当天新增文章数


class TagCount(BaseModel):
    tag: str
    count: int                # 该标签在本周文章中出现次数


class WeeklyReportData(BaseModel):
    period: str               # "2026年07月01日 — 07月07日"
    overview: WeeklyOverview
    top_trends: list[TrendItem]
    curated_articles: list[ArticleItem]
    insights: list[InsightItem]
    action_items: list[ActionItem]
    next_week_focus: list[str]
    daily_reads: list[DailyCount]
    tag_distribution: list[TagCount]
