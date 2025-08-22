<p align="center">
  <img src="static/images/bot.png" alt="TowerBot Logo" width="200"/>
</p>

[![Project Status](https://img.shields.io/badge/status-active-brightgreen)](https://github.com/frontiertower/towerbot)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

TowerBot is an open source, AI-powered Telegram assistant for Frontier Tower citizens. It answers questions, provides insights, and leverages persistent memory, semantic search, and a temporal knowledge graph to empower our Telegram Channel.

**This project is licensed under the [MIT License](LICENSE) and is free for both commercial and non-commercial use.**

---

## ✨ What is TowerBot?

TowerBot connects your Telegram group to powerful AI and community data. It can answer questions, summarize information, and provide analytics—all with persistent memory and semantic/graph search. It also provides detailed information about the building, events, and community using structured data.

---

## 👥 Who is this for?

- Frontier citizens (or similar communities)
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
- **PostgreSQL** (vector storage and memory)
- **Neo4j** (graph database)
- **Graphiti** (temporal knowledge graph)
- **APScheduler** (scheduled jobs)
- **LangChain, LangGraph, LangMem** (advanced LLM/graph features)
- **LangSmith** (LLM observability and tracing)
- **Pydantic** (settings and validation)
- **psycopg** (async Postgres connection pool)
- **pytest** (testing framework with async support)
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

## 🔗 Dynamic Ontology System

TowerBot implements a sophisticated ontology management system that automatically generates type definitions and relationship mappings from schema definitions. This eliminates hardcoded mappings and ensures compile-time safety as your knowledge graph evolves.

### How It Works

**1. Schema-First Design** (`app/schemas/ontology.py`)

- Entity types (User, Project, Event, etc.) defined as Pydantic models
- Relationship types (Sent, WorksOn, Attends, etc.) with metadata
- Each relationship specifies valid source and target entity types

**2. Automated Code Generation** (`scripts/generate_enums.py`)

- Extracts entity and relationship types from ontology definitions
- Generates `NodeTypeEnum` and `EdgeTypeEnum` automatically
- Creates `EDGE_TYPE_MAP` with valid relationship mappings
- Ensures zero drift between schema and application code

**3. Dynamic Type System** (`app/schemas/tools.py`)

- Search schemas accept both enum values and string literals
- New ontology types work immediately without code changes
- Maintains backward compatibility with existing functionality

### Adding New Types

To add new entity or relationship types:

1. **Define in Ontology** (`app/schemas/ontology.py`):

```python
class NewEntity(BaseModel):
    """A new entity type."""
    title: str

    class Config:
        label = "NewEntity"

class NewRelationship(BaseModel):
    """A new relationship type."""
    class Config:
        label = "NEW_RELATIONSHIP"
        source_types = ["User"]
        target_types = ["NewEntity"]
```

2. **Regenerate Types**:

```bash
python scripts/generate_enums.py
```

3. **Restart Application** - new types are automatically available

### Benefits

- **Zero Maintenance**: Relationship mappings update automatically
- **Compile-Time Safety**: Invalid relationships caught during generation
- **No Breaking Changes**: Existing functionality preserved
- **Future-Proof**: Schema evolution doesn't require code changes
- **Single Source of Truth**: Ontology defines both schemas and mappings

This system ensures your knowledge graph schema and application code stay perfectly synchronized as your community data model evolves.

---

## 🚀 Features

- **AI Q&A:** `/ask <question>` in Telegram, get instant, context-aware answers
- **Community Connections:** `/connect <interest>` to find people, projects, or resources
- **Supply Requests:** `/request <item>` to create supply requests through BerlinHouse API
- **Direct Messages:** Private conversations with memory agent for personalized interactions
- **Dynamic Agent System:** Specialized AI agents for different tasks with configurable tools
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
- **Multi-Layered Authentication:** Advanced three-tier authentication system including Soulink
- **User Validation:** Validates user membership before allowing private conversations
- **Automatic Group Management:** Bot automatically leaves unauthorized groups
- **Soulink Social Proximity:** Optional authentication based on shared group memberships

---

## 🗨️ Command Usage

TowerBot responds to the following commands in your Telegram group and handles direct messages in private chats:

### Commands (Group Chats)

- `/ask <question>` — Get answers to questions about the building, community, or general topics.  
  _Example:_ `/ask what's the wifi password?`
- `/connect <interest>` — Find people, projects, or resources related to a topic.  
  _Example:_ `/connect who can help me learn more about biotech?`
- `/request <item>` — Create supply requests for community resources and materials.  
  _Example:_ `/request office supplies for the co-working space`
- `/start` — Get an introduction message with bot capabilities

### Direct Messages (Private Chats)

- **Conversational AI:** Send any message directly to the bot for personalized responses
- **Memory Agent:** Uses specialized memory tools for context-aware conversations
- **Full Authentication:** Requires community membership validation
- **Persistent Context:** Maintains conversation history across sessions

### Available Tools

**Command Agents (Ask, Connect, Request):**

- **Tower Information:** Access building details, amenities, and floor plans
- **Calendar Events:** Get upcoming events from the community calendar
- **Community Search:** Find connections and relationships in the community graph
- **Supply Requests:** Create and manage supply requests through BerlinHouse API
- **Memory Management:** Persistent conversation memory for better context

**Memory Agent (Direct Messages):**

- **Memory Management:** Store and retrieve conversation context
- **Memory Search:** Search through previous conversations and interactions
- **Conversational AI:** Natural language processing for personalized responses

### Message Processing

- **Group Messages:** All messages processed for entity extraction and graph building
- **Private Messages:** Direct processing with memory agent for conversational interactions
- **Session Management:** Conversation continuity across interactions
- **Authentication:** Full three-tier validation for all private conversations

If you use a command without context, TowerBot will prompt you for more information with an example. Commands must include context in the initial message - no reply-based continuation.

---

## 🔗 Graph API

TowerBot provides a RESTful API endpoint for querying the temporal knowledge graph. This endpoint allows external applications to access community insights and relationships stored in the graph database.

### Graph Query Endpoint

**POST** `/api/v1/graph/query`

Query the temporal knowledge graph using natural language queries.

#### Authentication

The graph endpoint requires API key authentication via Bearer token:

```bash
curl -X POST "https://your-server.com/api/v1/graph/query" \
  -H "Authorization: Bearer your-api-key" \
  -H "Content-Type: application/json" \
  -d '{"query": "What relationships exist between users and projects?"}'
```

#### API Key Management

1. **Database Setup**: API keys are stored in the `keys` table in PostgreSQL:
   ```sql
   CREATE TABLE keys (
     id SERIAL PRIMARY KEY,
     key VARCHAR(255) UNIQUE NOT NULL,
     name VARCHAR(255),
     created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
     disabled BOOLEAN DEFAULT FALSE
   );
   ```

2. **Key Creation**: Insert API keys directly into the database:
   ```sql
   INSERT INTO keys (key, name) VALUES ('your-secure-api-key', 'External App');
   ```

3. **Key Validation**: The endpoint validates keys against the database on each request

#### Request Format

```json
{
  "query": "Find all connections related to biotech projects"
}
```

#### Response Format

```json
{
  "results": [
    {
      "uuid": "abc-123",
      "name": "WORKS_ON",
      "fact": "John works on the biotech project",
      "created_at": "2025-07-25T10:30:00Z",
      "source_node_uuid": "user-uuid",
      "target_node_uuid": "project-uuid",
      "episodes": ["episode-uuid"],
      "valid_at": "2025-07-20T15:00:00Z"
    }
  ]
}
```

#### Security Features

- **Bearer Token Authentication**: Secure API key validation
- **Database Integration**: Keys validated against PostgreSQL `keys` table
- **Filtered Responses**: Internal attributes (embeddings) removed from responses
- **Error Handling**: Proper HTTP status codes (401, 403, 500)

#### Error Responses

- **401 Unauthorized**: Missing or malformed Bearer token
- **403 Forbidden**: Invalid API key
- **500 Internal Server Error**: Database connection or query processing error

---

## 🔐 Authentication & Security

TowerBot implements a comprehensive three-tier authentication system to ensure secure access control for both commands and direct messages:

### Authentication Layers

1. **Group Membership Validation**

   - Users must be members of groups specified in `GROUP_ID` or `ALLOWED_GROUP_IDS`
   - Bot automatically leaves unauthorized groups
   - Supports multiple allowed groups for community expansion

2. **Soulink Social Proximity Authentication** (Optional)

   - A "soul connection" authentication mechanism based on social proximity
   - Requires users to share at least one Telegram group with the designated admin
   - Creates dynamic trust relationships based on social connections

3. **BerlinHouse API Validation**
   - Verifies users are active community members
   - Integrates with community management systems
   - Prevents access from non-community members

### Authentication Flow

- **Commands:** Full three-tier authentication for all bot commands
- **Direct Messages:** Complete authentication before allowing private conversations
- **Group Messages:** Group-level validation for knowledge graph processing

### Soulink: How It Works

Soulink is TowerBot's authentication layer that creates trust based on shared group memberships:

```mermaid
graph TD
    User[User Requests Access] --> Check1[Check Group Membership]
    Check1 --> Check2[Check Soulink if Enabled]
    Check2 --> GetGroups[Get User Groups]
    GetGroups --> GetAdminGroups[Get Admin Groups]
    GetAdminGroups --> Compare[Find Shared Groups]
    Compare --> Shared{Any Shared Groups?}
    Shared -->|Yes| Check3[Check BerlinHouse API]
    Shared -->|No| Deny[Deny Access]
    Check3 --> Allow[Allow Access]
```

**Soulink Benefits:**

- **Social Validation:** Ensures users have genuine connection to admin
- **Dynamic Trust:** Access adjusts automatically as group memberships change
- **Multi-Community Support:** Works across different communities you manage
- **Scalable Security:** No need to hardcode every allowed user

**Soulink Configuration:**

```env
SOULINK_ENABLED=true
SOULINK_ADMIN_ID=123456789  # Your Telegram user ID
```

**Soulink Use Cases:**

- Community gatekeeping with social validation
- Multi-community bot deployment
- Dynamic access control based on relationships
- Preventing unauthorized access through social proximity

### Security Features

- **Automatic Group Management:** Bot leaves unauthorized groups immediately
- **Robust Error Handling:** Handles API failures gracefully
- **Comprehensive Logging:** All authentication attempts logged for audit
- **Input Validation:** Configuration values validated at startup
- **Rate Limiting Detection:** Monitors and handles API rate limits

---

## 🏗️ Architecture Overview

```mermaid
graph TD;
  TG["Telegram Group"] -->|/ask, /connect, /request| BOT["TowerBot (python-telegram-bot)"]
  PM["Private Messages"] -->|Direct Messages| BOT
  BOT --> API["FastAPI Backend"]
  API --> AUTH["AuthService<br/>API Key Validation"]
  API --> AI["Dynamic AI Agents"]
  AI --> AG["Ask Agent<br/>QA Tools + Memory"]
  AI --> CN["Connect Agent<br/>Graph Tools + Memory"]
  AI --> RQ["Request Agent<br/>Supply Request Tools"]
  AI --> MM["Memory Agent<br/>All Tools + Memory"]
  API --> DB["PostgreSQL (Vectors)"]
  API --> GRAPH["Neo4j (Graph DB) + Graphiti"]
  API --> Health["/health Endpoint"]
  API --> Webhook["/telegram Endpoint"]
  API --> GraphAPI["/api/v1/graph/query Endpoint"]
```

**Agent System:**

- **Dynamic Configuration:** Easy addition of new agent types via AgentConfig
- **Specialized Tools:** Each agent has access to relevant tools for its purpose
- **Memory Integration:** All agents share memory capabilities for context retention
- **Session Management:** Conversation continuity across all interaction types

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
GROUP_ID=your-telegram-group-id      # Target group ID (negative number)
ALLOWED_GROUP_IDS=group1,group2      # Optional: Additional allowed groups (comma-separated)

# Soulink Authentication (Optional)
SOULINK_ENABLED=false                # Enable Soulink social proximity authentication
SOULINK_ADMIN_ID=your-telegram-user-id # Admin user ID for Soulink validation

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
BERLINHOUSE_API_KEY=your-api-key     # BerlinHouse API key for community data and supply requests
BERLINHOUSE_BASE_URL=https://api.berlinhouse.com  # BerlinHouse API base URL

# Observability (Optional)
LANGSMITH_API_KEY=your-langsmith-api-key      # LangSmith API key for tracing
LANGSMITH_PROJECT=your-langsmith-project      # LangSmith project name
LANGSMITH_TRACING=true                        # Enable LangSmith tracing
```

### 4. Run Locally

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

### 5. Add to Telegram Group

- Add your bot to a Telegram group.
- Use `/ask` or `/connect` to interact with the bot.
- Send direct messages in private chats for conversational AI interactions.

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

### Code Quality & Testing

```bash
# Run the complete test suite
uv run pytest tests/ -v

# Run tests with coverage reporting
uv run pytest tests/ --cov=app --cov-report=html

# Check Python syntax
python -m py_compile app/**/*.py

# The application includes comprehensive logging for debugging:
# - DEBUG: Detailed tracing and function calls
# - INFO: Important application events
# - ERROR: Exception handling with context
```

### Testing

TowerBot includes a comprehensive test suite with **91 unit tests** covering all core functionality:

```bash
# Run the complete test suite
uv run pytest tests/ -v

# Run tests with coverage
uv run pytest tests/ --cov=app --cov-report=html

# Run specific test modules
uv run pytest tests/test_ai_service.py -v
uv run pytest tests/test_graph_service.py -v
uv run pytest tests/test_config.py -v
```

**Test Coverage:**

- ✅ **AiService** (10 tests) - AI agent functionality, session management, command handling
- ✅ **GraphService** (16 tests) - Knowledge graph operations, message processing, community building
- ✅ **Configuration** (8 tests) - Settings validation, environment variables, authentication config
- ✅ **Tools** (17 tests) - External API integrations, graph search, data access tools
- ✅ **Main Application** (13 tests) - FastAPI endpoints, webhook handling, health checks
- ✅ **Schemas** (27 tests) - Data models, ontology definitions, enum mappings

**Test Infrastructure:**

- **pytest** + **pytest-asyncio** framework with async/await support
- Comprehensive fixtures for mocking dependencies
- Environment isolation for configuration tests
- Proper error handling and edge case testing

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
│   ├── schemas/
│   │   ├── ontology.py        # Graph database schema and entity definitions
│   │   ├── generated_enums.py # Auto-generated enums and relationship mappings
│   │   ├── responses.py       # Pydantic models for AI responses
│   │   └── tools.py           # Tool parameter schemas with dynamic enum support
│   ├── services/
│   │   ├── ai.py              # Dynamic AI service with configurable agents
│   │   ├── auth.py            # Authentication service for API key validation
│   │   └── graph.py           # Neo4j graph service with Graphiti
│   ├── main.py                # FastAPI application and endpoints
│   └── webhook.py             # Telegram webhook configuration
├── tests/
│   ├── conftest.py            # Test configuration and fixtures
│   ├── test_ai_service.py     # AI service and agent tests
│   ├── test_graph_service.py  # Graph database operation tests
│   ├── test_config.py         # Configuration and settings tests
│   ├── test_tools.py          # External API and tool integration tests
│   ├── test_main.py           # FastAPI application tests
│   └── test_schemas.py        # Schema definition and validation tests
├── scripts/
│   └── generate_enums.py      # Auto-generates enums from ontology definitions
├── static/
│   └── data/
│       └── tower.json         # Building and community data
├── supabase/
│   └── config.toml           # Database configuration
├── pyproject.toml            # Project dependencies and metadata
├── pytest.ini               # Test configuration
├── startup.sh               # Local development startup script
├── Dockerfile              # Container build instructions
└── uv.lock                # Dependency lock file
```

**Key Components:**

- **AI Service:** Dynamic agent system with specialized tools and memory integration
- **Graph Service:** Neo4j knowledge graph operations with Graphiti temporal processing
- **Data Schemas:** Structured schemas for entities, responses, and tools with dynamic enum generation
- **API Layer:** FastAPI endpoints for health checks and webhook handling
- **Configuration:** Environment-based settings with Pydantic validation
- **Testing Suite:** Comprehensive unit tests with 91 test cases covering all modules
- **Logging:** Comprehensive structured logging across all modules

**Agent Architecture:**

- **AgentConfig:** Configuration class for dynamic agent creation
- **Specialized Agents:** Ask, Connect, and Memory agents
- **Tool Integration:** Each agent has access to relevant tools and memory
- **Session Management:** Conversation continuity across all interaction types

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
- `POST /api/v1/graph/query`: Query the knowledge graph (requires API key authentication)

### Logging & Monitoring

- **Structured Logging:** Function names, line numbers, and context
- **Error Tracking:** Comprehensive exception logging with stack traces
- **Performance Monitoring:** Request/response timing and processing logs
- **Service Health:** Connection status for all external services
- **Log Levels:** Configurable DEBUG, INFO, WARNING, ERROR levels
- **LangSmith Integration:** LLM observability and tracing for AI operations

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

### LangSmith Observability

TowerBot integrates with LangSmith for comprehensive LLM observability and tracing:

- **Agent Tracing:** Complete visibility into AI agent decision-making processes
- **Performance Metrics:** Track response times, token usage, and model performance
- **Error Debugging:** Detailed traces for troubleshooting AI operations
- **Conversation Analytics:** Track user interactions and conversation patterns
- **Tool Usage Monitoring:** Monitor how agents use tools and external APIs

**Configuration:**

```env
LANGSMITH_API_KEY=your-langsmith-api-key
LANGSMITH_PROJECT=your-project-name
LANGSMITH_TRACING=true
```

---

## 📚 Resources

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [python-telegram-bot](https://python-telegram-bot.org/)
- [PostgreSQL Documentation](https://www.postgresql.org/docs/)
- [LangChain](https://python.langchain.com/)
- [LangSmith](https://docs.smith.langchain.com/)
- [Azure OpenAI](https://learn.microsoft.com/en-us/azure/ai-services/openai/)
- [Neo4j](https://neo4j.com/docs/)
- [Graphiti](https://github.com/getzep/graphiti)
- [pytest Documentation](https://docs.pytest.org/)
- [uv (Python package manager)](https://github.com/astral-sh/uv)

---

## 📝 License

TowerBot is open source and licensed under the [MIT License](LICENSE).

You are free to use, modify, and distribute this software for commercial and non-commercial purposes, subject to the terms of the MIT License.


# Instructions from debug session
Of course\! Based on the transcript, here is a detailed setup guide for the automation bot package, covering all the prerequisites, configurations, code modifications, and troubleshooting steps you discussed.

## **Bot Setup and Configuration Guide**

This guide will walk you through setting up the bot on your local machine. We'll cover everything from installing dependencies and setting up the database to configuring environment variables and running the application.

-----

### **1. Prerequisites**

Before you begin, make sure you have the following tools installed on your system:

  * **UV**: A fast Python package installer and resolver.
  * **Docker**: For running a local Postgres database instance. Make sure the Docker daemon is running.
  * **Ngrok**: A tool to expose your local server to the internet, which is necessary for Telegram webhooks. You'll need a free account to claim a static domain.

You can install `ngrok` using Homebrew if you're on a Mac:

```bash
brew install ngrok
```

-----

### **2. Initial Project Setup**

1.  **Clone the Repository**: Start by getting the code onto your local machine.
2.  **Install Dependencies**: Navigate to the root directory of the project in your terminal and run the following command to install all the required Python packages:
    ```bash
    uv sync
    ```

-----

### **3. Environment Configuration (`.env` file)**

Create a file named `.env` in the root directory of the project. This file will hold all your secret keys and configuration variables.

#### **Telegram Setup**

1.  **Create a Bot**: Talk to the **BotFather** on Telegram to create a new bot. It will give you a unique `TELEGRAM_BOT_TOKEN`.
2.  **Create a Test Group**: Create a new Telegram group for testing.
3.  **Get Group ID**: To find your group's ID, you can temporarily add a bot like `@myidbot` to the group, which will post the group's ID. It will be a negative number.
4.  **Add Variables to `.env`**:
    ```env
    # From BotFather
    TELEGRAM_BOT_TOKEN="your_telegram_bot_token_here"

    # The ID of your test group (must be a negative number)
    ALLOWED_GROUP_IDS="your_group_id_here"

    # Your personal Telegram user ID for admin privileges
    ADMIN_USER_IDS="your_personal_telegram_id"
    ```

#### **OpenAI and LangSmith Setup**

1.  **Get Keys**: You'll need an API key from **OpenAI** and another from **LangSmith** (for tracing and observability).
2.  **Add Variables to `.env`**:
    ```env
    # Your OpenAI API Key
    OPENAI_API_KEY="sk-..."

    # Your LangSmith API Key for tracing
    LANGSMITH_API_KEY="ls__..."
    LANGCHAIN_TRACING_V2="true"
    LANGCHAIN_PROJECT="Default" # Or any project name you prefer
    ```

### 2. Database Setup

#### PostgreSQL with pgvector

TowerBot requires PostgreSQL with the pgvector extension for vector embeddings and memory storage.

**Setup Commands:**

```bash
# Stop and remove any existing PostgreSQL container (if needed)
docker stop postgres-towerbot-2 && docker rm postgres-towerbot-2

# Run PostgreSQL with pgvector extension
docker run --name postgres-towerbot-2 \
  -e POSTGRES_PASSWORD=postgres \
  -p 5436:5432 \
  -d pgvector/pgvector:pg17

# Wait for container to start
sleep 3

# Create the towerbot database
PGPASSWORD=postgres psql -h localhost -p 5436 -U postgres \
  -c "CREATE DATABASE towerbot;"

# Enable pgvector extension for vector embeddings
PGPASSWORD=postgres psql -h localhost -p 5436 -U postgres -d towerbot \
  -c "CREATE EXTENSION IF NOT EXISTS vector;"

# Verify pgvector installation
PGPASSWORD=postgres psql -h localhost -p 5436 -U postgres -d towerbot \
  -c "SELECT * FROM pg_extension WHERE extname = 'vector';"
```

**Connection String for .env:**
```
POSTGRES_CONN_STRING=postgresql://postgres:postgres@localhost:5436/towerbot
```



#### **Ngrok Webhook Setup**

1.  **Claim a Static Domain**: Log in to your `ngrok` dashboard and claim a free static domain. It will look something like `your-choice-123.ngrok-free.app`.
2.  **Add Webhook URL to `.env`**:
    ```env
    # Your static ngrok domain
    WEBHOOK_URL="https://your-choice-123.ngrok-free.app"
    ```

-----

### **5. Running the Application**

1.  **Start Ngrok**: Open a new terminal window and run the following command to start tunneling your local port `3000` (the default for the app) to your public `ngrok` URL.

    ```bash
    ngrok http --domain=your-choice-123.ngrok-free.app 3000
    ```

    Leave this terminal window running.

2.  **Start the Bot Server**: In another terminal window, navigate to the project's root directory and run the startup script:

    ```bash
    ./startup.sh
    ```

3.  **Add Bot to Group as Admin**:

      * Go to your test Telegram group.
      * Add the bot you created as a member.
      * Promote the bot to an **admin**. This is a critical step, as the bot needs admin permissions to read messages in the group.

The server should now be running, connected to the database, and receiving webhooks from Telegram via `ngrok`.

-----

### **6. Final Testing and Troubleshooting**

  * **Initial Interaction**: Send a message (e.g., "Hello") in your test group. You should see activity in the terminal where `./startup.sh` is running, indicating that the bot has processed the message and added you as a user node to the graph.
  * **Direct Message**: Once you've sent a message in the group, you should be whitelisted and can now message the bot directly. Try sending it a query like, "Connect me with someone interested in AI agents."
  * **"Bad Gateway" Error**: If you see a `502 Bad Gateway` error in the `ngrok` terminal, it likely means the port number in your `ngrok` command doesn't match the port the application server is running on. The script uses port `3000`, so make sure your `ngrok` command also specifies port `3000`.
  * **Authentication Issues**: If the bot tells you you're not authorized even after messaging the group, ensure the bot was successfully promoted to an admin in the group. Without admin rights, it cannot see your messages and therefore cannot add you to the knowledge graph.