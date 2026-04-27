from abc import ABC, abstractmethod

class VectorRepositoryPort(ABC):
    @abstractmethod
    def save_chunk(self, chunk_id: str, department_id: str, content: str, embedding: list[float]):
        pass

    @abstractmethod
    def chunk_exists(self, department_id: str, content: str) -> bool:
        pass

    @abstractmethod
    def search_similar(
        self,
        question_vector: list[float],
        department_id: str,
        limit: int = 3,
        score_threshold: float | None = None,
    ) -> list[str]:
        pass
