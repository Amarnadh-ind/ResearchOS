# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2026-07-26

### Added

- Initial production-ready release of ResearchOS
- 10 specialized AI agents: Planner, Search, Browser, Reader, Claims, Critic, Novelty, Citation, Writer, IEEE Formatter
- LangGraph StateGraph orchestration with checkpointing and recovery
- FastAPI backend with REST and WebSocket endpoints
- Next.js 15 frontend with TypeScript and Tailwind CSS
- Multi-provider LLM routing with auto-fallback (Gemini, Gemma, Nemotron, OpenRouter, OpenAI, Grok, Manus)
- Hybrid RAG retrieval (BM25 + vector embeddings with re-ranking)
- Neo4j knowledge graph for claim-source-concept traceability
- Playwright-powered browser automation for web scraping
- PyMuPDF and fpdf2 for PDF generation
- Docker Compose setup for local development
- Render deployment configuration (render.yaml)
- Comprehensive test suite with 30+ test files
- Ruff linting and formatting configuration
- Environment variable templates (.env.example) for backend and frontend
- MIT License