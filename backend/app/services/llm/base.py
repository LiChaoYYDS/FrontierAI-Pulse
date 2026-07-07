from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class LLMResult:
    content: str
    tokens_used: int = 0
    provider: str = ""


class BaseLLMProvider(ABC):

    @abstractmethod
    async def complete(self, prompt: str, system: str | None = None) -> LLMResult:
        """发送 prompt 给 LLM，返回统一格式的结果。"""
        ...
