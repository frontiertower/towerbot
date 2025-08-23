# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

This project uses `uv` for Python dependency management and task execution:

- **Install dependencies**: `uv sync`
- **Run development server**: `uv run uvicorn app.main:app --reload --port 8000 --host 0.0.0.0`
- **Run tests**: `uv run pytest` (tests configured in pytest.ini)
- **Generate enums**: `uv run python scripts/generate_enums.py`
- **Start full application**: `./startup.sh` (generates enums, starts webhook, then API server)

The startup.sh script runs the enum generation, webhook service, and FastAPI server in sequence.

## Architecture Overview

**TowerBot** is a Telegram bot with a FastAPI web API that maintains a temporal knowledge graph of community interactions. It combines AI agents, graph storage, and real-time messaging.

### Core Components

- **FastAPI App** (`app/main.py`): Provides health endpoints, Telegram webhook handler, and graph query API
- **Telegram Bot** (`app/core/lifespan.py`): Handles user authorization, commands (/ask, /connect, /request), and message processing
- **AI Service** (`app/services/ai.py`): LangGraph-based agents with memory management and tool calling
- **Graph Service** (`app/services/graph.py`): Graphiti temporal knowledge graph for storing community interactions
- **Authentication** (`app/services/auth.py`): Group-based authorization with optional Soulink integration

### Key Features

1. **Dual Interface**: Telegram bot for community interaction + REST API for graph queries
2. **Authorization Flow**: Users must be in allowed Telegram groups and optionally pass Soulink validation
3. **AI Agents**: Three specialized agents (ask/connect/request) with memory and tool access
4. **Temporal Graph**: Episodes from group chats stored as nodes/edges with timestamps
5. **Generated Schemas**: Runtime enum generation from ontology definitions

### Database & Infrastructure

- **PostgreSQL**: Optional persistent storage for LangGraph checkpoints, memory store, and Graphiti graph storage (falls back to in-memory)
- **Connection Pooling**: AsyncConnectionPool with 20 max connections
- **Background Processing**: Telegram updates processed via FastAPI BackgroundTasks
- **Lifespan Management**: Proper startup/shutdown of services, pools, and connections

### Configuration

The app uses pydantic-settings for environment-based configuration. Key settings include:

- Telegram bot token and group IDs for authorization
- OpenAI/Azure OpenAI credentials and model settings
- PostgreSQL connection string (optional - uses in-memory fallback if not provided)
- Soulink integration settings

### Testing

- Test framework: pytest with asyncio support
- Test markers: unit, integration, slow
- Run specific test types: `uv run pytest -m unit`
