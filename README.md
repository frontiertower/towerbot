# TowerBot

[![Project Status](https://img.shields.io/badge/status-active-brightgreen)](https://github.com/frontiertower/towerbot)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

TowerBot is an open source, AI-powered Telegram assistant for Frontier Tower citizen developers. It answers questions, provides insights, and leverages persistent memory, semantic search, and a temporal knowledge graph to empower your Telegram community.

**This project is licensed under the [MIT License](LICENSE) and is free for both commercial and non-commercial use.**

---

## ✨ What is TowerBot?

TowerBot connects your Telegram group to powerful AI and community data. It can answer questions, summarize information, and provide analytics—all with persistent memory and semantic/graph search. It also provides detailed information about the building, events, and community using structured data.

---

## 👥 Who is this for?

- Frontier Tower citizen developers
- Community managers who want smarter group chats
- Developers interested in AI, LLMs, and chatbots
- Contributors of all skill levels (beginner to advanced)
- Anyone looking to extend or self-host an AI Telegram bot

---

## 🛠️ Tech Stack

- **Python 3.12+**
- **FastAPI** (API backend)
- **python-telegram-bot** (Telegram integration)
- **Azure OpenAI** (LLM via LangChain)
- **Supabase** (memory)
- **Neo4j** (graph database)
- **Graphiti** (temporal knowledge graph)
- **APScheduler** (scheduled jobs)
- **LangChain, LangGraph, LangMem** (advanced LLM/graph features)
- **Pydantic** (settings and validation)
- **psycopg_pool** (async Postgres connection pool)
- **Docker** (optional, for deployment)
- **uv** (Python package/dependency/runtime manager)

Dependencies are managed in `pyproject.toml` and installed using [`uv`](https://github.com/astral-sh/uv).

---

## 🧠 About Graphiti

TowerBot uses [**Graphiti**](https://github.com/getzep/graphiti) — a Python library for building temporal Knowledge Graphs using LLMs — to power its community graph analytics and persistent memory features.

**What is Graphiti?**

Graphiti manages evolving relationships and context over time by capturing and recording changes in facts and relationships. It enables TowerBot to construct a dynamic knowledge graph of your community, where facts (nodes and edges) can change as new data arrives. This allows TowerBot to:

- Track how relationships and facts change over time (temporal awareness)
- Maintain historical context for more accurate, context-aware answers
- Ingest both structured and unstructured data (e.g., Telegram messages, events, user interactions)
- Combine semantic and graph search for better recall and analytics

**How TowerBot uses Graphiti:**

- Stores and updates user, event, and project relationships in a Neo4j-powered graph
- Enables advanced community analytics and recommendations
- Supports persistent memory for conversations and group activity

For more on Graphiti, see: [Graphiti: A Python Library for Building Temporal Knowledge Graphs Using LLMs](https://help.getzep.com/graphiti)

---

## 🚀 Features

- **AI Q&A:** `/ask <question>` in Telegram, get instant, context-aware answers
- **Problem Reporting:** `/report <problem>` to report issues or requests (e.g., facilities, supplies)
- **Idea Proposals:** `/propose <idea>` to propose new ideas or initiatives for the community
- **Community Connections:** `/connect <interest>` to find people, projects, or resources
- **Persistent Memory:** Stores all questions/messages for analytics and context using LangMem
- **Vector & Graph Search:** Semantic and graph search over documents and community data
- **Building & Community Info:** Answers questions about the building, amenities, events, and more using structured data
- **Calendar Integration:** Fetches and summarizes events from Luma calendar API
- **BerlinHouse Integration:** Connects to BerlinHouse API for community data
- **Comprehensive Logging:** Structured logging with proper error handling and context
- **Health Check:** `/health` endpoint for monitoring
- **Webhook Endpoint:** `/telegram` endpoint for Telegram updates
- **Scheduled Community Analytics:** Uses APScheduler to run periodic community graph updates
- **Message Processing:** Processes all group messages for entity extraction and graph building
- **User Validation:** Validates user membership before allowing private conversations

---

## 🗨️ Command Usage

TowerBot responds to the following commands in your Telegram group:

- `/ask <question>` — Get answers to questions about the building, community, or general topics.  
  _Example:_ `/ask what's the wifi password?`
- `/report <problem>` — Report a problem or submit a maintenance request.  
  _Example:_ `/report we need more toilet paper on the 9th floor`
- `/propose <idea>` — Propose a new idea or initiative for the community.  
  _Example:_ `/propose let's organize a community garden on the rooftop`
- `/connect <interest>` — Find people, projects, or resources related to a topic.  
  _Example:_ `/connect who can help me learn more about biotech?`
- `/start` — Get an introduction message with bot capabilities

**Available Tools:**

- **Tower Information:** Access building details, amenities, and floor plans
- **Calendar Events:** Get upcoming events from the community calendar
- **Community Search:** Find connections and relationships in the community graph
- **Memory Management:** Persistent conversation memory for better context

**Message Processing:**

- All group messages are processed for entity extraction and graph building
- Reply-based command continuation for complex queries
- Private message validation (members only)

If you use a command without context, TowerBot will prompt you for more information with an example.

---

## 🏗️ Architecture Overview

```mermaid
graph TD;
  TG["Telegram Group"] -->|/ask, /report, /propose, /connect| BOT["TowerBot (python-telegram-bot)"]
  BOT --> API["FastAPI Backend"]
  API --> AI["Azure OpenAI (LangChain)"]
  API --> DB["Supabase (Vectors)"]
  API --> GRAPH["Neo4j (Graph DB) + Graphiti"]
  API --> Health["/health Endpoint"]
  API --> Webhook["/telegram Endpoint"]
```

---

## ⚡ Quickstart

### 1. Clone & Install

```bash
git clone <your-repo-url>
cd towerbot
pip install uv  # if you don't have it already
uv pip install --system  # ensure uv is set up for your Python
uv sync  # install all dependencies from pyproject.toml
```

### 2. Environment Setup

Create a `.env` file in the root directory with the following variables:

```env
# Application Environment
APP_ENV=dev                           # dev or prod
PORT=3000                            # Server port
WEBHOOK_URL=https://your-server-url  # Public webhook URL

# Telegram Bot
BOT_TOKEN=your-telegram-bot-token    # From @BotFather
GROUP_ID=your-telegram-group-id      # Target group ID

# Azure OpenAI
AZURE_OPENAI_API_KEY=your-azure-openai-key
AZURE_OPENAI_ENDPOINT=your-azure-endpoint
MODEL=your-azure-chat-model          # e.g., gpt-4
EMBEDDING_MODEL=your-embedding-model # e.g., text-embedding-ada-002
RERANKER_MODEL=your-azure-reranking-model

# Database Services (Connection Pooling)
POSTGRES_CONN_STRING=postgresql://user:pass@host:port/db

# Neo4j Graph Database
NEO4J_URI=your-neo4j-uri            # e.g., bolt://localhost:7687
NEO4J_USER=your-neo4j-user          # e.g., neo4j
NEO4J_PASSWORD=your-neo4j-password

# External APIs
BERLINHOUSE_EMAIL=your-email         # For BerlinHouse API
BERLINHOUSE_PASSWORD=your-password

# Observability (Optional)
LANGSMITH_API_KEY=your-langsmith-api-key
LANGSMITH_PROJECT=your-langsmith-project
LANGSMITH_TRACING=true
```

### 3. Run Locally

You can use the provided startup script to launch both the webhook and the FastAPI app:

```bash
./startup.sh
```

Or run manually:

```bash
uv run python -m app.webhook &
uv run uvicorn app.main:app --reload --port 3000 --host 0.0.0.0
```

The Telegram bot will start automatically as a background task.

### 4. Add to Telegram Group

- Add your bot to a Telegram group.
- Use `/ask`, `/report`, `/propose`, or `/connect` to interact with the bot.

---

## 🧑‍💻 Local Development & Testing

### Development Server

```bash
# Hot-reloading development server
uv run uvicorn app.main:app --reload --port 3000 --host 0.0.0.0

# Or use the startup script
./startup.sh
```

### Dependency Management

```bash
# Update dependencies in pyproject.toml
uv sync                    # Install/update all dependencies
uv add package-name        # Add a new dependency
uv remove package-name     # Remove a dependency
```

### Environment Setup

```bash
# Development environment
export APP_ENV=dev

# Production environment
export APP_ENV=prod
```

### Docker Development

```bash
# Build and run with Docker
docker build -t towerbot .
docker run -p 3000:3000 --env-file .env towerbot
```

### Code Quality

```bash
# Check Python syntax
python -m py_compile app/**/*.py

# The application includes comprehensive logging for debugging:
# - DEBUG: Detailed tracing and function calls
# - INFO: Important application events
# - ERROR: Exception handling with context
```

### Testing

- All Python files are syntax-checked during development
- Comprehensive error handling with structured logging
- Health check endpoint for monitoring: `GET /health`
- Test framework integration coming soon

---

## 📁 Project Structure

```
towerbot/
├── app/
│   ├── core/
│   │   ├── config.py          # Application configuration and settings
│   │   ├── constants.py       # System prompts and command examples
│   │   ├── lifespan.py        # Application startup/shutdown lifecycle
│   │   └── tools.py           # AI agent tools and external API integrations
│   ├── models/
│   │   ├── ontology.py        # Graph database schema and entity definitions
│   │   ├── responses.py       # Pydantic models for AI responses
│   │   └── tools.py           # Tool parameter schemas and enums
│   ├── services/
│   │   ├── ai.py              # AI service with LangChain agents
│   │   ├── database.py        # Async database operations with connection pooling
│   │   └── graph.py           # Neo4j graph service with Graphiti
│   ├── main.py                # FastAPI application and endpoints
│   └── webhook.py             # Telegram webhook configuration
├── static/
│   └── json/
│       └── tower.json         # Building and community data
├── supabase/
│   └── config.toml           # Supabase configuration
├── pyproject.toml            # Project dependencies and metadata
├── startup.sh               # Local development startup script
├── Dockerfile              # Container build instructions
└── uv.lock                # Dependency lock file
```

**Key Components:**

- **Core Services:** AI agents, database operations, graph processing
- **Data Models:** Structured schemas for entities, responses, and tools
- **API Layer:** FastAPI endpoints for health checks and webhook handling
- **Configuration:** Environment-based settings with Pydantic validation
- **Logging:** Comprehensive structured logging across all modules

---

## 🤝 Contributing

We welcome contributions from everyone! To get started:

1. **Fork the repo** and create your branch from `main` or `develop`.
2. **Write clear, well-documented code** and add comments where helpful.
3. **Open a pull request** with a clear description of your changes.
4. For major changes, open an issue first to discuss what you’d like to change.
5. Be kind and respectful in all interactions.

**Ways to contribute:**

- New features
- Bug fixes
- Documentation improvements
- Tests and examples

---

## 💬 Getting Help

- Open an [issue](https://github.com/frontiertower/towerbot/issues) for bugs, questions, or feature requests
- Join our Telegram group (link coming soon)
- Check the comprehensive logging output for debugging information
- Review the code structure and docstrings for implementation details
- See the resources below for tech-specific help

### Common Issues

- **Connection Errors:** Check database and API credentials in `.env`
- **Telegram Issues:** Verify bot token and webhook URL configuration
- **Performance:** Monitor logs for slow queries and API timeouts
- **Memory Usage:** Check graph database size and async connection pooling

---

## 🩺 Health Check & Monitoring

### API Endpoints

- `GET /health`: Returns API status and message
- `POST /telegram`: Receives Telegram webhook updates

### Logging & Monitoring

- **Structured Logging:** Function names, line numbers, and context
- **Error Tracking:** Comprehensive exception logging with stack traces
- **Performance Monitoring:** Request/response timing and processing logs
- **Service Health:** Connection status for all external services
- **Log Levels:** Configurable DEBUG, INFO, WARNING, ERROR levels

### Health Check Response

```json
{
  "status": "ok",
  "message": "TowerBot is running"
}
```

### Application Lifecycle

- **Startup:** Service initialization with connection validation
- **Runtime:** Background message processing and scheduled tasks
- **Shutdown:** Graceful cleanup of connections and resources

---

## 📚 Resources

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [python-telegram-bot](https://python-telegram-bot.org/)
- [Supabase Docs](https://supabase.com/docs)
- [LangChain](https://python.langchain.com/)
- [Azure OpenAI](https://learn.microsoft.com/en-us/azure/ai-services/openai/)
- [Neo4j](https://neo4j.com/docs/)
- [Graphiti](https://github.com/getzep/graphiti)
- [uv (Python package manager)](https://github.com/astral-sh/uv)

---

## 📝 License

TowerBot is open source and licensed under the [MIT License](LICENSE).

You are free to use, modify, and distribute this software for commercial and non-commercial purposes, subject to the terms of the MIT License.
