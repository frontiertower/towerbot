# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

### Package Management
- **Install dependencies**: `uv sync`
- **Add dependency**: `uv add package-name`
- **Remove dependency**: `uv remove package-name`

### Testing
- **Run all tests**: `uv run python -m pytest tests/ -v`
- **Run specific test file**: `uv run python -m pytest tests/test_ai_service.py -v`
- **Run tests with coverage**: `uv run python -m pytest tests/ --cov=app --cov-report=html`
- **Run single test method**: `uv run python -m pytest tests/test_ai_service.py::TestAiService::test_init -v`

### Application Startup
- **Quick start**: `./startup.sh` (generates enums, starts webhook, starts FastAPI server)
- **Manual startup**:
  1. `uv run python scripts/generate_enums.py` (generate type enums from ontology)
  2. `uv run python -m app.webhook &` (start Telegram webhook in background)
  3. `uv run uvicorn app.main:app --reload --port 3000 --host 0.0.0.0` (start FastAPI server)

### Code Generation
- **Regenerate ontology enums**: `uv run python scripts/generate_enums.py`

## Architecture Overview

### Core Architecture Pattern
TowerBot uses a **multi-layered AI agent system** with **temporal knowledge graph** processing:

1. **FastAPI Application Layer** (`app/main.py`): HTTP endpoints for health checks and Telegram webhooks
2. **Telegram Bot Layer** (`app/core/lifespan.py`): Message processing and authentication
3. **AI Agent Layer** (`app/services/ai.py`): Specialized agents for different command types
4. **Knowledge Graph Layer** (`app/services/graph.py`): Graphiti-powered temporal graph operations
5. **Tools Layer** (`app/core/tools.py`): External API integrations and search capabilities

### Key Services Architecture

**AiService** (`app/services/ai.py`):
- Manages three specialized agents: Ask, Connect, Request
- Each agent has different tool access patterns
- Memory-enabled conversational agent for direct messages
- Session management with 24-hour TTL
- LangSmith integration for LLM observability

**GraphService** (`app/services/graph.py`):
- Wraps Graphiti temporal knowledge graph
- Processes Telegram messages into graph episodes
- Handles user existence validation via BerlinHouse API
- Supports community building and graph analytics

### Dynamic Ontology System

**Critical Workflow**: The ontology system requires a specific regeneration workflow:

1. **Schema Definition** (`app/schemas/ontology.py`): Define entities and relationships as Pydantic models
2. **Code Generation** (`scripts/generate_enums.py`): Extracts types and generates enums + relationship mappings
3. **Generated Types** (`app/schemas/generated_enums.py`): Auto-generated `NodeTypeEnum`, `EdgeTypeEnum`, and `EDGE_TYPE_MAP`

**When adding new ontology types**:
1. Add new Pydantic model to `app/schemas/ontology.py` with `Config.label`
2. Run `uv run python scripts/generate_enums.py` to regenerate enums
3. Restart application to pick up new types

### Authentication System

TowerBot implements **three-tier authentication**:

1. **Group Membership**: User must be in allowed Telegram groups (`GROUP_ID`, `ALLOWED_GROUP_IDS`)
2. **Soulink (Optional)**: Social proximity authentication - user must share at least one group with admin
3. **BerlinHouse API**: User must be verified community member

**Authentication Flow** (handled in `app/core/lifespan.py`):
- Commands: Full three-tier authentication
- Direct Messages: Full authentication + memory agent processing
- Group Messages: Group validation + graph processing

### Agent Tool Architecture

**Tool Distribution Pattern**:
- **Ask Agent**: `get_tower_info`, `get_calendar_events`, `get_tower_communities` + memory tools
- **Connect Agent**: `get_connections` (graph search) + memory tools  
- **Request Agent**: `create_supply_request` (BerlinHouse API) + memory tools
- **Memory Agent**: All tools + memory management for direct messages

Tools are defined in `app/core/tools.py` and use LangChain's `@tool` decorator.

### Database Architecture

**Dual Database Pattern**:
- **PostgreSQL**: Vector embeddings, conversation checkpoints, LangMem storage
- **Neo4j**: Knowledge graph via Graphiti, community analytics

**Connection Management**:
- PostgreSQL: Async connection pooling via `psycopg_pool.AsyncConnectionPool`
- Neo4j: Managed through Graphiti client initialization

### Message Processing Flow

1. **Telegram Webhook** → **FastAPI endpoint** (`/telegram`)
2. **Background processing** → **Telegram Bot handlers** (lifespan.py)
3. **Authentication check** → **Multi-tier validation**
4. **Message routing**:
   - Private chats → Memory agent with full tools
   - Commands (`/ask`, `/connect`, `/request`) → Specialized agents
   - Group messages → Graph processing (episode extraction)

### Configuration System

**Environment-based configuration** (`app/core/config.py`):
- Pydantic Settings with automatic `.env` loading
- Validation and type safety for all configuration
- Support for Soulink social proximity authentication
- Azure OpenAI, BerlinHouse API, database connection strings

### Testing Architecture

**Test Structure** (`tests/`):
- Comprehensive fixtures in `conftest.py` with mocked services
- Service-specific test files with both unit and integration tests
- AsyncIO support with `pytest-asyncio`
- 92 test cases covering all major functionality

**Key Testing Patterns**:
- Mock external APIs (BerlinHouse, Luma calendar)
- Mock LLM responses for deterministic testing
- Telegram message mocking with proper user/chat objects
- Configuration testing with environment variable isolation

## Important Implementation Notes

### Ontology Changes
Always run enum generation after modifying `app/schemas/ontology.py`. The application will fail to start if generated enums are out of sync with ontology definitions.

### Authentication Configuration
Soulink authentication is optional but powerful for community management. When `SOULINK_ENABLED=true`, users must share at least one Telegram group with the configured admin.

### Memory Management
The memory agent (direct messages) maintains user context across sessions. Sessions expire after 24 hours and are managed per-user per-command-type.

### Graph Processing
All supergroup messages are processed into graph episodes for knowledge extraction, but only after group authorization. Private messages bypass graph processing.

### API Integration
BerlinHouse API integration uses API key authentication (not JWT tokens). Supply requests are created through the `/request` command via the Request agent.