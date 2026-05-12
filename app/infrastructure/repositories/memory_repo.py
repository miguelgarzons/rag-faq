import uuid

from app.domain.ports.memory import MemoryRepositoryPort
from app.infrastructure.repositories.database import SessionLocal
from app.infrastructure.repositories.models import ChatMessageModel


class SqlMemoryRepository(MemoryRepositoryPort):
    def save_message(self, user_id: str, session_id: str, role: str, content: str) -> None:
        with SessionLocal() as db:
            message = ChatMessageModel(
                id=str(uuid.uuid4()),
                user_id=user_id,
                session_id=session_id,
                role=role,
                content=content,
            )
            db.add(message)
            db.commit()

    def get_recent_messages(self, user_id: str, session_id: str, limit: int = 6) -> list[dict[str, str]]:
        with SessionLocal() as db:
            rows = (
                db.query(ChatMessageModel)
                .filter(
                    ChatMessageModel.user_id == user_id,
                    ChatMessageModel.session_id == session_id,
                )
                .order_by(ChatMessageModel.created_at.desc())
                .limit(limit)
                .all()
            )

            rows.reverse()
            return [{"role": row.role, "content": row.content} for row in rows]
