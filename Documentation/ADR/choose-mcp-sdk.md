# ADR-001: Choose MCP SDK for Memento Server

## Status
Accepted

## Date
2025-09-05

## Context

Memento requires a Model Context Protocol (MCP) server implementation to provide LLMs with persistent memory capabilities through vector database storage. The MCP server will:
- Store and retrieve memories (mementos) with semantic search
- Generate embeddings for memory content
- Interface with multiple vector database backends (ChromaDB, Pinecone, MongoDB, SQLite)
- Eventually support OAuth for web-based deployment to non-technical users

We need to select an SDK that balances multiple concerns:
- Type safety for data models and API contracts
- Local embedding generation capabilities for cost-effective development and deployment
- Community support and ecosystem maturity
- Distribution mechanism for both power users and general users
- Future OAuth support for web deployment

## Decision Drivers

1. **Local Embeddings Requirement**: Need to generate embeddings locally without API costs during development and for privacy-conscious power users
2. **Type Safety**: Strong typing for memory data models and MCP tool inputs to prevent runtime errors
3. **Distribution Strategy**: Initial focus on power users (local installation), later expansion to web-based access
4. **ML Capabilities**: Future features require ML ecosystem access (memory importance scoring, semantic clustering, consolidation)
5. **OAuth Support**: Eventually needed for multi-tenant web deployment
6. **Developer Experience**: Single language preferred to avoid cross-language complexity

## Considered Options

### Option 1: TypeScript SDK
The official TypeScript SDK with the largest MCP community adoption.

**Pros:**
- Largest community adoption (60-70% of MCP servers use TypeScript)
- 5.4k+ GitHub stars (highest among MCP repositories)
- Native compile-time type safety
- Excellent IDE support with IntelliSense
- NPM distribution familiar to web developers
- Mature OAuth support (used by Portal One and others)
- Good vector database client libraries available

**Cons:**
- **Cannot generate embeddings locally** - must use API services or separate microservice
- Requires external services for ML capabilities
- More boilerplate code compared to Python
- Complex build toolchain (TypeScript compilation, bundling)

### Option 2: Python SDK with FastMCP
The official Python SDK with FastMCP framework (3.7k+ stars, now part of official SDK).

**Pros:**
- **Direct access to ML ecosystem** (sentence-transformers, Hugging Face, PyTorch, etc.)
- **Local embedding generation** without API costs
- Full OAuth 2.1 support with RFC 9728 compliance
- Simpler, more Pythonic code with less boilerplate
- FastMCP provides high-level abstractions
- Native support for data science workflows
- All major vector databases have Python clients
- Single language for MCP server and ML operations

**Cons:**
- Smaller MCP community (25-30% of servers)
- Runtime type checking only (though Pydantic provides excellent validation)
- Python GIL limitations for CPU-bound operations
- Less familiar distribution mechanism for web developers (pip vs npm)

### Option 3: Hybrid Approach (TypeScript + Python Sidecar)
TypeScript MCP server with Python microservice for embeddings.

**Pros:**
- Leverages TypeScript's MCP ecosystem popularity
- Maintains ability to generate local embeddings
- Progressive enhancement possible

**Cons:**
- **Significant complexity overhead**
- Cross-language debugging challenges
- Serialization/deserialization overhead
- Two deployment pipelines and dependency management systems
- Network latency between services
- Increased maintenance burden

## Decision

**We will use Python with FastMCP** for the Memento MCP server.

### Key Rationale

1. **Local Embeddings are Non-Negotiable**: TypeScript cannot run transformer models locally. Python provides immediate access to sentence-transformers and Hugging Face models, enabling cost-free, private embedding generation.

2. **OAuth Parity Achieved**: Initial concerns about Python's OAuth support were resolved. The Python SDK includes full OAuth 2.1 resource server functionality with RFC 9728 compliance, matching TypeScript's capabilities.

3. **ML Ecosystem Critical for Vision**: Future features (memory importance decay, semantic clustering, consolidation) require Python's data science ecosystem. Starting with Python avoids future migration.

4. **Complexity Reduction**: A single-language solution eliminates cross-language communication overhead, serialization issues, and deployment complexity.

5. **Type Safety Achievable**: Pydantic provides runtime validation and can auto-generate TypeScript types for any client code, giving us a single source of truth.

## Consequences

### Positive

- **Immediate ML Capabilities**: Local embeddings work from day one, saving development costs
- **Future-Proof Architecture**: No migration needed when adding advanced ML features
- **Simpler Development**: Single language, single deployment pipeline, unified debugging
- **Flexible Deployment**: Same codebase can run locally (ChromaDB) or in cloud (Pinecone)
- **Progressive Enhancement**: Can start simple and add OAuth when needed
- **Cost Optimization**: Local embeddings eliminate API costs for development and power users

### Negative

- **Smaller MCP Examples**: Fewer MCP server examples to reference (mitigated by good FastMCP documentation)
- **NPM Distribution Lost**: Cannot distribute via npm (mitigated by pip, uvx, and Docker alternatives)
- **Python Learning Curve**: Team needs Python proficiency if not already present
- **Runtime Type Checking**: Type errors caught at runtime vs compile time (mitigated by Pydantic validation)

### Neutral

- Performance for I/O-bound operations (vector DB queries) is comparable between Python and TypeScript
- Both ecosystems have mature vector database clients
- OAuth implementation complexity is similar in both languages

## Distribution Strategy

```bash
# Power Users (Local)
pip install memento-mcp
memento-mcp serve --local

# Docker Users
docker run memento/mcp-server

# Web Users (Future)
# Hosted service with OAuth
https://api.memento.ai
```

## Alternatives Considered but Rejected

- **Go SDK**: High performance but lacks ML ecosystem
- **Rust SDK**: Excellent performance but immature MCP support
- **Starting with TypeScript, migrating later**: Migration complexity outweighs initial benefits
- **Using vector DB integrated embeddings**: Creates vendor lock-in

## References

- [Official Python MCP SDK](https://github.com/modelcontextprotocol/python-sdk) - Full OAuth 2.1 support confirmed
- [FastMCP Documentation](https://github.com/jlowin/fastmcp) - 3.7k+ stars, official SDK integration
- [MCP Server Examples](https://github.com/modelcontextprotocol/servers) - Community implementations
- [Portal One Migration Story](https://dev.to/jneums/why-we-ditched-python-for-typescript-and-survived-oauth-in-our-ai-agent-mcp-server-45al) - Different requirements (OAuth-first, no ML needs)

## Review Schedule

Review this decision in 6 months or if:
- TypeScript gains local embedding capabilities
- Python MCP adoption drops significantly
- Distribution becomes a critical bottleneck

## Notes

The decision was heavily influenced by the requirement for local embeddings and future ML capabilities. If these requirements were removed, TypeScript would have been a viable choice due to its larger MCP community. However, given Memento's core value proposition of intelligent memory management, the ML ecosystem access provided by Python is essential.

The initial concern about OAuth support in Python was resolved through investigation showing comprehensive OAuth 2.1 support in the Python SDK, eliminating the last significant advantage of TypeScript for this use case.