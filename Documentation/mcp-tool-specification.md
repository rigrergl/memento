# MCP Tool Specification

## Overview
This document defines the Model Context Protocol (MCP) tools that Memento exposes to LLM clients. This is the contract between the LLM and the memory system.

## Tools

### 1. store_memory

Stores a new memory or fact in the system.

```typescript
{
  name: "store_memory",
  description: "Store a new fact or memory about a person, preference, or situation. Use this when you learn something new that should be remembered for future conversations.",
  parameters: {
    type: "object",
    properties: {
      content: {
        type: "string",
        description: "The fact or memory to store. Should be a clear, standalone statement."
      },
      subject: {
        type: "string", 
        description: "The primary subject this memory is about (e.g., 'Antonia', 'Liam', 'Gordon')"
      },
      category: {
        type: "string",
        description: "Category of the memory",
        enum: ["preference", "restriction", "fact", "skill", "relationship", "goal", "history", "context"]
      },
      tags: {
        type: "array",
        items: { type: "string" },
        description: "Optional tags for additional categorization (e.g., ['food', 'allergy'], ['math', 'calculus'])"
      },
      confidence: {
        type: "number",
        minimum: 0,
        maximum: 1,
        description: "Confidence level in this memory (0-1). Default 1.0 for explicitly stated facts, lower for inferred information."
      }
    },
    required: ["content", "subject", "category"]
  }
}
```

**Example Usage:**
```json
{
  "content": "Emma is lactose intolerant",
  "subject": "Emma",
  "category": "restriction",
  "tags": ["dietary", "health"],
  "confidence": 1.0
}
```

### 2. search_memories

Searches for relevant memories using semantic similarity.

```typescript
{
  name: "search_memories",
  description: "Search for relevant memories based on a query. Use this to recall information about subjects, preferences, or past context.",
  parameters: {
    type: "object",
    properties: {
      query: {
        type: "string",
        description: "Natural language query to search for"
      },
      subject_filter: {
        type: "string",
        description: "Optional: Filter results to memories about a specific subject"
      },
      category_filter: {
        type: "string",
        description: "Optional: Filter results to a specific category",
        enum: ["preference", "restriction", "fact", "skill", "relationship", "goal", "history", "context"]
      },
      limit: {
        type: "integer",
        minimum: 1,
        maximum: 20,
        default: 5,
        description: "Maximum number of results to return"
      },
      threshold: {
        type: "number",
        minimum: 0,
        maximum: 1,
        default: 0.7,
        description: "Minimum similarity score for results (0-1)"
      }
    },
    required: ["query"]
  }
}
```

**Example Usage:**
```json
{
  "query": "dietary restrictions for the family",
  "category_filter": "restriction",
  "limit": 10
}
```

**Response Format:**
```json
{
  "memories": [
    {
      "id": "mem_abc123",
      "content": "Emma is lactose intolerant",
      "subject": "Emma",
      "category": "restriction",
      "tags": ["dietary", "health"],
      "confidence": 1.0,
      "created_at": "2024-01-15T10:30:00Z",
      "relevance_score": 0.92
    }
  ]
}
```

### 3. list_recent_memories

Lists the most recently stored memories.

```typescript
{
  name: "list_recent_memories",
  description: "List the most recently stored memories. Useful for reviewing what was just learned or stored.",
  parameters: {
    type: "object",
    properties: {
      limit: {
        type: "integer",
        minimum: 1,
        maximum: 50,
        default: 10,
        description: "Number of recent memories to retrieve"
      },
      subject_filter: {
        type: "string",
        description: "Optional: Filter to memories about a specific subject"
      }
    }
  }
}
```

### 4. update_memory

Updates or marks a memory as outdated (future implementation).

```typescript
{
  name: "update_memory",
  description: "Update an existing memory when information changes or becomes outdated.",
  parameters: {
    type: "object", 
    properties: {
      memory_id: {
        type: "string",
        description: "ID of the memory to update"
      },
      new_content: {
        type: "string",
        description: "Updated content for the memory"
      },
      mark_outdated: {
        type: "boolean",
        description: "If true, mark as outdated rather than updating content"
      },
      reason: {
        type: "string",
        description: "Reason for the update or why it's outdated"
      }
    },
    required: ["memory_id"]
  }
}
```

### 5. get_memory_stats

Get statistics about stored memories (for debugging/monitoring).

```typescript
{
  name: "get_memory_stats",
  description: "Get statistics about the stored memories for a subject or overall system.",
  parameters: {
    type: "object",
    properties: {
      subject_filter: {
        type: "string",
        description: "Optional: Get stats for a specific subject only"
      }
    }
  }
}
```

**Response Format:**
```json
{
  "total_memories": 156,
  "by_category": {
    "preference": 45,
    "restriction": 12,
    "fact": 38,
    "skill": 15,
    "relationship": 8,
    "goal": 10,
    "history": 20,
    "context": 8
  },
  "by_subject": {
    "Antonia": 25,
    "Gordon": 18,
    "Emma": 22,
    "Jake": 20
  },
  "oldest_memory": "2024-01-01T00:00:00Z",
  "newest_memory": "2024-01-15T14:30:00Z"
}
```

## Usage Guidelines for LLMs

### When to Store Memories
- Store when users explicitly share facts about themselves or others
- Store when users correct previous information  
- Store when learning about preferences, restrictions, or important context
- Store conclusions from successful interactions (e.g., "This meal plan worked well")

### When to Search Memories
- Before making recommendations that depend on preferences or restrictions
- When users reference past conversations or context
- When personalizing responses for specific individuals
- When users ask "Do you remember..." or similar queries

### Memory Content Best Practices
- Keep memories atomic - one fact per memory
- Use clear, unambiguous language
- Include relevant context in the content itself
- Maintain consistent subject naming (e.g., always "Emma", not sometimes "Emma" and sometimes "Gordon's daughter")

## Error Handling

All tools should return appropriate error responses:

```json
{
  "error": {
    "code": "MEMORY_NOT_FOUND",
    "message": "Memory with ID mem_xyz789 not found"
  }
}
```

Common error codes:
- `MEMORY_NOT_FOUND` - Requested memory doesn't exist
- `INVALID_PARAMETER` - Parameter validation failed
- `STORAGE_ERROR` - Database operation failed
- `EMBEDDING_ERROR` - Failed to generate embeddings
- `RATE_LIMIT` - Too many requests

## Implementation Notes

1. **Idempotency**: Multiple stores of identical content should be handled gracefully
2. **Consistency**: Subject names should be normalized for consistency
3. **Privacy**: No automatic sharing of memories between different user sessions
4. **Performance**: Search should return results within 200ms for optimal UX
