# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Getting Started - Context Awareness

**IMPORTANT**: At the beginning of every conversation, check the `Documentation/tasks/` folder to understand current project context:

- `Documentation/tasks/in-progress/`: Active tasks being worked on - review these first to understand what's currently happening
- `Documentation/tasks/planned/`: Upcoming tasks that have been planned. No need to look at this unless asked.
- `Documentation/tasks/done/`: Completed tasks for reference. No need to look at this unless asked.

This task folder system helps maintain context across conversations and ensures continuity of work.

## Project Overview

Memento is an MCP (Model Context Protocol) server that provides persistent memory capabilities for LLMs. It uses Python with FastMCP framework and Neo4j for graph-based vector storage, enabling semantic search and memory relationships.

## Architecture

The system follows a layered architecture:

- **MCP Server Layer**: FastMCP-based server exposing memory tools to LLM clients
- **Memory Service Layer**: Core business logic for memory operations (GraphMemoryService)
- **Repository Layer**: Neo4j database operations (Neo4jRepository)
- **Provider Layer**: Pluggable LLM and embedding providers (OpenAI, Ollama, local transformers)

Key components:
- `MCPServer`: Main server entry point with tool registration
- `GraphMemoryService`: Core memory operations with semantic search
- `Neo4jRepository`: Database abstraction for Neo4j operations
- `IEmbeddingProvider`/`ILLMProvider`: Interfaces for pluggable AI providers
- `EmbeddingFactory`/`LLMFactory`: Factory pattern for provider creation

## Memory Operations

The system exposes four main MCP tools:

1. **store_memory**: Store new memories, returns similar memories for conflict detection
2. **supersede_memory**: Mark old memories as outdated when new information conflicts
3. **search_memories**: Semantic search across memories (excludes superseded)
4. **list_recent_memories**: Get recently created memories

Important: Always check store_memory responses for similar memories and handle conflicts by calling supersede_memory when appropriate.

## Development Commands

Since this is an early-stage project with minimal implementation, there are currently no standardized build/test commands. The project uses Python virtual environment (`.venv/` directory present).

Expected future commands:
- `pytest` for running tests
- `python -m memento.mcp_server` for running the MCP server
- Standard Python development workflow

## Key Design Patterns

- **Factory Pattern**: For creating embedding and LLM providers
- **Repository Pattern**: For database operations abstraction
- **Interface Segregation**: Separate interfaces for embedding vs LLM providers
- **Plugin Architecture**: Swappable providers for different AI services

## Documentation Structure

- `Documentation/mcp-tool-specification.md`: Complete MCP tool API specifications
- `Documentation/detailed-architecture.md`: Class diagrams and detailed architecture
- `Documentation/data-model.md`: Memory data structure details
- `Documentation/sample-use-cases.md`: Example usage scenarios
- `Documentation/ADR/`: Architecture Decision Records

## Important Notes

- No actual Python implementation files exist yet in `src/` - this is planning/documentation phase
- The architecture supports both local (Ollama, transformers) and cloud (OpenAI) AI providers
- Multi-tenant support planned for future via user_id isolation
- All memory operations are designed to be atomic and immediately consistent