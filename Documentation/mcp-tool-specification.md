# MCP Tool Specification

## Overview
This document defines the Model Context Protocol (MCP) tools that Memento exposes to LLM clients. These tools provide a simple, powerful interface for managing long-term memory.

## Core Tools

### 1. store_memory

Stores a new memory in the system. Always succeeds and returns similar memories that might be outdated.

```typescript
{
  name: "store_memory",
  description: "Store a new memory. Always succeeds. Returns similar memories that might be outdated. ALWAYS check the response for supersede suggestions.",
  parameters: {
    type: "object",
    properties: {
      content: {
        type: "string",
        description: "The fact or information to remember. Should be a clear, standalone statement.",
        required: true
      },
      confidence: {
        type: "number",
        minimum: 0,
        maximum: 1,
        default: 1.0,
        description: "Confidence score from 0-1. Default 1.0 for explicit facts.",
        required: false
      },
      source: {
        type: "string",
        enum: ["explicit", "extracted"],
        default: "extracted",
        description: "Whether user explicitly asked to remember (explicit) or extracted from conversation (extracted).",
        required: false
      }
    },
    required: ["content"]
  },
  returns: {
    created: {
      type: "Memory",
      description: "The newly created memory with id, content, confidence, etc."
    },
    similar: {
      type: "array",
      items: { type: "Memory" },
      description: "Array of similar existing memories that might be outdated"
    },
    action_required: {
      type: "string",
      nullable: true,
      description: "Specific action to take if conflicts found, e.g., 'Call supersede_memory(old_id, new_id)'"
    }
  }
}
```

**Example Usage:**
```json
// Request
{
  "content": "User moved to Austin",
  "confidence": 1.0,
  "source": "explicit"
}

// Response with conflict
{
  "created": {
    "id": "mem_789",
    "content": "User moved to Austin",
    "confidence": 1.0,
    "source": "explicit",
    "created_at": "2024-06-15T10:00:00Z"
  },
  "similar": [
    {
      "id": "mem_123",
      "content": "User lives in Seattle",
      "confidence": 0.9,
      "created_at": "2024-01-01T10:00:00Z"
    }
  ],
  "action_required": "Call supersede_memory(\"mem_123\", \"mem_789\") to mark the old memory as outdated."
}
```

### 2. supersede_memory

Marks an old memory as outdated when replaced by newer information.

```typescript
{
  name: "supersede_memory",
  description: "Mark an old memory as outdated when replaced by newer information. Call this when store_memory suggests it.",
  parameters: {
    type: "object",
    properties: {
      old_memory_id: {
        type: "string",
        description: "ID of the outdated memory",
        required: true
      },
      new_memory_id: {
        type: "string",
        description: "ID of the new memory that replaces it",
        required: true
      }
    },
    required: ["old_memory_id", "new_memory_id"]
  },
  returns: {
    success: {
      type: "boolean",
      description: "Whether the operation succeeded"
    },
    message: {
      type: "string",
      description: "Confirmation or error message"
    }
  }
}
```

**Example Usage:**
```json
// Request
{
  "old_memory_id": "mem_123",
  "new_memory_id": "mem_789"
}

// Response
{
  "success": true,
  "message": "Memory mem_123 marked as superseded by mem_789"
}
```

### 3. search_memories

Searches for relevant memories using semantic similarity. Automatically filters out superseded memories.

```typescript
{
  name: "search_memories",
  description: "Search for relevant memories based on a query. Automatically filters out superseded memories.",
  parameters: {
    type: "object",
    properties: {
      query: {
        type: "string",
        description: "Natural language search query",
        required: true
      },
      limit: {
        type: "integer",
        minimum: 1,
        maximum: 20,
        default: 5,
        description: "Maximum number of results to return",
        required: false
      }
    },
    required: ["query"]
  },
  returns: {
    memories: {
      type: "array",
      items: { type: "Memory" },
      description: "Array of relevant memories, excluding superseded ones"
    }
  }
}
```

