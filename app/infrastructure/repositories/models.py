from sqlalchemy import Column, DateTime, String, Text, func
from pgvector.sqlalchemy import Vector
from app.infrastructure.repositories.database import Base

class DocumentChunkModel(Base):
    __tablename__ = "document_chunks"

    # Un ID único generado automáticamente
    id = Column(String, primary_key=True)
    
    # El departamento al que pertenece (ej. "rrhh", "ventas")
    department_id = Column(String, index=True, nullable=False)
    
    # El texto del documento original
    content = Column(Text, nullable=False)
    
    # El vector matemático (768 dimensiones para Google Vertex AI Embeddings)
    embedding = Column(Vector(768))


class ChatMessageModel(Base):
    __tablename__ = "chat_messages"

    id = Column(String, primary_key=True)
    user_id = Column(String, index=True, nullable=False)
    session_id = Column(String, index=True, nullable=False)
    role = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
