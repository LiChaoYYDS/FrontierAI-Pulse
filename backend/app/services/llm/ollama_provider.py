from openai import AsyncOpenAI

from app.services.llm.base import BaseLLMProvider, LLMResult


class OllamaProvider(BaseLLMProvider):
    """本地 Ollama 服务适配器。

    Ollama 也实现了 OpenAI 兼容接口，不需要 api_key。
    使用前需本地安装 Ollama 并下载对应模型：ollama pull qwen2:7b
    """

    def __init__(self, base_url: str, model: str):
        self.model = model
        # Ollama 不需要真实的 api_key，填任意字符串即可
        self._client = AsyncOpenAI(api_key="ollama", base_url=base_url)

    async def complete(self, prompt: str, system: str | None = None) -> LLMResult:
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        resp = await self._client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=0.3,
        )
        return LLMResult(
            content=resp.choices[0].message.content or "",
            tokens_used=resp.usage.total_tokens if resp.usage else 0,
            provider=f"ollama:{self.model}",
        )
