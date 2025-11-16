#!/usr/bin/env python3
"""
WOW-Factor Knowledge Graph Demo (Simplified - No Dependencies)
Demonstrates hierarchical memory organization with entities and relationships
"""
import json
from datetime import datetime
from typing import List, Dict
from dataclasses import dataclass
from collections import defaultdict


@dataclass
class Memento:
    """Raw memory - the atomic unit of knowledge"""
    id: str
    content: str
    timestamp: str


@dataclass
class Entity:
    """Extracted entity with type and properties"""
    id: str
    type: str
    name: str
    properties: Dict
    source_mementos: List[str]


@dataclass
class Relationship:
    """Connection between entities"""
    from_entity: str
    to_entity: str
    relation_type: str
    strength: float
    evidence: List[str]


class KnowledgeGraph:
    """In-memory knowledge graph with hierarchical organization"""

    def __init__(self):
        self.mementos: Dict[str, Memento] = {}
        self.entities: Dict[str, Entity] = {}
        self.relationships: List[Relationship] = []
        self.hierarchy = defaultdict(list)

    def add_memento(self, content: str) -> Memento:
        """Store a raw memento"""
        memento_id = f"m{len(self.mementos) + 1}"
        memento = Memento(
            id=memento_id,
            content=content,
            timestamp=datetime.now().isoformat()
        )
        self.mementos[memento_id] = memento
        return memento

    def add_entity(self, entity_type: str, name: str, properties: Dict, source_mementos: List[str]) -> Entity:
        """Extract and store an entity"""
        entity_id = f"e{len(self.entities) + 1}_{entity_type.lower()}"
        entity = Entity(
            id=entity_id,
            type=entity_type,
            name=name,
            properties=properties,
            source_mementos=source_mementos
        )
        self.entities[entity_id] = entity
        self.hierarchy[entity_type].append(entity_id)
        return entity

    def add_relationship(self, from_id: str, to_id: str, relation: str, strength: float, evidence: List[str]):
        """Create a relationship between entities"""
        rel = Relationship(
            from_entity=from_id,
            to_entity=to_id,
            relation_type=relation,
            strength=strength,
            evidence=evidence
        )
        self.relationships.append(rel)
        return rel

    def visualize(self):
        """Beautiful graph visualization"""
        print("\n" + "="*80)
        print("🧠 MEMENTO KNOWLEDGE GRAPH - LIVE DEMO")
        print("="*80)
        print("\nShowing multi-scale knowledge organization:")
        print("  Layer 1: Raw Mementos (atomic observations)")
        print("  Layer 2: Entities (organized by type hierarchy)")
        print("  Layer 3: Relationships (semantic connections)")
        print("\n" + "="*80)

        # Layer 1: Raw Mementos
        print("\n┌─ 📝 LAYER 1: RAW MEMENTOS")
        print("│  Atomic knowledge units - exactly as observed")
        print("└─" + "─"*77)
        for i, (m_id, memento) in enumerate(self.mementos.items(), 1):
            connector = "├─" if i < len(self.mementos) else "└─"
            print(f"   {connector} [{m_id}] {memento.content}")
            print(f"   │     ⏱  {memento.timestamp[:19]}")

        # Layer 2: Entities by Type (Hierarchical)
        print("\n┌─ 🎯 LAYER 2: EXTRACTED ENTITIES")
        print("│  Structured knowledge organized by type hierarchy")
        print("└─" + "─"*77)

        type_count = len(self.hierarchy)
        for idx, (entity_type, entity_ids) in enumerate(sorted(self.hierarchy.items()), 1):
            type_connector = "├─" if idx < type_count else "└─"
            print(f"\n   {type_connector} 📂 {entity_type.upper()}")

            for i, entity_id in enumerate(entity_ids, 1):
                entity = self.entities[entity_id]
                entity_connector = "├─" if i < len(entity_ids) else "└─"

                print(f"   │  {entity_connector} 🔹 {entity.name} [{entity.id}]")

                # Properties
                prop_count = len(entity.properties)
                for p_idx, (key, value) in enumerate(entity.properties.items(), 1):
                    prop_connector = "├─" if p_idx < prop_count else "└─"
                    if i < len(entity_ids):
                        print(f"   │  │  {prop_connector} {key}: {value}")
                    else:
                        print(f"   │     {prop_connector} {key}: {value}")

                # Sources
                source_text = ", ".join(entity.source_mementos)
                if i < len(entity_ids):
                    print(f"   │  │  └─ 🔗 Sources: {source_text}")
                else:
                    print(f"   │     └─ 🔗 Sources: {source_text}")

        # Layer 3: Relationships (Graph Connections)
        print("\n┌─ 🔗 LAYER 3: RELATIONSHIPS")
        print("│  Semantic connections forming the knowledge graph")
        print("└─" + "─"*77)

        for i, rel in enumerate(self.relationships, 1):
            connector = "├─" if i < len(self.relationships) else "└─"
            from_entity = self.entities[rel.from_entity]
            to_entity = self.entities[rel.to_entity]

            # Strength visualization
            strength_bar = "█" * int(rel.strength * 10)
            empty_bar = "░" * (10 - int(rel.strength * 10))

            print(f"\n   {connector} {from_entity.name} ({from_entity.type})")
            print(f"   │     ↓ [{rel.relation_type}]")
            print(f"   │     → {to_entity.name} ({to_entity.type})")
            print(f"   │     ├─ Strength: {strength_bar}{empty_bar} ({rel.strength:.1f})")
            print(f"   │     └─ Evidence: {', '.join(rel.evidence)}")

        # Graph Statistics
        print("\n┌─ 📊 GRAPH STATISTICS")
        print("└─" + "─"*77)
        print(f"   ├─ Total Mementos (raw memories): {len(self.mementos)}")
        print(f"   ├─ Total Entities (extracted): {len(self.entities)}")
        print(f"   ├─ Total Relationships (connections): {len(self.relationships)}")
        print(f"   ├─ Entity Types (hierarchy depth): {len(self.hierarchy)}")
        print(f"   └─ Average connections per entity: {len(self.relationships) / len(self.entities):.1f}")

        # Knowledge Density Visualization
        print("\n┌─ 🌐 KNOWLEDGE DENSITY MAP")
        print("└─" + "─"*77)

        # Count relationships per entity
        entity_connections = defaultdict(int)
        for rel in self.relationships:
            entity_connections[rel.from_entity] += 1
            entity_connections[rel.to_entity] += 1

        for entity_id, count in sorted(entity_connections.items(), key=lambda x: x[1], reverse=True):
            entity = self.entities[entity_id]
            density_bar = "●" * count + "○" * (max(0, 5 - count))
            print(f"   ├─ {entity.name:30s} {density_bar} ({count} connections)")

        print("\n" + "="*80)
        print("✨ WOW FACTOR ELEMENTS:")
        print("   • Multi-scale organization: raw → structured → connected")
        print("   • Hierarchical entity types: automatic categorization")
        print("   • Relationship strength: weighted connections with evidence")
        print("   • Surgical precision: each fact traced to original sources")
        print("   • Graph density: visualized knowledge interconnectedness")
        print("="*80 + "\n")


