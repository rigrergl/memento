# [MCP] Define MCP Tools

**Epic:** MCP Integration (Phase 2)

## Design Rationale

**Leveraging Client LLM for Intelligence:**
We're designing the MCP tool specification to leverage the client's LLM (e.g., Claude, GPT-4) for intelligent operations rather than building a server-side LLM. This approach keeps Memento simple and cost-effective while utilizing the powerful reasoning capabilities already available in the MCP client.

**Key responsibilities delegated to client LLM:**
- **Knowledge graph construction**: Client extracts entities and relationships from memories and passes structured data to the server
- **Intelligent graph traversal**: Client decides which graph relationships to explore based on the user's query
- **Conflict detection**: Client reasons about similar memories and decides when to call `supersede_memory`

**Server responsibilities (simple storage and retrieval):**
- Store memories with embeddings and graph structure
- Provide vector search for semantic similarity
- Expose graph navigation primitives for client-directed exploration
- Execute supersession and relationship management

This approach will be our first attempt. If we encounter bottlenecks or limitations, we can add server-side LLM capabilities later.

## Description

Implement the four MCP tools that expose memory operations to LLM clients. These tools define the interface that Claude and other LLMs will use to interact with the Memento memory system.

## Goal

Create production-ready MCP tools that:
- Follow the MCP tool specification from `Documentation/mcp-tool-specification.md`
- Provide intuitive interfaces for LLMs
- Include proper error handling and validation
- Return structured responses

## Acceptance Criteria

- [ ] Implement `store_memory` MCP tool
  - Accepts: `content` (string), `confidence` (float, optional), `source` (string, optional)
  - Returns: stored memory + list of similar memories for conflict detection
  - Includes examples in tool description
- [ ] Implement `search_memories` MCP tool
  - Accepts: `query` (string), `limit` (int, optional, default 5)
  - Returns: list of relevant memories ranked by similarity
  - Excludes superseded memories
- [ ] Implement `list_recent_memories` MCP tool
  - Accepts: `limit` (int, optional, default 10)
  - Returns: list of recently created memories
  - Ordered by created_at descending
- [ ] Implement `supersede_memory` MCP tool
  - Accepts: `old_memory_id` (string), `new_memory_id` (string)
  - Updates both memory records and creates relationship
  - Returns: confirmation of supersession
- [ ] All tools include proper error handling
- [ ] All tools validate input parameters
- [ ] All tools include helpful descriptions for LLM understanding
- [ ] Tests for each tool with various inputs
- [ ] Documentation matches `Documentation/mcp-tool-specification.md`

## Technical Details

**Tool Definitions:**

**store_memory:**
```python
@self.mcp.tool()
async def store_memory(
    content: str,
    confidence: float = 1.0,
    source: str = 'extracted'
) -> dict:
    """
    Store a new memory/fact about the user.

    Returns the stored memory along with similar existing memories
    to help detect conflicts or duplicates.

    Args:
        content: The memory content in natural language
        confidence: Confidence score 0-1 (default 1.0)
        source: 'explicit' if user asked to remember, 'extracted' if inferred

    Returns:
        {
            'stored': Memory object,
            'similar_memories': [list of similar Memory objects]
        }

    Example:
        store_memory("User prefers Python over JavaScript", confidence=0.9)
    """
    user_id = self._get_current_user_id()  # From MCP context
    return await self.memory_service.store_memory(
        user_id, content, confidence, source
    )
```

**search_memories:**
```python
@self.mcp.tool()
async def search_memories(query: str, limit: int = 5) -> list[dict]:
    """
    Search for relevant memories using semantic similarity.

    Args:
        query: Natural language search query
        limit: Maximum number of results (default 5)

    Returns:
        List of Memory objects ranked by relevance

    Example:
        search_memories("What programming languages does the user like?")
    """
    user_id = self._get_current_user_id()
    memories = await self.memory_service.search_memories(
        user_id, query, limit
    )
    return [memory.__dict__ for memory in memories]
```

**User Context:**
- For MVP: Use hardcoded user_id (e.g., "default_user")
- For future: Extract from MCP authentication context
- Add `_get_current_user_id()` helper method

**Response Format:**
- Return Memory objects as dictionaries
- Include all fields (id, content, confidence, timestamps, etc.)
- Format timestamps as ISO 8601 strings

**Dependencies:**
- Requires completed `[mcp]-build-fastmcp-server.md` story
- Requires `GraphMemoryService` from Core Components epic
- See `Documentation/mcp-tool-specification.md` for complete API spec

**Testing:**
- Test each tool with valid inputs
- Test error cases (invalid parameters, missing memories)
- Test conflict detection in store_memory
- Test supersession workflow

## Estimated Complexity

**Medium** - Straightforward tool wrappers with proper validation and documentation
