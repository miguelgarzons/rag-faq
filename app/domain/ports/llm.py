from abc import ABC, abstractmethod
from typing import Iterator

class LLMClientPort(ABC):
    @abstractmethod
    def generate_answer(self, context: list[str], question: str) -> str:
        pass

    @abstractmethod
    def stream_answer(self, context: list[str], question: str) -> Iterator[str]:
        pass
