# Virtual Research Assistant (VRA) - System Documentation

## 1. System Overview

The **Virtual Research Assistant (VRA)** is an agentic AI system designed to automate the scientific research process. It operates on a state-based workflow that transitions through distinct phases: Research, Analysis, Graph Construction, Gap Identification, Hypothesis Generation, and Reporting.

### High-Level Architecture

The system follows a layered architecture:

- **API Layer (`api/`)**: FastAPI endpoints that expose system capabilities to the frontend (`vra_web`).
- **Orchestration Layer (`workflow.py`)**: A central state machine that manages the `VRAState` and transitions between workflow steps. This explicitly event-driven design allows for clean separation of concerns and easy extensibility.
- **Agent Layer (`agents/`)**: Specialized, autonomous units responsible for executing complex, multi-step tasks (e.g., searching arXiv, analyzing graphs).
- **Service Layer (`services/`)**: Core business logic and shared utilities (algorithm implementations, database access, LLM interaction).
- **Data Layer**:
    - **PostgreSQL**: Relational data (Papers, Research Tasks, User State).
    - **ChromaDB**: Vector storage for semantic search and RAG (Retrieval-Augmented Generation).

---

## 2. Core Agents

The system uses specialized agents to handle distinct cognitive tasks.

| Agent                       | Source File                             | Responsibilities                                                                                                           |
| :-------------------------- | :-------------------------------------- | :------------------------------------------------------------------------------------------------------------------------- |
| **ArxivAgent**              | `agents/arxiv_agent.py`                 | Searches arXiv, sanitizes metadata, and normalizes output into a standard `Paper` schema.                                  |
| **DataAcquisitionAgent**    | `agents/data_acquisition_agent.py`      | Orchestrates fetching from multiple sources (arXiv, Semantic Scholar) and handles broader queries.                         |
| **GraphBuilderAgent**       | `agents/graph_builder_agent.py`         | Orchestrates the construction of Knowledge, Citation, and Author graphs. Integrates analysis output into graph structures. |
| **GapAnalysisAgent**        | `agents/gap_analysis_agent.py`          | Analyzes graph topology to identify "Research Gaps" (e.g., under-explored concepts, structural holes).                     |
| **HypothesisGenAgent**      | `agents/hypothesis_generation_agent.py` | Uses identified gaps to prompt an LLM to generate novel, testable research hypotheses.                                     |
| **PaperSummarizationAgent** | `agents/paper_summarization_agent.py`   | Generates structured summaries for collected papers.                                                                       |
| **ReviewerAgent**           | `agents/reviewer_agent.py`              | (Phase 4.1) Reviews generated hypotheses or reports for quality and rigorousness.                                          |
| **ReportingAgent**          | `agents/reporting_agent.py`             | Compiles all research artifacts into a final comprehensive report.                                                         |

---

## 3. Workflow & Lifecycle

The system execution is governed by `workflow.py`. The state machine flows through these key steps:

1.  **Research Phase (`awaiting_research_review`)**:
    - User inputs a query.
    - System fetches papers using **Adaptive Expansion** (see Algorithms).
    - Papers are deduplicated and stored.
2.  **Global Analysis (`awaiting_analysis`)**:
    - System performs a global reading of the papers to identify key concepts and themes using LLM.
    - Papers are optionally re-ranked for relevance.
3.  **Paper Summarization (`awaiting_paper_summaries`)**:
    - Detailed summaries are generated for each paper.
    - **Trend Analysis** is run concurrently to detect temporal patterns.
4.  **Graph Construction (`awaiting_graphs`)**:
    - **Knowledge Graph**: Maps concepts and their relations.
    - **Citation Graph**: Maps citations between papers.
    - **Author Graph**: Maps co-authorship.
5.  **Graph Review (`awaiting_graph_review`)**:
    - User interaction point to approve or edit the generated graphs.
6.  **Gap Analysis (`awaiting_gap_analysis`)**:
    - System identifies missing links or sparse areas in the approved graph.
7.  **Hypothesis Generation (`awaiting_hypothesis`)**:
    - New research ideas are generated based on the gaps.
8.  **Reporting (`awaiting_report`)**:
    - Final output generation.

---

## 4. Key Algorithms

The system employs several custom algorithms to ensure scientific rigor and data quality.

### A. Adaptive Query Expansion (`research_service.py`)

