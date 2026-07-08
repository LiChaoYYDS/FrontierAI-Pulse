from pydantic.v1 import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql+asyncpg://postgres:ChaoNi123%40@localhost:5433/tech_news"
    CORS_ORIGINS: list[str] = ["http://localhost:3000", "http://localhost:5173"]

    # LLM 配置 — 优先使用 DeepSeek，也可切换到 OpenAI
    # ⚠️ 敏感信息请勿硬编码，应在项目根目录的 .env 文件中配置（已加入 .gitignore）
    # 可用模型：deepseek-chat（V3，性价比高）/ deepseek-reasoner（R1，深度推理）
    DEEPSEEK_API_KEY: str = "sk-96f2db99245e4bf9aa5d140bfdbb02df"
    DEEPSEEK_BASE_URL: str = "https://api.deepseek.com"
    DEEPSEEK_MODEL: str = "deepseek-v4-pro"

    OPENAI_API_KEY: str = ""
    OPENAI_BASE_URL: str = "https://api.openai.com/v1"
    OPENAI_MODEL: str = "gpt-4o-mini"

    # Ollama 本地服务地址（默认端口 11434）
    OLLAMA_BASE_URL: str = "http://localhost:11434/v1"
    OLLAMA_MODEL: str = "qwen2:7b"

    # Embedding 配置
    # EMBEDDING_BACKEND: "local" 使用本地 sentence-transformers（无需 API Key）
    #                    "api"   使用 OpenAI 兼容接口

    EMBEDDING_BACKEND: str = "local"
    EMBEDDING_LOCAL_MODEL: str = "BAAI/bge-small-zh-v1.5"  # 512 维，优秀中文支持，~130MB
    EMBEDDING_API_KEY: str = ""
    EMBEDDING_BASE_URL: str = "https://api.openai.com/v1"
    EMBEDDING_MODEL: str = "text-embedding-3-small"
    EMBEDDING_DIM: int = 512             # bge-small-zh-v1.5 输出 512 维

    # Git 工具配置
    GIT_CMD_PATH: str = ""  # git 可执行文件路径，留空则自动从 PATH 查找


settings = Settings()
DATABASE_URL = settings.DATABASE_URL
DEEPSEEK_API_KEY = settings.DEEPSEEK_API_KEY
CORS_ORIGINS = settings.CORS_ORIGINS
