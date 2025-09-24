# ADR-005: No LangChain – Direct Provider Integration

## Status
Accepted

## Date
2025-09-23

## Context
Memento requires integration of LLMs and embeddings. While LangChain is the most popular framework, its abstractions are primarily designed for document retrieval and don’t align well with our graph-based requirements. We need sophisticated graph traversal with temporal relationships, contradiction detection, and custom Cypher queries that LangChain’s Neo4j integration cannot express.

## Decision
**Do not use LangChain.**  
Integrate directly with provider SDKs instead.

## Rationale

### Our Graph RAG Requirements Don’t Fit LangChain
- **Graph traversal**: Requires temporal relationships and contradiction detection  
- **Custom Cypher queries**: Needed for memory operations, not supported by LangChain’s Neo4j integration  
- **Document-first abstractions**: LangChain is optimized for text retrieval, not graph navigation

### Direct Integration Is Simpler
- **Focused needs**: Extract memories, generate embeddings, analyze contradictions  
- **Transparency**: Direct SDK calls are more debuggable than framework abstractions  
- **Avoid complexity**: No need to learn or fight conventions that don’t match our patterns

### Control and Flexibility
- **User isolation**: Fine-grained control at the query level  
- **Access to features**: Direct use of new provider features without waiting for framework updates  
- **Custom memory operations**: Importance decay and consolidation require bespoke implementations

## Consequences

### Positive
- Full control over implementation details  
- Clear and debuggable code paths  
- No framework version conflicts or breaking changes  
- Smaller dependency footprint  

### Negative
- Must write provider integration code (~50 lines per provider)  
- No pre-built chains or document loaders  
- Manual implementation of retry logic and error handling  

### Future Considerations
If we later need complex agent orchestration or document-processing pipelines, we can reconsider. Our factory pattern allows LangChain to be added as an adapter in the future without major refactoring.
