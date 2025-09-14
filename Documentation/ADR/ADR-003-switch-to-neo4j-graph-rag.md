# ADR-003: Switch to Neo4j for Graph RAG Memory Architecture

## Status
Proposed

## Date
2025-09-13

## Context

Following ADR-002's choice of MongoDB, additional research reveals that Memento's memory system would benefit significantly from Graph RAG instead of traditional vector search. Graph RAG enables:

- Vector search to identify initial relevant memories
- Graph traversal to discover related memories through relationships
- Temporal connections between memories over time
- Better context assembly through memory relationships

Neo4j is purpose-built for graph operations and provides superior tooling for graph debugging and visualization compared to MongoDB's graph lookup capabilities.

Remote MCP servers with OAuth 2.1 authentication became officially supported in March 2025, enabling cloud deployment with proper user isolation.

## Decision

**Switch to Neo4j for memory storage with Graph RAG approach**

### Two Deployment Modes

#### Local Mode (Power Users)
```
┌──────────────────────────────────────┐
│        Docker Container              │
│  ┌──────────────────┐                │
│  │  MCP Server      │                │
│  │ (Query Service)  │                │
│  └──────────────────┘                │
│           │                          │
│  ┌──────────────────┐                │
│  │    Neo4j         │                │
│  │ (Memory + Vector)│                │
│  └──────────────────┘                │
└──────────────────────────────────────┘
```

- **100% Local**: No data leaves the machine
- **No Authentication**: Single user (`user_id = "local_user"`)
- **Single Container**: Neo4j Community Edition + MCP Server

#### Cloud Mode (Hosted Service)
```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Auth0         │    │  MCP Server      │    │ MongoDB Atlas   │
│ (OAuth Provider)│    │ (Query Service)  │    │ (User Auth DB)  │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                              │                            
                       ┌──────────────────┐                       
                       │   Neo4j Aura     │                       
                       │ (Memory + Vector)│                       
                       └──────────────────┘                       
```

- **Multi-user**: OAuth 2.1 authentication with Auth0
- **Managed Services**: Neo4j Aura + MongoDB Atlas (both free tiers)
- **Remote MCP**: Users connect via Claude Custom Connectors

### Components

1. **Neo4j**: Single database for both graph relationships and vector embeddings
2. **Query Service Layer**: Enforces user isolation by auto-injecting `user_id` filters  
3. **MongoDB Atlas** (cloud only): User authentication and management
4. **Auth0** (cloud only): OAuth 2.1 provider for social login

### Multi-tenancy Strategy

**Single Neo4j database** with user isolation:

- **Local Mode**: Single user (`user_id = "local_user"`) - no isolation needed
- **Cloud Mode**: `user_id` properties on all memory nodes with query service enforcement

Security enforced through query service layer that never allows raw Cypher to reach Neo4j.

```python
# Example secure query pattern for cloud mode
def search_memories(self, user_id: str, query_embedding: List[float]):
    cypher = """
    CALL db.index.vector.queryNodes('memory_embeddings', $limit, $embedding)
    YIELD node, score
    WHERE node.user_id = $user_id
    MATCH (node)-[:RELATES_TO]-(connected:Memory {user_id: $user_id})
    RETURN node, connected, score
    """
    return self.neo4j.run(cypher, user_id=user_id, embedding=query_embedding, limit=10)
```

### Authentication Flow

#### Local Mode
1. No authentication required - single user deployment
2. MCP server runs locally via Docker
3. Direct connection to local Neo4j instance

#### Cloud Mode  
1. User connects to remote MCP server via Claude Custom Connectors
2. OAuth flow redirects to Auth0 (supports Google/Facebook/email signup)
3. Auth0 returns JWT with consistent `user_id`
4. MCP server validates JWT against MongoDB Atlas user records
5. All Neo4j queries auto-inject `user_id` for isolation

## Decision Drivers Evaluation

Revisiting ADR-002's original drivers:

| Driver | Neo4j + MongoDB (Cloud) | Neo4j (Local) |
|--------|-------------------------|----------------|
| **Zero Development Costs** | ✅ Neo4j Aura + Atlas + Auth0 free tiers | ✅ Neo4j Community + Docker |
| **Local-First Deployment** | N/A - Cloud mode | ✅ Single container, no external deps |
| **General-Purpose Data** | ✅ MongoDB Atlas handles user management | ✅ No user management needed |
| **Python Integration** | ✅ Excellent Neo4j Python driver | ✅ Same driver |
| **Production Path** | ✅ Managed services with free tiers | ✅ Power users control deployment |
| **Simplicity** | ✅ Each service does what it's best at | ✅ Single database, no auth |

## Competitive Positioning

**vs Mem0's Architecture:**
- **Mem0**: ChromaDB (vectors) + Neo4j (graph) + KV store (facts)  
- **Memento**: Neo4j (vectors + graph + properties) - simpler with Neo4j's native vector search

**Advantages over Mem0:**
- **Unified Database**: Single Neo4j instance vs coordinating multiple databases
- **True Local Privacy**: No external services in local mode vs Mem0's cloud dependency  
- **Self-Controlled Cloud**: Users deploy own cloud instance vs vendor lock-in
- **Graph-Native**: Built for Graph RAG from ground up vs traditional vector RAG

## Consequences

### Positive
- **Graph RAG Capabilities**: Superior memory relationship traversal
- **Purpose-Built Tools**: Neo4j's graph visualization and debugging
- **Dual Deployment**: Supports both privacy-focused power users and hosted service
- **Scalable**: Single database handles few users (local) or many users (cloud)
- **Cloud Ready**: OAuth 2.1 support for remote MCP deployment
- **Cost Effective**: Free tiers for all cloud services during development

### Negative
- **Learning Curve**: Need to learn Cypher queries and graph concepts
- **Two Architectures**: Local vs cloud modes have different complexity
- **Neo4j Expertise**: Graph modeling requires different thinking than relational

### Mitigation
- Use Docker Compose for simple local deployment
- Abstract Neo4j behind service layer to minimize Cypher exposure
- Start with simple graph models and evolve complexity over time

## Deployment Strategy

### Local Development & Power Users
- **Docker Compose**: MCP Server + Neo4j Community Edition
- **No External Services**: Everything runs locally
- **No Authentication**: Single user mode
- **Zero Setup**: `docker-compose up` and ready

### Cloud Production (Friends & Family)
- **MCP Server**: Cloud compute (GCP/AWS/etc.)
- **Neo4j Aura**: Managed graph database (free tier)
- **MongoDB Atlas**: User management (free tier)
- **Auth0**: OAuth provider (free tier)

## Implementation Priority

1. **Phase 1**: Basic Neo4j integration with vector search
2. **Phase 2**: Graph relationships between memories  
3. **Phase 3**: Advanced Graph RAG with temporal connections
4. **Phase 4**: Remote deployment with OAuth

## References

- [MCP Remote Server Authentication](https://modelcontextprotocol.io/docs/tutorials/use-remote-mcp-server)
- [Neo4j Vector Search](https://neo4j.com/docs/cypher-manual/current/indexes-for-vector-search/)
- [Auth0 MCP Integration](https://auth0.com/blog/an-introduction-to-mcp-and-authorization/)
