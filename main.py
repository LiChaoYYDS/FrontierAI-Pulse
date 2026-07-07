"""FrontierAI Pulse API — 项目唯一入口。
启动方式: uvicorn main:app --port 8000 --reload
"""

import sys
import logging
from pathlib import Path
from contextlib import asynccontextmanager

BACKEND_DIR = Path(__file__).parent / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.db.config import engine, Base
from app.api.endpoints.articles import router as articles_router
from app.api.endpoints.sources import router as sources_router
from app.api.endpoints.user import router as user_router
from app.api.endpoints.brief import router as brief_router
from app.api.endpoints.dashboard import router as dashboard_router
from app.api.endpoints.search import router as search_router
from app.api.endpoints.knowledge import router as knowledge_router
from app.api.endpoints.rag import router as rag_router
from app.api.endpoints.tools import router as tools_router

logger = logging.getLogger("uvicorn")


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        async with engine.begin() as conn:
            # 确保 pgvector 扩展存在（首次部署自动创建，幂等）
            await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            await conn.run_sync(Base.metadata.create_all)
        logger.info("数据库表创建/确认成功（pgvector 扩展已就绪）")
    except Exception as e:
        logger.warning(f"数据库连接失败，跳过建表: {e}")

    from app.services.scraper.scheduler import start_scheduler, stop_scheduler
    start_scheduler(interval_hours=2)

    yield

    stop_scheduler()
    try:
        await engine.dispose()
    except Exception:
        pass


app = FastAPI(
    title="FrontierAI Pulse API",
    description="前沿AI脉搏（个人版）— 资讯采集与智能处理后端",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(articles_router)
app.include_router(sources_router)
app.include_router(user_router)
app.include_router(brief_router)
app.include_router(dashboard_router)
app.include_router(search_router)
app.include_router(knowledge_router)
app.include_router(rag_router)
app.include_router(tools_router)


@app.get("/")
async def root():
    return {"message": "FrontierAI Pulse API 运行中", "docs": "/docs"}
