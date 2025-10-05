# [MCP] Build FastMCP Server

**Epic:** MCP Integration (Phase 2)

## Description

Implement the FastMCP server that exposes Memento's memory capabilities to LLM clients like Claude Desktop. This is the main entry point for the MCP protocol integration.

## Goal

Create a production-ready MCP server that:
- Initializes with proper configuration
- Connects to the memory service layer
- Provides a clean foundation for MCP tools
- Handles server lifecycle properly

## Acceptance Criteria

- [ ] `src/mcp/server.py` implements `MCPServer` class using FastMCP
- [ ] Server initialization loads configuration from environment
- [ ] Creates embedding provider via factory pattern
- [ ] Creates Neo4j repository instance
- [ ] Creates memory service with injected dependencies
- [ ] Implements `start()` method to run the server
- [ ] Implements `stop()` method for graceful shutdown
- [ ] Proper error handling and logging
- [ ] Configuration validation on startup
- [ ] Tests for server initialization
- [ ] Documentation for running the server

## Technical Details

**Server Structure:**
```python
from fastmcp import FastMCP

class MCPServer:
    def __init__(self):
        self.mcp = FastMCP("Memento Memory Server")
        self.config = load_config()
        self.embedding_provider = EmbeddingFactory.create(self.config)
        self.repository = Neo4jRepository(self.config)
        self.memory_service = GraphMemoryService(
            embedding_provider=self.embedding_provider,
            repository=self.repository
        )

    def register_tools(self):
        # Tools will be added in next story
        pass

    def start(self):
        self.register_tools()
        self.mcp.run()

    def stop(self):
        # Cleanup resources
        self.repository.close()
```

**Configuration:**
- Read from `.env` file using `python-dotenv`
- Validate required environment variables
- Support different embedding providers (local/OpenAI)
- Neo4j connection settings

**Factory Pattern:**
- Create `EmbeddingFactory` in `src/embeddings/__init__.py`
- Support multiple provider types based on config

**Dependencies:**
- `fastmcp>=0.3.0`
- Requires completed Core Components epic stories
- `src/utils/config.py` for configuration management

**Running the Server:**
```bash
# Development mode
python -m src.mcp.server

# Production mode (future)
memento-server --config production.env
```

## Estimated Complexity

**Medium** - Server setup and dependency wiring with proper configuration
