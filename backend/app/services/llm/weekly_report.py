from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.article import Article
from app.services.llm.provider_factory import get_provider


async def generate_weekly_report(db: AsyncSession, user_interests: list[str]) -> str:
    since = datetime.now(timezone.utc) - timedelta(days=7)
    stmt = (
        select(Article)
        .where(Article.created_at >= since)
        .order_by(Article.importance_score.desc())
        .limit(30)
    )
    articles = (await db.execute(stmt)).scalars().all()

    if not articles:
        return (
            "# 📊 AI 周报\n\n"
            "> 本周暂无新文章。\n\n"
            "**建议：**\n"
            "1. 前往 **📡 来源管理** 启用感兴趣的资讯来源\n"
            "2. 前往 **🎯 兴趣标签** 设置你的技术方向\n"
            "3. 点击「立即抓取」获取最新内容"
        )

    read_articles = [a for a in articles if a.is_read]
    top_articles = articles[:8]
    interests_str = "、".join(user_interests[:6]) if user_interests else "技术通用"

    # 与兴趣相关的文章
    relevant = []
    for a in articles:
        tags_lower = [t.lower() for t in (a.tags or [])]
        if any(
            kw.lower() in tag
            for interest in user_interests
            for kw in interest.replace("(", " ").replace(")", " ").split()
            for tag in tags_lower
            if len(kw) > 1
        ):
            relevant.append(a)

    titles_str = "\n".join(f"- {a.title}" for a in top_articles)
    relevant_str = "\n".join(f"- {a.title}" for a in relevant[:5]) if relevant else "（本周暂无与你兴趣高度匹配的文章）"

    week_start = (datetime.now() - timedelta(days=7)).strftime("%Y年%m月%d日")
    week_end = datetime.now().strftime("%Y年%m月%d日")

    try:
        provider = get_provider()
        result = await provider.complete(
            prompt=(
                f"用户兴趣领域：{interests_str}\n"
                f"本周新增文章：{len(articles)} 篇，已读 {len(read_articles)} 篇\n"
                f"高分文章（按相关度排序）：\n{titles_str}\n"
                f"与用户兴趣相关的文章：\n{relevant_str}\n\n"
                "请严格按照以下5个章节生成个性化中文技术周报，使用Markdown格式：\n"
                "## 📈 本周阅读概况\n（阅读数量、文章质量分析）\n"
                "## 🔥 热点趋势\n（本周技术热点概括）\n"
                "## 🎯 与你兴趣相关\n（结合用户兴趣的深度分析）\n"
                "## 💡 学习建议\n（具体可执行的学习建议）\n"
                "## 👀 下周关注\n（值得持续关注的方向）\n"
                "每个章节2-4句话，语气专业亲切，内容具体。"
            ),
            system="你是技术学习顾问，根据用户阅读数据生成个性化周报。",
        )
        ai_body = result.content.strip()
    except Exception:
        ai_body = (
            f"## 📈 本周阅读概况\n\n本周新增 **{len(articles)}** 篇文章，已读 **{len(read_articles)}** 篇。"
            f"\n\n## 🔥 热点趋势\n\n技术资讯持续更新中，保持关注。"
            f"\n\n## 🎯 与你兴趣相关\n\n已为你筛选出 {len(relevant)} 篇与 {interests_str} 相关的文章。"
            f"\n\n## 💡 学习建议\n\n每天保持阅读习惯，尝试将理论与实践结合。"
            f"\n\n## 👀 下周关注\n\n持续关注 {interests_str} 领域的最新进展。"
        )

    lines = [f"# 📊 AI 周报  {week_start} — {week_end}\n", ai_body]

    if top_articles:
        lines.append("\n---\n## 📌 本周精选文章\n")
        for a in top_articles:
            score = f"（匹配度 {a.importance_score}%）" if a.importance_score > 50 else ""
            lines.append(f"- [{a.title}]({a.url}) {score}")

    return "\n".join(lines)
