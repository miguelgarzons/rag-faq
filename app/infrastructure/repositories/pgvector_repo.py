from app.domain.ports.repositories import VectorRepositoryPort
from app.infrastructure.repositories.database import SessionLocal
from app.infrastructure.repositories.models import DocumentChunkModel


class PgVectorRepository(VectorRepositoryPort):
    def save_chunk(self, chunk_id: str, department_id: str, content: str, embedding: list[float]):
        with SessionLocal() as db:
            chunk = DocumentChunkModel(
                id=chunk_id,
                department_id=department_id,
                content=content,
                embedding=embedding
            )
            db.add(chunk)
            db.commit()

    def chunk_exists(self, department_id: str, content: str) -> bool:
        with SessionLocal() as db:
            return (
                db.query(DocumentChunkModel.id)
                .filter(
                    DocumentChunkModel.department_id == department_id,
                    DocumentChunkModel.content == content,
                )
                .first()
                is not None
            )

    def search_similar(
        self,
        question_vector: list[float],
        department_id: str,
        limit: int = 3,
        score_threshold: float | None = None,
    ) -> list[str]:
        with SessionLocal() as db:
            print(f"[DB] Buscando coincidencias reales en pgvector para: {department_id}")
            distance = DocumentChunkModel.embedding.cosine_distance(question_vector).label("distance")
            query = db.query(DocumentChunkModel.content, distance).filter(
                DocumentChunkModel.department_id == department_id
            ).order_by(
                distance
            )

            candidates = query.limit(limit * 5).all()

            filtered: list[str] = []
            for content, candidate_distance in candidates:
                if score_threshold is not None and candidate_distance > score_threshold:
                    continue
                filtered.append(content)
                if len(filtered) >= limit:
                    break

            return filtered
