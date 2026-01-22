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

## 7. Limitations

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
