# CV Optimizer System - Reglas de Arquitectura

## Stack
- Python 3.12+ con uv
- Framework: FastAPI + Pydantic v2
- Orquestación: LangGraph
- HTTP Client: HTTPX (AsyncClient)

## Arquitectura Hexagonal
1. **Domain (`src/domain/`)**: Entidades puras y reglas de auditoría. Cero dependencias externas.
2. **Application / Ports (`src/application/`)**:
   - `ports/inbound/`: Interfaces de casos de uso (ej. `OptimizeCVUseCase`). No se puede usar `ports/in/` porque `in` es una palabra reservada en Python.
   - `ports/out/`: Interfaces abstractas (`ABC`) para parsers, orquestador, LLM y exporters.
   - `services/`: Implementación de los casos de uso.
3. **Infrastructure (`src/infrastructure/`)**:
   - `adapters/inbound/api/`: Controladores FastAPI, routers y DTOs.
   - `adapters/out/`: Implementaciones de los puertos de salida (HTTPX para LLM, LangGraph, parsers).

## Regla de Dependencias
- `domain/` y `application/` no importan nada desde `infrastructure/`.
- La inversión de dependencias se logra porque `infrastructure/` importa los puertos definidos en `application/ports/`.

## Reglas de Codificación
- Usar siempre tipado estricto con anotaciones de tipo.
- Todo I/O debe ser asíncrono (`async` / `await`).
- Mantener los puertos independientes de frameworks de terceros.

## Reglas de Testing (Pruebas Unitarias)
- Framework: `pytest` y `pytest-asyncio`.
- Ubicación: Cada archivo en `src/` debe tener su espejo en `tests/` (ej. `src/domain/entities.py` -> `tests/domain/test_entities.py`).
- Convención: Usar el patrón AAA (Arrange, Act, Assert).
- Aislamiento Hexagonal:
  - En pruebas de Dominio: No usar mocks, probar lógica pura.
  - En pruebas de Aplicación / Servicios: Mockear los puertos de salida (`ports/out/`) usando `unittest.mock.AsyncMock`.
  - En pruebas de Adaptadores Primarios (FastAPI): Usar `httpx.AsyncClient` con `ASGITransport` sobre la app de FastAPI para pruebas de integración/controlador.