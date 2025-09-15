# Memento: Long-Term Memory for LLMs

## Overview
Memento provides Large Language Models with persistent, intelligent memory capabilities through the Model Context Protocol (MCP). It enables LLMs to remember facts across conversations, update their knowledge over time, and retrieve relevant information when needed.

## 🎯 Vision
Transform stateless LLM interactions into continuous, personalized relationships by giving AI assistants the ability to learn and remember over time.

## 🏗️ High-Level Architecture

```mermaid
graph TB
    User[User] -->|Conversation| Client[LLM Client<br/>Claude/GPT/etc]
    Client -->|MCP Protocol| MCP[Memento MCP Server<br/>FastMCP + OAuth]
    
    MCP -->|Memory Operations| LC[LangChain Orchestration Layer]
    
    LC -->|Graph Operations| Neo4j[(Neo4j<br/>Graph + Vector Store)]
    LC -->|Entity Extraction| LLM[LLM]
    
    MCP -->|User Management| MongoDB[(MongoDB<br/>User Auth & Preferences)]
    
    subgraph "Memento Core"
        MCP
        LC
        LLM
    end
    
    subgraph "Data Layer"
        Neo4j
        MongoDB
    end
    
    style User fill:#e1f5fe
    style Client fill:#fff3e0
    style MCP fill:#f3e5f5
    style LC fill:#e8f5e9
    style Neo4j fill:#fff9c4
    style MongoDB fill:#ffebee
    style LLM fill:#e0f2f1
```

## 🚀 Quick Start

TODO

## 📁 Project Structure

```
memento/
├── Documentation/          # Project documentation
├── src/
│   ├── mcp-server/        # MCP server implementation
│   ├── memory-store/      # Vector DB abstraction
│   └── utils/             # Shared utilities
└── tests/                 # Test suites
```

## 🎮 Core Features

### Current (MVP)
- ✅ Store factual memories with metadata
- ✅ Semantic search across all memories
- ✅ List recent memories
- ✅ Basic relevance scoring

### Roadmap
- 🔄 Memory updates and contradiction resolution
- 🏷️ Memory categorization and namespaces  
- 🧠 Memory synthesis and insight generation
- 📊 Memory lifecycle management (importance decay, consolidation)
- 🔐 Multi-tenant support

## 📚 Documentation

- [Sample Use Cases](Documentation/sample-use-cases.md) - See Memento in action
- [MCP Tool Specification](Documentation/mcp-tool-specification.md) - API contract
- [Data Model](Documentation/data-model.md) - Memory structure details
- [Architecture Decisions](Documentation/ADR/) - Key design rationale

## 🛠️ Technology Stack

- **MCP Server**: Node.js + TypeScript
- **Vector Database**: ChromaDB (swappable)
- **Embeddings**: OpenAI Ada-002 (swappable)
- **Testing**: Jest + MCP test harness

## 📝 License

MIT

## 🤝 Contributing

This is an early-stage project. Contributions and feedback welcome!
