# cv-aligner-ai-backend

Backend del optimizador de CV multi-agente, construido con FastAPI y arquitectura hexagonal.

## Stack

- Python 3.12+
- Gestor de dependencias y entornos: [uv](https://docs.astral.sh/uv/)
- Frameworks: FastAPI, Pydantic v2, LangGraph
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

> **Aviso:** el pipeline corre hoy contra un `StubLLMAgentAdapter`, no contra un modelo real. El texto devuelto es fijo y no es una optimización legítima. Sustituir el adaptador en `src/composition.py` antes de usar la salida en producción.

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
        └── out/                   # Implementaciones de los puertos de salida (HTTPX, LangGraph, parsers)
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
