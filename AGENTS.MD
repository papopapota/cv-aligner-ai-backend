# CV Optimizer System - Reglas de Arquitectura

## Stack
- Python 3.12+ con uv
- Framework: FastAPI + Pydantic v2
- Orquestación: LangGraph
- LLM: SDK oficial `openai` (compatible con OpenAI, Ollama, LM Studio, etc.)
- HTTP Client: HTTPX (AsyncClient) para parsers/testeo

## Diagrama de Arquitectura
- El diagrama de la arquitectura está en [`arquitectura-tecnica-mermaid.md`](arquitectura-tecnica-mermaid.md) y representa la **arquitectura objetivo (hoja de ruta)**, no necesariamente lo implementado. **Léelo antes de crear o modificar cualquier puerto, caso de uso o adapter**, y mantén los nombres alineados con el (ej. `OptimizeCVUseCase`, `CVParserPort`, `WorkflowOrchestratorPort`, `LLMAgentPort`, `MatchScorerPort`, `VectorStorePort`, `DocumentExporterPort`). Los elementos del diagrama que aún no tienen código no están implementados (por ejemplo, `VectorStorePort` y el RAG, o `DocumentExporterPort`: el puerto existe y `OptimizeCVService` lo acepta opcionalmente, pero no hay adaptador ni cableado en `composition.py`); el módulo de scoring `IC` (sección "Hoja de Ruta: Scoring Cuantitativo") ya está implementado.

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

## Hoja de Ruta: Scoring Cuantitativo IC

> Reglas de decisión para el módulo de matching matemático (Li et al., 2025) descrito en el diagrama (`MatchScorerPort`, `CompatibilityScore`, métricas `Ncos`/`Ntfidf`/`Neuc` e `IC`). La fórmula, la separación de responsabilidades y los tests están implementados; lo pendiente es la calibración de hiperparámetros (D).

### Estado actual (implementado)
- `MatchScorerPort` + `CompatibilityScore` (dominio) + `EmbeddingMatchScorerAdapter` (sanitización previa, embeddings del mismo proveedor que el LLM y delegación de métricas al dominio) implementados, testeados y **cableados en `composition.py`**.
- `src/domain/compatibility_metrics.py`: `normalized_cosine`, `normalized_euclidean` y `compatibility_index` puros, con clamping y manejo de vectores nulos.
- `src/domain/tfidf.py`: tokenizador determinista y `normalized_tfidf_relevance` con corpus `[CV, oferta]`, IDF suavizado y protección ante oferta vacía o denominador cero.
- `src/infrastructure/adapters/out/openai_embedding_client.py`: cliente dedicado a `embeddings.create`, con orden por índice y excepción propia `EmbeddingClientError`.
- `SemanticProfile` (dominio) + `parse_semantic_profile` (orquestador) + prompt `EXTRACTOR` en JSON estricto (`summary` + 5 subdimensiones, con instrucción de ignorar atributos demográficos) implementados y testeados.
- El orquestador (`LangGraphOrchestratorAdapter`) acepta `match_scorer` e `ic_target` opcionales: si se inyectan, **extrae `candidate_profile`/`job_profile`** (llamada LLM extra sobre la oferta), calcula el **baseline de IC** y el **IC del CV optimizado** (re-extrayendo sus dimensiones en cada auditoría), alimenta al ANALYZER con un **scorecard por dimensión**, aplica **routing dual** (`variance_score <= AUDIT_VARIANCE_THRESHOLD` y `ic >= ic_target`) y **trackea la mejor versión** (`best_text`/`best_ic`/`best_variance`/`best_per_dimension`). Sin scorer, el comportamiento es el clásico (solo varianza).
- El scorer puntúa todas las dimensiones no vacías solicitadas por la oferta. Si el CV no aporta texto para una de ellas (por ejemplo `education` o `certifications`), la dimensión se registra con `0.0`; el desglose sigue siendo diagnóstico y no altera el IC global.
- **Latencia**: la extracción del CV y de la oferta arranca en paralelo; el auditor original se solapa con el writer; el auditor optimizado y el extractor de su perfil usan `asyncio.gather`; y `EmbeddingMatchScorerAdapter` agrupa los embeddings globales y por dimensión en una sola petición. Los logs registran duración por fase y tamaño del batch de embeddings.
- **Best-effort**: `OptimizeCVService` no lanza `AuditFailedError`; al agotar `MAX_WRITER_ATTEMPTS (3)` devuelve la mejor versión obtenida (`OptimizedCV.optimized_ic`, `optimized_per_dimension` y `gap_report`), junto con la evaluación previa en `original_ic`/`original_per_dimension`.
- Gates activos: `variance_score` (LLM Auditor, `<= AUDIT_VARIANCE_THRESHOLD`, default `0.45`, configurable) **y** `IC` del CV optimizado (`>= MATCH_TARGET_IC`, default `85.0`), ambos evaluados en el routing del orquestador.

### A. Ciclo de vida del IC y responsabilidades por agente
- **Agente Extractor**: genera tanto el texto crudo estructurado como las subdimensiones semánticas (`technical_skills`, `experience`, `education`, `certifications`, `languages`) en JSON estricto (`summary` + subdimensiones, schema en `SemanticProfile`/`parse_semantic_profile`).
- **Agente Analizador (baseline match)**: invoca `MatchScorerPort` **antes** de redactar para obtener el `IC` inicial y el desglose de similitud por dimensión. Define la estrategia para el redactor: priorizar las dimensiones con menor similitud.
- **Agente Auditor (gatekeeper & feedback loop)**: verifica la varianza factual y ejecuta nuevamente el cálculo de `IC` sobre el CV optimizado vía `MatchScorerPort`. Devuelve `{"variance_score": …, "reason": …}`; el orquestador conserva `audit_reason` y lo **reinyecta en el prompt del writer** junto al CV anterior.
- **Condición de parada**: `IC_optimizado >= MATCH_TARGET_IC` (mayor es mejor) **y** `variance_score <= AUDIT_VARIANCE_THRESHOLD` (menor es mejor).

### B. Política contra loops infinitos (retry strategy)
- Límite estricto de iteraciones: `MAX_WRITER_ATTEMPTS = 3`.
- Si tras 3 intentos no se superan los umbrales, se aprueba la mejor versión posible (`best_text`, la de mayor `IC`, con `best_variance` y `best_per_dimension`) y se adjunta el **gap report** (`gap_analysis`).

### C. Inmutabilidad y mitigación de sesgos (Li et al., 2025)
- El prompt del Extractor/Auditor indica explícitamente que cualquier atributo demográfico no laboral (género, edad, nacionalidad, estado civil, fotografía) debe ser filtrado/ofuscado.
- La sanitización se aplica **antes** de generar los embeddings y de calcular `Ncos`/`Ntfidf`/`Neuc`, garantizando un cribado no sesgado (`sanitize_report_text` en `EmbeddingMatchScorerAdapter`).

### D. Calibración de hiperparámetros (defaults versionables)
- Fórmula: `IC = 100 · (w1·Ncos + w2·Ntfidf + w3·Neuc)`.
- Defaults: `w1 = 0.50` (similitud semántica), `w2 = 0.30` (relevancia léxica TF-IDF), `w3 = 0.20` (proximidad geométrica normalizada con `dmax = 2`).
- `Ncos`, `Ntfidf` y `Neuc` se acotan a `[0,1]`; `IC` se acota a `[0,100]`.
- Versionables vía `MATCH_WEIGHT_*` y `MATCH_TARGET_IC`; **pendiente la calibración con datos reales**.