**Example Usage:**
```json
// Request
{
  "query": "Where does the user live?",
  "limit": 3
}

// Response
{
  "memories": [
    {
      "id": "mem_789",
      "content": "User moved to Austin",
      "confidence": 1.0,
      "source": "explicit",
      "created_at": "2024-06-15T10:00:00Z",
      "relevance_score": 0.92
    },
    {
      "id": "mem_456",
      "content": "User works remotely from home in Austin",
      "confidence": 0.9,
      "source": "extracted",
      "created_at": "2024-06-20T14:00:00Z",
      "relevance_score": 0.85
    }
  ]
}
```

### 4. list_recent_memories

Returns the most recently created memories. Useful for reviewing what was just stored.

```typescript
{
  name: "list_recent_memories",
  description: "Get the most recently created memories. Useful for reviewing what was just stored.",
  parameters: {
    type: "object",
    properties: {
      limit: {
        type: "integer",
        minimum: 1,
        maximum: 50,
        default: 10,
        description: "Number of recent memories to return",
        required: false
      }
    }
  },
  returns: {
    memories: {
      type: "array",
      items: { type: "Memory" },
      description: "Array of recent memories, excluding superseded ones"
    }
  }
}
```

**Example Usage:**
```json
// Request
{
  "limit": 5
}

// Response
{
  "memories": [
    {
      "id": "mem_892",
      "content": "User prefers window seats on flights",
      "confidence": 1.0,
      "source": "explicit",
      "created_at": "2024-12-01T16:45:00Z"
    },
    {
      "id": "mem_891",
      "content": "User is planning a trip to Japan in March",
      "confidence": 0.95,
      "source": "extracted",
      "created_at": "2024-12-01T16:40:00Z"
    }
  ]
}
```

## Usage Guidelines for LLMs

### When to Store Memories
- When users explicitly say "remember that..." or similar
- When learning new facts about users, preferences, or situations
- When information updates or changes (e.g., "I moved to...")
- After successful interactions that reveal preferences

### When to Search Memories
- Before making personalized recommendations
- When context from past conversations would be helpful
- When users ask "Do you remember..." or reference past discussions
- To avoid asking for information already provided

### Handling Conflicts
1. When `store_memory` returns similar memories with an `action_required` field
2. Review if the memories truly conflict (e.g., old location vs new location)
3. Call `supersede_memory` if the old information is now outdated
4. Otherwise, keep both memories if they're complementary

### Memory Content Best Practices
- Keep memories atomic - one fact per memory
- Use clear, specific language
- Include relevant context in the content
- Be consistent with naming (e.g., always "the user" or always "John")

## Example Conversation Flow

```
User: "I moved to Austin last month"

1. LLM calls: store_memory("User moved to Austin last month", confidence=1.0, source="explicit")

2. MCP returns:
{
  "created": {"id": "mem_789", "content": "User moved to Austin last month"},
  "similar": [{"id": "mem_123", "content": "User lives in Seattle"}],
  "action_required": "Call supersede_memory(\"mem_123\", \"mem_789\") to mark the old memory as outdated."
}

3. LLM recognizes the conflict and calls: supersede_memory("mem_123", "mem_789")

4. MCP returns: {"success": true, "message": "Memory mem_123 marked as superseded by mem_789"}

5. LLM responds to user: "I've noted that you've moved to Austin! I'll remember this for our future conversations."
```

## Memory Object Structure

The Memory object returned by tools has this structure:

```typescript
{
  id: string,                  // Unique identifier
  content: string,              // The memory text
  confidence: number,           // 0-1 score
  source: 'explicit' | 'extracted',
  created_at: string,          // ISO 8601 timestamp
  updated_at: string,          // ISO 8601 timestamp
  accessed_at: string,         // ISO 8601 timestamp
  supersedes?: string,         // ID of memory this replaces
  superseded_by?: string,      // ID of memory that replaces this
  relevance_score?: number     // Only in search results
}
```

## Error Handling

All tools may return error responses:

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

## Implementation Notes

### Performance Targets
- `store_memory`: < 500ms including embedding generation
- `search_memories`: < 200ms for optimal UX
- `supersede_memory`: < 100ms
- `list_recent_memories`: < 100ms

### Consistency Guarantees
- Memories are immediately available after storing
- Superseded memories are immediately filtered from search
- All operations are atomic

### Future Enhancements
- Batch operations for multiple memories
- Memory analytics and insights
- Export/import functionality
- Namespace support for multi-user scenarios
