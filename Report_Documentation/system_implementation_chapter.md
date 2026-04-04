# System Implementation

## 1. Introduction and Architectural Paradigm

The Virtual Research Assistant (VRA) is engineered as an autonomous, multi-agent artificial intelligence system designed to accelerate the scientific research lifecycle. The system transcends traditional retrieval-augmented generation (RAG) by operating as a state-driven machine capable of proactive literature acquisition, knowledge synthesis, graph-based gap analysis, and hypothesis generation.

The overarching architecture is highly modular and divided into distinct logical layers:

- **API Layer (`api/`)**: Built on **FastAPI**, it serves as the synchronous boundary exposing RESTful endpoints to the frontend application while gracefully handling fast I/O and concurrent request routing.
- **Orchestration Layer (`workflow.py`)**: A centralized state machine managing the context and progression of the `VRAState` object. It enforces a strict, event-driven progression through complex cognitive phases.
- **Agentic Layer (`agents/`)**: Specialized encapsulation of Large Language Model (LLM) prompts, chaining logic, and tool usage governing distinct operational phases.
- **Service Layer (`services/`)**: The system's "backend brain," housing complex algorithms, database transactions, network requests, and the mathematical implementation for graph routing and analysis.
- **Data Persistence Layer**:
    - **PostgreSQL**: Manages relational entities such as User sessions, Research Tasks metadata, and canonical paper records.
    - **ChromaDB**: The vector storage engine used for encoding paper abstracts and full-texts via embeddings, enabling high-dimensional semantic search and retrieval.
- **Frontend Interactivity**: Engineered using **Next.js**, it presents a responsive, dark-themed "Research Dashboard" that visualizes dynamic knowledge graphs and tracks real-time generation metrics.

## 2. Multi-Agent Orchestration

