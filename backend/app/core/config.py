from pathlib import Path

from pydantic.v1 import BaseSettings

# .env 文件位于项目根目录（backend/app/core/ 向上3层）
_ENV_FILE = Path(__file__).resolve().parents[3] / ".env"


class Settings(BaseSettings):
    # ── 数据库 ────────────────────────────────────────────────────────────────
    # 敏感值从 .env 读取，此处仅为占位默认值（本地开发请在 .env 中填写）
    DATABASE_URL: str = ""
    CORS_ORIGINS: list[str] = ["http://localhost:3000", "http://localhost:5173"]

    # ── LLM 配置（优先 DeepSeek → OpenAI → Ollama → Mock 降级）────────────────
    # ⚠️ API Key 敏感信息，必须在 .env 中配置，禁止硬编码
    DEEPSEEK_API_KEY: str = ""
    DEEPSEEK_BASE_URL: str = "https://api.deepseek.com"
    DEEPSEEK_MODEL: str = "deepseek-v4-pro"       # 默认值；.env 中可覆盖

    OPENAI_API_KEY: str = ""
    OPENAI_BASE_URL: str = "https://api.openai.com/v1"
    OPENAI_MODEL: str = "gpt-4o-mini"

    # ── Ollama 本地服务（默认端口 11434）────────────────────────────────────────
    OLLAMA_BASE_URL: str = "http://localhost:11434/v1"
    OLLAMA_MODEL: str = "qwen2:7b"

    # ── Embedding 配置 ─────────────────────────────────────────────────────────
    # local: 本地 sentence-transformers（无需 API Key，首次运行自动下载 ~130MB）
    # api  : OpenAI 兼容接口
    EMBEDDING_BACKEND: str = "local"
    EMBEDDING_LOCAL_MODEL: str = "BAAI/bge-small-zh-v1.5"
    EMBEDDING_API_KEY: str = ""
    EMBEDDING_BASE_URL: str = "https://api.openai.com/v1"
    EMBEDDING_MODEL: str = "text-embedding-3-small"
    EMBEDDING_DIM: int = 512

    # ── 工具配置 ───────────────────────────────────────────────────────────────
    GIT_CMD_PATH: str = ""   # 留空则自动从 PATH 查找 git

    class Config:
        env_file = str(_ENV_FILE)
        env_file_encoding = "utf-8"
        # 允许 .env 中未定义的字段（宽松模式）
        extra = "ignore"


settings = Settings()
DATABASE_URL = settings.DATABASE_URL
DEEPSEEK_API_KEY = settings.DEEPSEEK_API_KEY
CORS_ORIGINS = settings.CORS_ORIGINS
