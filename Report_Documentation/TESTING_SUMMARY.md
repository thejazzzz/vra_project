# TESTING_SUMMARY.md

## Testing Procedures

The project utilizes a comprehensive multi-level testing strategy, ensuring robustness from individual agents to the full system workflow.

### 1. Unit Testing

_Verified individual components using `pytest`._

- **Logic Verification**:
    - `tests/test_abstract_logic.py`: Validates logic for abstract synthesis and late-binding content generation, including behavior when chapter dependencies are skipped.
    - `tests/test_local_ingestion.py`: Ensures local PDF ingestion, text extraction, and metadata parsing work correctly.
    - `tests/test_postgres.py` & `tests/test_chroma.py`: Verifies database connectivity and vector store operations.
    - `tests/test_validation_fixes.py`: Validates the `ExportService.sanitize_markdown()` logic — confirms dangerous HTML tags (e.g., `<script>`, `<iframe>`) are stripped while preserving safe content.
    - `tests/test_rate_limit_logic.py`: Verifies the `LLMOrchestrator` global sequential lock and minimum delay enforcement — confirms that 3 concurrent calls take at least `N × LLM_MIN_DELAY` seconds elapsed time.
- **Infrastructure Testing**:
    - `tests/ping_server.py`: basic health check for the API.

### 2. Functional Testing

_End-to-end pipeline validation._

- **Agent Workflows**:
    - `tests/test_phase4_agents.py`: Validates the interaction between GapAnalysis and HypothesisGeneration agents.
    - `tests/test_reporting_interactive.py`: Tests the interactive reporting flow (Review -> Approve -> Regenerate).
- **System Integration**:
    - `verify_full_system.py`: Runs the complete pipeline from Research -> Analysis -> Graphs -> Reporting.
    - `verify_rag_fix.py`: Ensures Retrieval Augmented Generation correctly contextualizes answers.

### 3. Scenario-based Testing

_Validating edge cases and specific research conditions._

- **Data Scarcity**:
    - `tests/test_s2_limit.py`: Tests system behavior when Semantic Scholar rate limits are hit (Fallbacks validation).
- **Graph Integrity**:
    - `verify_research_grade_graph.py`: Validates that Knowledge Graphs meet "Research Grade" standards (connectivity, node density).
    - `test_author_graph_fix.py`: Ensures author network correctness.

### 4. UI Testing

_Frontend interaction validation (Manual & Automated)._

- **Visual Regression**:
    - Verified "Dark Mode" consistency across Research Dashboard (`page.tsx`) and Graph Views (`graph-view.tsx`).
- **Component Logic**:
    - `src/components/research-progress.tsx`: Validated real-time progress bar updates driven by WebSocket events.
    - `src/app/research/[id]/report/full-preview.tsx`: Tested report markdown rendering and "Download PDF" functionality.

---

## Performance Benchmarks

### 1. Retrieval Relevance

- **Metric**: Semantic Cosine Similarity (ChromaDB)
- **Target**: > 0.75 for top-5 retrieved papers.
- **Validation**: `tests/chroma_inspector.py` allows manual inspection of embedding distances to ensure retrieved context matches the query.

### 2. Graph Coherence

- **Metric**: Network Connectivity (Largest Connected Component)
- **Target**: > 80% coverage (Main Cluster).
- **Optimization**: "Bridging Candidates" algorithm in `GapAnalysisAgent` actively identifies and connects fragmented sub-clusters.

### 3. Agent Efficiency

- **Metric**: Token Budgeting
- **Efficiency**: `SectionCompiler` uses a multi-pass approach (Draft -> Expand -> Refine) to maximize output quality while staying within token limits (avoiding context window overflows).

### 4. Response Latency

- **Metric**: End-to-End Task Duration.
- **Performance**:
    - **Research Phase**: ~30-60s (Parallelized arXiv searches).
    - **Graph Build**: ~15s (NetworkX in-memory construction).
    - **Reporting (per section)**: ~2-3 mins per chapter (sequential LLM calls with 12s inter-call delay for Google AI Studio free tier); a full 10-chapter report takes approximately 30-60 minutes depending on provider and rate limits.

---

## Baseline Comparison

| Feature       | Baseline Approach (Traditional) | VRA (Agentic System)                                                                                   |
| :------------ | :------------------------------ | :----------------------------------------------------------------------------------------------------- |
| **Search**    | Keyword-based (Manual)          | **Adaptive Retrieval**: Expands queries semantically using LLMs.                                       |
| **Analysis**  | Manual Reading & Note-taking    | **Global Synthesis**: Auto-summarizes themes across 50+ papers.                                        |
| **Gaps**      | Intuition-based                 | **Graph-Theoretical**: Mathematically identifies structural holes and under-explored nodes.            |
| **Reporting** | Manual Drafting                 | **Agentic Compilation**: Multi-pass drafting, refining, and "fact-anchoring" to reduce hallucinations. |
