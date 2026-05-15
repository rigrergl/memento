# MCP Tool Response Contracts

**Source of truth**: `src/mcp/server.py`, `src/memory/service.py`

Integration tests assert against these exact strings. Any divergence between these contracts and the source code is a bug in either the implementation or the tests.

---

## `remember` Tool

**Parameters**: `content: str`, `confidence: float`

### Success

```
Memory stored with id: {uuid}
```

Where `{uuid}` is a UUID v4 string (e.g., `"3fa85f64-5717-4562-b3fc-2c963f66afa6"`).

**Assertion pattern**: `assert result.data.startswith("Memory stored with id: ")`

### Validation Errors

| Trigger | Response String |
|---------|----------------|
| `content` is empty or whitespace-only | `"Memory text cannot be empty."` |
| `len(content) > 4000` (default max) | `"Memory text exceeds maximum length of 4000 characters (got {n})."` |
| `confidence < 0.0` or `confidence > 1.0` | `"Invalid confidence value {v}: must be between 0.0 and 1.0."` |

### Unexpected Error

```
Failed to store memory: unexpected error. Please try again.
```

---

## `recall` Tool

**Parameters**: `query: str`, `limit: int = 10`

### Success (results found)

```
Found {n} result(s) for "{query}":
1. (score: {score:.3f}) {content}
2. (score: {score:.3f}) {content}
...
```

**Assertion pattern**: `assert result.data.startswith(f'Found ')`

### No Results

```
No memories found for "{query}".
```

**Assertion pattern**: `assert result.data == f'No memories found for "{query}".'`

### Validation Error

| Trigger | Response String |
|---------|----------------|
| `query` is empty or whitespace-only | `"Query cannot be empty."` |

### Unexpected Error

```
Failed to search memories: unexpected error. Please try again.
```
