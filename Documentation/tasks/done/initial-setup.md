# Initial Setup - Memento Project

## Project Structure

### Complete Folder Structure
```
memento/
├── Documentation/           # Project documentation
│   ├── ADR/                # Architecture Decision Records
│   ├── tasks/              # Task tracking
│   │   └── in-progress/    # Current work
│   └── sample-use-cases.md # Use case examples
│
├── src/                     # Source code
│   ├── __init__.py
│   │
│   ├── embeddings/          # Embedding providers
│   │   ├── __init__.py
│   │   ├── base.py         # Abstract base class
│   │   └── local.py        # Local sentence-transformers
│   │
│   ├── graph/               # Graph database layer
│   │   ├── __init__.py
│   │   ├── base.py         # Repository interface
│   │   └── neo4j.py        # Neo4j implementation
│   │
│   ├── memory/              # Core memory logic
│   │   ├── __init__.py
│   │   ├── models.py       # Data models (Memory, User)
│   │   └── service.py      # Business logic
│   │
│   ├── llms/                # LLM providers (future)
│   │   ├── __init__.py
│   │   └── base.py         # LLM interface
│   │
│   ├── mcp/                 # MCP server (future)
│   │   ├── __init__.py
│   │   └── server.py       # FastMCP server
│   │
│   └── utils/               # Utilities
│       ├── __init__.py
│       └── config.py       # Configuration management
│
├── tests/                   # Test files
│   ├── __init__.py
│   ├── conftest.py         # Pytest fixtures
│   ├── test_embeddings/    # Embedding tests
│   │   ├── __init__.py
│   │   └── test_local.py
│   ├── test_graph/         # Graph tests
│   │   ├── __init__.py
│   │   └── test_neo4j.py
│   └── test_memory/        # Memory service tests
│       ├── __init__.py
│       └── test_service.py
│
├── .env                    # Local environment variables (gitignored)
├── .env.example            # Example environment variables
├── .gitignore              # Git ignore file
├── pyproject.toml          # Modern Python project config
├── README.md               # Project overview
└── requirements.txt        # Pinned dependencies (generated)
```

## Architecture Overview

This project follows a **modular, tool-based architecture** where each component is independent and composable:

- **`embeddings/`**: Handles text → vector conversion
- **`graph/`**: Manages Neo4j storage and retrieval
- **`memory/`**: Contains business logic that orchestrates the tools
- **`llms/`**: (Future) LLM providers for advanced features
- **`mcp/`**: (Future) MCP server for Claude/LLM integration
- **`utils/`**: Shared utilities and configuration

## Setup Instructions

### 1. Prerequisites

- Python 3.9+
- Neo4j Aura account (free tier)
- PyCharm or VS Code (recommended)

### 2. Environment Setup

```bash
# Clone the repository
git clone <your-repo-url>
cd memento

# PyCharm will create venv automatically, or:
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install in editable mode with dev dependencies
pip install -e ".[dev]"
```

### 3. Configuration

Copy the example environment file and add your credentials:

```bash
cp .env.example .env
```

Edit `.env` with your Neo4j Aura credentials:
```bash
# Neo4j Aura Connection
NEO4J_URI=neo4j+s://xxxxx.databases.neo4j.io
NEO4J_USER=neo4j
NEO4J_PASSWORD=your-password-here

# Embedding Model (local, no API costs)
EMBEDDING_MODEL=all-MiniLM-L6-v2
```

### 4. Run Tests

```bash
# Test everything
pytest

# Test specific module
pytest tests/test_embeddings/

# With coverage
pytest --cov=src
```

## File Contents

### pyproject.toml
```toml
[build-system]
requires = ["setuptools>=61.0", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "memento"
version = "0.1.0"
description = "Long-term memory for LLMs via MCP"
readme = "README.md"
requires-python = ">=3.9"
dependencies = [
    "fastmcp>=0.3.0",
    "neo4j>=5.0.0",
    "sentence-transformers>=2.2.0",
    "python-dotenv>=1.0.0",
    "pydantic>=2.0.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=7.0.0",
    "pytest-asyncio>=0.21.0",
    "pytest-cov>=4.0.0",
]

[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = "test_*.py"
addopts = "-v --color=yes"
```

### .env.example
```bash
# Neo4j Aura Connection (cloud free tier)
NEO4J_URI=neo4j+s://xxxxx.databases.neo4j.io
NEO4J_USER=neo4j
NEO4J_PASSWORD=your-password-here

# Embedding Model (local, no API costs)
EMBEDDING_MODEL=all-MiniLM-L6-v2  # 384 dimensions, fast
```

### .gitignore
```
# Python
__pycache__/
*.py[cod]
*$py.class
.Python
venv/
.env

# Testing
.pytest_cache/
.coverage
htmlcov/
*.cover

# IDE
.vscode/
.idea/
*.swp
.DS_Store

# Project specific
data/
*.db
*.log
```

## Development Workflow

### Phase 1: Core Components (Current)
1. ✅ Project structure setup
2. ⬜ Implement local embeddings provider
3. ⬜ Implement Neo4j graph repository
4. ⬜ Create memory service with basic operations

### Phase 2: MCP Integration
1. ⬜ Build FastMCP server
2. ⬜ Define MCP tools (remember, search, list_recent)
3. ⬜ Test with Claude Desktop

### Phase 3: Advanced Features
1. ⬜ Add LLM providers for entity extraction
2. ⬜ Implement Graph RAG traversal
3. ⬜ Add memory importance and decay

## Testing Strategy

- **Unit Tests**: Test each component in isolation
- **Integration Tests**: Test component interactions
- **Test-Driven Development**: Write tests first, then implementation

## Next Steps

1. Start with `src/embeddings/local.py` - implement and test
2. Move to `src/graph/neo4j.py` - connect to Neo4j Aura
3. Build `src/memory/service.py` - orchestrate the components
4. Finally, create the MCP server in `src/mcp/server.py`

## Notes

- Keep components independent and composable
- Use abstract base classes for all providers
- Follow TDD - write tests first
- Document as you go
