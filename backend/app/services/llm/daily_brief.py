from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.article import Article
from app.services.llm.provider_factory import get_provider

# 兴趣方向对应的图标
_ICONS = {
    "大语言模型": "🧠", "llm": "🧠", "ai agent": "🤖", "agent": "🤖",
    "rag": "🔍", "计算机视觉": "👁️", "cv": "👁️", "机器学习": "📊",
    "前端": "🎨", "后端": "⚙️", "云原生": "☁️", "开源": "📦",
    "信息安全": "🔐", "数据库": "🗄️", "devops": "🛠️", "芯片": "💾",
}


def _icon(interest: str) -> str:
    key = interest.lower().replace("(", "").replace(")", "").replace("/", "")
    for k, v in _ICONS.items():
        if k in key:
            return v
    return "📌"


def _keywords(interest: str) -> list[str]:
    """将兴趣标签拆成可匹配的关键词列表。"""
    raw = interest.replace("(", " ").replace(")", " ").replace("（", " ").replace("）", " ").replace("/", " ")
    return [w.strip().lower() for w in raw.split() if len(w.strip()) > 1]


def _match(article: Article, keywords: list[str]) -> bool:
    """判断文章是否与兴趣关键词匹配（标签 + 标题双重匹配）。"""
    text = " ".join((article.tags or []) + [article.title or ""]).lower()
    return any(kw in text for kw in keywords)


async def _section_for_interest(interest: str, articles: list[Article]) -> str:
    """为单个兴趣方向生成 Markdown 章节（LLM 分析 + 文章列表）。"""
    titles = "\n".join(f"- {a.title}" for a in articles[:6])
    try:
        provider = get_provider()
        result = await provider.complete(
            prompt=(
                f"技术方向：{interest}\n"
                f"今日相关文章：\n{titles}\n\n"
                "请用2-3句话概括该方向今日的新发现、新进展或趋势，语气简洁专业。"
            ),
            system="你是技术资讯分析助手，直接输出分析内容，不加标题前缀。",
        )
        analysis = result.content.strip()
    except Exception:
        analysis = f"今日 {interest} 领域新增 {len(articles)} 篇资讯，建议重点关注。"

    icon = _icon(interest)
    lines = [f"## {icon} {interest}  今日动态\n", f"> 今日新增 **{len(articles)}** 篇\n", analysis, ""]
    for a in articles[:3]:
        lines.append(f"- [{a.title}]({a.url})")
    lines.append("")
    return "\n".join(lines)


async def generate_daily_brief(db: AsyncSession, user_interests: list[str]) -> str:
    """按用户兴趣方向分块生成今日简报，每个方向展示新发现/进展/趋势。"""
    import asyncio

    since = datetime.now(timezone.utc) - timedelta(hours=24)
    articles = (await db.execute(
        select(Article).where(Article.created_at >= since).order_by(Article.created_at.desc()).limit(80)
    )).scalars().all()

    if not articles:
        return _no_articles_guide(bool(user_interests))

    today = datetime.now().strftime("%Y年%m月%d日")
    lines = [f"# 📅 今日简报  ·  {today}\n", f"> 今日共新增 **{len(articles)}** 篇资讯\n"]

    # ── 兴趣方向过滤（纯CPU，同步即可）────────────────────────────────────────
    matched_interests: list[tuple[str, list[Article]]] = []
    if user_interests:
        for interest in user_interests:
            kws = _keywords(interest)
            matched = [a for a in articles if _match(a, kws)]
            if matched:
                matched_interests.append((interest, matched))

    if matched_interests:
        # 各兴趣方向的 LLM 调用并行执行，整体耗时 = 最慢那一次，而非累加
        sections = await asyncio.gather(
            *[_section_for_interest(interest, arts) for interest, arts in matched_interests]
        )
        lines.extend(sections)
    else:
        # 无匹配或无兴趣：显示全量热点
        lines.append("## 🔥 今日热点\n")
        for a in articles[:8]:
            lines.append(f"- [{a.title}]({a.url})")
        lines.append("")

    # 学习建议（与章节并列执行可进一步提速，但语义上依赖章节内容，保持串行更合理）
    tip = await _learning_tip(articles[:8], user_interests)
    lines.append(f"## ⏰ 今日学习建议\n\n{tip}")

    return "\n".join(lines)


async def _learning_tip(articles: list[Article], interests: list[str]) -> str:
    try:
        provider = get_provider()
        interests_str = "、".join(interests[:4]) if interests else "技术通用"
        titles = "、".join(a.title for a in articles[:5])
        result = await provider.complete(
            prompt=f"用户关注：{interests_str}\n今日文章：{titles}\n\n给出1句具体的今日学习行动建议（不超过40字）。",
            system="你是一位有着15年经验的学习助手，直接输出建议，不加任何前缀。",
        )
        return result.content.strip()
    except Exception:
        return "选择今日一篇感兴趣的文章深度阅读，记录一个新知识点。"


def _no_articles_guide(has_interests: bool) -> str:
    if not has_interests:
        return (
            "# 📅 今日简报\n\n> 暂无今日文章\n\n**建议：**\n"
            "1. 前往 **📡 来源管理** 启用感兴趣的资讯来源\n"
            "2. 前往 **🎯 兴趣标签** 设置你的技术方向\n"
            "3. 等待系统自动抓取或手动触发抓取"
        )
    return (
        "# 📅 今日简报\n\n> 今日暂无新文章\n\n"
        "系统每2小时自动抓取，或前往 **📡 来源管理** 手动触发。"
    )
