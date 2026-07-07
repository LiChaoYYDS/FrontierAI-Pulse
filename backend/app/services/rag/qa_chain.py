"""
QA Chain：基于检索到的文章，用 LLM 生成结构化回答。

Prompt 设计原则：
  - 明确告知 LLM 只能基于给定文章作答，避免幻觉
  - 要求引用文章编号 [1][2]，便于前端展示来源
  - 字数控制在 150-250 字，平衡完整性与可读性
  - 支持多轮对话：将历史记录拼入 Prompt，LLM 能理解上下文指代
  - LLM 失败时降级为结构化摘要列表，保证接口始终可用
"""
from app.models.article import Article
from app.services.llm.provider_factory import get_provider

_LAYER_DESC = {
    "personal": "你的个人收藏和笔记",
    "curated":  "精选高分资讯",
    "general":  "全量资讯库",
}

_SYSTEM_PROMPT = (
    "你是用户的个人技术知识助手，支持多轮对话。"
    "你只能基于用户提供的文章内容回答问题，不能编造或引用外部知识。"
    "回答时必须引用对应文章的编号（如 [1][3]），让用户能追溯来源。"
    "如果上下文中有之前的对话记录，请结合对话历史理解用户当前问题的意图（如「它」「那个」等指代）。"
    "如果提供的文章无法完整回答问题，诚实说明不足之处，并建议用户补充更多文章。"
)

# 每次最多携带最近 N 条历史（防止 token 爆炸）
_MAX_HISTORY = 6


def _build_context(articles: list[Article]) -> str:
    """将文章列表格式化为 LLM 可读的上下文块。"""
    parts = []
    for i, a in enumerate(articles, start=1):
        body = a.summary or (a.content[:300] if a.content else "（无摘要）")
        tag_str = "、".join(a.tags) if a.tags else ""
        parts.append(
            f"[{i}] 标题：{a.title}\n"
            f"    标签：{tag_str or '—'} | 相关度：{a.importance_score}分\n"
            f"    摘要：{body}"
        )
    return "\n\n".join(parts)


def _build_history_str(history: list[dict]) -> str:
    """将对话历史格式化为 Prompt 片段，截取最近 _MAX_HISTORY 条。"""
    if not history:
        return ""
    recent = history[-_MAX_HISTORY:]
    lines = ["【对话历史（供理解上下文指代，不作为回答依据）】"]
    for msg in recent:
        role_label = "用户" if msg["role"] == "user" else "AI助手"
        # 历史中的 AI 回答截断到前100字，节省 token
        content = msg["content"][:100] + "…" if msg["role"] == "assistant" and len(msg["content"]) > 100 else msg["content"]
        lines.append(f"{role_label}：{content}")
    return "\n".join(lines) + "\n\n"


async def answer_question(
    question: str,
    articles: list[Article],
    layer: str,
    history: list[dict] | None = None,
) -> str:
    """生成回答。history 格式：[{"role":"user"|"assistant","content":"..."},...]"""
    layer_name = _LAYER_DESC.get(layer, "资讯库")
    history = history or []

    if not articles:
        return (
            f"在「{layer_name}」中未找到与「{question}」相关的内容。\n\n"
            "建议：\n"
            "- 换个关键词重新提问\n"
            "- 先阅读或收藏更多相关文章，丰富个人知识库\n"
            "- 切换到「全量资讯库」层级（去掉「我的/最近」等限定词）"
        )

    context = _build_context(articles)
    history_str = _build_history_str(history)

    prompt = (
        f"{history_str}"
        f"【检索来源】{layer_name}\n"
        f"【当前问题】{question}\n\n"
        f"【相关文章（共 {len(articles)} 篇）】\n{context}\n\n"
        "请结合对话历史（如有）和以上文章内容，简洁准确地回答当前问题（150-250字）。"
        "在回答中用 [编号] 标注引用了哪篇文章。"
        "若文章内容不足以完整回答，请注明并说明缺少哪方面信息。"
    )

    try:
        provider = get_provider()
        result = await provider.complete(prompt=prompt, system=_SYSTEM_PROMPT)
        return result.content.strip()
    except Exception:
        # LLM 调用失败 → 降级为结构化摘要列表
        lines = [f"（AI 回答暂不可用，以下为在「{layer_name}」中检索到的相关文章）\n"]
        for i, a in enumerate(articles, start=1):
            lines.append(f"**[{i}] {a.title}**")
            if a.summary:
                lines.append(f"> {a.summary[:120]}…")
            lines.append("")
        return "\n".join(lines)

