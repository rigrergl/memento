#!/usr/bin/env python3
"""
Knowledge Graph Demo: Multi-Scale Memory Organization
Demonstrates raw mementos → structured knowledge graph with hierarchy
"""

import json
from dataclasses import dataclass, asdict
from typing import List, Dict, Set
from datetime import datetime
from collections import defaultdict

# ============================================================================
# LAYER 1: RAW MEMENTOS (Original Unstructured Data)
# ============================================================================

@dataclass
class Memento:
    """Raw memory - the original unstructured observation"""
    id: str
    content: str
    timestamp: str
    source: str = "conversation"

MEMENTOS = [
    Memento("m001", "User is working on a project called Memento", "2025-11-16T00:01:00Z"),
    Memento("m002", "Memento is an MCP server that provides persistent memory for LLMs", "2025-11-16T00:01:30Z"),
    Memento("m003", "The project uses Python with FastMCP framework", "2025-11-16T00:02:00Z"),
    Memento("m004", "The project uses Neo4j for graph-based vector storage", "2025-11-16T00:02:15Z"),
    Memento("m005", "User is working in an isolated cloud environment", "2025-11-16T00:03:00Z"),
    Memento("m006", "Current branch is claude/knowledge-graph-prototype-016woGkvRjndwTdvaeEGhz73", "2025-11-16T00:03:15Z"),
    Memento("m007", "User cares about isolation from other agents", "2025-11-16T00:04:00Z"),
    Memento("m008", "The project has two main tasks in progress: local embeddings and basic demo", "2025-11-16T00:04:30Z"),
    Memento("m009", "User wants to see knowledge organized with hierarchy, entities, and relationships", "2025-11-16T00:05:00Z"),
    Memento("m010", "User values the WOW factor in visualizations", "2025-11-16T00:05:15Z"),
    Memento("m011", "The project uses sentence-transformers for local embeddings", "2025-11-16T00:05:30Z"),
    Memento("m012", "User distinguishes between raw 'Mementos' and structured knowledge", "2025-11-16T00:05:45Z"),
    Memento("m013", "The architecture leverages client LLM instead of server-side LLM (ADR-006)", "2025-11-16T00:06:00Z"),
    Memento("m014", "Neo4j supports both graph relationships and vector embeddings in single database", "2025-11-16T00:06:15Z"),
    Memento("m015", "User asked about worktrees and operating system - they are technical", "2025-11-16T00:06:30Z"),
]

# ============================================================================
# LAYER 2: ENTITIES (Extracted Structured Concepts)
# ============================================================================

@dataclass
class Entity:
    """Structured entity extracted from mementos"""
    id: str
    name: str
    type: str  # Person, Project, Technology, Concept, Task
    properties: Dict
    scale: str  # atomic, component, system, domain
    extracted_from: List[str]  # memento IDs

@dataclass
class Relationship:
    """Connection between entities"""
    source: str
    target: str
    type: str
    properties: Dict
    extracted_from: List[str]