Used when the initial search yields insufficient results (default < 5 papers).

1.  **Trigger**: `process_research_task` checks result count.
2.  **Action**: Uses an LLM to generate 3-6 broadly related academic sub-queries.
3.  **Execution**: Runs parallel searches for these sub-queries to broaden the search horizon.

### B. Smart Deduplication (`research_service.py`)

Merges papers from different sources (e.g., a local file and an arXiv result) into a single canonical entry.

- **Priority Logic**:
    1.  **Semantic Scholar ID**: Strongest identifier.
    2.  **DOI**: Second strongest.
    3.  **Normalized Title + Year**: Fallback for entries with no IDs.
- **Merging**: Combines metadata, preferring Semantic Scholar for metadata quality but keeping the longest abstract available.

### C. Gap Analysis (`gap_analysis_agent.py`)

Scanning the Knowledge Graph (KG) to find opportunities.

1.  **Conceptual Gaps (Under-explored attributes)**:
    - **Metric**: `Confidence = 0.5*(1 - NormalizedCover) + 0.3*(1 - ClusteringCoef) + 0.2`.
    - **Logic**: High confidence gaps are those with _few_ associated papers (Low Coverage) that are also not well-connected to other concepts (Low Clustering).
2.  **Structural Gaps (Bridging Candidates)**:
    - **Logic**: Identifies weakly connected components in the graph.
    - **Opportunity**: Suggests "bridging" these disconnected clusters (structural holes) as a high-impact research opportunity.

### D. Trend Detection (`trend_analysis_service.py`)

Analyzes the temporal distribution of concepts.

- **Input**: Paper concepts + Publication years.
- **Logic**:
    - Calculates growth rates over defined windows (e.g., recent 3 years vs previous 3 years).
    - Classifies trends as **Emerging** (high growth), **Saturated** (high count, low growth), or **Declining**.

---

## 5. Evaluation Strategy & Metrics

To ensure the research output is high-quality and trustworthy, the system employs the following evaluation metrics:

- **Graph Quality**:
    - **Node Coverage**: Percentage of core concepts from papers that appear in the Knowledge Graph.
    - **Clustering Coefficient**: Measures the degree to which nodes tend to cluster together, indicating how well-connected a topic's sub-fields are.
- **Hypothesis Scoring**:
    - The `ReviewerAgent` evaluates hypotheses on:
        - **Novelty**: Is this suggestion unique compared to the existing corpus?
        - **Testability**: Can this hypothesis be validated experimentally?
        - **Confidence Score**: A calculated probability (0-1) indicating the strength of the evidence backing the gap.

## 6. Error Handling & Fallbacks

The system is designed to be resilient to common external failures:

- **API Resilience**: If primary paper sources (e.g., Semantic Scholar) fail, the system falls back to secondary sources (arXiv) or cached results.
- **Graph Construction**: If a Knowledge Graph cannot be fully populated due to sparse data, the system degrades gracefully to a "Concept-Only" graph, ensuring the user can still proceed with limited analysis.
- **Gap Analysis Weakness**: If no strong structural gaps are found (low confidence), the Hypothesis Generation agent downgrades its output to "Future Directions" rather than specific "Novel Hypotheses," maintaining intellectual honesty.
- **LLM Provider Resilience**: The system uses a configurable, multi-provider `LLMFactory` (supporting **Google AI Studio / Gemini**, OpenAI, OpenRouter, Azure, and local Ollama) with a primary/secondary fallback chain in `SectionCompiler`. If the primary cloud provider (default: Google Gemini) returns a 429 rate-limit error or times out, generation automatically falls back to the secondary provider. A global sequential `LLMOrchestrator` enforces a minimum inter-call delay (default: 12 s, tunable via `LLM_MIN_DELAY`) to respect Google AI Studio's free-tier limits (5 RPM).

## 7. Reporting & Formatting

The final phase of the VRA pipeline converts raw output into academic-grade documentation:

- **Native Exporters**: The Reporting Agent utilizes dedicated formatters to export the multi-stage research data natively to `PDF`, `DOCX`, `Markdown`, and `LaTeX`, preserving structured elements like citations, headers, and reference tables contextually without external dependencies.
- **Interactive Review**: Users preview live compiled Markdown in the dashboard before initiating large file exports.
- **Multi-Pass Compilation**: The `SectionCompiler` orchestrates a Draft → Expand → Refine pipeline for each report section, with a separate specialised path for the Abstract (pure synthesis from accepted chapter content).
- **Markdown Sanitization**: `ExportService.sanitize_markdown()` strips dangerous HTML tags (`<script>`, `<iframe>`, etc.) while preserving safe content and generic code syntax.

