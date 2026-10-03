```mermaid
flowchart TB
    %% ==========================================
    %% CAPA DE ADAPTADORES INBOUND
    %% ==========================================
    subgraph InboundAdapters["ADAPTADORES INBOUND<br/>src/infrastructure/adapters/inbound"]
        direction TB
        API["FastAPI / REST Controller<br/>(Upload CV & Job Spec)"]
    end

    %% ==========================================
    %% HEXÁGONO CENTRAL: DOMINIO Y APLICACIÓN
    %% ==========================================
    subgraph Hexagon["NÚCLEO DE LA APLICACIÓN (EL HEXÁGONO)"]
        direction TB
        
        subgraph PortsIn["PUERTOS INBOUND<br/>src/application/ports/inbound"]
            P_In["OptimizeCVUseCase<br/>(Interfaz)"]
        end

        subgraph Application["LÓGICA DE APLICACIÓN"]
            Service["OptimizeCVService<br/>(Coordina el flujo de negocio)"]
        end

        subgraph Domain["NÚCLEO DE DOMINIO"]
            State["SharedState / Context<br/>(Estado Global)"]
            AuditRules["Reglas de Auditoría<br/>(Filtro de Varianza)"]
            Entities["Entidades:<br/>CandidateCV, JobDescription, OptimizedCV"]
        end

        subgraph PortsOut["PUERTOS OUT<br/>src/application/ports/out"]
            P_Parser["CVParserPort"]
            P_Graph["WorkflowOrchestratorPort"]
            P_LLM["LLMAgentPort"]
            P_Vector["VectorStorePort (RAG)"]
            P_Export["DocumentExporterPort"]
        end

        P_In --> Service
        Service --> Domain
        Service --> PortsOut
    end

    %% ==========================================
    %% CAPA DE ADAPTADORES OUT
    %% ==========================================
    subgraph OutboundAdapters["ADAPTADORES OUT<br/>src/infrastructure/adapters/out"]
        direction TB

        subgraph AdapterParsers["Adaptador Parsers"]
            PDFParser["PyPDF / Docx Parser"]
        end

        subgraph AdapterGraph["Adaptador LangGraph (Control Lógico)"]
            direction TB
            LG_Engine["LangGraph StateGraph Engine"]
            NodeExt["Nodo: Agente Extractor"]
            NodeAna["Nodo: Agente Analizador"]
            NodeWri["Nodo: Agente Redactor"]
            NodeAud["Nodo: Agente Auditor"]
            EdgeCond{"Filtro de Varianza<br/>(Retry / Approved)"}

            LG_Engine --> NodeExt --> NodeAna --> NodeWri --> NodeAud --> EdgeCond
            EdgeCond -- "Retry" --> NodeWri
        end

        subgraph AdapterLLM["Adaptador Modelos"]
            LLM_API["OpenAI / Anthropic / Local LLM"]
        end

        subgraph AdapterRAG["Adaptador Base de Datos Vectorial"]
            VDB["Chroma / Pinecone / Qdrant<br/>(Embeddings & Retriever)"]
        end

        subgraph AdapterExport["Adaptador Exportador"]
            DocGen["DOCX / Weasyprint PDF Engine"]
        end
    end

    %% Conexiones Primarias
    API --> P_In

    %% Conexiones Secundarias (Puertos a Adaptadores)
    P_Parser -. Implementado por .-> PDFParser
    P_Graph -. Implementado por .-> LG_Engine
    P_LLM -. Implementado por .-> LLM_API
    P_Vector -. Implementado por .-> VDB
    P_Export -. Implementado por .-> DocGen

    %% Interacciones de los Nodos de Infraestructura con Servicios Externos
    NodeExt -. Usa .-> LLM_API
    NodeAna -. Usa .-> LLM_API
    NodeWri -. Contexto RAG .-> VDB
    NodeWri -. Genera borrador .-> LLM_API
    NodeAud -. Evalúa .-> LLM_API
    EdgeCond -- "Approved" --> DocGen
```