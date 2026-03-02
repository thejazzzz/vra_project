# System Testing

## 1. Introduction to the Testing Strategy

The Virtual Research Assistant (VRA) project employs a comprehensive, multi-layered testing strategy to guarantee maximum reliability and continuous correctness of the entire research pipeline. Given the highly autonomous, agentic nature of the system—where one set of LLM outputs (e.g., entity extraction) acts as the direct input for complex mathematical algorithms (e.g., topological graph gaps)—ensuring deterministic behavior amidst probabilistic language models is paramount.

The testing architecture spans from isolated microscopic logic checks (Unit Testing) to full-scale end-to-end pipeline executions involving multiple autonomous agents.

## 2. Unit Testing

Unit testing forms the foundational layer of the system's test suite. These tests isolate individual functions, utility methods, and specific programmatic logic pieces to verify their correctness independent of external API calls or databases. The system heavily leverages `pytest` for executing these granular checks.

- **Logic Verification**:
    - **Abstract Synthesis & Content Generation**: Tests like `test_abstract_logic.py` validate the deterministic fallback mechanisms and logic sequences that govern how the system synthesizes data when LLMs return unpredictable formats or late-binding content is required.
    - **Local Ingestion Pipeline**: `test_local_ingestion.py` ensures that local PDF uploads are correctly parsed, text is extracted accurately using fallback libraries (like `pdfplumber` or `PyMuPDF`), and the resulting metadata is perfectly clean before embedding.
- **Infrastructure & Database Validation**:
    - **Database Operations**: `test_postgres.py` confirms that SQL ORM transactions, schema models, and constraints work correctly.
    - **Vector Store Connectivity**: `test_chroma.py` checks that semantic chunks are accurately embedded and can be retrieved using standard Euclidean or Cosine distance metrics.
    - **Health and Liveliness Checks**: `ping_server.py` performs rudimentary fast-fail health checks against the FastAPI endpoints.

## 3. Integration & Functional Testing

Because the VRA system is composed of numerous interacting state machines, integration and functional tests ensure that the distinct phases of the workflow harmonize without data loss or unexpected deadlocks.

- **Agent Workflows (Inter-Agent Communication)**:
    - **Phase 4 Handshaking**: Scripts such as `test_phase4_agents.py` enforce the contract between the Gap Analysis Agent and the Hypothesis Generation Agent. It ensures that identified topological graph gaps are parsed correctly into valid context windows for the subsequent hypothesis generation prompt.
    - **Interactive State Transitions**: `test_reporting_interactive.py` models a human-in-the-loop interaction, validating that the system properly pauses workflows upon requiring user approval, allows edit injections, and can successfully regenerate subsections based on user feedback.
- **Full System Pipeline**:
    - **End-to-End Orchestration**: `verify_full_system.py` acts as the project's most critical smoke test. It simulates a complete, un-interrupted research task traversing through all phases: Initialization $\rightarrow$ Data Acquisition $\rightarrow$ Global Analysis $\rightarrow$ Graph Construction $\rightarrow$ Gap Analysis $\rightarrow$ Reporting compilation.
    - **Semantic Integrity**: `verify_rag_fix.py` tests the core Retrieval-Augmented Generation pipeline. It ensures that the system accurately synthesizes answers contextualized entirely by fetched peer-reviewed literature and doesn't hallucinate non-existent citations.

## 4. Scenario-Based & Edge Case Testing

To ensure robustness, the testing methodology incorporates specific programmatic scenarios designed to intentionally stress-test the system's guardrails, fallback behaviors, and algorithmic constraints.

- **Data Scarcity & Rate Limits**:
    - Scripts such as `test_s2_limit.py` trigger artificial 429 (Too Many Requests) errors from the Semantic Scholar API to validate the system's backoff logic and graceful degradation (e.g., falling back heavily to arXiv or local cache seamlessly).
- **Graph Topological Integrity**:
    - `verify_research_grade_graph.py` enforces mathematical boundaries. It validates that the generated Knowledge Graphs maintain a minimum internal node density, adequate edge-weights, and do not overly fragment into isolated un-connected islands.
    - `test_author_graph_fix.py` ensures author-collaboration maps resolve name disambiguation properly.

## 5. User Interface (UI) Testing

The frontend operations, built on Next.js, are critical for human-in-the-loop validation and data visualization.

- **Logic & State Rendering**:
    - Components like `research-progress.tsx` are evaluated to ensure they accurately reflect global WebSocket event streams emitted by `workflow.py` without desynchronization.
- **Visual Regression & Theming**:
    - The system includes checks to guarantee the visual fidelity of complex D3/Vis.js graph renders (`graph-view.tsx`) and ensures "Dark Mode" aesthetic consistency across generated markdown previews (`full-preview.tsx`).

## 6. Performance Benchmarks and Validation Metrics

Beyond traditional pass/fail tests, the VRA pipeline runs continuous validations against specific quality benchmarks:

- **Retrieval Relevance**: Measured via Semantic Cosine Similarity (ChromaDB) ensuring a $>0.75$ baseline for the top-5 retrieved context chunks (`chroma_inspector.py`).
- **Graph Coherence**: Evaluated by tracking the network's Largest Connected Component, optimizing algorithms to automatically identify structural holes ("Bridging Candidates").
- **Execution Latency Targets**: Research phases are aggressively parallelized with expected performance of ~30-60 seconds for data harvesting, under 15 seconds for graph matrix building, and iterative drafting bounds designed to stay safely within context token limits.
