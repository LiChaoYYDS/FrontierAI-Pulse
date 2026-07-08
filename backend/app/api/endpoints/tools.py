import asyncio
import logging
import uuid
from pathlib import Path

from fastapi import APIRouter

from app.schemas.tools import CloneRequest
from app.services.tools.git_cloner import (
    GITHUB_RE,
    build_clone_url,
    create_task_entry,
    get_task,
    run_clone,
)

router = APIRouter(prefix="/api/tools", tags=["tools"])
logger = logging.getLogger("uvicorn")

# 防止后台 asyncio.Task 被 GC 回收的强引用集合（需在端点函数前定义）
_background_tasks: set = set()


@router.post("/clone")
async def start_clone(body: CloneRequest):
    """
    启动 Git 克隆任务（异步后台执行）
    - 仅支持 GitHub 仓库 URL
    - 公开仓库无需填写凭据；私有仓库需提供 username + token
    - 克隆目标路径：Documents/github-projects/<仓库名>
    - 返回 task_id，用于轮询进度
    """
    m = GITHUB_RE.match(body.git_url)
    if not m:
        return {"error": "非有效的 GitHub 仓库地址"}

    repo_name = m.group(2)
    target_dir = Path.home() / "Documents" / "github-projects" / repo_name
    logger.info("[Tools] 开始克隆：%s -> %s", repo_name, target_dir)

    task_id = str(uuid.uuid4())[:8]
    create_task_entry(task_id, repo_name, target_dir)

    clone_url = build_clone_url(body.git_url, body.username, body.token)
    task = asyncio.create_task(run_clone(task_id, clone_url, target_dir))
    # 防止 task 被 GC 回收
    _background_tasks.add(task)
    task.add_done_callback(_background_tasks.discard)

    return {"task_id": task_id, "repo": repo_name, "target": str(target_dir)}


@router.get("/clone/{task_id}")
async def get_clone_status(task_id: str):
    """
    轮询克隆任务进度
    - status: running（进行中）/ done（完成）/ failed（失败）
    - progress: 0-100 的进度百分比
    - message: 当前进度描述或错误信息
    - target: 克隆目标本地路径（完成后可打开）
    """
    task = get_task(task_id)
    if not task:
        return {"error": "任务不存在"}
    return task
