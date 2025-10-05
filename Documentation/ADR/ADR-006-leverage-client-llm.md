# ADR-006: Leverage Client LLM via MCP

## Status
Accepted

## Date
2025-10-04

## Context
Memento needs intelligent processing for knowledge graph construction (extracting entities and relationships from memories) and smart graph traversal (deciding which relationships to explore based on queries). We could implement this with a server-side LLM or leverage the client's LLM through MCP tool design.

## Decision
**Attempt to leverage the MCP client's LLM for all intelligent operations.**
Avoid implementing server-side LLM unless we hit clear limitations.

## Rationale

### MCP Clients Already Have Powerful LLMs
- Claude, GPT-4, and other MCP clients have sophisticated reasoning capabilities
- No need to duplicate intelligence on the server side
- Client LLMs are likely more powerful than what we'd run server-side

### Simpler Architecture
- Server becomes a pure storage and retrieval layer
- No need to manage LLM provider integrations (OpenAI, Ollama, etc.)
- Fewer dependencies, smaller codebase
- Easier to deploy and maintain

### Cost-Effective
- No server-side LLM inference costs
- Can deploy on minimal infrastructure
- Scales better (computation happens on client side)

### YAGNI Principle
- Don't build server-side LLM capabilities until we prove we need them
- Start simple, add complexity only when required

## Implementation Approach

### Client LLM Responsibilities (via MCP):
- Extract entities and relationships from memory content
- Decide which graph relationships are relevant to explore
- Detect conflicts between similar memories
- Reason about supersession decisions

### Server Responsibilities:
- Generate embeddings for semantic search (local sentence-transformers)
- Store memories with vector embeddings and graph structure
- Provide vector search capabilities
- Expose graph navigation primitives
- Execute CRUD operations on memories and relationships

### MCP Tool Design:
Design tools to accept structured data from client (entities, relationships) rather than expecting server to extract them from raw text.

## Consequences

### Positive
- Dramatically simpler server architecture
- Lower operational costs
- Smaller deployment footprint
- Leverages best-in-class LLMs (client-side)
- Faster development cycle

### Negative
- More complex MCP tool contracts (must accept structured data)
- Requires sophisticated client LLM to use effectively
- Multiple round-trips for complex graph traversal
- Client must understand graph schema

### Mitigation
If we discover that client-directed graph traversal is too slow or complex:
- We can add server-side graph traversal heuristics
- We can add server-side LLM for specific bottleneck operations
- Our architecture allows adding `ILLMProvider` later without major refactoring

## Future Considerations
This is an experiment. We'll monitor:
- Performance of multi-step graph traversal via MCP
- Quality of client-extracted entities and relationships
- User experience and latency

If client-directed intelligence proves insufficient, we can revisit and add targeted server-side LLM capabilities.
