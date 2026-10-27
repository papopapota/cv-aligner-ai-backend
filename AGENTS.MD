# CV Optimizer System - Reglas de Arquitectura

## Stack
- Python 3.12+ con uv
- Framework: FastAPI + Pydantic v2
- Orquestación: LangGraph
- LLM: SDK oficial `openai` (compatible con OpenAI, Ollama, LM Studio, etc.)
- HTTP Client: HTTPX (AsyncClient) para parsers/testeo

## Diagrama de Arquitectura
- El diagrama de la arquitectura está en [`arquitectura-tecnica-mermaid.md`](arquitectura-tecnica-mermaid.md) y representa la **arquitectura objetivo (hoja de ruta)**, no necesariamente lo implementado. **Léelo antes de crear o modificar cualquier puerto, caso de uso o adapter**, y mantén los nombres alineados con el (ej. `OptimizeCVUseCase`, `CVParserPort`, `WorkflowOrchestratorPort`, `LLMAgentPort`, `MatchScorerPort`, `VectorStorePort`, `DocumentExporterPort`). Los elementos del diagrama que aún no tienen código no están implementados (por ejemplo, `VectorStorePort` y el RAG, o `DocumentExporterPort`: el puerto existe y `OptimizeCVService` lo acepta opcionalmente, pero no hay adaptador ni cableado en `composition.py`); el módulo de scoring `R_total` (sección "Hoja de Ruta: Scoring Cuantitativo") ya está implementado.

## Arquitectura Hexagonal
1. **Domain (`src/domain/`)**: Entidades puras y reglas de auditoría. Cero dependencias externas.
2. **Application / Ports (`src/application/`)**:
   - `ports/inbound/`: Interfaces de casos de uso (ej. `OptimizeCVUseCase`). No se puede usar `ports/in/` porque `in` es una palabra reservada en Python.
   - `ports/out/`: Interfaces abstractas (`ABC`) para parsers, orquestador, LLM y exporters.
   - `services/`: Implementación de los casos de uso.
3. **Infrastructure (`src/infrastructure/`)**:
   - `adapters/inbound/api/`: Controladores FastAPI, routers y DTOs.
   - `adapters/out/`: Implementaciones de los puertos de salida (LLM con SDK `openai`, LangGraph, parsers).

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
  - En pruebas de Adaptadores Inbound (FastAPI): Usar `httpx.AsyncClient` con `ASGITransport` sobre la app de FastAPI para pruebas de integración/controlador.

## Hoja de Ruta: Scoring Cuantitativo R_total

> Reglas de decisión para el módulo de matching matemático (Li et al., 2025) descrito en el diagrama (`MatchScorerPort`, `CompatibilityScore`, ec. 1-5). Las secciones A-D están implementadas (ver "Estado actual"); lo pendiente es la calibración de hiperparámetros (D).

### Estado actual (implementado)
- `MatchScorerPort` + `CompatibilityScore` (dominio) + `EmbeddingMatchScorerAdapter` (embeddings del mismo proveedor que el LLM, `numpy`, sanitización previa) implementados, testeados y **cableados en `composition.py`** (reutiliza el mismo cliente OpenAI que el LLM; `r_total_target = MATCH_TARGET_R_TOTAL`).
- `SemanticProfile` (dominio) + `parse_semantic_profile` (orquestador) + prompt `EXTRACTOR` en JSON estricto (`summary` + 5 subdimensiones, con instrucción de ignorar atributos demográficos) implementados y testeados.
- El orquestador (`LangGraphOrchestratorAdapter`) acepta `match_scorer` y `r_total_target` opcionales: si se inyectan, **extrae `candidate_profile`/`job_profile`** (llamada LLM extra sobre la oferta), calcula **baseline `R_total`** y el **`R_total` del CV optimizado** (re-extrayendo sus dimensiones en cada auditoría), alimenta al ANALYZER con un **scorecard por dimensión**, aplica **routing dual** (`variance_score <= AUDIT_VARIANCE_THRESHOLD` (default `0.45`, configurable) y `r_total >= target`) y **trackea la mejor versión** (`best_text`/`best_r_total`/`best_variance`/`best_per_dimension`). Sin scorer, el comportamiento es el clásico (solo varianza).
- **Best-effort**: `OptimizeCVService` ya no lanza `AuditFailedError`; al agotar `MAX_WRITER_ATTEMPTS (3)` devuelve la mejor versión obtenida (`OptimizedCV.r_total`, `per_dimension` y `gap_report`). Se eliminaron `AuditFailedError`, su exception handler y el registro en `main.py`.
- Gates activos: `variance_score` (LLM Auditor, `<= AUDIT_VARIANCE_THRESHOLD`, default `0.45`, configurable vía entorno y propagado a `OptimizedCV`) **y** `R_total` del CV optimizado (`>= MATCH_TARGET_R_TOTAL 0.85`), ambos evaluados en el routing del orquestador.

