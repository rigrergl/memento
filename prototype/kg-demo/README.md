# 🧠 Knowledge Graph Demo: Multi-Scale Memory Organization

## Overview

This prototype demonstrates how **raw mementos** (unstructured observations) are transformed into a **structured knowledge graph** with hierarchy, entities, and relationships across multiple scales.

## The WOW Factor ✨

This demo showcases:

1. **Raw Mementos** → The original unstructured observations from our conversation
2. **Surgical Extraction** → Entities pulled from mementos with full traceability
3. **Multi-Scale Hierarchy** → 4 levels of abstraction (Domain → System → Component → Atomic)
4. **Rich Relationships** → 16 typed connections showing how concepts relate
5. **Full Provenance** → Every entity traces back to source mementos

## Files Generated

### 📊 `graph.json`
Complete structured data export with:
- 15 raw mementos (the original observations)
- 14 extracted entities across 4 scale levels
- 16 relationships between entities
- Full statistics and provenance tracking

### 🎨 `interactive_graph.html`
**Interactive visualization** with:
- Drag-and-drop force-directed graph
- Color-coded entity types
- Size-coded hierarchy scales
- Click nodes to see source mementos
- Physics simulation for natural layout

**To view:** Open in any web browser

### 🗂️ `graph.cypher`
Neo4j Cypher script for database import:
- Creates all mementos as nodes
- Creates all entities as nodes
- Establishes relationships
- Links entities back to source mementos via `EXTRACTED_TO` relationships

**To use:**
```bash
# Option 1: Neo4j Browser
# Copy/paste into Neo4j Browser at http://localhost:7474

# Option 2: cypher-shell
cat graph.cypher | cypher-shell -u neo4j -p yourpassword
```

### 📐 `graph.mmd`
Mermaid diagram for quick visualization:
- Hierarchical layout
- Relationship labels
- Color-coded by entity type

**To render:**
- GitHub/GitLab (renders automatically)
- VS Code (with Mermaid extension)
- Online: https://mermaid.live

## Multi-Scale Architecture

### Domain Scale (Highest Level)
- **User** - The person (you)
- **AI Memory Systems** - The broader field

### System Scale
- **Memento Project** - The complete system being built

### Component Scale
- **Neo4j** - Graph database
- **FastMCP** - Python framework
- **Model Context Protocol** - Integration protocol
- **Local Embeddings** - Semantic search component

### Atomic Scale (Finest Detail)
- **Feature Branch** - Current working branch
- **Agent Isolation** - Isolation concept
- **Tasks** - Specific implementation work
- **ADR-006** - Architectural decision
- **Preferences** - Your stated preferences

## Key Insights from the Graph

1. **You value hierarchy and structure** - evident from preference nodes
2. **Memento uses a layered architecture** - MCP → Neo4j → Embeddings
3. **Isolation is important** - both conceptually and practically (branch)
4. **Client-side intelligence** - ADR-006 guides architectural decisions
5. **Active development** - 2 tasks in progress, building toward demo

## Data Flow

```
Raw Conversation
      ↓
  Mementos (m001-m015)
      ↓
  Entity Extraction
      ↓
  Entities (e_user, e_memento, etc.)
      ↓
  Relationship Mapping
      ↓
  Knowledge Graph
```

## Running the Demo

```bash
# Generate all outputs
python3 knowledge_graph_demo.py

# View interactive visualization
open interactive_graph.html

# Or on Linux
xdg-open interactive_graph.html
```

## Statistics

- **15 raw mementos** → original observations
- **14 entities** → structured concepts
- **16 relationships** → connections
- **4 scales** → levels of hierarchy
- **6 entity types** → Person, Project, Technology, Concept, Task, Preference

## Why This Matters for Memento

This demo proves the core concept:

1. **Mementos are preserved** - raw data never lost
2. **Surgical extraction** - entities cleanly pulled from source
3. **Multi-scale organization** - from high-level concepts to specific details
4. **Relationship-rich** - not just facts, but how they connect
5. **Queryable at any level** - can zoom in/out through the hierarchy

This is exactly what Memento will do for LLM memory - transform unstructured conversation into queryable knowledge graphs!

---

**Generated:** 2025-11-16
**Session:** claude/knowledge-graph-prototype-016woGkvRjndwTdvaeEGhz73
**Isolated Environment:** ✓
