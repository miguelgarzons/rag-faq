from sqlalchemy import Column, String, Text
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