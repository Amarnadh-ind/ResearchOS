# ResearchOS

**Autonomous Multi-Agent Research Laboratory**

ResearchOS accepts short research prompts and autonomously produces IEEE-grade academic papers with verified citations. It orchestrates 10 specialized AI agents through a LangGraph pipeline backed by OpenRouter models.

---

## Architecture

```
User Prompt
    │
    ▼
┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐
│ Planner  │──▶│  Search  │──▶│ Browser  │──▶│  Reader  │
│  (Qwen3) │   │ (Qwen3)  │   │ (Gemma4) │   │ (Gemma4) │
└──────────┘   └──────────┘   └──────────┘   └──────────┘
                                                    │
    ┌───────────────────────────────────────────────┘
    ▼
┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐
│  Claims  │──▶│  Critic  │──▶│ Novelty  │──▶│ Citation │
│ (Gemma4) │   │(Hermes)  │   │(Hermes)  │   │ (Gemma4) │
└──────────┘   └──────────┘   └──────────┘   └──────────┘
                                                    │
    ┌───────────────────────────────────────────────┘
    ▼
┌──────────┐   ┌──────────┐
│  Writer  │──▶│   IEEE   │──▶ Final Paper (Markdown)
│  (Qwen3) │   │ (Gemma4) │
└──────────┘   └──────────┘
```

## Stack

| Layer | Technology |
|-------|-----------|
| Frontend | Next.js 15, TypeScript, Tailwind CSS, Framer Motion |
| Backend | FastAPI, Python 3.12, async |
| Orchestration | LangGraph StateGraph |
| LLM | OpenRouter (Qwen3, Gemma4, Hermes 405B) |
| Vector DB | Qdrant |
| Graph DB | Neo4j |
| Cache | Redis |
| Relational DB | PostgreSQL |
| Browser | Playwright |
| Document | PyMuPDF |
| Container | Docker Compose |

## Quick Start

### Prerequisites

- Docker & Docker Compose
- OpenRouter API key ([get one](https://openrouter.ai))

### 1. Clone & Configure

```bash
cd "research os"
cp .env.example .env
# Edit .env and add your OPENROUTER_API_KEY
```

### 2. Start with Docker

```bash
docker compose up --build
```

Services will start:
- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **Neo4j Browser**: http://localhost:7474
- **Qdrant Dashboard**: http://localhost:6333/dashboard

### 3. Local Development (without Docker)

**Backend:**
```bash
cd backend
python -m venv .venv
.venv\Scripts\activate  # Windows
pip install -r requirements.txt
playwright install chromium
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

**Frontend:**
```bash
cd frontend
npm install
npm run dev
```

**Infrastructure (databases):**
```bash
docker compose up postgres redis qdrant neo4j
```

## Non-Negotiable Rules

| Rule | Description |
|------|-------------|
| RULE-1 | NO EVIDENCE = NO CLAIM |
| RULE-2 | NO SOURCE = NO CITATION |
| RULE-3 | No hallucinated references |
| RULE-4 | All citations must be verified |
| RULE-5 | Claims must be traceable |
| RULE-6 | Critique phase mandatory |
| RULE-7 | Verification gates mandatory |

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/research` | Start research session |
| GET | `/api/research/{id}` | Get session status |
| GET | `/api/research/{id}/paper` | Get generated paper |
| GET | `/api/research` | List sessions |
| GET | `/api/agents/status` | Agent configurations |
| GET | `/api/agents/pipeline` | Pipeline structure |
| WS | `/ws/research/{id}` | Live updates |

## Memory Architecture

| Layer | Storage | Purpose |
|-------|---------|---------|
| Session | Redis | Active session state, events |
| Retrieval | Qdrant | Vector embeddings, semantic search |
| Knowledge | Neo4j | Claim-source-concept graph |
| Metadata | PostgreSQL | Sessions, sources, claims, papers |

## Project Structure

```
research os/
├── docker-compose.yml
├── .env.example
├── backend/
│   ├── main.py              # FastAPI app
│   ├── config/               # Settings, model routing
│   ├── agents/               # 10 research agents
│   ├── graph/                # LangGraph workflow
│   ├── schemas/              # Pydantic models
│   ├── services/             # LLM, search, browser, PDF
│   ├── memory/               # Redis, Qdrant, Neo4j, Postgres
│   ├── retrieval/            # Hybrid RAG system
│   └── api/routes/           # REST + WebSocket endpoints
├── frontend/
│   └── src/
│       ├── app/              # Next.js pages
│       ├── components/       # React components
│       ├── hooks/            # WebSocket, research hooks
│       ├── stores/           # Zustand state
│       └── lib/              # API client, types, utils
└── infra/                    # DB init scripts
```

## License

MIT