### A. Ciclo de vida de R_total y responsabilidades por agente
- **Agente Extractor**: genera tanto el texto crudo estructurado como las subdimensiones semánticas requeridas por la Ecuación (3): `technical_skills`, `experience`, `education`, `certifications`, `languages`, en un formato JSON estricto (`summary` + subdimensiones, schema ya definido y testeado en `SemanticProfile`/`parse_semantic_profile`).
- **Agente Analizador (baseline match)**: invoca `MatchScorerPort` **antes** de redactar para obtener el `R_total` inicial y el desglose de similitud por dimensión. Define la estrategia para el Agente Redactor: priorizar las dimensiones con menor `S_cosine` o brechas detectadas en `A_contextual`.
- **Agente Auditor (gatekeeper & feedback loop)**: no solo verifica que no haya alucinaciones (filtro de varianza factual), sino que ejecuta nuevamente el cálculo de `R_total` sobre el CV optimizado vía `MatchScorerPort`. Además devuelve un `reason` (`{"variance_score": …, "reason": …}`) que el orquestador conserva como `audit_reason` y **reinyecta en el prompt del writer en cada reintento**, junto al CV anterior, para corregir de forma dirigida las carencias señaladas.
- **Condición de parada (convivencia de ambos gates, distinta dirección)**: `R_total_optimizado >= target_score` (default `0.85`, mayor es mejor) **y** `variance_score <= AUDIT_VARIANCE_THRESHOLD` (default `0.45`, configurable, menor es mejor).

### B. Política contra loops infinitos (retry strategy)
- Límite estricto de iteraciones: `max_retries = 3` (coincide con `MAX_WRITER_ATTEMPTS`).
- Si tras 3 reintentos el CV no supera el umbral de `R_total`, el Agente Auditor aprueba la mejor versión posible (`best_text`, la de mayor `R_total` entre los intentos, con su `best_variance` y `best_per_dimension`) y adjunta un **gap report** (el `gap_analysis`) explicando qué exige la oferta.
- Implementado: el flujo ya no lanza `AuditFailedError`; `OptimizeCVService` devuelve la mejor versión + gap report.

### C. Inmutabilidad y mitigación de sesgos (lineamiento de Li et al., 2025)
- Establecer explícitamente en el prompt del Extractor/Auditor que cualquier atributo demográfico no laboral (género, edad, nacionalidad, estado civil, fotografía) debe ser filtrado/ofuscado.
- La sanitización se aplica **antes** de generar los embeddings y el cálculo de `A_contextual`, para garantizar un cribado no sesgado (`sanitize_report_text` en `EmbeddingMatchScorerAdapter`).

### D. Calibración de hiperparámetros (defaults versionables)
- Fórmula: `R_total = λ1·S_cosine + λ2·D_euclidean + λ3·A_contextual`.
- Defaults: `λ1 = 0.45` (alineamiento dimensional / `S_cosine`), `λ2 = 0.25` (proximidad global / `D_euclidean`), `λ3 = 0.30` (alineamiento contextual fina / `A_contextual`).
- Balance: mayor peso al alineamiento por dimensión (`λ1`), la proximidad global como soporte (`λ2`) y el ajuste fino contextual como matiz (`λ3`). Versionables vía `MATCH_*`; **pendiente la calibración con datos reales**.