import json

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from app.domain.entities import AskRequest, AnswerResponse
from app.application.faq_use_cases import AskFaqUseCase
from app.dependencies import get_ask_faq_use_case

router = APIRouter(prefix="/faq", tags=["FAQ"])

@router.post(
    "/ask",
    response_model=AnswerResponse,
    summary="Responder una pregunta con RAG",
    description=(
        "Recibe una pregunta junto con user_id y session_id opcional; busca contexto "
        "en la base vectorial y retorna una respuesta completa con session_id y fuentes."
    ),
    responses={
        200: {
            "description": "Respuesta generada correctamente",
            "content": {
                "application/json": {
                    "example": {
                        "answer": "El horario de entrada es a las 9:00 AM.",
                        "sources": [
                            "El horario de entrada es a las 9:00 AM.",
                            "Las vacaciones se piden con 15 dias de anticipacion.",
                        ],
                        "session_id": "2c1a453b-06e6-413f-940c-708296428e66",
                    }
                }
            },
        },
        422: {"description": "Error de validacion del body"},
    },
)
def ask_question(request: AskRequest, use_case: AskFaqUseCase = Depends(get_ask_faq_use_case)):
    return use_case.execute(request)


@router.post(
    "/ask/stream",
    summary="Responder pregunta por streaming SSE",
    description=(
        "Mismo input que /faq/ask, pero responde en streaming SSE (text/event-stream). "
        "Eventos emitidos: session, sources, token y done."
    ),
    responses={
        200: {
            "description": "Flujo SSE iniciado correctamente",
            "content": {
                "text/event-stream": {
                    "example": "event: session\\ndata: {\"session_id\": \"...\"}\\n\\n"
                    "event: sources\\ndata: {\"sources\": [\"...\"]}\\n\\n"
                    "event: token\\ndata: {\"token\": \"Hola\"}\\n\\n"
                    "event: done\\ndata: {}\\n\\n"
                }
            },
        },
        422: {"description": "Error de validacion del body"},
    },
)
def ask_question_stream(request: AskRequest, use_case: AskFaqUseCase = Depends(get_ask_faq_use_case)):
    context, answer_stream, session_id = use_case.execute_stream(request)

    def event_stream():
        session_payload = json.dumps({"session_id": session_id}, ensure_ascii=False)
        yield f"event: session\ndata: {session_payload}\n\n"

        sources_payload = json.dumps({"sources": context}, ensure_ascii=False)
        yield f"event: sources\ndata: {sources_payload}\n\n"

        for chunk in answer_stream:
            token_payload = json.dumps({"token": chunk}, ensure_ascii=False)
            yield f"event: token\ndata: {token_payload}\n\n"

        yield "event: done\ndata: {}\n\n"

    headers = {
        "Cache-Control": "no-cache",
        "Connection": "keep-alive",
    }

    return StreamingResponse(event_stream(), media_type="text/event-stream", headers=headers)


@router.post(
    "/ask/chunked",
    summary="Responder pregunta por streaming NDJSON",
    description=(
        "Mismo input que /faq/ask, pero responde en streaming chunked NDJSON "
        "(application/x-ndjson). Cada linea es un JSON con type=session|sources|token|done."
    ),
    responses={
        200: {
            "description": "Flujo NDJSON iniciado correctamente",
            "content": {
                "application/x-ndjson": {
                    "example": "{\"type\":\"session\",\"session_id\":\"...\"}\\n"
                    "{\"type\":\"sources\",\"sources\":[\"...\"]}\\n"
                    "{\"type\":\"token\",\"token\":\"Hola\"}\\n"
                    "{\"type\":\"done\"}\\n"
                }
            },
        },
        422: {"description": "Error de validacion del body"},
    },
)
def ask_question_chunked(request: AskRequest, use_case: AskFaqUseCase = Depends(get_ask_faq_use_case)):
    context, answer_stream, session_id = use_case.execute_stream(request)

    def chunk_stream():
        yield json.dumps({"type": "session", "session_id": session_id}, ensure_ascii=False) + "\n"
        yield json.dumps({"type": "sources", "sources": context}, ensure_ascii=False) + "\n"

        for chunk in answer_stream:
            yield json.dumps({"type": "token", "token": chunk}, ensure_ascii=False) + "\n"

        yield json.dumps({"type": "done"}, ensure_ascii=False) + "\n"

    headers = {
        "Cache-Control": "no-cache",
        "Connection": "keep-alive",
    }

    return StreamingResponse(chunk_stream(), media_type="application/x-ndjson", headers=headers)


@router.post(
    "/debug/retrieval",
    summary="Diagnosticar retrieval y reranking",
    description=(
        "Devuelve detalle del proceso de recuperacion: configuracion RAG activa, "
        "tokens de la pregunta, candidatos y puntajes de reranking hibrido."
    ),
    responses={
        200: {
            "description": "Diagnostico generado correctamente",
            "content": {
                "application/json": {
                    "example": {
                        "question": "Que habilidades menciona?",
                        "department_id": "rrhh",
                        "rag_config": {
                            "profile": "balanced",
                            "top_k": 3,
                            "candidate_multiplier": 4,
                            "candidate_limit": 12,
                            "keyword_weight": 0.35,
                            "score_threshold": 0.45,
                            "thresholds_used": [0.45, 0.55],
                            "effective_score_threshold": 0.55,
                        },
                        "question_tokens": ["habilidades", "menciona"],
                        "candidates_count": 5,
                        "selected_count": 3,
                        "selected_sources": ["..."],
                        "ranked_candidates": [
                            {
                                "rank": 1,
                                "selected": True,
                                "semantic_score": 1.0,
                                "keyword_score": 0.5,
                                "combined_score": 0.825,
                                "content_preview": "...",
                            }
                        ],
                    }
                }
            },
        },
        422: {"description": "Error de validacion del body"},
    },
)
def debug_retrieval(request: AskRequest, use_case: AskFaqUseCase = Depends(get_ask_faq_use_case)):
    return use_case.debug_retrieval(request)
