# README.md
# Virtual Research Assistant (VRA)
A modular AI research system powered by FastAPI, ChromaDB, and multi-agent orchestration.


## Quick Start
```bash
# Build and run the full stack
docker-compose up --build
```


## Endpoints
- `GET /health` — Service health check
- `POST /research/` — Submit research query


## Development
1. Create and activate a virtual environment
2. Install dependencies
```bash
pip install -r requirements.txt
```
3. Run API locally
```bash
uvicorn api.main:app --reload
```
4. cp .env.example .env
# Then edit .env and add your OpenAI key



## Services
| Service | URL |
|--------|-----|
| API | http://localhost:8001 |
| ChromaDB | http://localhost:8000 |
| Postgres | localhost:5432 |


## Project Structure
(Will be updated as the agent-based workflow expands)