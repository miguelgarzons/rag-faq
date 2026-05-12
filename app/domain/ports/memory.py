from abc import ABC, abstractmethod


class MemoryRepositoryPort(ABC):
    @abstractmethod
    def save_message(self, user_id: str, session_id: str, role: str, content: str) -> None:
        raise NotImplementedError

    @abstractmethod
    def get_recent_messages(self, user_id: str, session_id: str, limit: int = 6) -> list[dict[str, str]]:
        raise NotImplementedError
