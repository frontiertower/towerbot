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
- **Supabase** (vector search)
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
- **Help Requests:** `/help <request>` to submit issues or requests (e.g., facilities, supplies)
- **Community Connections:** `/connect <interest>` to find people, projects, or resources
- **Persistent Memory:** Stores all questions/messages for analytics and context
- **Vector & Graph Search:** Semantic and graph search over documents and community data
- **Building & Community Info:** Answers questions about the building, amenities, events, and more using structured data
- **Health Check:** `/health` endpoint for monitoring
- **Webhook Endpoint:** `/telegram` endpoint for Telegram updates
- **Scheduled Community Analytics:** Uses APScheduler to run periodic community graph updates

---

## 🗨️ Command Usage

TowerBot responds to the following commands in your Telegram group:

- `/ask <question>` — Get answers to questions about the building, community, or general topics.  
  _Example:_ `/ask what's the wifi password?`
- `/help <request>` — Submit a help or maintenance request.  
  _Example:_ `/help we need more toilet paper on the 9th floor`
- `/connect <interest>` — Find people, projects, or resources related to a topic.  
  _Example:_ `/connect who can help me learn more about biotech?`

If you use a command without context, TowerBot will prompt you for more information with an example.

---

## 🏗️ Architecture Overview

```mermaid
graph TD;
  TG["Telegram Group"] -->|/ask, /help, /connect| BOT["TowerBot (python-telegram-bot)"]
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
APP_ENV=dev
AZURE_OPENAI_API_KEY=your-azure-openai-key
AZURE_OPENAI_ENDPOINT=your-azure-endpoint
BERLINHOUSE_EMAIL=your-email
BERLINHOUSE_PASSWORD=your-password
BOT_TOKEN=your-telegram-bot-token
DEFAULT_DATABASE=your-default-db
EMBEDDING_MODEL=your-embedding-model
GROUP_ID=your-telegram-group-id
LANGSMITH_API_KEY=your-langsmith-api-key
LANGSMITH_PROJECT=your-langsmith-project
LANGSMITH_TRACING=true
MODEL=your-azure-chat-model
NEO4J_PASSWORD=your-neo4j-password
NEO4J_URI=your-neo4j-uri
NEO4J_USER=your-neo4j-user
PORT=3000
RERANKER_MODEL=your-azure-reranking-model
SUPABASE_SERVICE_ROLE_KEY=your-supabase-service-role-key
SUPABASE_URL=your-supabase-url
WEBHOOK_URL=https://your-server-url
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
- Use `/ask`, `/help`, or `/connect` to interact with the bot.

---

## 🧑‍💻 Local Development & Testing

- Use `uv run uvicorn app.main:app --reload` for hot-reloading during development.
- Update dependencies in `pyproject.toml` as needed and run `uv sync` to install.
- Write tests for new features (test framework coming soon).
- Use Docker for consistent local environments:

```bash
docker build -t towerbot .
docker run -p 3000:3000 --env-file .env towerbot
```

---

## 📁 Project Structure

- `app/core/` — Config, constants, shared tools, and startup/shutdown logic (`lifespan.py`)
- `app/services/` — AI, database, and graph services
- `app/models/` — Data models (ontology, responses, tools)
- `app/main.py` — FastAPI entrypoint and API endpoints
- `app/webhook.py` — Telegram webhook setup
- `static/json/tower.json` — Building and community data for Q&A
- `supabase/` — Supabase config and related files
- `pyproject.toml` — Project dependencies and metadata
- `startup.sh` — Local startup script
- `Dockerfile` — Container build instructions

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

- Open an [issue](https://github.com/frontiertower/towerbot/issues) for bugs, questions, or feature requests.
- Join our Telegram group (link coming soon).
- See the resources below for tech-specific help.

---

## 🩺 Health Check

- `GET /health`: Returns API status and message.
- `POST /telegram`: Receives Telegram webhook updates.

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
