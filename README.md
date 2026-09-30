# cv-aligner-ai-backend

Backend del optimizador de CV multi-agente, construido con FastAPI y arquitectura hexagonal.

## Stack

- Python 3.12+
- Gestor de dependencias y entornos: [uv](https://docs.astral.sh/uv/)
- Frameworks: FastAPI, Pydantic v2, LangGraph
- Testing: pytest, pytest-asyncio

## Puesta en marcha

```bash
uv sync
uv run uvicorn src.main:app --reload
```

La app queda disponible en `http://127.0.0.1:8000`, con la documentación interactiva en `/docs`.

## Endpoints

| Método | Ruta       | Descripción                 | Respuesta             |
| ------ | ---------- | --------------------------- | --------------------- |
| GET    | `/health`  | Verificación de estado      | `{"status": "ok"}`    |

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
