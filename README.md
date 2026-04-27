# RAG FAQ API

API backend con FastAPI para:

- cargar documentos de conocimiento por departamento,
- consultar respuestas con RAG,
- consumir respuestas en modo normal o en streaming.

## URLs base

- API local: `http://localhost:8002`
- Swagger UI: `http://localhost:8002/docs`
- ReDoc: `http://localhost:8002/redoc`
- OpenAPI JSON: `http://localhost:8002/openapi.json`

## Resumen rapido de endpoints

- `GET /` -> salud de la API
- `POST /knowledge/upload` -> sube conocimiento (`.txt`, `.pdf`, `.docx`)
- `POST /faq/ask` -> respuesta completa en JSON
- `POST /faq/ask/stream` -> streaming SSE (`text/event-stream`)
- `POST /faq/ask/chunked` -> streaming NDJSON (`application/x-ndjson`)
- `POST /faq/debug/retrieval` -> diagnostico de retrieval y reranking

---

## 1) `GET /`

### Objetivo

Confirmar que el backend esta arriba y responde.

### Request

- Metodo: `GET`
- Body: no aplica
- Headers requeridos: ninguno

### Response exitosa (200)

```json
{
  "status": "Arquitectura Hexagonal en línea"
}
```

### Errores comunes

- `502/503`: servicio no disponible o contenedor caido.

---

## 2) `POST /knowledge/upload`

### Objetivo

Subir un documento para indexarlo en la base vectorial (pgvector) por departamento.

### Formatos soportados

- `.txt`
- `.pdf`
- `.docx`

### Request

- Metodo: `POST`
- Content-Type: `multipart/form-data`
- Campos:
  - `department_id` (string): identificador del departamento. Ejemplo: `rrhh`.
  - `file` (archivo): documento a procesar.

### Ejemplo curl

```bash
curl -X POST "http://localhost:8002/knowledge/upload" \
  -F "department_id=rrhh" \
  -F "file=@./cv.txt"
```

### Response exitosa (200)

```json
{
  "message": "Documento procesado correctamente",
  "chunks_processed": 12
}
```

Cuando el archivo trae contenido repetido (o ya fue cargado antes para el mismo `department_id`), la API evita insertar duplicados y responde con mensajes como:

- `"El documento ya existe para este departamento. No se insertaron chunks."`
- `"Documento procesado con deduplicacion. Se insertaron X chunks y se omitieron Y repetidos."`

### Errores posibles

- `400` cuando:
  - el formato no es `.txt`, `.pdf` o `.docx`,
  - el archivo esta vacio o no se pudo extraer texto.
- `422` si falta `department_id` o `file`.
- `500` si ocurre un error interno durante extraccion/procesamiento.

### Notas

- Un mismo `department_id` puede tener multiples documentos.
- El contenido se guarda en fragmentos (`chunks`) con su embedding.

---

## 3) `POST /faq/ask`

### Objetivo

Responder una pregunta en una sola respuesta JSON usando RAG.

### Request

- Metodo: `POST`
- Content-Type: `application/json`
- Body:

```json
{
  "question": "Cual es el horario de entrada?",
  "department_id": "rrhh"
}
```

### Response exitosa (200)

```json
{
  "answer": "El horario de entrada es a las 9:00 AM.",
  "sources": [
    "El horario de entrada es a las 9:00 AM.",
    "Las vacaciones se piden con 15 dias de anticipacion."
  ]
}
```

### Errores posibles

- `422` si faltan campos o tienen tipo invalido.

### Notas

- `sources` trae los fragmentos recuperados de la base vectorial.
- Si el LLM no esta disponible, el backend puede devolver una respuesta fallback.

---

## 4) `POST /faq/ask/stream` (SSE)

### Objetivo

Enviar la respuesta por partes para que el frontend la vaya pintando en tiempo real.

### Tipo de streaming

- Protocolo: SSE
- Response Content-Type: `text/event-stream`

### Request

- Metodo: `POST`
- Content-Type: `application/json`
- Body igual que `/faq/ask`:

