import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from app.infrastructure.controllers import faq_controller
from app.infrastructure.controllers import knowledge_controller
from app.infrastructure.repositories.database import engine, Base
from app.infrastructure.repositories.models import DocumentChunkModel # Importar para que reconozca la tabla

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

# Este evento se ejecuta al arrancar el servidor
@app.on_event("startup")
def startup_event():
    try:
        with engine.connect() as conn:
            # Activa pgvector en PostgreSQL
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
            conn.commit()

        # Crea las tablas si no existen
        Base.metadata.create_all(bind=engine)
        logger.info("Base de datos y extension pgvector listas.")
    except Exception as exc:
        logger.exception("No se pudo inicializar la base de datos al arranque: %s", exc)

app.include_router(faq_controller.router)
app.include_router(knowledge_controller.router)


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
