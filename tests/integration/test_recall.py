"""Integration tests for the recall MCP tool: response strings, relevance, limit, and error paths."""


async def test_recall_returns_matching_memory(client):
    await client.call_tool("remember", {"content": "Photosynthesis is how plants convert sunlight into energy.", "confidence": 0.9})
    result = await client.call_tool("recall", {"query": "how do plants make energy from sunlight"})
    assert result.data.startswith("Found ")


async def test_recall_limit_honored(client):
    await client.call_tool("remember", {"content": "The mitochondria is the powerhouse of the cell.", "confidence": 0.9})
    await client.call_tool("remember", {"content": "DNA carries genetic information in living organisms.", "confidence": 0.9})
    await client.call_tool("remember", {"content": "Enzymes are biological catalysts that speed up chemical reactions.", "confidence": 0.9})
    result = await client.call_tool("recall", {"query": "biology science", "limit": 2})
    assert "1." in result.data
    assert "2." in result.data
    assert "3." not in result.data


async def test_recall_no_results(client):
    result = await client.call_tool("recall", {"query": "quantum entanglement"})
    assert result.data == 'No memories found for "quantum entanglement".'


async def test_recall_empty_query(client):
    result = await client.call_tool("recall", {"query": ""})
    assert result.data == "Query cannot be empty."
