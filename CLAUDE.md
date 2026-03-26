# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Memento is an MCP (Model Context Protocol) server that provides persistent memory capabilities for LLMs. It uses Python with FastMCP framework and Neo4j for graph-based vector storage, enabling semantic search and memory relationships.

## Architecture

The system follows a layered architecture:

- **MCP Server Layer**: FastMCP-based server exposing memory tools to LLM clients
- **Memory Service Layer**: Core business logic for memory operations (MemoryService)
- **Repository Layer**: Neo4j database operations (Neo4jRepository)
- **Provider Layer**: Pluggable LLM and embedding providers (OpenAI, Ollama, local transformers)

Key components:
- `MCPServer`: Main server entry point with tool registration
- `MemoryService`: Core memory operations with semantic search
- `Neo4jRepository`: Database abstraction for Neo4j operations
- `IEmbeddingProvider`/`ILLMProvider`: Interfaces for pluggable AI providers
- `EmbeddingFactory`/`LLMFactory`: Factory pattern for provider creation


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

## Development Philosophy

**YAGNI (You Ain't Gonna Need It)**: Don't build features, methods, or abstractions until they're actually needed. If we don't have a concrete use case right now, don't implement it. This keeps the codebase lean and focused.

**KISS (Keep It Simple, Stupid)**: Always choose the simplest solution that works. Avoid over-engineering, premature optimization, and unnecessary complexity. Simple code is easier to understand, test, and maintain.

When reviewing architecture or planning tasks:
- Remove unused methods from interfaces
- Avoid building "might need later" features
- Choose simple implementations over clever ones
- Refactor to add complexity only when requirements demand it

## Working with Time-Sensitive Information

**IMPORTANT**: Always look up time-sensitive information online rather than relying on training data. Information that changes over time should be verified using web search or fetch tools.

**Always verify online:**
- Package versions (e.g., `pydantic-settings`, `sentence-transformers`)
- Framework APIs and breaking changes
- Best practices and current conventions
- Release dates and deprecation notices
- Security advisories and CVEs

**Example**: When adding a dependency, search PyPI for the latest version and release date rather than using potentially outdated training data.

## Documentation Structure

- `Documentation/mcp-tool-specification.md`: Complete MCP tool API specifications
- `Documentation/detailed-architecture.md`: Class diagrams and detailed architecture
- `Documentation/data-model.md`: Memory data structure details
- `Documentation/sample-use-cases.md`: Example usage scenarios
- `Documentation/ADR/`: Architecture Decision Records

## Active Technologies
- Python 3.10+ (per pyproject.toml `requires-python = ">=3.10"`) + FastMCP 2.11+, Neo4j driver 5.28+, sentence-transformers 5.1+, Pydantic 2.11+ (001-baseline-rag)
- Neo4j (graph database with vector index capabilities) (001-baseline-rag)

## Recent Changes
- 001-baseline-rag: Added Python 3.10+ (per pyproject.toml `requires-python = ">=3.10"`) + FastMCP 2.11+, Neo4j driver 5.28+, sentence-transformers 5.1+, Pydantic 2.11+
