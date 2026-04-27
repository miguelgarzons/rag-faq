from abc import ABC, abstractmethod

class EmbeddingsPort(ABC):
    @abstractmethod
    def get_embedding(self, text: str) -> list[float]:
        pass