import logging

import httpx

from app.core.config import settings
from app.services.llm.base import BaseLLMProvider

logger = logging.getLogger("uvicorn")

_provider: BaseLLMProvider | None = None


async def _ollama_available() -> bool:
    """快速探测本地 Ollama 是否在运行（100ms 超时）"""
    try:
        async with httpx.AsyncClient() as client:
            """
            rstrip("v1")：删除右侧的/v1
            通常，Ollama 的 API 端点默认在 /v1 下（如 /v1/chat/completions）。而许多 OpenAI 兼容的客户端库（如 openai-python）在初始化时，要求传入的 base_url 必须指向根路径（不携带 /v1），
            因为库本身会自动在请求时拼接 /v1。
            本意是为了防御性编程：即使用户在配置里填写了带 /v1 的地址，也能自动去掉，避免最终请求变成 http://x/v1/v1/chat。
            """
            r = await client.get(f"{settings.OLLAMA_BASE_URL.rstrip('/v1')}", timeout=0.1)
            return r.status_code < 500
    except Exception:
        return False


"""
#该方法是同步方法，而ollama_available()方法是异步方法，所以不能用get_provider()方法，因此ollama不能写在该方法里
那把 get_provider() 改成 async def 不就行了？
可以改，但会产生连锁影响。

调用链会变成：

# 业务层（摘要/标签/评分）每次调用都要await
provider = await get_provider()
result = await provider.complete(prompt)
而 get_provider() 99% 的情况下直接从缓存返回，根本没有 I/O 操作，却要强制所有调用方加 await。这是不必要的开销和代码噪声。
"""
def get_provider() -> BaseLLMProvider:
    """返回当前会话复用的 provider 实例（单例）。

    选择优先级：
    1. DeepSeek API Key 已配置 → OpenAIProvider（接 DeepSeek）
    2. OpenAI API Key 已配置  → OpenAIProvider（接 OpenAI）
    3. 以上都没有             → MockProvider（降级，不中断服务）

    注意：Ollama 需要异步探测，用 get_provider_async() 获取。
    """
    global _provider
    if _provider is not None:
        return _provider

    if settings.DEEPSEEK_API_KEY:
        from app.services.llm.openai_provider import OpenAIProvider
        _provider = OpenAIProvider(
            api_key=settings.DEEPSEEK_API_KEY,
            base_url=settings.DEEPSEEK_BASE_URL,
            model=settings.DEEPSEEK_MODEL,
        )
        logger.info("[LLM] 使用 DeepSeek API")

    elif settings.OPENAI_API_KEY:
        from app.services.llm.openai_provider import OpenAIProvider
        _provider = OpenAIProvider(
            api_key=settings.OPENAI_API_KEY,
            base_url=settings.OPENAI_BASE_URL,
            model=settings.OPENAI_MODEL,
        )
        logger.info("[LLM] 使用 OpenAI API")

    else:
        from app.services.llm.mock_provider import MockProvider
        _provider = MockProvider()
        logger.warning("[LLM] 未配置 API Key，降级为 Mock")

    return _provider


async def get_provider_async() -> BaseLLMProvider:
    """异步版本：额外检查本地 Ollama，适合启动时调用。"""
    if settings.DEEPSEEK_API_KEY or settings.OPENAI_API_KEY:
        return get_provider()

    if await _ollama_available():
        from app.services.llm.ollama_provider import OllamaProvider
        logger.info("[LLM] 检测到本地 Ollama，使用 %s", settings.OLLAMA_MODEL)
        return OllamaProvider(base_url=settings.OLLAMA_BASE_URL, model=settings.OLLAMA_MODEL)

    return get_provider()  # 降级到 Mock
