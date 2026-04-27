from app.infrastructure.repositories.pgvector_repo import PgVectorRepository
from app.infrastructure.clients.vertex_client import VertexAILlmClient
from app.infrastructure.clients.embeddings_client import VertexAIEmbeddingsClient
from app.application.faq_use_cases import AskFaqUseCase
from app.application.upload_use_case import UploadDocumentUseCase
def get_vector_repo():
    return PgVectorRepository()

def get_llm_client():
    return VertexAILlmClient()

def get_embeddings_client():
    return VertexAIEmbeddingsClient()

def get_ask_faq_use_case():
    return AskFaqUseCase(
        vector_repo=get_vector_repo(), 
        llm_client=get_llm_client(),
        embeddings_client=get_embeddings_client()
    )

def get_upload_use_case():
    return UploadDocumentUseCase(
        vector_repo=get_vector_repo(), 
        embeddings_client=get_embeddings_client()
    )