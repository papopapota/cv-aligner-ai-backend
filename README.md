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

El adaptador (`OpenAILLMAgentAdapter`) envía mensajes `system` por rol (extractor/analyzer/writer/auditor) con temperatura distinta por rol. El auditor responde JSON `{"variance_score": …}` y, si no, el grafo intenta parsear el primer número del texto como fallback.

## Endpoints

| Método | Ruta            | Descripción                                | Respuesta                  |
| ------ | --------------- | ------------------------------------------ | -------------------------- |
| GET    | `/health`       | Verificación de estado                     | `{"status": "ok"}`         |
| POST   | `/cv/upload`    | Carga de CV y job spec, ambos en multipart | CV y spec parseados        |
| POST   | `/cv/optimize`  | Pipeline multi-agente sobre el CV y la spec | CV optimizado y auditado   |

Ambos endpoints reciben los mismos dos campos multipart (`cv_file` y `job_description_file`), porque el flujo es sin estado: `/cv/optimize` vuelve a parsear los archivos en lugar de guardarlos.

### Contrato de `POST /cv/optimize`

Ejecuta el grafo de LangGraph (extractor → analyzer → writer → auditor). Si la varianza del auditor supera el umbral, el writer se reintenta hasta 3 veces.

| Campo         | Extensiones     |
| ------------- | --------------- |
| `cv_file`     | `.pdf`, `.docx` |
| `job_description_file` | `.txt`  |

Respuesta: `optimized_content`, `variance_score`, `writer_attempts` e `is_within_threshold`.

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

## Convenciones

- Tipado estricto en todas las anotaciones.
- Todo el I/O es asíncrono (`async` / `await`).
- Los puertos no dependen de frameworks de terceros.
