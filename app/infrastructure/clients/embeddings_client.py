import os
from langchain_google_vertexai import VertexAIEmbeddings
from app.domain.ports.embeddings import EmbeddingsPort

class VertexAIEmbeddingsClient(EmbeddingsPort):
    def __init__(self):
        project_id = os.getenv("GCP_PROJECT_ID")
        # Usamos el modelo más reciente de embeddings de Google
        self.embeddings = VertexAIEmbeddings(
            model_name="text-embedding-004", 
            project=project_id
        )

    def get_embedding(self, text: str) -> list[float]:
        print("[IA] Convirtiendo texto a vector matemático...")
        return self.embeddings.embed_query(text)