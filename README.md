# cv-aligner-ai-backend

Backend del optimizador de CV multi-agente, construido con FastAPI y arquitectura hexagonal.

## Stack

- Python 3.12+
- Gestor de dependencias y entornos: [uv](https://docs.astral.sh/uv/)
- Frameworks: FastAPI, Pydantic v2, LangGraph
- LLM: SDK oficial `openai` (compatible con OpenAI, Ollama, LM Studio, etc.)
- Testing: pytest, pytest-asyncio

## Instalación

### Requisitos

- Python 3.12+ (la versión exacta está fijada en `.python-version`)
- [uv](https://docs.astral.sh/uv/)

### 1. Instalar uv

Si ya lo tienes, sáltate este paso.

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Alternativas: `pipx install uv` o `brew install uv`.

### 2. Clonar el repositorio

```bash
git clone https://github.com/papopapota/cv-aligner-ai-backend.git
cd cv-aligner-ai-backend
```

### 3. Crear el entorno e instalar dependencias

```bash
uv sync
```

Crea `.venv` con la versión de Python de `.python-version`, instala el proyecto en editable y el grupo `dev` (pytest, pytest-asyncio).

## Ejecución

```bash
uv run uvicorn src.main:app --reload
```

La app queda disponible en `http://127.0.0.1:8000`, con la documentación interactiva en `/docs`.

```bash
curl http://127.0.0.1:8000/health
# {"status":"ok"}
```

`uv run` usa el entorno del proyecto automáticamente. Si prefieres activarlo a mano: `source .venv/bin/activate` (en Windows, `.venv\Scripts\activate`).

## Configuración del LLM

Copia `.env.example` a `.env` (el `.env` no se commitea):

| Variable | Uso |
| --- | --- |
| `LLM_API_KEY` | Obligatoria. Sin ella `uvicorn` falla al arrancar con un mensaje claro. |
| `LLM_BASE_URL` | Vacío usa el endpoint de OpenAI. Para local (Ollama, LM Studio) pon su URL de API. |
| `LLM_MODEL` | Modelo por defecto (`gpt-4o-mini`). |
| `LLM_MAX_TOKENS` | Default global: tope de cada rol que no defina su propia variable. |
| `LLM_EXTRACTOR_MAX_TOKENS` | Tope del extractor. No definida → `LLM_MAX_TOKENS`. |
| `LLM_ANALYZER_MAX_TOKENS` | Tope del analyzer. No definida → `LLM_MAX_TOKENS`. |
| `LLM_WRITER_MAX_TOKENS` | Tope del writer. No definida → `LLM_MAX_TOKENS`. |
| `LLM_AUDITOR_MAX_TOKENS` | Tope del auditor. No definida → `LLM_MAX_TOKENS`. |
| `LLM_TIMEOUT_SECONDS` | Timeout por llamada en segundos. |
| `AUDIT_VARIANCE_THRESHOLD` | Umbral de varianza del auditor (0..1, default 0.45). Por encima, el writer se reintenta. |

### Autenticación y CORS

| Variable | Uso |
| --- | --- |
| `JWT_SECRET_KEY` | Clave con la que se firman los tokens. Si no se define, se genera una aleatoria por proceso y los tokens dejan de ser válidos al reiniciar. |
| `JWT_ALGORITHM` | Algoritmo de firma (`HS256` por defecto). |
| `JWT_ACCESS_TOKEN_EXPIRE_MINUTES` | Vida del access token en minutos (30 por defecto). |
| `JWT_REFRESH_TOKEN_EXPIRE_DAYS` | Vida del refresh token en días (7 por defecto). |
| `CORS_ORIGINS` | Orígenes permitidos, separados por coma (`http://localhost:3000,http://127.0.0.1:3000` por defecto). |

El adaptador (`OpenAILLMAgentAdapter`) envía mensajes `system` por rol (extractor/analyzer/writer/auditor) con temperatura distinta por rol. El auditor evalúa tanto el CV original como el optimizado y responde JSON `{"variance_score": …}`; si no, el grafo intenta parsear el primer número del texto como fallback. El primer score se calcula una sola vez en paralelo con las fases de extracción y análisis, y el segundo se recalcula en cada intento del auditor.

En cada reintento el writer recibe el CV optimizado anterior y el motivo (`reason`) del auditor para corregir las carencias señaladas. El adaptador registra por log el `variance_score` y el `reason` de cada intento (nivel INFO/WARNING) para diagnosticar por qué no converge.

## Base de datos, migraciones y almacenamiento

La persistencia usa SQLAlchemy 2.0 async con `asyncpg`. La configuración se toma de las variables `DB_*` del `.env` (`DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`).

Los CVs se guardan en S3 (o LocalStack en desarrollo). La app verifica/crea el bucket al arrancar mediante `S3StorageAdapter.ensure_bucket()`; si el almacenamiento no está disponible, registra un warning y continúa.

| Variable | Uso |
| --- | --- |
| `S3_ENDPOINT_URL` | Endpoint de S3. LocalStack: `http://localhost:4566`. Vacío usa AWS. |
| `S3_REGION` | Región de S3 (default `us-east-1`). |
| `S3_ACCESS_KEY_ID` | Access key de S3/LocalStack. |
| `S3_SECRET_ACCESS_KEY` | Secret key de S3/LocalStack. |
| `S3_BUCKET` | Bucket de los CVs (default `cv-aligner-cvs`). |
| `S3_USE_SSL` | Usa TLS contra S3 (`false` para LocalStack local). |

### Levantar PostgreSQL y LocalStack con Docker Compose

El `compose.yaml` levanta PostgreSQL, LocalStack (servicio S3) y un contenedor de inicialización que crea el bucket. Usa las variables `DB_*` y `S3_*` del `.env`:

```bash
docker compose up -d db localstack
docker compose ps
```

Espera a que `db` y `localstack` aparezcan como `healthy` antes de aplicar las migraciones o subir CVs. Para detenerlo:

```bash
docker compose down
```

`docker compose down -v` también elimina el volumen y, por tanto, los datos de PostgreSQL.

El esquema se gestiona con Alembic:

```bash
# Aplica todas las migraciones pendientes
uv run alembic upgrade head

# Crea una nueva migración a partir de los modelos
uv run alembic revision --autogenerate -m "descripcion"

# Revierte la última migración
uv run alembic downgrade -1
```

Si la tabla `users` ya existía antes de adoptar Alembic, marca la migración inicial como aplicada en lugar de volver a crearla:

```bash
uv run alembic stamp head
```

## Scoring cuantitativo (IC)

El `EmbeddingMatchScorerAdapter` calcula el Índice de Compatibilidad (IC) entre candidato y oferta. Está **cableado en `composition.py`**: reutiliza el mismo cliente OpenAI para embeddings y delega las métricas al dominio (`compatibility_metrics.py` y `tfidf.py`). El orquestador extrae las subdimensiones (`SemanticProfile`) del candidato y de la oferta, calcula el baseline de IC, re-verifica el CV optimizado y condiciona la aprobación a `ic >= MATCH_TARGET_IC` **y** al umbral de varianza. La extracción del CV y de la oferta arranca en paralelo, y los embeddings globales y por dimensión se agrupan en una sola petición. Si tras `MAX_WRITER_ATTEMPTS` no convergen ambos gates, se devuelve la mejor versión de IC con su **gap report** (best-effort).

Fórmula implementada:

```text
Ncos   = similitud coseno de embeddings, clampada a [0, 1]
Ntfidf = suma de TF-IDF de los términos compartidos / suma de TF-IDF de la oferta
Neuc   = 1 - (distancia euclidiana de vectores unitarios / 2)
IC     = 100 * (0.50 * Ncos + 0.30 * Ntfidf + 0.20 * Neuc)
```

El corpus TF-IDF es la pareja `[CV, oferta]`, con `idf(w) = log((1 + N) / (1 + df(w))) + 1`. Si la oferta no tiene tokens válidos, `Ntfidf = 0`. Los vectores se normalizan L2 antes de calcular `Neuc`, con `dmax = 2`; los vectores nulos y los textos vacíos producen métricas `0`.

| Variable | Uso |
| --- | --- |
| `MATCH_TARGET_IC` | Umbral de aprobación del IC, escala `0..100` (default `85`). |
| `MATCH_WEIGHT_NCOS` | Peso de `Ncos` (default `0.50`). |
| `MATCH_WEIGHT_NTFIDF` | Peso de `Ntfidf` (default `0.30`). |
| `MATCH_WEIGHT_NEUC` | Peso de `Neuc` (default `0.20`). |
| `MATCH_EMBEDDING_MODEL` | Modelo de embeddings (default `text-embedding-3-small`). |

Los pesos deben sumar 1. Antes de generar embeddings y calcular TF-IDF se ofuscan datos personales y atributos demográficos (edad, email, teléfono, nacionalidad, foto, etc.). Los desgloses `original_per_dimension` y `optimized_per_dimension` siguen siendo un diagnóstico con similitud coseno por dimensión y no influyen en el IC. Se puntúan todas las dimensiones no vacías de la oferta; si el CV no aporta texto para una de ellas, recibe `0.0`. Esto incluye `education` y `certifications` cuando la oferta las pide.

## Endpoints

| Método | Ruta | Descripción | Respuesta |
| ------ | ---- | ----------- | --------- |
| GET | `/health` | Verificación de estado | `{"status": "ok"}` |
| POST | `/api/v1/auth/register` | Registro de usuario (hash bcrypt) | Usuario creado |
| POST | `/api/v1/auth/login` | Login con email y contraseña | Tokens JWT |
| POST | `/api/v1/auth/refresh` | Renueva tokens con un refresh token | Tokens JWT |
| POST | `/api/v1/cvs` | Sube un CV a S3 e inicia el parseo en background | CV creado (`202`) |
| GET | `/api/v1/cvs` | Lista los CVs del usuario autenticado | Array de CVs |
| GET | `/api/v1/cvs/{cv_id}` | Consulta el estado/procesamiento de un CV | Estado del CV |
| GET | `/api/v1/cvs/{cv_id}/content` | Devuelve el texto extraído; opcionalmente el JSON estructurado | Contenido del CV |
| POST | `/api/v1/cvs/{cv_id}/optimize` | Optimiza un CV ya parseado contra una oferta | CV optimizado |
| GET | `/api/v1/applications` | Lista las postulaciones del usuario autenticado | Array de postulaciones |
| POST | `/api/v1/applications` | Crea una postulación para el usuario autenticado | Postulación creada (`201`) |
| PATCH | `/api/v1/applications/{id}/status` | Actualiza el estado de una postulación | Postulación actualizada |
| DELETE | `/api/v1/applications/{id}` | Elimina una postulación del usuario autenticado | `204` sin body |

Todos los endpoints de CV y postulaciones requieren `Authorization: Bearer <access_token>`. El dueño se obtiene del `sub` del JWT (email), nunca de un `user_id` enviado por el cliente.

### Contrato de `/api/v1/applications`

```http
GET /api/v1/applications
```

Devuelve solo las postulaciones del usuario autenticado, ordenadas por `created_at` descendente:

```json
[
  {
    "id": 1,
    "user_id": 7,
    "job_title": "Desarrollador Frontend",
    "company": "Tech Corp",
    "status": "pending",
    "created_at": "2026-01-15T10:30:00"
  }
]
```

```http
POST /api/v1/applications
Content-Type: application/json

{ "job_title": "Desarrollador Frontend", "company": "Tech Corp" }
```

El estado inicial siempre es `pending`. El `user_id` del body se ignora (no forma parte del schema).

```http
PATCH /api/v1/applications/1/status
Content-Type: application/json

{ "status": "accepted" }
```

Estados válidos: `pending`, `under-review`, `accepted`, `rejected`. Un estado fuera de esa lista devuelve `422`; una postulación inexistente o de otro usuario devuelve `404`. Sin token o con un token inválido/expirado, `401`.

```http
DELETE /api/v1/applications/1
```

Elimina la postulación y responde `204 No Content` sin body. Si no existe o pertenece a otro usuario, devuelve `404`; sin token o con un token inválido/expirado, `401`.

### Contrato de `/api/v1/cvs`

El flujo es asíncrono y con estado: el CV se guarda en S3, se procesa en background y el cliente consulta su estado hasta que esté listo para optimizar.

#### `POST /api/v1/cvs`

Multipart con un único archivo `cv_file`:

| Campo | Tipo | Extensiones |
| ----- | ---- | ----------- |
| `cv_file` | archivo | `.pdf`, `.docx` |

El archivo se limita a 10 MB. La respuesta es `202 Accepted`:

```json
{
  "id": "2f4c9d8e-7a5b-4c1d-9e0f-123456789abc",
  "filename": "cv.pdf",
  "content_type": "application/pdf",
  "size_bytes": 102400,
  "sha256": "…",
  "status": "UPLOADED",
  "action_required": "WAIT_FOR_PARSING",
  "created_at": "2026-01-15T10:30:00Z",
  "updated_at": "2026-01-15T10:30:00Z"
}
```

El parseo/estructuración se ejecuta en una tarea de background de FastAPI (in-process, no durable). Un formato no permitido, archivo vacío, texto extraído vacío o exceder el tamaño devuelven `400`; si falta `cv_file`, `422`.

#### `GET /api/v1/cvs/{cv_id}`

Devuelve el estado actual del CV. Es el endpoint de polling:

```json
{
  "id": "2f4c9d8e-7a5b-4c1d-9e0f-123456789abc",
  "filename": "cv.pdf",
  "content_type": "application/pdf",
  "size_bytes": 102400,
  "sha256": "…",
  "status": "PARSED",
  "error_code": null,
  "error_message": null,
  "action_required": null,
  "created_at": "2026-01-15T10:30:00Z",
  "updated_at": "2026-01-15T10:31:00Z"
}
```

| Estado | Significado | `action_required` |
| ------ | ----------- | ----------------- |
| `UPLOADED` | Guardado en S3, pendiente de procesar | `WAIT_FOR_PARSING` |
| `PARSING` | Parseo/estructuración en curso | `WAIT_FOR_PARSING` |
| `PARSED` | Listo para optimizar | `null` |
| `ERROR` | El procesamiento falló | `REUPLOAD_CV` |

Un CV en `ERROR` sigue devolviendo `200` con `error_code` y `error_message`. El objeto S3 se conserva; actualmente no existe endpoint de reintento. Un `cv_id` inexistente o de otro usuario devuelve `404`.

Para el polling se recomienda empezar con intervalos de 1 segundo, pasar a 2 y luego a 5 segundos, y detenerse cuando el estado sea `PARSED` o `ERROR`. La consulta de estado no carga el texto del CV ni el JSON estructurado desde PostgreSQL.

#### `GET /api/v1/cvs/{cv_id}/content`

Devuelve el texto original extraído cuando el CV está en `PARSED`:

```json
{
  "id": "2f4c9d8e-7a5b-4c1d-9e0f-123456789abc",
  "status": "PARSED",
  "raw_text": "Texto extraído del CV original...",
  "characters_extracted": 1234
}
```

Con `?include_structured=true` añade el JSON estructurado:

```http
GET /api/v1/cvs/2f4c9d8e-7a5b-4c1d-9e0f-123456789abc/content?include_structured=true
```

```json
{
  "id": "2f4c9d8e-7a5b-4c1d-9e0f-123456789abc",
  "status": "PARSED",
  "raw_text": "Texto extraído del CV original...",
  "characters_extracted": 1234,
  "structured_cv": {
    "personal_info": {},
    "technical_data": {}
  }
}
```

Si el CV está en `UPLOADED` o `PARSING`, devuelve `409` con `action_required: "WAIT_FOR_PARSING"`; si está en `ERROR`, `409` con `error_code` y `action_required: "REUPLOAD_CV"`; si no existe o pertenece a otro usuario, `404`.

#### `GET /api/v1/cvs`

Lista los CVs del usuario autenticado con el mismo esquema de estado. No incluye el texto del CV ni el JSON estructurado.

#### `POST /api/v1/cvs/{cv_id}/optimize`

Requiere que el CV esté en `PARSED`. El body es JSON:

```http
POST /api/v1/cvs/2f4c9d8e-7a5b-4c1d-9e0f-123456789abc/optimize
Content-Type: application/json

{ "job_description": "Buscamos Python developer con FastAPI y PostgreSQL." }
```

También se acepta el alias `job_description_text`. La respuesta incluye la cabecera personal inmutable, el cuerpo técnico optimizado y las métricas de auditoría:

```json
{
  "optimized_content": "Ana Developer\nBackend Developer\n…\n\n<contenido optimizado>",
  "optimized_body": "<contenido técnico optimizado>",
  "original_variance_score": 0.72,
  "optimized_variance_score": 0.12,
  "writer_attempts": 2,
  "is_within_threshold": true,
  "original_ic": 61.0,
  "optimized_ic": 89.5,
  "original_per_dimension": {"technical_skills": 0.3},
  "optimized_per_dimension": {"technical_skills": 0.9},
  "gap_report": "",
  "personal_info": {
    "full_name": "Ana Developer",
    "headline": "Backend Developer",
    "email": "ana@example.com",
    "phone": "",
    "location": {"city": "Lima", "country": "Peru"},
    "links": {"linkedin": "", "github": "github.com/ana", "portfolio": ""}
  }
}
```

El optimizador solo recibe los datos técnicos (`summary`, skills, experiencia, proyectos, educación, certificaciones, idiomas); la información personal se reinserta después sin pasar por el LLM. Si el CV no está listo devuelve `409` con `action_required: "WAIT_FOR_PARSING"`; si falló, `409` con `error_code` y `action_required: "REUPLOAD_CV"`; si no existe o es de otro usuario, `404`. Un `job_description` vacío devuelve `422`.

> **Nota:** el pipeline llama a un LLM real compatible OpenAI (SDK `openai`). Requiere `LLM_API_KEY` en `.env`; si no está configurada, la app no arranca. Para desarrollo sin clave, apunta `LLM_BASE_URL` a un servidor local como Ollama o LM Studio.

## Arquitectura

El flujo completo del sistema —adaptadores inbound → puertos → dominio → puertos out → adaptadores out— está documentado en [`arquitectura-tecnica-mermaid.md`](arquitectura-tecnica-mermaid.md).

Las reglas que lo gobiernan están en [`AGENTS.MD`](AGENTS.MD).

## Estructura

```text
src/
├── main.py                     # App de FastAPI y routers
├── domain/                     # Entidades puras y reglas de auditoría (sin dependencias externas)
├── application/
│   ├── ports/
│   │   ├── inbound/            # Interfaces de casos de uso
│   │   └── out/                # Interfaces abstractas (ABC) de parsers, orquestador, LLM, scorer y exporter
│   └── services/               # Implementación de los casos de uso
└── infrastructure/
    └── adapters/
        ├── inbound/
        │   └── api/                # Controladores FastAPI, routers y DTOs
        └── out/                   # Implementaciones de los puertos de salida (SDK openai, LangGraph, parsers, scorer)
```

`ports/out/` incluye `DocumentExporterPort` (y `VectorStorePort`), pero aún **no tienen adaptador** en `adapters/out/` ni cableado en `composition.py`: son parte de la arquitectura objetivo.

`ports/inbound/` no se llama `ports/in/` porque `in` es una palabra reservada en Python y no se puede importar de forma estática.

## Tests

Cada archivo en `src/` tiene su espejo en `tests/`. Las pruebas de adaptadores inbound usan `httpx.AsyncClient` con `ASGITransport` sobre la app de FastAPI.

```bash
uv run pytest
```

### TEST COVERAGE
Reporte en terminal
```
uv run pytest --cov=src --cov-report=term-missing
```

Reporte en Html interactivo
```
uv run pytest --cov=src --cov-report=html
```
## Pre-commit

Hooks locales que se ejecutan en cada `git commit`, limitados a linting y pruebas relacionadas con los archivos staged:

- `ruff check`: linting de los archivos staged (config en `pyproject.toml`).
- `related-tests`: `pytest` sobre los tests afectados (tests staged directamente y el espejo de cada `src/` modificado; si no hay espejo exacto, busca los tests que referencian el módulo). Si no hay tests relevantes, el hook no hace nada.

La suite completa y los chequeos de tipos quedan en la CI (GitHub Actions).

```bash
uv run pre-commit install          # instalar los hooks en el repositorio
uv run pre-commit run --all-files  # primera vez: validar todo el proyecto
```

## Convenciones

- Tipado estricto en todas las anotaciones.
- Todo el I/O es asíncrono (`async` / `await`).
- Los puertos no dependen de frameworks de terceros.