class KnowledgeGraph:
    """Multi-scale knowledge graph with hierarchy"""

    def __init__(self):
        self.mementos: List[Memento] = []
        self.entities: Dict[str, Entity] = {}
        self.relationships: List[Relationship] = []
        self.hierarchy: Dict[str, List[str]] = defaultdict(list)

    def add_memento(self, memento: Memento):
        """Add raw memento"""
        self.mementos.append(memento)

    def add_entity(self, entity: Entity):
        """Add extracted entity"""
        self.entities[entity.id] = entity

    def add_relationship(self, rel: Relationship):
        """Add relationship between entities"""
        self.relationships.append(rel)

    def add_hierarchy(self, parent: str, child: str):
        """Add hierarchical relationship"""
        self.hierarchy[parent].append(child)

    def to_mermaid(self) -> str:
        """Generate Mermaid diagram"""
        lines = ["graph TB"]
        lines.append("")
        lines.append("    %% === RAW MEMENTOS (Foundation Layer) ===")

        # Add entities by scale
        scales = ["domain", "system", "component", "atomic"]
        colors = {
            "Person": "#e1f5fe",
            "Project": "#f3e5f5",
            "Technology": "#fff3e0",
            "Concept": "#e8f5e9",
            "Task": "#fff9c4",
            "Preference": "#fce4ec"
        }

        for scale in scales:
            entities_in_scale = [e for e in self.entities.values() if e.scale == scale]
            if entities_in_scale:
                lines.append(f"    %% {scale.upper()} SCALE")
                for entity in entities_in_scale:
                    label = entity.name.replace('"', "'")
                    lines.append(f'    {entity.id}["{label}"]')
                lines.append("")

        # Add relationships
        lines.append("    %% === RELATIONSHIPS ===")
        for rel in self.relationships:
            label = rel.type.replace("_", " ")
            lines.append(f'    {rel.source} -->|{label}| {rel.target}')

        lines.append("")
        lines.append("    %% === STYLING ===")
        for eid, entity in self.entities.items():
            color = colors.get(entity.type, "#ffffff")
            lines.append(f"    style {eid} fill:{color}")

        return "\n".join(lines)

    def to_neo4j_cypher(self) -> str:
        """Generate Neo4j Cypher script"""
        lines = ["// Knowledge Graph Demo - Neo4j Cypher Script", ""]
        lines.append("// Clean slate")
        lines.append("MATCH (n) DETACH DELETE n;")
        lines.append("")

        # Create mementos
        lines.append("// ============ RAW MEMENTOS ============")
        for m in self.mementos:
            content = m.content.replace('"', '\\"')
            lines.append(f'CREATE (:{m.id}:Memento {{')
            lines.append(f'  id: "{m.id}",')
            lines.append(f'  content: "{content}",')
            lines.append(f'  timestamp: datetime("{m.timestamp}"),')
            lines.append(f'  source: "{m.source}"')
            lines.append('});')

        lines.append("")
        lines.append("// ============ ENTITIES ============")
        for e in self.entities.values():
            props = ", ".join([f'{k}: "{v}"' for k, v in e.properties.items()])
            lines.append(f'CREATE (:{e.id}:{e.type} {{')
            lines.append(f'  id: "{e.id}",')
            lines.append(f'  name: "{e.name}",')
            lines.append(f'  scale: "{e.scale}",')
            lines.append(f'  {props}')
            lines.append('});')

        lines.append("")
        lines.append("// ============ RELATIONSHIPS ============")
        for rel in self.relationships:
            rel_type = rel.type.upper().replace(" ", "_")
            props = ", ".join([f'{k}: "{v}"' for k, v in rel.properties.items()])
            props_str = f' {{{props}}}' if props else ''
            lines.append(f'MATCH (s:{rel.source}), (t:{rel.target})')
            lines.append(f'CREATE (s)-[:{rel_type}{props_str}]->(t);')

        lines.append("")
        lines.append("// ============ MEMENTO -> ENTITY EXTRACTION ============")
        for e in self.entities.values():
            for memento_id in e.extracted_from:
                lines.append(f'MATCH (m:{memento_id}), (e:{e.id})')
                lines.append(f'CREATE (m)-[:EXTRACTED_TO]->(e);')

        return "\n".join(lines)

    def to_json(self) -> str:
        """Export as JSON for analysis"""
        return json.dumps({
            "mementos": [asdict(m) for m in self.mementos],
            "entities": [asdict(e) for e in self.entities.values()],
            "relationships": [asdict(r) for r in self.relationships],
            "hierarchy": dict(self.hierarchy),
            "statistics": {
                "total_mementos": len(self.mementos),
                "total_entities": len(self.entities),
                "total_relationships": len(self.relationships),
                "entities_by_type": self._count_by_type(),
                "entities_by_scale": self._count_by_scale()
            }
        }, indent=2)

    def _count_by_type(self) -> Dict[str, int]:
        counts = defaultdict(int)
        for e in self.entities.values():
            counts[e.type] += 1
        return dict(counts)

    def _count_by_scale(self) -> Dict[str, int]:
        counts = defaultdict(int)
        for e in self.entities.values():
            counts[e.scale] += 1
        return dict(counts)

    def print_summary(self):
        """Print beautiful ASCII summary"""
        print("\n" + "="*80)
        print("🧠 KNOWLEDGE GRAPH DEMO: Multi-Scale Memory Organization")
        print("="*80)

        print(f"\n📝 RAW MEMENTOS: {len(self.mementos)} unstructured observations")
        print("-" * 80)
        for m in self.mementos[:5]:
            print(f"  [{m.id}] {m.content}")
        if len(self.mementos) > 5:
            print(f"  ... and {len(self.mementos) - 5} more")

        print(f"\n🎯 EXTRACTED ENTITIES: {len(self.entities)} structured concepts")
        print("-" * 80)

        # Group by scale
        for scale in ["domain", "system", "component", "atomic"]:
            entities = [e for e in self.entities.values() if e.scale == scale]
            if entities:
                print(f"\n  {scale.upper()} SCALE ({len(entities)} entities):")
                for e in entities:
                    sources = f"from {len(e.extracted_from)} mementos"
                    print(f"    • {e.name} ({e.type}) - {sources}")

        print(f"\n🔗 RELATIONSHIPS: {len(self.relationships)} connections")
        print("-" * 80)
        for rel in self.relationships[:10]:
            src = self.entities[rel.source].name
            tgt = self.entities[rel.target].name
            print(f"  {src} --[{rel.type}]--> {tgt}")
        if len(self.relationships) > 10:
            print(f"  ... and {len(self.relationships) - 10} more")

        print("\n" + "="*80)


