# TowerBot

<p align="center">
  <img src="static/images/bot.png" alt="TowerBot Logo" width="200"/>
</p>

[![Project Status](https://img.shields.io/badge/status-active-brightgreen)](https://github.com/frontiertower/towerbot)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

TowerBot is an open source, AI-powered Telegram bot for Frontier Tower citizens. It answers questions, provides insights, and leverages persistent memory, semantic search, and a temporal knowledge graph to empower our Telegram Channel.

**This project is licensed under the [MIT License](LICENSE) and is free for both commercial and non-commercial use.**

## ✨ Features

- **Telegram Integration**: Commands (`/ask`, `/connect`, `/request`) and direct messaging
- **AI Agents**: Specialized agents with LangGraph, memory management, and tool calling
- **Temporal Knowledge Graph**: Community interaction tracking with Graphiti
- **REST API**: Query the knowledge graph via `/api/v1/graph/query` endpoint
- **Multi-tier Authentication**: Group membership + optional Soulink social proximity validation
- **Persistent Memory**: LangMem integration for conversation context
- **Dynamic Ontology**: Auto-generated enums and type mappings from schema definitions

## 🛠️ Tech Stack

- **Python 3.12+** with **uv** dependency management
- **FastAPI** (API backend)
- **python-telegram-bot** (Telegram integration)
- **LangChain/LangGraph/LangMem** (AI agents and memory)
- **Graphiti** (temporal knowledge graph)
- **PostgreSQL** with **pgvector** (optional vector storage, falls back to in-memory)
- **OpenAI/Azure OpenAI** (LLM services)
- **pytest** (testing with 91 test cases)

## 🚀 Quick Start

### 1. Prerequisites

- **Python 3.12+**
- **Docker** (optional, for PostgreSQL)
- **ngrok** (for webhook tunneling)

Install uv package manager:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### 2. Setup

```bash
git clone <your-repo-url>
cd towerbot
uv sync
```

### 3. Database Setup

```bash
# Start PostgreSQL with pgvector
docker run --name postgres-towerbot \
  -e POSTGRES_PASSWORD=postgres \
  -p 5436:5432 \
  -d pgvector/pgvector:pg17

# Create database and enable vector extension
sleep 3
PGPASSWORD=postgres psql -h localhost -p 5436 -U postgres \
  -c "CREATE DATABASE towerbot;"
PGPASSWORD=postgres psql -h localhost -p 5436 -U postgres -d towerbot \
  -c "CREATE EXTENSION IF NOT EXISTS vector;"
```

### 4. Environment Configuration

Create `.env` file:

```env
# Telegram (get from @BotFather)
BOT_TOKEN=your-telegram-bot-token
ALLOWED_GROUP_IDS=your-telegram-group-id

# OpenAI
OPENAI_API_KEY=your-openai-key
MODEL=gpt-4
EMBEDDING_MODEL=text-embedding-3-small

# Database (optional - uses in-memory fallback if not provided)
POSTGRES_CONN_STRING=postgresql://postgres:postgres@localhost:5436/towerbot

# Webhook (get free domain from ngrok.com)
WEBHOOK_URL=https://your-domain.ngrok-free.app

# Optional: Observability
LANGSMITH_API_KEY=your-langsmith-key
LANGCHAIN_TRACING_V2=true
```

### 5. Run Application

```bash
# Terminal 1: Start ngrok tunnel
ngrok http --domain=your-domain.ngrok-free.app 8000

# Terminal 2: Start application
./startup.sh
```

### 6. Add Bot to Telegram

1. Add bot to your Telegram group
2. **Promote bot to admin** (required for receiving webhooks and processing messages)
3. Test with `/ask what is this bot?`

## 🏗️ Architecture

```mermaid
graph TD
    TG[Telegram Group] -->|Commands| BOT[TowerBot]
    PM[Private Messages] -->|Direct Chat| BOT
    BOT --> API[FastAPI Backend]
    API --> AI[AI Service<br/>LangGraph Agents]
    API --> GRAPH[Graph Service<br/>Graphiti + PostgreSQL]
    API --> AUTH[Auth Service<br/>API Key Validation]
    API --> REST["/api/v1/graph/query<br/>REST Endpoint"]
```

**Core Components:**

- **AI Service**: Dynamic agent system with memory and tool integration
- **Graph Service**: Temporal knowledge graph with episode tracking
- **Auth Service**: Multi-tier authentication with group validation
- **REST API**: External graph query access with API key auth

## 🗨️ Usage

### Telegram Commands

- `/ask <question>` — Get AI-powered answers with context
- `/connect <interest>` — Find community connections and relationships
- `/request <item>` — Create supply requests
- **Direct Messages** — Full conversational AI with persistent memory

### REST API

Query the knowledge graph programmatically:

```bash
curl -X POST "https://your-server.com/api/v1/graph/query" \
  -H "Authorization: Bearer your-api-key" \
  -H "Content-Type: application/json" \
  -d '{"query": "Find all connections related to AI projects"}'
```

## 🔐 Authentication

**Three-tier system:**

1. **Telegram Group Membership** — Users must be in allowed groups
2. **Soulink Social Proximity** (Optional) — Shared group validation with admin
3. **API Key Authentication** — Required for REST API access

## 🧪 Development

```bash
# Run tests
uv run pytest

# Run with hot reload
uv run uvicorn app.main:app --reload --port 8000

# Generate ontology enums
uv run python scripts/generate_enums.py

# Run specific test categories
uv run pytest -m unit
uv run pytest -m integration
```

## 📁 Project Structure

```
app/
├── core/           # Configuration, constants, lifecycle
├── services/       # AI, graph, and auth services
├── schemas/        # Data models and ontology
├── api/           # FastAPI routes
├── main.py        # Application entry point
└── webhook.py     # Telegram webhook setup

tests/             # 91 comprehensive test cases
scripts/           # Enum generation utilities
static/            # Images and data files
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Ensure all tests pass: `uv run pytest`
5. Submit a pull request

## 📚 Resources

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [LangChain](https://python.langchain.com/) / [LangGraph](https://langchain-ai.github.io/langgraph/)
- [Graphiti](https://github.com/getzep/graphiti) (Temporal Knowledge Graph)
- [python-telegram-bot](https://python-telegram-bot.org/)
- [pgvector](https://github.com/pgvector/pgvector) (PostgreSQL Vector Extension)

## 📝 License

This project is licensed under the [MIT License](LICENSE).
