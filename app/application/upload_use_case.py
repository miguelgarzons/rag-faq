import uuid
from langchain.text_splitter import RecursiveCharacterTextSplitter
from app.domain.entities import UploadResponse # La crearemos en el siguiente paso
from app.domain.ports.repositories import VectorRepositoryPort
from app.domain.ports.embeddings import EmbeddingsPort

class UploadDocumentUseCase:
    def __init__(self, vector_repo: VectorRepositoryPort, embeddings_client: EmbeddingsPort):
        self.vector_repo = vector_repo
        self.embeddings_client = embeddings_client
        
        # Configuramos cómo LangChain cortará el texto
        # 500 caracteres por pedazo, con un traslape de 50 para no cortar ideas a la mitad
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=500,
            chunk_overlap=50
        )

    def execute(self, text_content: str, department_id: str) -> UploadResponse:
        # 1. Dividir el texto gigante en pedazos pequeños
        chunks = self.text_splitter.split_text(text_content)
        
        # 2. Procesar cada pedazo
        for chunk in chunks:
            chunk_id = str(uuid.uuid4()) # ID único
            
            # Convertir a vector
            embedding = self.embeddings_client.get_embedding(chunk)
            
            # Guardar en base de datos
            self.vector_repo.save_chunk(chunk_id, department_id, chunk, embedding)
        
        return UploadResponse(
            message="Documento procesado y guardado con éxito.", 
            chunks_processed=len(chunks)
        )