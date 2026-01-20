# Implementation Plan: Hybrid Execution Strategy for Report Generation (Refined)

## Goal

Upgrade the `SectionCompiler` to support a **Hybrid Execution Strategy**, routing "High-Reasoning" tasks (Abstract, Refinement) to state-of-the-art cloud models (e.g., GPT-4o) and "High-Volume" tasks (Expansion, Drafting) to cost-efficient local models.

## User Review Required

> [!IMPORTANT] > **Configuration Changes**: New environment variables `VRA_HYBRID_MODE`, `PRIMARY_PROVIDER`, and `SECONDARY_PROVIDER`.
> **Cost Guardrail**: Automated limit on cloud calls (Default: 15 per report) to prevent runaway costs.
> **Abstract Policy**: Abstracts will now **ALWAYS** prefer the Primary Provider (High Reasoning) even if Hybrid Mode is disabled, provided `PRIMARY_PROVIDER` (case-insensitive) is not "local".

## Proposed Changes

### 1. Configuration & Architecture (`services/reporting/section_compiler.py`)

#### New Enums

Introduce `CompilationPhase` to ensure type-safe routing:

```python
class CompilationPhase(Enum):
    DRAFT = "DRAFTING"
    EXPAND = "EXPANDING"
    REFINE = "REFINING"
    ABSTRACT = "ABSTRACT"
```

#### New Environment Variables

-   `VRA_HYBRID_MODE` (bool, default: `False`)
-   `PRIMARY_PROVIDER` (defaults to current `REPORT_PROVIDER` or `openai`)
-   `SECONDARY_PROVIDER` (defaults to `local`)
-   `SECONDARY_MODEL` (defaults to `llama3:8b`)
-   `MAX_CLOUD_CALLS` (int, default: 15)

### 2. Logic Updates

#### A. Provider Routing Logic (`_resolve_provider`)

Implement `_resolve_provider(phase: CompilationPhase, section_type: str) -> (LLMProvider, str)`.

**Routing Matrix:**

| Condition  | Phase        | Section Type         | Provider              | Rationale                                                                                               |
| :--------- | :----------- | :------------------- | :-------------------- | :------------------------------------------------------------------------------------------------------ |
| **Always** | **ABSTRACT** | _Any_                | **PRIMARY**           | Pure reasoning/synthesis. High risk.                                                                    |
| Hybrid=Off | _Other_      | _Any_                | **Default (PRIMARY)** | **Default**: Falls back to `PRIMARY_PROVIDER` if configured; otherwise falls back to `REPORT_PROVIDER`. |
| Hybrid=On  | **REFINE**   | _Any_                | **PRIMARY**           | Polishing content, tone check.                                                                          |
| Hybrid=On  | **EXPAND**   | _Any_                | **SECONDARY**         | Bulk text generation.                                                                                   |
| Hybrid=On  | **DRAFT**    | INTRO/CONCL/ANALYSIS | **PRIMARY**           | Structural reasoning required.                                                                          |
| Hybrid=On  | **DRAFT**    | METHOD/IMPL          | **SECONDARY**         | Varied structural templates.                                                                            |

#### B. Cost & Safety Guardrails

-   **Cloud Call Tracking**: Increment `state["metrics"]["cloud_calls"]` when a cloud provider is used.
-   **Cost Limit Fallback**: If `cloud_calls >= MAX_CLOUD_CALLS`, raise `CostLimitExceededError`. Catch this error in `compile` and **fallback to`SECONDARY_PROVIDER`** (Local) for the remainder of the report. Log: `[Hybrid] Event=FALLBACK | Reason=COST_LIMIT`. _Note: distinct from failure-based circuit breakers._
-   **Provider Error Fallback**: Catch timeouts/API errors from `PRIMARY_PROVIDER` (e.g., 500s). Retry with backoff. If exhausted, **fallback to `SECONDARY_PROVIDER`**. Log: `[Hybrid] Phase=... | Event=FALLBACK | From=PRIMARY | To=SECONDARY | Error=...`.
-   **Secondary Failure**: If `SECONDARY_PROVIDER` fails, log `[Hybrid] Event=FALLBACK_FAILED` and raise exception.
-   **Logging**: Structured logs: `[Hybrid] Phase=REFINE | Section=1.3 | Provider=OPENAI | Model=gpt-4o`

### 3. File Modifications

#### [MODIFY] [section_compiler.py](file:///c:/Users/theja/OneDrive/Documents/AI%20PRC22CA027/MAIN%20PROJECT/vra_project/services/reporting/section_compiler.py)

-   **Imports**: Add `Enum` and `OS`.
-   **Classes**: Define `CompilationPhase(Enum)`.
-   **Attributes**: Add `cloud_call_count` tracking (or use ReportState metrics).
-   **Methods**:
    -   `_resolve_provider(phase: CompilationPhase, section_type: str)`
    -   Update `_draft_skeleton`, `_expand_content`, `_refine_content`, `_compile_abstract` to use `_resolve_provider` and pass the `CompilationPhase` enum.
    -   Update `_compile_abstract` to force `CompilationPhase.ABSTRACT`.
    -   Implement Cloud Guardrail check before generation.

### 4. Step-by-Step Execution Flow (Hybrid Example)

1. **Section 1.1 (Introduction)**

    - **Draft**: `_resolve_provider(DRAFT, INTRO)` -> **Primary** (Reasoning).
    - **Expand**: `_resolve_provider(EXPAND, INTRO)` -> **Secondary** (Volume).
    - **Refine**: `_resolve_provider(REFINE, INTRO)` -> **Primary** (Polish).

2. **Section 4.1 (Methodology)**

    - **Draft**: `_resolve_provider(DRAFT, METHOD)` -> **Secondary** (Local, standard template).
    - **Expand**: `_resolve_provider(EXPAND, METHOD)` -> **Secondary** (Local).
    - **Refine**: `_resolve_provider(REFINE, METHOD)` -> **Primary** (Polish).

3. **Abstract**
    - **Synthesize**: `_resolve_provider(ABSTRACT, ...)` -> **Force Primary**.

## Verification Plan

### Automated Tests

1. **Unit Test**: Test `_resolve_provider` with various combinations of `Hybrid Mode`, `Phase`, and `SectionType`. Confirm Abstract always hits Primary.
2. **Guardrail Test**: Simulate a report with high call count and verify Circuit Breaker triggers.

### Manual Verification

1. Set `.env`: `VRA_HYBRID_MODE=true`, `REPORT_PROVIDER=openai`, `SECONDARY_PROVIDER=local`.
2. Run report generation.
3. specific check: Verify "Evolution" logs show Local usage for Expansion and OpenAI for Refinement.