def main():
    print("🚀 Building knowledge graph from conversation...")
    graph = KnowledgeGraph()

    # Store raw mementos about the user
    print("   ⚡ Storing raw mementos...")
    m1 = graph.add_memento("User asked about glob patterns in Claude Code context")
    m2 = graph.add_memento("User uses casual language like 'Aight cool'")
    m3 = graph.add_memento("User is working on Memento project - a knowledge graph system")
    m4 = graph.add_memento("User wants to see hierarchy, entities, and relationships in the demo")
    m5 = graph.add_memento("User emphasizes keeping things simple and efficient")
    m6 = graph.add_memento("User wants WOW factor in the demonstration")
    m7 = graph.add_memento("User mentioned organizing data surgically into structure at different scales")
    m8 = graph.add_memento("User is interested in knowledge graphs with raw 'Mementos' as base layer")
    m9 = graph.add_memento("User values YAGNI and KISS principles in development")
    m10 = graph.add_memento("User is currently on branch claude/explain-glob-patterns-*")

    # Extract entities from mementos
    print("   ⚡ Extracting entities...")
    user = graph.add_entity(
        entity_type="Person",
        name="User",
        properties={
            "communication_style": "casual, direct ('Aight cool')",
            "technical_level": "advanced developer",
            "current_focus": "knowledge graphs & memory systems",
            "working_branch": "claude/explain-glob-patterns-*"
        },
        source_mementos=[m1.id, m2.id, m3.id, m10.id]
    )

    project = graph.add_entity(
        entity_type="Project",
        name="Memento",
        properties={
            "type": "MCP server for persistent LLM memory",
            "status": "active development",
            "architecture": "graph-based vector storage with Neo4j",
            "key_feature": "multi-scale hierarchical organization"
        },
        source_mementos=[m3.id, m8.id]
    )

    principle_simplicity = graph.add_entity(
        entity_type="Design Principle",
        name="KISS (Keep It Simple)",
        properties={
            "description": "Keep things simple and efficient",
            "priority": "core value",
            "application": "avoid over-engineering"
        },
        source_mementos=[m5.id, m9.id]
    )

    principle_yagni = graph.add_entity(
        entity_type="Design Principle",
        name="YAGNI (You Ain't Gonna Need It)",
        properties={
            "description": "Don't build features until needed",
            "priority": "core value",
            "application": "lean codebase"
        },
        source_mementos=[m9.id]
    )

    principle_surgical = graph.add_entity(
        entity_type="Design Principle",
        name="Surgical Organization",
        properties={
            "description": "Organize data surgically at different scales",
            "applies_to": "hierarchy, entities, relationships",
            "implementation": "multi-layer knowledge structure"
        },
        source_mementos=[m7.id, m4.id]
    )

    concept_multiscale = graph.add_entity(
        entity_type="Concept",
        name="Multi-Scale Knowledge",
        properties={
            "layers": "raw mementos → entities → relationships → hierarchy",
            "purpose": "organize information at multiple abstraction levels",
            "benefit": "trace high-level concepts back to atomic facts"
        },
        source_mementos=[m4.id, m7.id, m8.id]
    )

    requirement = graph.add_entity(
        entity_type="Requirement",
        name="WOW Factor",
        properties={
            "description": "Demo must be impressive and compelling",
            "elements": "visualization, clarity, power",
            "target": "demonstrate system capabilities"
        },
        source_mementos=[m6.id]
    )

    tool = graph.add_entity(
        entity_type="Tool",
        name="Claude Code",
        properties={
            "type": "AI coding assistant",
            "feature_of_interest": "glob patterns for file matching",
            "usage_context": "development workflow"
        },
        source_mementos=[m1.id]
    )

    # Create relationships
    print("   ⚡ Building relationship graph...")

    graph.add_relationship(
        user.id, project.id,
        relation="WORKS_ON",
        strength=1.0,
        evidence=[m3.id]
    )

    graph.add_relationship(
        user.id, principle_simplicity.id,
        relation="VALUES",
        strength=0.95,
        evidence=[m5.id, m9.id]
    )

    graph.add_relationship(
        user.id, principle_yagni.id,
        relation="VALUES",
        strength=0.95,
        evidence=[m9.id]
    )

    graph.add_relationship(
        user.id, principle_surgical.id,
        relation="VALUES",
        strength=0.9,
        evidence=[m7.id, m4.id]
    )

    graph.add_relationship(
        user.id, requirement.id,
        relation="REQUIRES",
        strength=1.0,
        evidence=[m6.id]
    )

    graph.add_relationship(
        project.id, concept_multiscale.id,
        relation="IMPLEMENTS",
        strength=1.0,
        evidence=[m8.id, m4.id]
    )

    graph.add_relationship(
        principle_surgical.id, concept_multiscale.id,
        relation="GUIDES",
        strength=0.85,
        evidence=[m7.id, m4.id]
    )

    graph.add_relationship(
        principle_simplicity.id, project.id,
        relation="CONSTRAINS",
        strength=0.8,
        evidence=[m5.id]
    )

    graph.add_relationship(
        principle_yagni.id, project.id,
        relation="CONSTRAINS",
        strength=0.8,
        evidence=[m9.id]
    )

    graph.add_relationship(
        user.id, tool.id,
        relation="USES",
        strength=0.7,
        evidence=[m1.id]
    )

    graph.add_relationship(
        requirement.id, concept_multiscale.id,
        relation="DEMANDS",
        strength=0.75,
        evidence=[m6.id, m4.id]
    )

    # Visualize the complete graph
    print("   ✅ Graph built!\n")
    graph.visualize()


if __name__ == "__main__":
    main()
