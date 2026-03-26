# [MCP] Test Claude Desktop Integration

**Epic:** MCP Integration (Phase 2)

## Description

Test the Memento MCP server with Claude Desktop to ensure end-to-end functionality. This validates that the entire system works correctly in a real-world scenario.

## Goal

Successfully integrate and test Memento with Claude Desktop:
- Configure Claude Desktop to use Memento MCP server
- Test all memory operations in real conversations
- Document the setup process
- Validate the user experience

## Acceptance Criteria

- [ ] Claude Desktop configured to connect to Memento MCP server
- [ ] Configuration documented in README or setup guide
- [ ] Test storing explicit memories (user says "remember that...")
- [ ] Test semantic search ("what do you know about...")
- [ ] Test listing recent memories
- [ ] Test superseding outdated memories
- [ ] Test conflict detection when storing similar memories
- [ ] Verify memories persist across conversation sessions
- [ ] Document any issues or limitations discovered
- [ ] Create troubleshooting guide for common issues
- [ ] Screenshots or examples of working integration

## Technical Details

**Claude Desktop Configuration:**

1. Locate Claude Desktop config file:
   - macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`
   - Windows: `%APPDATA%/Claude/claude_desktop_config.json`

2. Add Memento MCP server:
```json
{
  "mcpServers": {
    "memento": {
      "command": "python",
      "args": ["-m", "src.mcp.server"],
      "cwd": "/path/to/memento",
      "env": {
        "NEO4J_URI": "neo4j+s://xxxxx.databases.neo4j.io",
        "NEO4J_USER": "neo4j",
        "NEO4J_PASSWORD": "your-password",
        "EMBEDDING_MODEL": "all-MiniLM-L6-v2"
      }
    }
  }
}
```

**Test Scenarios:**

1. **Basic Storage:**
   - User: "Remember that I prefer Python for data science"
   - Verify memory is stored
   - Ask: "What programming languages do I prefer?"
   - Verify correct retrieval

2. **Conflict Detection:**
   - Store: "I live in Seattle"
   - Store: "I live in Austin" (should return Seattle as similar)
   - LLM should recognize conflict and ask about superseding

3. **Supersession:**
   - Supersede old "Seattle" memory with new "Austin" memory
   - Search for "where do I live?"
   - Verify only Austin is returned

4. **Cross-Session Persistence:**
   - Store memories in one conversation
   - Close Claude Desktop
   - Open new conversation
   - Verify memories are still accessible

5. **Semantic Search Quality:**
   - Store various facts about user
   - Test semantically similar queries
   - Verify relevant memories are retrieved

**Troubleshooting Guide:**

Common issues to document:
- Server fails to start (missing dependencies, config errors)
- Connection timeout to Neo4j
- Embedding model download issues
- Permission errors
- Claude Desktop not detecting the server

**Success Criteria:**
- All test scenarios pass
- Setup documented clearly
- Any workarounds documented
- Performance is acceptable (< 2 second response time)

**Dependencies:**
- Requires completed `[mcp]-define-mcp-tools.md` story
- Requires Neo4j Aura instance configured
- Requires Claude Desktop installed

## Estimated Complexity

**Small** - Primarily configuration and testing, but important for validation