```json
{
  "question": "Cual es el horario de entrada?",
  "department_id": "rrhh"
}
```

### Eventos emitidos

- `sources`: fuentes recuperadas antes de emitir tokens.
- `token`: fragmento de texto de la respuesta.
- `done`: fin de stream.

### Ejemplo de stream

```text
event: sources
data: {"sources": ["..."]}

event: token
data: {"token": "El horario"}

event: token
data: {"token": " de entrada"}

event: token
data: {"token": " es a las 9:00 AM."}

event: done
data: {}
```

### Ejemplo curl

```bash
curl -N -X POST "http://localhost:8002/faq/ask/stream" \
  -H "Content-Type: application/json" \
  -d '{"question":"Cual es el horario de entrada?","department_id":"rrhh"}'
```

### Errores posibles

- `422` si el JSON de entrada es invalido.

### Nota frontend

- Como el endpoint es `POST`, normalmente se consume con `fetch` + `ReadableStream`.

---

## 5) `POST /faq/ask/chunked` (NDJSON)

### Objetivo

Alternativa de streaming para clientes que prefieren lineas JSON en vez de SSE.

### Tipo de streaming

- Response Content-Type: `application/x-ndjson`
- Cada linea es un JSON independiente.

### Request

- Metodo: `POST`
- Content-Type: `application/json`
- Body igual que `/faq/ask`.

### Formato de eventos NDJSON

- `{"type":"sources","sources":[...]}`
- `{"type":"token","token":"..."}` (varias lineas)
- `{"type":"done"}`

### Ejemplo de stream

```text
{"type":"sources","sources":["..."]}
{"type":"token","token":"El horario"}
{"type":"token","token":" de entrada"}
{"type":"token","token":" es a las 9:00 AM."}
{"type":"done"}
```

### Ejemplo curl

```bash
curl -N -X POST "http://localhost:8002/faq/ask/chunked" \
  -H "Content-Type: application/json" \
  -d '{"question":"Cual es el horario de entrada?","department_id":"rrhh"}'
```

### Errores posibles

- `422` si el JSON de entrada es invalido.

---

## 6) `POST /faq/debug/retrieval`

### Objetivo

Inspeccionar como se recupera y reordena el contexto en el pipeline RAG.

### Request

- Metodo: `POST`
- Content-Type: `application/json`
- Body igual que `/faq/ask`.

### Response exitosa (200)

Devuelve:

- configuracion RAG activa,
- tokens de la pregunta,
- total de candidatos recuperados,
- fuentes seleccionadas finales,
- ranking completo de candidatos con puntajes.

Ejemplo:

```json
{
  "question": "Que habilidades menciona?",
  "department_id": "rrhh",
  "rag_config": {
    "profile": "balanced",
    "top_k": 3,
    "candidate_multiplier": 4,
    "candidate_limit": 12,
    "keyword_weight": 0.35,
    "score_threshold": 0.45
  },
  "question_tokens": ["habilidades", "menciona"],
  "candidates_count": 5,
  "selected_count": 3,
  "selected_sources": ["..."],
  "ranked_candidates": [
    {
      "rank": 1,
      "selected": true,
      "semantic_score": 1.0,
      "keyword_score": 0.5,
      "combined_score": 0.825,
      "content_preview": "..."
    }
  ]
}
```

### Ejemplo curl

```bash
curl -X POST "http://localhost:8002/faq/debug/retrieval" \
  -H "Content-Type: application/json" \
  -d '{"question":"Que habilidades menciona?","department_id":"rrhh"}'
```

### Errores posibles

- `422` si el JSON de entrada es invalido.

---

## Estados HTTP esperados

- `200`: operacion correcta
- `400`: validacion funcional (ejemplo: formato de archivo no soportado)
- `422`: validacion de esquema/entrada FastAPI
- `500`: error interno del servidor

---

## Flujo recomendado de uso

