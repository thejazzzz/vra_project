# README.md

# Virtual Research Assistant (VRA)

A modular, multi-agent AI research system powered by **FastAPI**, **ChromaDB**, **PostgreSQL**, and a configurable multi-provider LLM architecture (Google AI Studio / Gemini, OpenAI, OpenRouter, Azure, or local Ollama).

## Quick Start

```bash
# Build and run the full stack
docker-compose up --build
```

## Endpoints

| Method | Endpoint | Description |
|:---|:---|:---|
| `GET` | `/health` | Service health check |
| `GET` | `/healthz` | Kubernetes-style liveliness probe |
| `POST` | `/research/` | Submit research query |
| `GET/POST` | `/planner/` | Planner agent routes |
| `GET/POST` | `/analysis/` | Analysis agent routes |
| `GET/POST` | `/reporting/` | Interactive reporting workflow |
| `GET/POST` | `/graphs/` | Graph CRUD operations |
| `GET/POST` | `/graph-viewer/` | Graph visualization data |
| `POST` | `/upload/` | Local PDF upload & ingestion |
| `POST` | `/auth/login`, `/auth/register` | User authentication (JWT) |

## Development

1. Create and activate a virtual environment
2. Install dependencies

```bash
pip install -r requirements.txt
```

3. Copy and configure environment

```bash
cp .env.example .env
# Edit .env — set GOOGLE_API_KEY (primary LLM), DATABASE_URL, CHROMA settings
```

4. Run API locally

```bash
uvicorn api.main:app --reload
```

5. (Optional) Start Ollama for local/secondary LLM

```bash
ollama serve
ollama pull llama3          # or whichever model you configure as LOCAL_MODEL
```

## LLM Configuration

The system supports multiple LLM providers. Set the following in `.env`:

| Variable | Default | Description |
|:---|:---|:---|
| `GOOGLE_API_KEY` | — | Google AI Studio API key (primary) |
| `GOOGLE_MODEL` | `gemini-2.5-pro` | Primary model name |
| `VRA_HYBRID_MODE` | `false` | Enable hybrid primary/secondary routing |
| `PRIMARY_PROVIDER` | `openai` | Provider for high-reasoning tasks |
| `SECONDARY_PROVIDER` | `local` | Provider for bulk/expansion tasks |
| `MAX_CLOUD_CALLS` | `15` | Max cloud LLM calls per report (cost guardrail) |
| `LLM_MIN_DELAY` | `12.0` | Minimum seconds between LLM calls (rate limiting) |

## Services

| Service | URL |
|:---|:---|
| API | http://localhost:8000 |
| ChromaDB | http://localhost:8000 (default Chroma port) |
| Postgres | localhost:5432 |

## Project Structure

```
vra_project/
├── api/                  # FastAPI app (main.py, routers/, middleware/)
│   ├── routers/          # auth, health, planner, research, analysis,
│   │                     #   reporting, graphs, graph_viewer, upload
│   └── middleware/       # rate_limit.py (custom + slowapi)
├── agents/               # Autonomous research agents
│   ├── arxiv_agent.py
│   ├── data_acquisition_agent.py
│   ├── graph_builder_agent.py
│   ├── gap_analysis_agent.py
│   ├── hypothesis_generation_agent.py
│   ├── paper_summarization_agent.py
│   ├── reviewer_agent.py
│   └── reporting_agent.py
├── services/
│   ├── llm_factory.py         # Multi-provider LLM client factory
│   ├── llm_service.py         # Core generate_response() with retry
│   ├── llm/
│   │   └── orchestrator.py    # Sequential calls + multi-model fallback chain
│   ├── reporting/             # Report compilation pipeline
│   │   ├── section_compiler.py   # Hybrid draft→expand→refine engine
│   │   ├── section_planner.py    # Section outline & dependency planning
│   │   ├── reporting_service.py  # Stateful report orchestration
│   │   └── export_service.py     # PDF/DOCX/LaTeX/MD export
│   ├── graph_service.py       # Knowledge graph construction
│   ├── research_service.py    # Paper retrieval & deduplication
│   └── trend_analysis_service.py  # Temporal concept trend detection
├── state/                # VRAState & ReportState schema definitions
├── database/             # SQLAlchemy models & DB init
├── tests/                # Unit & integration tests
├── migrations/           # Alembic DB migrations
└── vra_web/              # Next.js frontend dashboard
```