# ============================================================================
# BUILD THE KNOWLEDGE GRAPH
# ============================================================================

def build_demo_graph() -> KnowledgeGraph:
    """Construct the knowledge graph from conversation"""
    kg = KnowledgeGraph()

    # Add all mementos
    for m in MEMENTOS:
        kg.add_memento(m)

    # DOMAIN SCALE: Highest level concepts
    kg.add_entity(Entity("e_user", "User", "Person",
        {"role": "developer", "expertise": "technical"},
        "domain", ["m001", "m007", "m009", "m015"]))

    kg.add_entity(Entity("e_ai_memory", "AI Memory Systems", "Concept",
        {"domain": "artificial_intelligence", "subdomain": "memory"},
        "domain", ["m002", "m012"]))

    # SYSTEM SCALE: Major projects/systems
    kg.add_entity(Entity("e_memento", "Memento Project", "Project",
        {"status": "in_development", "purpose": "LLM persistent memory"},
        "system", ["m001", "m002", "m003"]))

    # COMPONENT SCALE: Architectural components
    kg.add_entity(Entity("e_neo4j", "Neo4j", "Technology",
        {"category": "database", "features": "graph+vector"},
        "component", ["m004", "m014"]))

    kg.add_entity(Entity("e_fastmcp", "FastMCP", "Technology",
        {"category": "framework", "language": "python"},
        "component", ["m003"]))

    kg.add_entity(Entity("e_mcp", "Model Context Protocol", "Technology",
        {"category": "protocol", "purpose": "LLM tool integration"},
        "component", ["m002"]))

    kg.add_entity(Entity("e_embeddings", "Local Embeddings", "Technology",
        {"provider": "sentence-transformers", "model": "all-MiniLM-L6-v2"},
        "component", ["m008", "m011"]))

    # ATOMIC SCALE: Specific implementation details
    kg.add_entity(Entity("e_branch", "Feature Branch", "Concept",
        {"name": "claude/knowledge-graph-prototype-016woGkvRjndwTdvaeEGhz73"},
        "atomic", ["m006"]))

    kg.add_entity(Entity("e_isolation", "Agent Isolation", "Concept",
        {"importance": "high", "reason": "prevent interference"},
        "atomic", ["m005", "m007"]))

    kg.add_entity(Entity("e_task_embeddings", "Implement Local Embeddings", "Task",
        {"status": "in_progress", "epic": "core_components"},
        "atomic", ["m008"]))

    kg.add_entity(Entity("e_task_demo", "Basic Demo", "Task",
        {"status": "in_progress", "epic": "core_components"},
        "atomic", ["m008"]))

    kg.add_entity(Entity("e_adr006", "ADR-006: Leverage Client LLM", "Concept",
        {"decision": "use_client_llm", "principle": "YAGNI"},
        "atomic", ["m013"]))

    kg.add_entity(Entity("e_pref_hierarchy", "Preference: Hierarchical Organization", "Preference",
        {"valued": "hierarchy, entities, relationships"},
        "atomic", ["m009"]))

    kg.add_entity(Entity("e_pref_wow", "Preference: WOW Factor", "Preference",
        {"valued": "impressive visualizations"},
        "atomic", ["m010"]))

    # RELATIONSHIPS - Multi-scale connections

    # User relationships
    kg.add_relationship(Relationship("e_user", "e_memento", "WORKS_ON",
        {"role": "creator"}, ["m001"]))
    kg.add_relationship(Relationship("e_user", "e_isolation", "VALUES",
        {"priority": "high"}, ["m007"]))
    kg.add_relationship(Relationship("e_user", "e_pref_hierarchy", "HAS_PREFERENCE",
        {}, ["m009"]))
    kg.add_relationship(Relationship("e_user", "e_pref_wow", "HAS_PREFERENCE",
        {}, ["m010"]))

    # Project composition
    kg.add_relationship(Relationship("e_memento", "e_ai_memory", "BELONGS_TO_DOMAIN",
        {}, ["m002"]))
    kg.add_relationship(Relationship("e_memento", "e_mcp", "IMPLEMENTS",
        {"role": "server"}, ["m002"]))
    kg.add_relationship(Relationship("e_memento", "e_fastmcp", "USES",
        {"purpose": "framework"}, ["m003"]))
    kg.add_relationship(Relationship("e_memento", "e_neo4j", "USES",
        {"purpose": "storage"}, ["m004"]))
    kg.add_relationship(Relationship("e_memento", "e_embeddings", "USES",
        {"purpose": "semantic_search"}, ["m011"]))

    # Architectural relationships
    kg.add_relationship(Relationship("e_neo4j", "e_embeddings", "STORES",
        {"data_type": "vector_embeddings"}, ["m014"]))
    kg.add_relationship(Relationship("e_adr006", "e_memento", "GUIDES",
        {"aspect": "architecture"}, ["m013"]))

    # Task relationships
    kg.add_relationship(Relationship("e_task_embeddings", "e_memento", "CONTRIBUTES_TO",
        {"phase": "1"}, ["m008"]))
    kg.add_relationship(Relationship("e_task_demo", "e_memento", "CONTRIBUTES_TO",
        {"phase": "1"}, ["m008"]))
    kg.add_relationship(Relationship("e_task_embeddings", "e_embeddings", "IMPLEMENTS",
        {}, ["m008", "m011"]))

    # Development environment
    kg.add_relationship(Relationship("e_branch", "e_isolation", "PROVIDES",
        {"mechanism": "git_branch"}, ["m006", "m007"]))
    kg.add_relationship(Relationship("e_user", "e_branch", "WORKS_IN",
        {"environment": "cloud"}, ["m005", "m006"]))

    return kg


# ============================================================================
# GENERATE WOW FACTOR OUTPUTS
# ============================================================================

if __name__ == "__main__":
    print("\n🚀 Building Knowledge Graph from Conversation...")
    kg = build_demo_graph()

    # Print summary
    kg.print_summary()

    # Save outputs
    print("\n💾 Generating output files...")

    with open("/home/user/memento/prototype/kg-demo/graph.json", "w") as f:
        f.write(kg.to_json())
    print("  ✓ Saved: graph.json (structured data)")

    with open("/home/user/memento/prototype/kg-demo/graph.cypher", "w") as f:
        f.write(kg.to_neo4j_cypher())
    print("  ✓ Saved: graph.cypher (Neo4j visualization script)")

    with open("/home/user/memento/prototype/kg-demo/graph.mmd", "w") as f:
        f.write(kg.to_mermaid())
    print("  ✓ Saved: graph.mmd (Mermaid diagram)")

    print("\n✨ Knowledge Graph Demo Complete!")
    print("\n📊 Next steps:")
    print("  • View graph.json for full structured data")
    print("  • Load graph.cypher into Neo4j for interactive exploration")
    print("  • Render graph.mmd with Mermaid for quick visualization")
    print()