Rather than relying on a single monolithic LLM prompt, VRA distributes computational reasoning across specialized agents. This separation of concerns strictly bounds the context window for each agent, drastically reducing hallucinations (a known issue that the Reporting Agent's context boundaries seek to minimize).

- **DataAcquisitionAgent & ArxivAgent**: Collaboratively orchestrate concurrent search queries across Semantic Scholar and arXiv, dynamically expanding initial user queries to ensure sufficient literature capture.
- **SemanticScholarAgent**: Provides dual-mode access to Semantic Scholar — keyword-based query search and direct lookup-by-paper-ID. The `get_by_ids()` method enables **citation snowballing**, recursively fetching references to expand the literature pool beyond the initial query horizon.
- **DataMergerAgent**: A dedicated post-acquisition deduplication agent. After all sources have reported, `DataMergerAgent.merge()` consolidates the full paper list into a unique, canonical corpus by resolving `canonical_id` conflicts and deep-merging metadata. It prefers the longest available abstract to maximize RAG context quality.
- **GraphBuilderAgent**: Translates unstructured textual data concepts into structured network matrices (Knowledge Graphs, Citation Graphs).
- **GapAnalysisAgent & HypothesisGenAgent**: Work sequentially. The Gap Analysis agent uses statistical topology to identify structural holes in the graph, which the Hypothesis Generation agent then translates into novel, testable future work.
- **PaperSummarizationAgent**: Responsible for dense information extraction on a per-paper basis.
- **ReviewerAgent & ReportingAgent**: In the final phases, these agents evaluate the generated hypotheses for novelty and synthesize all accumulated data (the `VRAState` memory) into a formatted, exportable scientific markdown report.

## 3. Workflow State Machine

The core execution engine is defined within `workflow.py`, utilizing an iterative polling structure designed to execute cognitive tasks until manual human interaction is required. The primary phases include:

1.  **`awaiting_research_review`**: Initial data gathering. Validates the incoming query and fetches the first batch of literature.
2.  **`awaiting_analysis`**: The system performs a "global read," reranking papers for relevance and initializing the concept extraction space.
3.  **`awaiting_paper_summaries`**: Spawns parallel processes to extract dense abstracts and, concurrently, uses the `detect_concept_trends` service to compute temporal metadata (e.g., categorizing concepts as "Emerging" vs "Saturated").
4.  **`awaiting_graphs` & `awaiting_graph_review`**: The system generates NetworkX node-link data structures. The workflow halts here to allow human researchers to approve, delete, or modify nodes before proceeding.
5.  **`awaiting_gap_analysis` & `awaiting_hypothesis`**: The topological scanning phase where the graph is mined for structural weaknesses, acting as seeds for new research questions.
6.  **`reviewing_hypotheses` & `awaiting_report`**: Final compilation, critique, and artifact generation.

## 4. Core Algorithmic Implementations

The sophistication of the VRA lies in the deterministic algorithms acting in concert with probabilistic LLMs.

### 4.1. Smart Deduplication and Canonical Resolution

To prevent redundant processing of the same paper retrieved from multiple sources (e.g., local PDF upload, arXiv, Semantic Scholar), the `research_service` implements a smart deduplication pipeline. It utilizes a prioritized canonical ID resolution system:

1.  **Semantic Scholar ID** (Highest confidence)
2.  **Digital Object Identifier (DOI)**
3.  **Normalized Title and Publication Year** (Fallback heuristic)
    When duplicates are found, metadata is intelligently merged, favoring the longest available abstract to maximize RAG context.

### 4.2. Adaptive Query Expansion

Recognizing that naive user queries often yield poor initial search results (the "Graph Scope Limited" problem), the system employs Adaptive Expansion. If the initial literature pool falls below a minimum threshold, an LLM dynamically generates 3-6 orthagonal sub-queries. The data acquisition layer then executes parallel, asynchronous requests across these expanded parameters, significantly broadening the recall.

### 4.3. Topological Gap Analysis

The system calculates scientific opportunity using network theory metrics applied to the Knowledge Graph.

- **Conceptual Gaps**: Identified via a weighted confidence metric: `Confidence = 0.5*(1 - NormalizedCover) + 0.3*(1 - ClusteringCoef) + 0.2`. Concepts with low representation (Coverage) and low peer connectivity (Clustering) are flagged as under-explored.
- **Structural Gaps**: Discovered by computing algorithms for weakly connected components. Clusters of papers that are densely connected internally but lack edges bridging them to other clusters represent "structural holes," which the system suggests as immediate opportunities for cross-disciplinary research.

## 5. LLM Architecture & Rate Limit Strategy

The VRA employs a **configurable, multi-provider LLM architecture** designed for both production reliability and research flexibility.

### 5.1 LLMFactory

`services/llm_factory.py` is a factory-pattern client manager. It maintains a cached instance pool keyed by `(provider, api_key, base_url, …)` to avoid unnecessary re-initialization. Supported providers:

| Provider Identifier | Cloud/Local | Default Model | Environment Key |
|:---|:---|:---|:---|
| `google` | Cloud | `gemini-2.5-pro` | `GOOGLE_API_KEY`, `GOOGLE_MODEL` |
| `openai` | Cloud | `gpt-4o-mini` | `OPENAI_API_KEY`, `OPENAI_MODEL` |
| `openrouter` | Cloud (free tier) | `google/gemini-2.5-pro-exp-03-25:free` | `OPENROUTER_API_KEY`, `OPENROUTER_MODEL` |
| `azure` | Cloud | `azure-gpt-4` | `AZURE_OPENAI_API_KEY`, `AZURE_OPENAI_ENDPOINT` |
| `local` | Local (Ollama) | `llama3` | `LOCAL_LLM_URL`, `LOCAL_MODEL` |

### 5.2 Hybrid Execution Strategy (SectionCompiler)

`services/reporting/section_compiler.py` implements a **Hybrid Execution Strategy** governed by the `CompilationPhase` enum:

- **`ABSTRACT` (Always Primary)**: The abstract synthesis always uses the primary provider regardless of hybrid mode — it requires the highest reasoning quality.
- **`REFINE` (Hybrid=On → Primary)**: Final polishing uses the primary provider for tone and precision.
- **`EXPAND` (Hybrid=On → Secondary)**: Bulk text generation uses the cost-efficient secondary provider.
- **`DRAFT` (Hybrid=On → Context-Dependent)**: Complex section types (INTRO, CONCLUSION, ANALYSIS) use Primary; structural sections (METHOD, IMPL) use Secondary.
- **Hybrid=Off**: All phases unconditionally use `PRIMARY_PROVIDER`.

A **Cost Guardrail** (`MAX_CLOUD_CALLS`, default 15) limits cloud API consumption per report. When exceeded, generation automatically falls back to the secondary provider.

### 5.3 LLMOrchestrator

`services/llm/orchestrator.py` adds a centralized, async-safe execution layer:

- **Global Serialization Lock**: An `asyncio.Lock` ensures only one LLM call is in-flight at a time, preventing API rate-limit bursts from concurrent requests.
- **Minimum Inter-Call Delay**: `LLM_MIN_DELAY` (default `12.0` s) enforces a minimum gap between calls, respecting Google AI Studio's 5 RPM free-tier limit.
- **Model Chain Fallback**: On any provider failure, the orchestrator iterates through a `MODEL_CHAIN` list. If all models fail, `tenacity` applies exponential back-off (up to 5 attempts) before raising a terminal error.
- **Rate Limit Detection**: HTTP 429 responses trigger an additional random 5–15 second sleep before switching to the next model.
## 6. Advanced Graph Analytics (`GraphAnalyticsService`)

Beyond the topological gap analysis, the `GraphAnalyticsService` provides a comprehensive suite of research-grade insights operating on the finalized Knowledge Graph:

### 6.1 Conflict Detection
Scans the directed graph for semantic contradictions using two strategies:
- **Direct Contradiction**: Two edges on the same directed pair `(A→B)` with opposing polarity values (`+1` vs `-1`).
- **Feedback Loop Conflict**: Detects circular causal edges `(A→B)` and `(B→A)` with opposing polarity, which indicates a scientifically inconsistent claim.
Meta-edges, purely associative relationships, and hypothesis-tagged edges are excluded to prevent noise.

### 6.2 Novelty Scoring
Ranks edges by a composite novelty index:
```
Novelty = EdgeBetweenness × (1 / evidence_count+1) × confidence × causal_weight × longitudinal_decay
```
A `MemoryService` lookup applies a **longitudinal decay** factor — edges seen in previous research runs yield lower novelty, rewarding genuinely unusual connections. Contested edges receive an additional 80% penalty.

### 6.3 Negative Evidence Detection
Identifies research "dead ends": edges with `evidence_count ≥ 2` (well-studied) but consistently neutral or negative polarity — distinguishing "not studied" (gap) from "studied and found ineffective" (negative result).

### 6.4 Citation Graph Metrics
The `graph_service.py` implements additional network-science algorithms over the Citation Graph:
- **HITS (Hubs & Authorities)**: Separates important *citing* hubs from highly cited *authorities*.
- **Shortest Path**: Traces intellectual lineage and dependency chains between papers.
- **Co-Citation & Bibliographic Coupling**: Groups papers by shared references or shared citations for clustering.
- **Citation Snowballing**: Recursively follows reference chains to expand corpus coverage automatically.

## 7. Deployment Architecture

The system is deployed on a fully managed, zero-cost cloud infrastructure:

| Service | Platform | Notes |
|:---|:---|:---|
| FastAPI + ChromaDB | Render.com | Python Web Service deployed from `render.yaml`. ChromaDB at `/tmp/chroma` (ephemeral). |
| Redis | Upstash | Serverless TLS Redis (`rediss://`). Handles JWT blocklist, login lockouts, rate limiting. |
| PostgreSQL | Neon | Serverless Postgres for all relational data (Users, Tasks, Papers). |
| Frontend | Vercel | Next.js app auto-deployed from `vra_web/`. Includes Vercel Analytics. |
