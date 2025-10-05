# [Advanced] Implement Graph RAG

**Epic:** Advanced Features (Phase 3)

## Description

Enhance the memory system with graph-based retrieval augmented generation (Graph RAG) by extracting entities and relationships from memories and storing them in Neo4j's graph structure. This enables more sophisticated memory retrieval through graph traversal.

## Goal

Implement Graph RAG capabilities that:
- Extract entities from memory content
- Extract relationships between entities
- Store entities and relationships in Neo4j graph
- Enhance semantic search with graph traversal
- Retrieve related memories through entity connections

## Acceptance Criteria

- [ ] Entity extraction integrated into memory storage workflow
- [ ] Relationship extraction integrated into memory storage workflow
- [ ] Neo4j schema extended with Entity and Relationship nodes
- [ ] `(:Memory)-[:MENTIONS]->(:Entity)` relationships created
- [ ] `(:Entity)-[:RELATES_TO]->(:Entity)` relationships created
- [ ] Enhanced search that combines vector similarity + graph traversal
- [ ] `search_with_graph(query, depth)` method in memory service
  - Finds semantically similar memories
  - Traverses graph to find related entities
  - Returns expanded memory context
- [ ] Graph traversal queries optimized for performance
- [ ] Tests for entity extraction and storage
- [ ] Tests for relationship extraction and storage
- [ ] Tests for graph-enhanced search
- [ ] Documentation for Graph RAG architecture

## Technical Details

**Extended Neo4j Schema:**
```cypher
// New node types
(:Entity {
  id: string,
  name: string,
  type: string,  // Person, Location, Technology, etc.
  embedding: list[float],
  first_seen: datetime,
  last_seen: datetime
})

// New relationships
(:Memory)-[:MENTIONS]->(:Entity)
(:Entity)-[:RELATES_TO {
  type: string,  // relationship type
  strength: float,  // confidence
  source_memory_id: string
}]->(:Entity)
```

**Enhanced Storage Workflow:**
```python
async def store_memory(
    self,
    user_id: str,
    content: str,
    confidence: float = 1.0,
    source: str = 'extracted'
) -> dict:
    # 1. Store memory (existing logic)
    memory = await self._store_basic_memory(user_id, content, confidence, source)

    # 2. Extract entities using LLM
    if self.llm_provider:
        entities = await self.llm_provider.extract_entities(content)
        for entity in entities:
            # Create or update entity node
            entity_node = await self.repository.create_or_update_entity(entity)

            # Create MENTIONS relationship
            await self.repository.create_mentions_relationship(
                memory.id, entity_node.id
            )

        # 3. Extract relationships
        relationships = await self.llm_provider.extract_relationships(content)
        for rel in relationships:
            await self.repository.create_entity_relationship(
                subject=rel['subject'],
                predicate=rel['predicate'],
                object=rel['object'],
                source_memory_id=memory.id
            )

    return memory
```

**Graph-Enhanced Search:**
```python
async def search_with_graph(
    self,
    user_id: str,
    query: str,
    limit: int = 5,
    graph_depth: int = 2
) -> List[Memory]:
    # 1. Vector search for initial memories
    initial_memories = await self.search_memories(user_id, query, limit)

    # 2. Extract entities from query
    query_entities = await self.llm_provider.extract_entities(query)

    # 3. Graph traversal to find related memories
    related_memory_ids = set()
    for entity in query_entities:
        # Traverse: Entity -> RELATES_TO -> Entity -> MENTIONS <- Memory
        paths = await self.repository.traverse_graph(
            entity_name=entity['name'],
            depth=graph_depth
        )
        for path in paths:
            related_memory_ids.update(path.memory_ids)

    # 4. Fetch related memories
    related_memories = await self.repository.get_memories_by_ids(
        list(related_memory_ids)
    )

    # 5. Combine and deduplicate results
    all_memories = self._merge_and_rank(initial_memories, related_memories)

    return all_memories[:limit * 2]  # Return expanded context
```

**Graph Traversal Query:**
```cypher
// Find related memories through entity connections
MATCH (e:Entity {name: $entity_name})
MATCH path = (e)-[:RELATES_TO*1..$depth]-(related:Entity)
MATCH (m:Memory)-[:MENTIONS]->(related)
WHERE m.superseded_by IS NULL
RETURN DISTINCT m
ORDER BY length(path) ASC
LIMIT 20
```

**Repository Methods to Add:**
- `create_or_update_entity(entity_data) -> Entity`
- `create_mentions_relationship(memory_id, entity_id)`
- `create_entity_relationship(subject, predicate, object, source_memory_id)`
- `traverse_graph(entity_name, depth) -> list[Path]`
- `get_memories_by_ids(memory_ids) -> list[Memory]`

**Performance Considerations:**
- Create indexes on Entity.name and Entity.type
- Limit graph traversal depth (max 3)
- Cache frequently accessed entities
- Batch entity creation to reduce database calls

**Dependencies:**
- Requires `[advanced]-add-llm-providers.md` story completed
- Requires Neo4j repository extended with graph operations
- Requires Entity model in `src/models/`

**Testing:**
- Test entity extraction from sample memories
- Test relationship extraction accuracy
- Test graph traversal with various depths
- Test performance with large graphs (>1000 entities)
- Test search quality improvements with graph enhancement

## Estimated Complexity

**Large** - Complex graph operations, LLM integration, and sophisticated search algorithms
