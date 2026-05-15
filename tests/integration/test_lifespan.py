"""Integration tests verifying the MCP server lifespan creates Neo4j schema artifacts."""


def test_vector_index_created(client, neo4j_driver):
    with neo4j_driver.session() as session:
        records = session.run("SHOW INDEXES WHERE type = 'VECTOR' AND name = 'memory_embedding_index'")
        assert records.single() is not None


def test_uniqueness_constraint_created(client, neo4j_driver):
    with neo4j_driver.session() as session:
        records = session.run("SHOW CONSTRAINTS WHERE name = 'memory_id_unique'")
        assert records.single() is not None
