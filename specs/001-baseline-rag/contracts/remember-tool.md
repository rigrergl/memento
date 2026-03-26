# Contract: `remember` MCP Tool

**Tool name**: `remember`
**Layer**: MCP Server (`src/mcp/server.py`)
**Related spec requirements**: FR-001, FR-002, FR-003, FR-004, FR-005, FR-009, FR-010, FR-011, FR-012, FR-013, FR-015, FR-016

---

## Input Parameters

| Parameter  | Type  | Required | Constraints                      |
|------------|-------|----------|----------------------------------|
| `content`  | `str` | Yes      | Non-empty, non-whitespace, ≤ `max_memory_length` characters (default 4,000) |
| `confidence` | `float` | Yes  | Range `[0.0, 1.0]` inclusive    |

---

## Success Response

Returned when the memory is stored successfully. The response is a **plain-text confirmation string** containing the created Memory's UUID (FR-016).

**Format**: `"Memory stored with id: <uuid>"`

**Example**:
```
Memory stored with id: a1b2c3d4-e5f6-7890-abcd-ef1234567890
```

---

## Error Response

When any error occurs, the tool returns a **plain-text error message string**. The exception is **never allowed to propagate unhandled** to the MCP client (FR-011, FR-012).

The error message must be human-readable so the LLM calling the tool understands what went wrong and can take corrective action.

### Error categories and example messages

| Cause                              | Example message                                                             |
|------------------------------------|-----------------------------------------------------------------------------|
| Empty content                      | `"Memory text cannot be empty."`                                            |
| Whitespace-only content            | `"Memory text cannot be empty."`                                            |
| Content exceeds max length         | `"Memory text exceeds maximum length of 4000 characters (got 4500)."`       |
| Invalid confidence value           | `"Invalid confidence value 1.5: must be between 0.0 and 1.0."`              |
| Embedding provider failure         | `"Failed to store memory: embedding service error. Please try again."`      |
| Neo4j / database failure           | `"Failed to store memory: database error. Please try again."`               |
| Unexpected error                   | `"Failed to store memory: unexpected error. Please try again."`             |

### Implementation rule

```python
@mcp.tool()
def remember(content: str, confidence: float) -> str:
    try:
        memory = service.store_memory(content, confidence)
        return f"Memory stored with id: {memory.id}"
    except ValueError as e:
        return str(e)          # validation errors: return message directly
    except Exception:
        return "Failed to store memory: unexpected error. Please try again."
```

The `ValueError` path surfaces user-actionable validation errors verbatim. All other exceptions are caught and wrapped in a fixed generic message — no internal detail is forwarded to the MCP client. See `Documentation/known-tech-debt.md` (TD-001) for the remediation plan.
