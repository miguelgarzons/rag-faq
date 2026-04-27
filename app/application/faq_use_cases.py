from typing import Iterator
import os
import re

from app.domain.entities import AskRequest, AnswerResponse
from app.domain.ports.repositories import VectorRepositoryPort
from app.domain.ports.llm import LLMClientPort
from app.domain.ports.embeddings import EmbeddingsPort

class AskFaqUseCase:
    def __init__(self, vector_repo: VectorRepositoryPort, llm_client: LLMClientPort, embeddings_client: EmbeddingsPort):
        self.vector_repo = vector_repo
        self.llm_client = llm_client
        self.embeddings_client = embeddings_client
        self.rag_profile = os.getenv("RAG_PROFILE", "balanced").strip().lower()
        defaults = self._profile_defaults(self.rag_profile)

        self.search_limit = self._read_int("RAG_TOP_K", defaults["top_k"], min_value=1)
        self.candidate_multiplier = self._read_int("RAG_CANDIDATE_MULTIPLIER", defaults["candidate_multiplier"], min_value=1)
        self.keyword_weight = self._read_float("RAG_KEYWORD_WEIGHT", defaults["keyword_weight"], min_value=0.0, max_value=1.0)
        self.score_threshold = self._read_float("RAG_SCORE_THRESHOLD", defaults["score_threshold"], min_value=0.0, max_value=2.0)
        self.threshold_fallback_steps = self._read_threshold_fallback_steps("RAG_THRESHOLD_FALLBACK_STEPS", "0.10,0.20,0.35")
        self.max_score_threshold = self._read_float("RAG_MAX_SCORE_THRESHOLD", 0.95, min_value=0.0, max_value=2.0)

    def execute(self, request: AskRequest) -> AnswerResponse:
        # 1. Convertir la pregunta en un vector
        question_vector = self.embeddings_client.get_embedding(request.question)
        
        # 2. Buscar fragmentos reales en pgvector
        retrieval_debug = self._retrieve_context_debug(
            question_vector=question_vector,
            question=request.question,
            department_id=request.department_id,
        )
        context = retrieval_debug["selected_context"]
        clean_sources = self._clean_sources(context)

        if not context:
            return AnswerResponse(answer="No tengo informacion suficiente sobre ese tema.", sources=[])
        
        # 3. Generar respuesta con Gemini
        answer = self.llm_client.generate_answer(context, request.question)
        
        return AnswerResponse(answer=answer, sources=clean_sources)

    def execute_stream(self, request: AskRequest) -> tuple[list[str], Iterator[str]]:
        question_vector = self.embeddings_client.get_embedding(request.question)
        retrieval_debug = self._retrieve_context_debug(
            question_vector=question_vector,
            question=request.question,
            department_id=request.department_id,
        )
        context = retrieval_debug["selected_context"]
        clean_sources = self._clean_sources(context)

        if not context:
            return [], iter(["No tengo informacion suficiente sobre ese tema."])

        answer_stream = self.llm_client.stream_answer(context, request.question)

        return clean_sources, answer_stream

    def debug_retrieval(self, request: AskRequest) -> dict:
        question_vector = self.embeddings_client.get_embedding(request.question)
        retrieval_debug = self._retrieve_context_debug(
            question_vector=question_vector,
            question=request.question,
            department_id=request.department_id,
        )

        selected_context = retrieval_debug["selected_context"]
        clean_sources = self._clean_sources(selected_context)

        return {
            "question": request.question,
            "department_id": request.department_id,
            "rag_config": retrieval_debug["rag_config"],
            "question_tokens": retrieval_debug["question_tokens"],
            "candidates_count": retrieval_debug["candidates_count"],
            "selected_count": len(selected_context),
            "selected_sources": clean_sources,
            "ranked_candidates": retrieval_debug["ranked_candidates"],
        }

    def _read_int(self, key: str, default: int, min_value: int = 1) -> int:
        raw_value = os.getenv(key)
        if not raw_value:
            return default
        try:
            parsed = int(raw_value)
        except ValueError:
            return default
        return max(min_value, parsed)

    def _read_float(self, key: str, default: float, min_value: float, max_value: float) -> float:
        raw_value = os.getenv(key)
        if not raw_value:
            return default
        try:
            parsed = float(raw_value)
        except ValueError:
            return default
        return min(max_value, max(min_value, parsed))

    def _profile_defaults(self, profile: str) -> dict[str, float | int]:
        profiles: dict[str, dict[str, float | int]] = {
            "strict": {
                "top_k": 2,
                "candidate_multiplier": 5,
                "keyword_weight": 0.25,
                "score_threshold": 0.35,
            },
            "balanced": {
                "top_k": 3,
                "candidate_multiplier": 4,
                "keyword_weight": 0.35,
                "score_threshold": 0.45,
            },
            "recall": {
                "top_k": 5,
                "candidate_multiplier": 3,
                "keyword_weight": 0.45,
                "score_threshold": 0.70,
            },
        }
        return profiles.get(profile, profiles["balanced"])

    def _read_threshold_fallback_steps(self, key: str, default: str) -> list[float]:
        raw_value = os.getenv(key, default)
        parts = [p.strip() for p in raw_value.split(",") if p.strip()]
        steps: list[float] = []
        for part in parts:
            try:
                value = float(part)
            except ValueError:
                continue
            if value > 0:
                steps.append(value)
        return steps

    def _retrieve_context_debug(self, question_vector: list[float], question: str, department_id: str) -> dict:
        candidate_limit = self.search_limit * self.candidate_multiplier
        thresholds_used: list[float] = []
        candidates: list[str] = []

        current_threshold = self.score_threshold
        thresholds_used.append(current_threshold)
        candidates = self.vector_repo.search_similar(
            question_vector,
            department_id,
            limit=candidate_limit,
            score_threshold=current_threshold,
        )

        if not candidates and self.threshold_fallback_steps:
            for step in self.threshold_fallback_steps:
                current_threshold = min(self.max_score_threshold, (self.score_threshold or 0.0) + step)
                if current_threshold in thresholds_used:
                    continue
                thresholds_used.append(current_threshold)
                candidates = self.vector_repo.search_similar(
                    question_vector,
                    department_id,
                    limit=candidate_limit,
                    score_threshold=current_threshold,
                )
                if candidates:
                    break

        question_tokens = sorted(self._tokenize(question))
        rag_config = {
            "profile": self.rag_profile,
            "top_k": self.search_limit,
            "candidate_multiplier": self.candidate_multiplier,
            "candidate_limit": candidate_limit,
            "keyword_weight": self.keyword_weight,
            "score_threshold": self.score_threshold,
            "thresholds_used": thresholds_used,
            "effective_score_threshold": current_threshold,
        }

        if not candidates:
            return {
                "rag_config": rag_config,
                "question_tokens": question_tokens,
                "candidates_count": 0,
                "selected_context": [],
                "ranked_candidates": [],
            }

        scored_candidates = self._score_candidates(question_tokens, candidates)
        selected_context = [item["content"] for item in scored_candidates[: self.search_limit]]

        ranked_candidates = []
        for rank, item in enumerate(scored_candidates, start=1):
            ranked_candidates.append(
                {
                    "rank": rank,
                    "selected": rank <= self.search_limit,
                    "semantic_score": round(item["semantic_score"], 4),
                    "keyword_score": round(item["keyword_score"], 4),
                    "combined_score": round(item["combined_score"], 4),
                    "content_preview": self._preview(item["content"]),
                }
            )

        return {
            "rag_config": rag_config,
            "question_tokens": question_tokens,
            "candidates_count": len(candidates),
            "selected_context": selected_context,
            "ranked_candidates": ranked_candidates,
        }

    def _score_candidates(self, question_tokens: list[str], candidates: list[str]) -> list[dict]:
        question_token_set = set(question_tokens)
        if not question_tokens:
            return [
                {
                    "content": candidate,
                    "semantic_score": 1.0,
                    "keyword_score": 0.0,
                    "combined_score": 1.0,
                }
                for candidate in candidates
            ]

        total = len(candidates)
        scored: list[dict] = []

        for idx, candidate in enumerate(candidates):
            semantic_score = 1.0 - (idx / max(1, total))
            candidate_tokens = self._tokenize(candidate)

            keyword_score = 0.0
            if candidate_tokens:
                overlap = len(question_token_set.intersection(candidate_tokens))
                keyword_score = overlap / len(question_token_set)

            combined_score = ((1.0 - self.keyword_weight) * semantic_score) + (self.keyword_weight * keyword_score)
            scored.append(
                {
                    "content": candidate,
                    "semantic_score": semantic_score,
                    "keyword_score": keyword_score,
                    "combined_score": combined_score,
                    "_idx": idx,
                }
            )

        scored.sort(key=lambda item: (item["combined_score"], -item["_idx"]), reverse=True)
        for item in scored:
            item.pop("_idx", None)
        return scored

    def _tokenize(self, text: str) -> set[str]:
        stopwords = {
            "de", "la", "el", "en", "y", "a", "los", "las", "del", "por", "para", "con",
            "que", "una", "un", "se", "es", "al", "como", "su", "sus", "o", "lo", "mi", "tu",
            "the", "and", "for", "with", "to", "of", "in", "on", "is", "are",
        }
        tokens = re.findall(r"[a-zA-Z0-9_]+", text.lower())
        return {token for token in tokens if len(token) > 2 and token not in stopwords}

    def _clean_sources(self, sources: list[str]) -> list[str]:
        cleaned: list[str] = []
        seen: set[str] = set()

        for source in sources:
            normalized = re.sub(r"\s+", " ", source).strip()
            if not normalized:
                continue

            snippet = normalized[:220].rstrip()
            if len(normalized) > 220:
                snippet += "..."

            if snippet in seen:
                continue

            seen.add(snippet)
            cleaned.append(snippet)

        return cleaned

    def _preview(self, text: str, max_len: int = 220) -> str:
        normalized = re.sub(r"\s+", " ", text).strip()
        if len(normalized) <= max_len:
            return normalized
        return normalized[:max_len].rstrip() + "..."
