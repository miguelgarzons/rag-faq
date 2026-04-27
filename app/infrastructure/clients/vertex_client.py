import logging
import os
from typing import Iterator

from langchain_core.prompts import PromptTemplate
from langchain_google_vertexai import ChatVertexAI
from app.domain.ports.llm import LLMClientPort

logger = logging.getLogger(__name__)
logging.getLogger("langchain_google_vertexai").setLevel(logging.ERROR)

class VertexAILlmClient(LLMClientPort):
    def __init__(self):
        self.vertex_enabled = os.getenv("ENABLE_VERTEX_AI", "true").lower() == "true"
        self.model_unavailable = False
        
        project_id = os.getenv("GCP_PROJECT_ID")
        # Por defecto usará gemini-1.0-pro que es el más estable y disponible
        self.model_name = os.getenv("GCP_MODEL_NAME", "gemini-1.0-pro")
        location = os.getenv("GCP_LOCATION", "us-central1")
        timeout = float(os.getenv("GCP_TIMEOUT_SECONDS", "20"))

        if not self.vertex_enabled or not project_id:
            self.llm = None
            return

        # Inicialización directa del modelo
        self.llm = ChatVertexAI(
            model_name=self.model_name,
            project=project_id,
            location=location,
            timeout=timeout,
        )

    def generate_answer(self, context: list[str], question: str) -> str:
        template = """
        Eres un asistente corporativo. Responde a la pregunta del usuario utilizando UNICAMENTE el contexto proporcionado.
        Si la respuesta no esta en el contexto, di "No tengo informacion suficiente sobre ese tema".

        Contexto de los documentos:
        {context}

        Pregunta del usuario: {question}

        Respuesta util:
        """
        prompt = PromptTemplate(template=template, input_variables=["context", "question"])
        context_str = "\n---\n".join(context)

        if not self.llm or self.model_unavailable:
            return "No tengo informacion suficiente sobre ese tema"

        chain = prompt | self.llm

        try:
            response = chain.invoke({"context": context_str, "question": question})
        except Exception as exc:
            message = str(exc)
            if "was not found" in message or "does not have access" in message:
                self.model_unavailable = True
            logger.error("Vertex AI no disponible (model=%s): %s", self.model_name, exc)
            return "No tengo informacion suficiente sobre ese tema"

        if hasattr(response, "content"):
            return str(response.content).strip()

        return str(response).strip()

    def stream_answer(self, context: list[str], question: str) -> Iterator[str]:
        template = """
        Eres un asistente corporativo. Responde a la pregunta del usuario utilizando UNICAMENTE el contexto proporcionado.
        Si la respuesta no esta en el contexto, di "No tengo informacion suficiente sobre ese tema".

        Contexto de los documentos:
        {context}

        Pregunta del usuario: {question}

        Respuesta util:
        """
        prompt = PromptTemplate(template=template, input_variables=["context", "question"])
        context_str = "\n---\n".join(context)

        if not self.llm or self.model_unavailable:
            yield "No tengo informacion suficiente sobre ese tema"
            return

        chain = prompt | self.llm

        try:
            for chunk in chain.stream({"context": context_str, "question": question}):
                if hasattr(chunk, "content"):
                    text = str(chunk.content)
                else:
                    text = str(chunk)

                if text:
                    yield text
        except Exception as exc:
            message = str(exc)
            if "was not found" in message or "does not have access" in message:
                self.model_unavailable = True
            logger.error("Vertex AI no disponible (model=%s): %s", self.model_name, exc)
            yield "No tengo informacion suficiente sobre ese tema"
