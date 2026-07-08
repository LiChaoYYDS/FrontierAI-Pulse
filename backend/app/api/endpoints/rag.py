"""
RAG 问答 API

端点：
  POST /api/rag/ask          — 混合检索 + LLM 生成回答
  POST /api/rag/embed-all    — 批量为所有未向量化的文章生成 Embedding（后台任务）
  GET  /api/rag/embed-status — 查询 Embedding 覆盖率统计
  POST /api/rag/rescore-all  — 基于用户兴趣质心，一条 SQL 批量更新全库评分（后台任务）
"""
import logging

from fastapi import APIRouter, BackgroundTasks, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import RAG_LAYER_DESCRIPTIONS
from app.db.deps import get_db
from app.models.article import Article
from app.schemas.article import ArticleResponse
from app.schemas.rag import (
    AskRequest,
    AskResponse,
    EmbedStatusResponse,
    RescoreRequest,
    RescoreResponse,
)
from app.services.rag.background_jobs import embed_job, rescore_job, run_embed_job, run_rescore_job
from app.services.rag.qa_chain import answer_question
from app.services.rag.retriever import route_layer, retrieve

logger = logging.getLogger("uvicorn")
router = APIRouter(prefix="/api/rag", tags=["rag"])


# ── 问答接口 ──────────────────────────────────────────────────────────────────

@router.post("/ask", response_model=AskResponse)
async def ask(body: AskRequest, db: AsyncSession = Depends(get_db)):
    """
    RAG 知识库问答（混合检索版）

    检索流程：
      1. route_layer  — 根据问题意图路由到 personal / curated / general 层
      2. retrieve     — 向量检索 + jieba 关键词检索，RRF 融合 Top-5
      3. answer       — 将文章上下文喂给 LLM 生成带引用编号的回答

    返回：AI 回答 + 来源文章列表（[1][2] 编号与 sources 数组下标对应）
    """
    layer = route_layer(body.question)
    articles = await retrieve(db, body.question, layer)
    history = [h.model_dump() for h in body.history]
    answer = await answer_question(body.question, articles, layer, history)
    return AskResponse(
        answer=answer,
        layer=layer,
        layer_desc=RAG_LAYER_DESCRIPTIONS[layer],
        sources=[ArticleResponse.model_validate(a) for a in articles],
    )


# ── 批量 Embedding ─────────────────────────────────────────────────────────────

@router.post("/embed-all", summary="批量生成文章 Embedding（后台异步）")
async def embed_all(background_tasks: BackgroundTasks):
    """
    触发后台任务，为所有尚未向量化的文章生成 Embedding。
    - 任务异步执行，接口立即返回
    - 用 GET /embed-status 轮询进度
    - 同一时间只允许一个任务运行
    """
    if embed_job["running"]:
        return {"message": "任务已在运行中", "status": embed_job}
    background_tasks.add_task(run_embed_job)
    return {"message": "批量 Embedding 任务已启动，请用 /embed-status 查询进度"}


@router.get("/embed-status", response_model=EmbedStatusResponse, summary="查询 Embedding 覆盖率")
async def embed_status(db: AsyncSession = Depends(get_db)):
    """返回文章向量化覆盖率，用于判断 RAG 质量。"""
    total_res = await db.execute(select(func.count()).select_from(Article))
    total = total_res.scalar_one()

    embedded_res = await db.execute(
        select(func.count()).select_from(Article).where(Article.embedding.isnot(None))
    )
    embedded = embedded_res.scalar_one()
    pending = total - embedded

    return EmbedStatusResponse(
        total=total,
        embedded=embedded,
        pending=pending,
        coverage_pct=round(embedded / total * 100, 1) if total else 0.0,
        job_running=embed_job["running"],
    )


# ── 全库重评分 ─────────────────────────────────────────────────────────────────

@router.post(
    "/rescore-all",
    response_model=RescoreResponse,
    summary="基于用户兴趣质心批量更新全库评分（后台异步）",
)
async def rescore_all(body: RescoreRequest, background_tasks: BackgroundTasks):
    """
    触发后台任务，将用户兴趣短语融合为质心向量，
    再通过一条 SQL UPDATE 更新所有已向量化文章的 importance_score。

    使用场景：
      - 用户修改了兴趣配置后，重新为全库文章打分
      - 首次批量 Embedding 完成后，补全历史文章评分

    注意：
      - 任务异步执行，接口立即返回；可用 GET /embed-status 确认向量化覆盖率
      - 同一时间只允许一个任务运行，重复调用返回当前状态
      - interests 为空时直接拒绝，返回提示信息
    """
    if not body.interests:
        return RescoreResponse(
            message="interests 不能为空，请提供至少一个兴趣标签",
            status=rescore_job,
        )

    if rescore_job["running"]:
        return RescoreResponse(
            message="重评分任务已在运行中，请稍后再试",
            status=rescore_job,
        )

    background_tasks.add_task(run_rescore_job, body.interests)
    logger.info("[RescoreJob] 任务已提交，兴趣标签: %s", body.interests)
    return RescoreResponse(
        message=f"重评分任务已启动（{len(body.interests)} 个兴趣标签），数据库将在后台更新",
        status=rescore_job,
    )
