import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

logger = logging.getLogger(__name__)

app = FastAPI(
    title="FAQ RAG API - Hexagonal",
    version="1.0.0",
    description=(
        "API RAG para carga de conocimiento y preguntas por departamento. "
        "Incluye respuesta normal y streaming (SSE y NDJSON)."
    ),
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8080"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
def startup_event():
    try:
        from app.infrastructure.controllers import faq_controller

        app.include_router(faq_controller.router)
    except Exception as exc:
        logger.exception("No se pudo registrar router FAQ: %s", exc)

    try:
        from app.infrastructure.controllers import knowledge_controller

        app.include_router(knowledge_controller.router)
    except Exception as exc:
        logger.exception("No se pudo registrar router Knowledge: %s", exc)


@app.get(
    "/",
    summary="Health check",
    description="Verifica que la API este arriba y respondiendo.",
    responses={
        200: {
            "description": "API disponible",
            "content": {
                "application/json": {
                    "example": {"status": "Arquitectura Hexagonal en linea"}
                }
            },
        }
    },
)
def health_check():
    return {"status": "Arquitectura Hexagonal en línea"}
