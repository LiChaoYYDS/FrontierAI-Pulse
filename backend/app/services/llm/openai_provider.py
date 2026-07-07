from openai import AsyncOpenAI

from app.services.llm.base import BaseLLMProvider, LLMResult


class OpenAIProvider(BaseLLMProvider):
    """支持 OpenAI 格式的所有兼容服务（OpenAI / DeepSeek 等）。

    DeepSeek 完全兼容 OpenAI API，只需传入不同的 base_url 和 api_key。
    """

    def __init__(self, api_key: str, base_url: str, model: str):
        self.model = model
        self._client = AsyncOpenAI(api_key=api_key, base_url=base_url)

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
            provider=f"openai:{self.model}",
        )