1. Subir documentos con `POST /knowledge/upload`.
2. Preguntar con `POST /faq/ask` si quieres respuesta completa.
3. Usar `POST /faq/ask/stream` o `POST /faq/ask/chunked` si tu frontend necesita render progresivo.
4. Usar `POST /faq/debug/retrieval` cuando quieras calibrar calidad RAG.

---

## Observaciones para frontend

- Si usas SSE con `POST`, evita `EventSource` directo y usa `fetch` con lectura de stream.
- Para parsing simple por linea, `NDJSON` suele ser mas facil de manejar en algunos clientes.
- En ambos streams, usa `sources` al inicio para mostrar referencias y luego concatena `token` para construir la respuesta final.

---

## Deploy automatico a Cloud Run (GitHub Actions)

Se agrego el workflow:

- `.github/workflows/deploy-cloud-run.yml`

Dispara en `push` a `main/master` o manual (`workflow_dispatch`).

### Secrets requeridos

- `GCP_PROJECT_ID`: ID del proyecto de Google Cloud.
- `GCP_SA_KEY`: JSON de Service Account con permisos para:
  - Cloud Run Admin
  - Service Account User
  - Storage Admin (si aplica)
  - Artifact Registry Writer (o permisos de push a gcr.io)

### Variables opcionales (Repository Variables)

- `CLOUD_RUN_SERVICE` (default: `rag-faq-api`)
- `CLOUD_RUN_REGION` (default: `us-central1`)
- `GCP_MODEL_NAME` (default: `gemini-2.5-pro`)
- `GCP_LOCATION` (default: `us-central1`)
- `ENABLE_VERTEX_AI` (default: `true`)

---

## Ajustes de calidad RAG

Puedes afinar la calidad de recuperacion con variables en `.env`:

- `RAG_PROFILE`: perfil predefinido (`strict`, `balanced`, `recall`).
- `RAG_TOP_K`: cantidad maxima de fragmentos usados como contexto.
- `RAG_CANDIDATE_MULTIPLIER`: cuantos candidatos iniciales recuperar antes de rerank.
- `RAG_KEYWORD_WEIGHT`: peso del matching de palabras clave (0.0 a 1.0).
- `RAG_SCORE_THRESHOLD`: umbral maximo de distancia coseno.
- `RAG_THRESHOLD_FALLBACK_STEPS`: incrementos de threshold si no hay candidatos.
- `RAG_MAX_SCORE_THRESHOLD`: limite superior del fallback.

Perfiles sugeridos:

- `strict`: menos ruido, mas conservador.
- `balanced`: equilibrio general recomendado.
- `recall`: recupera mas contexto, tolera mas ruido.

Recomendacion inicial:

- `RAG_PROFILE=balanced`
- `RAG_TOP_K=3`
- `RAG_CANDIDATE_MULTIPLIER=4`
- `RAG_KEYWORD_WEIGHT=0.35`
- `RAG_SCORE_THRESHOLD=0.45`
- `RAG_THRESHOLD_FALLBACK_STEPS=0.10,0.20,0.35`
- `RAG_MAX_SCORE_THRESHOLD=0.95`

Nota: si defines `RAG_TOP_K`, `RAG_CANDIDATE_MULTIPLIER`, `RAG_KEYWORD_WEIGHT` o `RAG_SCORE_THRESHOLD`, esos valores sobrescriben el perfil.

Interpretacion de `RAG_SCORE_THRESHOLD`:

- valor mas bajo -> mas estricto, menos ruido, mas posibles "no tengo informacion".
- valor mas alto -> mas flexible, mas recall, pero puede meter contexto irrelevante.

Interpretacion de `RAG_KEYWORD_WEIGHT`:

- cercano a `0.0` -> prioriza similitud semantica pura.
- cercano a `1.0` -> prioriza overlap de palabras clave.

Fallback de threshold:

- Si no hay candidatos con `RAG_SCORE_THRESHOLD`, el backend intenta thresholds mas flexibles usando `RAG_THRESHOLD_FALLBACK_STEPS`.
- El valor final usado queda visible en `/faq/debug/retrieval` como `effective_score_threshold` y `thresholds_used`.
