from app.services.llm.base import BaseLLMProvider, LLMResult


class MockProvider(BaseLLMProvider):
    """无 AI 服务时的降级方案，返回占位文本。

    用途：
    - 开发阶段不消耗 API 费用
    - 无网络/无 key 时保证流程不中断
    - 单元测试时隔离外部依赖
    """

    async def complete(self, prompt: str, system: str | None = None) -> LLMResult:
        return LLMResult(
            content="[AI 处理待配置] 请设置 DEEPSEEK_API_KEY 或启动 Ollama 后重新处理。",
            tokens_used=0,
            provider="mock",
        )
