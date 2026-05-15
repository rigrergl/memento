"""Integration tests for the remember MCP tool: protocol layer + Neo4j graph state."""


async def test_remember_success(client, neo4j_driver):
    result = await client.call_tool("remember", {"content": "The sky is blue on clear days.", "confidence": 0.9})
    assert result.data.startswith("Memory stored with id: ")

    with neo4j_driver.session() as session:
        record = session.run("MATCH (m:Memory) RETURN m").single()
    node = record["m"]
    assert node["id"] is not None
    assert node["content"] == "The sky is blue on clear days."
    assert node["embedding"] is not None
    assert len(node["embedding"]) == 384
    assert node["confidence"] == 0.9
    assert node["created_at"] is not None
    assert node["updated_at"] is not None
    assert node["accessed_at"] is not None
    assert node["source"] == "user_requested"
    assert node["supersedes"] is None
    assert node["superseded_by"] is None


async def test_remember_empty_content(client, neo4j_driver):
    result = await client.call_tool("remember", {"content": "", "confidence": 0.5})
    assert result.data == "Memory text cannot be empty."

    with neo4j_driver.session() as session:
        records = list(session.run("MATCH (n:Memory) RETURN n"))
    assert len(records) == 0


async def test_remember_content_too_long(client, neo4j_driver):
    long_content = "x" * 4001
    result = await client.call_tool("remember", {"content": long_content, "confidence": 0.5})
    assert result.data == "Memory text exceeds maximum length of 4000 characters (got 4001)."

    with neo4j_driver.session() as session:
        records = list(session.run("MATCH (n:Memory) RETURN n"))
    assert len(records) == 0


async def test_remember_invalid_confidence(client, neo4j_driver):
    result = await client.call_tool("remember", {"content": "Some content.", "confidence": 1.5})
    assert result.data == "Invalid confidence value 1.5: must be between 0.0 and 1.0."

    with neo4j_driver.session() as session:
        records = list(session.run("MATCH (n:Memory) RETURN n"))
    assert len(records) == 0
