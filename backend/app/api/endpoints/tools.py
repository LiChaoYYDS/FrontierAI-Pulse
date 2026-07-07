import asyncio
import logging
import re
import shutil
import uuid
from pathlib import Path

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/api/tools", tags=["tools"])
logger = logging.getLogger("tools")
# 内存任务池（进程级别，重启后清空）
_tasks: dict[str, dict] = {}

_GITHUB_RE = re.compile(r"^https?://github\.com/([^/]+)/([^/]+?)(?:\.git)?/?$")


class CloneRequest(BaseModel):
    git_url: str       # GitHub 仓库地址，如 https://github.com/user/repo
    username: str = "" # GitHub 用户名（私有仓库必填）
    token: str = ""    # Personal Access Token（私有仓库必填）


def _build_clone_url(git_url: str, username: str, token: str) -> str:
    if token:
        clean = re.sub(r"^https://", "", git_url)
        return f"https://{username}:{token}@{clean}"
    return git_url


@router.post("/clone")
async def start_clone(body: CloneRequest):
    """
    启动 Git 克隆任务（异步后台执行）
    - 仅支持 GitHub 仓库 URL
    - 公开仓库无需填写凭据；私有仓库需提供 username + token
    - 克隆目标路径：Documents/github-projects/<仓库名>
    - 返回 task_id，用于轮询进度
    """
    m = _GITHUB_RE.match(body.git_url)
    if not m:
        return {"error": "非有效的 GitHub 仓库地址"}

    repo_name = m.group(2)
    target_dir = Path.home() / "Documents" / "github-projects" / repo_name
    logger.info(f"[Tools] 开始克隆：{repo_name} -> {target_dir}")
    task_id = str(uuid.uuid4())[:8]

    _tasks[task_id] = {
        "status": "running",
        "progress": 0,
        "message": "正在克隆...",
        "repo": repo_name,
        "target": str(target_dir),
    }

    clone_url = _build_clone_url(body.git_url, body.username, body.token)
    task = asyncio.create_task(_run_clone(task_id, clone_url, target_dir))
    _tasks[task_id]["_task"] = task  # 防止被 GC 回收
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
    task = _tasks.get(task_id)
    if not task:
        return {"error": "任务不存在"}
    return task


async def _run_clone(task_id: str, url: str, target: Path):
    # Bug 3 fix: 目标目录已存在时提前报错，避免 git 报错信息不清晰
    if target.exists():
        _tasks[task_id].update({"status": "failed", "message": f"目标目录已存在：{target}"})
        return

    # Bug 1 fix: 用 shutil.which 找 git，找不到时给出明确提示
    git_cmd = shutil.which("git") or r"E:\软件\Git\cmd\git.exe"
    if not Path(git_cmd).exists():
        _tasks[task_id].update({"status": "failed", "message": "找不到 git 命令，请确认 Git 已安装并加入 PATH"})
        return

    target.parent.mkdir(parents=True, exist_ok=True)
    stderr_lines: list[str] = []

    try:
        proc = await asyncio.create_subprocess_exec(
            git_cmd, "clone", "--progress", str(url), str(target),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        async def _read_progress(stream):
            async for line in stream:
                text = line.decode(errors="ignore").strip()
                if text:
                    stderr_lines.append(text)  # Bug 2 fix: 收集 stderr 行
                m = re.search(r"(\d+)%", text)
                if m:
                    _tasks[task_id]["progress"] = int(m.group(1))
                    _tasks[task_id]["message"] = text[:80]

        await asyncio.gather(_read_progress(proc.stderr), proc.wait())

        if proc.returncode == 0:
            _tasks[task_id].update({"status": "done", "progress": 100, "message": "克隆完成！"})
        else:
            # Bug 2 fix: 用已收集的 stderr 行报错，而非读空的 stdout
            err = "\n".join(stderr_lines[-5:]) if stderr_lines else "未知错误"
            _tasks[task_id].update({"status": "failed", "message": f"克隆失败：{err[:300]}"})
    except Exception as e:
        _tasks[task_id].update({"status": "failed", "message": str(e)})
