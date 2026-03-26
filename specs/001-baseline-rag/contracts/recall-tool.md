# Contract: `recall` MCP Tool

**Tool name**: `recall`
**Layer**: MCP Server (`src/mcp/server.py`)
**Related spec requirements**: FR-001, FR-018, FR-019, FR-020, FR-021, FR-022, FR-023

---

## Input Parameters

| Parameter | Type    | Required | Constraints                                           |
|-----------|---------|----------|-------------------------------------------------------|
| `query`   | `str`   | Yes      | Non-empty, non-whitespace string to search for        |
| `limit`   | `int`   | No       | Maximum number of results to return (default: 10, min: 1); values < 1 are rejected with a plain-text error (FR-023) |

---

## Success Response

The response is a **plain-text string** listing matching memories ordered by similarity score (descending).

**Format with results**:
```
Found {count} result(s) for "{query}":
1. (score: {score:.3f}) {content}
2. (score: {score:.3f}) {content}
...
```

**Format with no results**:
```
No memories found for "{query}".
```

**Examples**:

```
Found 2 result(s) for "color preferences":
1. (score: 0.954) My favorite color is blue
2. (score: 0.821) I prefer blue and green over red
```

```
No memories found for "quantum physics".
```

---

## Error Response

When any error occurs, the tool returns a **plain-text error message string**. The exception is **never allowed to propagate unhandled** to the MCP client (FR-022).

### Error categories and example messages

| Cause                       | Example message                                                        |
|-----------------------------|------------------------------------------------------------------------|
| Empty query                 | `"Query cannot be empty."`                                             |
| Whitespace-only query       | `"Query cannot be empty."`                                             |
| Invalid limit (< 1)         | `"Limit must be at least 1."`                                          |
| Embedding provider failure  | `"Failed to search memories: embedding service error. Please try again."` |
| Neo4j / database failure    | `"Failed to search memories: database error. Please try again."`       |
| Unexpected error            | `"Failed to search memories: unexpected error. Please try again."`     |

### Implementation rule

```python
@mcp.tool()
def recall(query: str, limit: int = 10) -> str:
    try:
        results = service.search_memory(query, limit)
        if not results:
            return f'No memories found for "{query}".'
        lines = [f'Found {len(results)} result(s) for "{query}":']
        for i, (memory, score) in enumerate(results, 1):
            lines.append(f'{i}. (score: {score:.3f}) {memory.content}')
        return "\n".join(lines)
    except ValueError as e:
        return str(e)          # validation errors: return message directly
    except Exception:
        return "Failed to search memories: unexpected error. Please try again."
```

The `ValueError` path surfaces user-actionable validation errors verbatim. All other exceptions are caught and wrapped in a fixed generic message — no internal detail is forwarded to the MCP client. See `Documentation/known-tech-debt.md` (TD-001) for the remediation plan.
