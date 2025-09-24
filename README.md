# Memento: Long-Term Memory for LLMs

## Overview
Memento provides Large Language Models with persistent, intelligent memory capabilities through the Model Context Protocol (MCP). It enables LLMs to remember facts across conversations, update their knowledge over time, and retrieve relevant information when needed.

## 🎯 Vision
Transform stateless LLM interactions into continuous, personalized relationships by giving AI assistants the ability to learn and remember over time.

## 🏗️ High-Level Architecture

```mermaid
graph TB
    User[User] -->|Conversation| Client[LLM Client<br/>Claude/GPT/etc]
    Client -->|MCP Protocol| MCP[Memento MCP Server<br/>FastMCP + Python]
    
    MCP -->|Memory Operations| MS[Memory Service Layer]
    
    MS -->|Direct Queries| Neo4j[(Neo4j<br/>Graph + Vector Storage)]
    MS -->|Intelligence| LLM[LLM Provider]
    MS -->|Embeddings| EMB[Embedding Provider]
    
    subgraph "Providers via Factory Pattern"
        LLM -->|Cloud| OpenAI[OpenAI API]
        LLM -->|Local| Ollama[Ollama Server]
        
        EMB -->|Cloud| OAIEmb[OpenAI Embeddings]
        EMB -->|Local| STEmb[Sentence Transformers]
        EMB -->|Local| OllamaEmb[Ollama Embeddings]
    end
    
    subgraph "Neo4j Graph RAG"
        Neo4j --> VM[(Vector Index<br/>Semantic Search)]
        Neo4j --> GM[(Graph Structure<br/>Relationships)]
        Neo4j --> TM[(Properties<br/>Metadata & Time)]
    end
    
    subgraph "Deployment Modes"
        LocalMode[Local Mode<br/>Docker Compose<br/>Single User]
        CloudMode[Cloud Mode<br/>Neo4j Aura + Auth0<br/>Multi-tenant]
    end
    
    style User fill:#e1f5fe
    style Client fill:#fff3e0
    style MCP fill:#f3e5f5
    style MS fill:#fff9c4
    style Neo4j fill:#e8f5e9
    style LLM fill:#fce4ec
    style EMB fill:#f0f4c3
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

- **MCP Server**: Python + FastMCP
- **Database**: Neo4j (graph + vectors)
- **LLM**: Local (Ollama/llama.cpp) or API (OpenAI/Anthropic)
- **Embeddings**: Local transformers or API (OpenAI/Anthropic)
- **Auth (Cloud)**: Auth0 OAuth 2.1
- **Testing**: Python pytest + MCP test harness

## 📝 License

MIT

## 🤝 Contributing

This is an early-stage project. Contributions and feedback welcome!
