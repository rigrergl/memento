# ADR-002: Choose Vector Database for Memento

## Status
Proposed

## Date
2025-01-06

## Context

Memento requires a vector database to store and retrieve semantic memories (mementos) for LLMs. The database must support:
- Semantic similarity search using embeddings
- User data isolation (each user can only access their own memories)
- Metadata storage and filtering
- General data storage beyond vectors (user profiles, preferences, sessions)

Following ADR-001, I've chosen Python with FastMCP. The vector database must integrate well with this Python-first architecture while maintaining zero development costs and supporting fully local deployment for privacy-conscious power users.

## Decision Drivers

1. **Zero Development Costs**: No paid tiers during development
2. **Local-First Deployment**: Must run entirely locally for power users
3. **General-Purpose Capabilities**: Need to store user data, not just vectors
4. **Python Integration**: Native Python client
5. **Production Path**: Clear migration from local to cloud deployment
6. **Simplicity**: Minimal setup friction for the MVP

## Considered Options

### Option 1: MongoDB with Atlas Vector Search
My familiar database with recently available local vector capabilities.

**Pros:**
- **I already know MongoDB** - zero learning curve
- **LOCAL VECTOR SEARCH AVAILABLE** - Atlas CLI enables local deployments with full vector search
- **General-purpose database** - can store users, sessions, preferences alongside vectors
- **Free tier for demos** - Atlas has generous free tier (512MB)
- **Production-ready** - built-in auth, monitoring, backups
- **Managed cloud option** - Atlas handles operations when scaling

**Cons:**
- Requires Docker for local deployment (not pure Python)
- More setup steps than embedded databases
- Larger resource footprint locally

### Option 2: ChromaDB
Open-source embedding database designed for LLM applications.

**Pros:**
- **Pure Python** - just `pip install chromadb`
- **Zero cost** - completely open source
- **Embedded mode** - runs in-process, no server
- **Designed for LLM use cases** - simple API
- **Minimal setup** - 3 lines to start

**Cons:**
- Vector-only database (need separate solution for user data)
- No built-in cloud offering
- Would need to self-host for production
- Less mature ecosystem

### Option 3: Pinecone
Cloud-native vector database with excellent performance.

**Pros:**
- **Best-in-class performance**
- **Generous free tier** - 100K vectors
- **Fully managed** - zero operations
- **Excellent Python SDK**

**Cons:**
- **NO local option** - privacy concerns for power users
- **Cloud-only** - requires internet
- **Vendor lock-in**
- **Expensive at scale**

### Option 4: Weaviate
Open-source vector database with hybrid search.

**Pros:**
- **Hybrid search** - combines vector + keyword
- **Local deployment available**
- **Cloud offering exists**
- **GraphQL API**

**Cons:**
- **Requires Docker** - not pure Python
- **Complex setup** - steeper learning curve
- **Resource intensive** locally

### Option 5: Qdrant
High-performance vector search engine.

**Pros:**
- **Local mode available**
- **Rich filtering capabilities**
- **Rust performance**
- **Cloud offering available**

**Cons:**
- Requires compilation or Docker
- More complex than needed for MVP
- Smaller ecosystem

### Option 6: PGVector
PostgreSQL extension for vector similarity.

**Pros:**
- **PostgreSQL ecosystem** - battle-tested
- **SQL interface** - familiar
- **General-purpose database**
- **Many hosting options**

**Cons:**
- Extension installation complexity
- Not optimized for vector operations
- PostgreSQL overhead for simple use case

## Decision

**Choose: MongoDB with Atlas Vector Search**

### Rationale

1. **Single database for everything**: Vectors, user profiles, preferences, sessions - all in one place
2. **I already know it**: Can move fast without learning a new system
3. **True local option**: Atlas CLI provides local vector search capability
4. **Clear production path**: Local → Atlas free tier → Atlas production
5. **No additional infrastructure**: Don't need separate databases for users vs vectors

### Implementation Strategy

```python
# Abstract interface for future flexibility
class VectorStore(ABC):
    @abstractmethod
    async def store_memory(self, user_id: str, text: str, embedding: List[float]) -> str:
        pass
    
    @abstractmethod
    async def search_memories(self, user_id: str, embedding: List[float], limit: int) -> List[Memory]:
        pass

# MongoDB implementation with user isolation
class MongoVectorStore(VectorStore):
    async def search_memories(self, user_id: str, embedding: List[float], limit: int):
        pipeline = [
            {
                "$vectorSearch": {
                    "index": "memory_vector_index",
                    "path": "embedding",
                    "queryVector": embedding,
                    "filter": {"user_id": user_id},  # User isolation
                    "limit": limit
                }
            }
        ]
        return list(self.memories.aggregate(pipeline))
```

## Consequences

### Positive
- **Unified platform**: All data in one database
- **Familiar technology**: Leverage existing MongoDB knowledge
- **User management built-in**: Can store user profiles, preferences, sessions
- **Production pathway clear**: Atlas handles scaling, auth, monitoring
- **Flexible deployment**: Works locally and in cloud

### Negative
- **Docker dependency**: Local setup requires Docker
- **Resource usage**: MongoDB heavier than ChromaDB
- **Setup complexity**: More steps than `pip install`

### Mitigation
- Provide Docker setup script for easy local installation
- Document ChromaDB as lightweight alternative if needed
- Create setup automation for Atlas CLI

## Deployment Path

```
Development: Atlas CLI local (Docker) - Zero cost
Demo: Atlas free tier (512MB) - Zero cost  
Production: Atlas dedicated cluster - Pay as needed
```

## Alternative if Simplicity Critical

If pure Python deployment becomes critical, implement with ChromaDB for vectors + SQLite for user data. The abstraction layer makes switching easy.

## Review Triggers

- MongoDB local vector search has significant issues
- Need pure Python deployment (no Docker)
- Scaling beyond Atlas free tier limits during development

## References

- [MongoDB Atlas CLI Local Development](https://www.mongodb.com/blog/post/introducing-local-development-experience-atlas-search-vector-search-atlas-cli)
- [Build Local RAG with Atlas Vector Search](https://www.mongodb.com/docs/atlas/atlas-vector-search/tutorials/local-rag/)
- Project Requirements: ADR-001 (Python with FastMCP)