"""
工具类功能相关的 Pydantic Schema 定义
"""
from pydantic import BaseModel


class CloneRequest(BaseModel):
    git_url: str        # GitHub 仓库地址，如 https://github.com/user/repo
    username: str = ""  # GitHub 用户名（私有仓库必填）
    token: str = ""     # Personal Access Token（私有仓库必填）
