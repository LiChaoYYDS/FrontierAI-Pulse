"""
Git 克隆服务

将 tools 端点中与克隆任务相关的业务逻辑从接口层剥离，
集中管理：任务状态、URL 构建、后台克隆执行。
"""
import asyncio
import logging
import re
import shutil
from pathlib import Path

from app.core.config import settings

logger = logging.getLogger("uvicorn")

# 内存任务池（进程级，重启后清空）
_tasks: dict[str, dict] = {}

# GitHub 仓库地址正则
GITHUB_RE = re.compile(r"^https?://github\.com/([^/]+)/([^/]+?)(?:\.git)?/?$")


def build_clone_url(git_url: str, username: str, token: str) -> str:
    """将 PAT 凭据嵌入 URL，用于克隆私有仓库。"""
    if token:
        clean = re.sub(r"^https://", "", git_url)
        return f"https://{username}:{token}@{clean}"
    return git_url


def get_task(task_id: str) -> dict | None:
    """获取任务状态，不存在返回 None。"""
    return _tasks.get(task_id)


def create_task_entry(task_id: str, repo_name: str, target_dir: Path) -> dict:
    """初始化并注册新任务状态记录，返回任务字典。"""
    entry = {
        "status": "running",
        "progress": 0,
        "message": "正在克隆...",
        "repo": repo_name,
        "target": str(target_dir),
    }
    _tasks[task_id] = entry
    return entry


async def run_clone(task_id: str, url: str, target: Path) -> None:
    """
    后台异步执行 git clone：
    - 实时解析 --progress 输出更新进度百分比
    - 目标目录已存在时提前报错
    - git 不在 PATH 时优先尝试配置路径
    """
    if target.exists():
        _tasks[task_id].update({"status": "failed", "message": f"目标目录已存在：{target}"})
        return

    git_cmd = shutil.which("git") or settings.GIT_CMD_PATH
    if not git_cmd or not Path(git_cmd).exists():
        _tasks[task_id].update({
            "status": "failed",
            "message": "找不到 git 命令，请确认 Git 已安装并加入 PATH，或在 config 中设置 GIT_CMD_PATH",
        })
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
                    stderr_lines.append(text)
                m = re.search(r"(\d+)%", text)
                if m:
                    _tasks[task_id]["progress"] = int(m.group(1))
                    _tasks[task_id]["message"] = text[:80]

        await asyncio.gather(_read_progress(proc.stderr), proc.wait())

        if proc.returncode == 0:
            _tasks[task_id].update({"status": "done", "progress": 100, "message": "克隆完成！"})
        else:
            err = "\n".join(stderr_lines[-5:]) if stderr_lines else "未知错误"
            _tasks[task_id].update({"status": "failed", "message": f"克隆失败：{err[:300]}"})

    except Exception as e:
        _tasks[task_id].update({"status": "failed", "message": str(e)})
