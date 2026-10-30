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

El adaptador (`OpenAILLMAgentAdapter`) envía mensajes `system` por rol (extractor/analyzer/writer/auditor) con temperatura distinta por rol. El auditor evalúa tanto el CV original como el optimizado y responde JSON `{"variance_score": …}`; si no, el grafo intenta parsear el primer número del texto como fallback. El primer score se calcula una sola vez en paralelo con las fases de extracción y análisis, y el segundo se recalcula en cada intento del auditor.

En cada reintento el writer recibe el CV optimizado anterior y el motivo (`reason`) del auditor para corregir las carencias señaladas. El adaptador registra por log el `variance_score` y el `reason` de cada intento (nivel INFO/WARNING) para diagnosticar por qué no converge.

## Base de datos y migraciones

La persistencia usa SQLAlchemy 2.0 async con `asyncpg`. La configuración se toma de las variables `DB_*` del `.env` (`DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`).

### Levantar PostgreSQL con Docker Compose

El `compose.yaml` levanta únicamente el servicio de base de datos. Usa las variables `DB_*` del `.env` y persiste los datos en el volumen `postgres_data`:

```bash
docker compose up -d db
docker compose ps
```

Espera a que el servicio aparezca como `healthy` antes de aplicar las migraciones. Para detenerlo:

```bash
docker compose down
```

`docker compose down -v` también elimina el volumen y, por tanto, los datos de la base de datos.

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

## Endpoints

| Método | Ruta            | Descripción                                | Respuesta                  |
| ------ | --------------- | ------------------------------------------ | -------------------------- |
| GET    | `/health`       | Verificación de estado                     | `{"status": "ok"}`         |
| POST   | `/auth/register`| Registro de usuario (hash bcrypt)          | Usuario creado             |
| POST   | `/auth/login`   | Login con email y contraseña               | Tokens JWT                 |
| POST   | `/auth/refresh` | Renueva tokens con un refresh token        | Tokens JWT                 |
| POST   | `/cv/upload`    | Carga de CV y job spec, ambos en multipart | CV y spec parseados        |
| POST   | `/cv/optimize`  | Pipeline multi-agente sobre el CV y la spec | CV optimizado y auditado   |

Ambos endpoints reciben los mismos dos campos multipart (`cv_file` y `job_description_file`), porque el flujo es sin estado: `/cv/optimize` vuelve a parsear los archivos en lugar de guardarlos.

### Contrato de `POST /cv/optimize`

Ejecuta el grafo de LangGraph: la cadena `extractor → analyzer` corre en paralelo con el auditor del CV original, y el writer espera a ambas ramas para continuar. El score del CV original se calcula una sola vez y solo se informa; si la varianza del CV optimizado supera el umbral, el writer se reintenta hasta 3 intentos totales.

| Campo         | Extensiones     |
| ------------- | --------------- |
| `cv_file`     | `.pdf`, `.docx` |
| `job_description_file` | `.txt`  |

Respuesta: `optimized_content`, `original_variance_score`, `optimized_variance_score`, `writer_attempts` e `is_within_threshold`. `is_within_threshold` se calcula únicamente con `optimized_variance_score`.

Si el CV no converge tras los reintentos, devuelve `422` con el detalle del fallo de auditoría. `400` para formatos o tamaños inválidos, `422` si falta un campo.

> **Nota:** el pipeline llama a un LLM real compatible OpenAI (SDK `openai`). Requiere `LLM_API_KEY` en `.env`; si no está configurada, la app no arranca. Para desarrollo sin clave, apunta `LLM_BASE_URL` a un servidor local como Ollama o LM Studio.

### Contrato de `POST /cv/upload`

Envía dos campos multipart. La job description es **un archivo `.txt`**, no texto pegado:

| Campo                 | Tipo       | Extensiones        |
| --------------------- | ---------- | ------------------ |
| `cv_file`             | archivo    | `.pdf`, `.docx`    |
| `job_description_file`| archivo    | `.txt`             |

Ambos archivos están limitados a 10 MB. La respuesta incluye los metadatos y el texto extraído de cada uno (`extracted_text` / `jd_extracted_text`, con sus respectivos `sha256` y `characters_extracted`).

Un formato no permitido, un archivo vacío, texto extraído vacío o superar el límite devuelven `400`. Si falta algún campo, `422`.

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
│   │   └── out/                # Interfaces abstractas (ABC) de parsers, orquestador, LLM y exporters
│   └── services/               # Implementación de los casos de uso
└── infrastructure/
    └── adapters/
        ├── inbound/
        │   └── api/                # Controladores FastAPI, routers y DTOs
        └── out/                   # Implementaciones de los puertos de salida (SDK openai, LangGraph, parsers)
```

`ports/inbound/` no se llama `ports/in/` porque `in` es una palabra reservada en Python y no se puede importar de forma estática.

## Tests

Cada archivo en `src/` tiene su espejo en `tests/`. Las pruebas de adaptadores inbound usan `httpx.AsyncClient` con `ASGITransport` sobre la app de FastAPI.

```bash
uv run pytest
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
