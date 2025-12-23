# [Core] Basic Demo

**Epic:** Core Components (Phase 1)

## Description

Make a simple demo for Memento that demonstrates basic graph entity creation. The goal is to create a minimal working implementation of a "remember" MCP tool that stores knowledge graph triples in Neo4j.

## Goal

Create a simple MCP tool called "remember" that:
1. Accepts the raw memory text from the user (exact words)
2. Accepts a structured Triple (subject-predicate-object)
3. Creates nodes and relationships in the Neo4j graph database

## Requirements

### Input Parameters

The MCP tool should accept:

1. **raw_memory** (string, required)
   - The exact text from the user, word for word
   - Example: "My favorite color is blue"

2. **triple** (object, required)
   - **source_node** (string): The subject/source node
   - **relationship** (string): The predicate/relationship type
   - **target_node** (string): The object/target node
   - Example: `{source_node: "User", relationship: "LIKES", target_node: "blue"}`

### Functionality (Keep Simple!)

For this basic demo:
- Create two nodes in Neo4j (source_note and target_note)
- Create a relationship between them with the specified relationship type
- Store the original raw_memory text with the graph structure
- **DO NOT** implement (save for future tasks):
  - Checking for existing nodes
  - Detecting contradictory information
  - Deduplication
  - Supersession logic
  - Any complex conflict resolution

### Data Models Needed

1. **Node**: Represents a graph node
   - Properties: name/content, created_at

2. **Triple**: Represents a subject-predicate-object structure
   - Properties: source_note, relationship, target_note

3. **Memento**: Links the raw text to the triple
   - Properties: raw_memory, triple reference, created_at

## Thought Process

This is a graph-first approach that differs from the vector-based Memory model in the existing documentation. We're building a knowledge graph where:
- Nodes represent entities (people, places, concepts)
- Relationships represent connections between entities
- The raw memory text is preserved for context

The user's LLM client will be responsible for:
- Parsing the user's statement into a triple structure
- Determining appropriate relationship types
- Calling the remember tool with both the raw text and structured triple

Future iterations will add:
- Node deduplication (recognizing "User" and "The user" as the same entity)
- Contradiction detection (finding conflicting facts)
- Supersession (marking old facts as outdated)

## Implementation Steps

1. **Create Data Models** (`src/models/`)
   - Create `Node` model for graph nodes
   - Create `Triple` model for the triple structure
   - Update or create models to support memory with triple

2. **Implement Neo4j Repository** (`src/graph/neo4j.py`)
   - Method to create/get a node by name
   - Method to create a relationship between two nodes
   - Method to store the memory with its triple

3. **Implement Memory Service** (`src/memory/service.py`)
   - Method to handle the "remember" operation
   - Coordinates creating nodes, relationship, and memory storage
   - Simple implementation without conflict detection

4. **Create MCP Tool** (`src/mcp/server.py`)
   - Register "remember" tool with FastMCP
   - Define tool parameters (raw_memory, triple object)
   - Wire up to memory service

5. **Testing/Demo**
   - Manual test with example triples
   - Verify nodes and relationships are created in Neo4j
   - Verify memory is stored with raw text

## Success Criteria

- MCP tool "remember" is callable via the MCP protocol
- Creates two nodes in Neo4j when called
- Creates a relationship between the nodes
- Stores the original raw_memory text
- Returns a success response with created entity IDs