---

## 8. LLM Architecture & Provider Strategy

The system employs a **configurable, multi-provider LLM architecture** rather than a single fixed model:

### LLMFactory (`services/llm_factory.py`)

A factory-pattern client manager that supports the following providers:

| Provider | Identifier | Default Model | Notes |
|:---|:---|:---|:---|
| **Google AI Studio** | `google` | `gemini-2.5-pro` (env: `GOOGLE_MODEL`) | Primary production provider |
| **OpenAI** | `openai` | `gpt-4o-mini` (env: `OPENAI_MODEL`) | Fallback / alternate |
| **OpenRouter** | `openrouter` | `google/gemini-2.5-pro-exp-03-25:free` | Free-tier fallback |
| **Azure OpenAI** | `azure` | `azure-gpt-4` (env: `AZURE_DEPLOYMENT_NAME`) | Enterprise option |
| **Local (Ollama)** | `local` | `llama3` (env: `LOCAL_MODEL`) | Offline / privacy-first |

### SectionCompiler Hybrid Mode (`services/reporting/section_compiler.py`)

Controlled by environment variables:

- `PRIMARY_PROVIDER` / `PRIMARY_MODEL`: Used for high-reasoning phases (Abstract, Refine, complex Drafts). Defaults to `REPORT_PROVIDER` or `openai`.
- `SECONDARY_PROVIDER` / `SECONDARY_MODEL`: Used for high-volume phases (Expand, simple Drafts). Defaults to `local`.
- `VRA_HYBRID_MODE` (`true`/`false`): When enabled, routes phases to the optimal provider per the routing matrix above. When disabled, all phases use `PRIMARY_PROVIDER`.
- `MAX_CLOUD_CALLS` (default 15): Hard cost guardrail — if cloud API calls exceed this threshold, generation automatically falls back to the secondary provider.

### LLMOrchestrator (`services/llm/orchestrator.py`)

A centralized async orchestrator enforcing the following:

- **Sequential Execution**: A global `asyncio.Lock` ensures LLM calls are never made in parallel, preventing rate limit bursts.
- **Minimum Delay**: A configurable inter-call delay (`LLM_MIN_DELAY`, default `12.0` seconds) respects Google AI Studio's free-tier limit of 5 requests per minute.
- **Model Chain Fallback**: On failure, the orchestrator steps through a `MODEL_CHAIN` list (e.g., `openai/gpt-4o-mini` → `openrouter/gemini-flash` → `openrouter/llama3.1`) with exponential backoff via `tenacity`.
- **Rate Limit Detection**: Explicitly detects HTTP 429 errors and applies an additional random 5–15 second back-off before trying the next model.

## 9. Limitations

While powerful, the system operates within specific constraints:

- **Abstract-Level Context**: The system largely relies on paper abstracts. Full-text PDF parsing is attempted but not guaranteed for all sources, which may limit the depth of specific technical extraction.
- **Extraction Accuracy**: Knowledge Graph quality is downstream of the LLM's entity extraction accuracy; hallucinations or missed entities in the extraction phase will propagate potential noise into the graph.
- **Domain Bias**: The primary data sources (arXiv, Semantic Scholar) have a strong bias, meaning the system performs best on CS, Physics, and Math topics, with variable performance in Humanities or Social Sciences.
- **Hypothesis Nature**: Generated hypotheses are _suggestive_ based on literature gaps. They are not experimentally validated truths and require human expert review.

---

## 8. Data Layout

### VRAState Object

The `state` dictionary passed through the workflow acts as the "Memory" of the session. Key keys include:

- `query`: The original research topic.
- `selected_papers`: List of papers chosen for the current context.
- `knowledge_graph`: NetworkX node-link data format of the constructed KG.
- `research_gaps`: List of identified gap objects.
- `hypotheses`: List of generated hypotheses.
- `current_step`: The pointer to the current workflow phase.

### Persistence

- **SQL (Papers)**: Stores metadata, raw text, and canonical IDs.
- **Chroma (Embeddings)**: Stores vector embeddings of paper abstracts for RAG tasks (Retrieval Augmented Generation).
