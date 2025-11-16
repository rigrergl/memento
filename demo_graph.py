#!/usr/bin/env python3
"""
WOW-Factor Knowledge Graph Demo
Demonstrates hierarchical memory organization with entities and relationships
"""
import json
from datetime import datetime
from typing import List, Dict, Tuple
from dataclasses import dataclass, asdict
from collections import defaultdict
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from embeddings.local_embedding_provider import LocalEmbeddingProvider


@dataclass
class Memento:
    """Raw memory - the atomic unit of knowledge"""
    id: str
    content: str
    timestamp: str
    embedding: List[float] = None


@dataclass
class Entity:
    """Extracted entity with type and properties"""
    id: str
    type: str  # Person, Project, Concept, Preference, etc.
    name: str
    properties: Dict
    source_mementos: List[str]  # Which mementos mention this entity


@dataclass
class Relationship:
    """Connection between entities"""
    from_entity: str
    to_entity: str
    relation_type: str
    strength: float
    evidence: List[str]  # Memento IDs that support this relationship


class KnowledgeGraph:
    """In-memory knowledge graph with hierarchical organization"""

    def __init__(self, embedding_provider):
        self.mementos: Dict[str, Memento] = {}
        self.entities: Dict[str, Entity] = {}
        self.relationships: List[Relationship] = []
        self.embedder = embedding_provider
        self.hierarchy = defaultdict(list)  # type -> entities

    def add_memento(self, content: str) -> Memento:
        """Store a raw memento with embedding"""
        memento_id = f"m{len(self.mementos) + 1}"
        embedding = self.embedder.generate_embedding(content)

        memento = Memento(
            id=memento_id,
            content=content,
            timestamp=datetime.now().isoformat(),
            embedding=embedding
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

    def find_similar_mementos(self, query: str, top_k: int = 3) -> List[Tuple[Memento, float]]:
        """Semantic search across mementos"""
        query_emb = self.embedder.generate_embedding(query)

        similarities = []
        for memento in self.mementos.values():
            # Cosine similarity
            dot_product = sum(a * b for a, b in zip(query_emb, memento.embedding))
            norm_q = sum(a * a for a in query_emb) ** 0.5
            norm_m = sum(b * b for b in memento.embedding) ** 0.5
            similarity = dot_product / (norm_q * norm_m)
            similarities.append((memento, similarity))

        similarities.sort(key=lambda x: x[1], reverse=True)
        return similarities[:top_k]

    def visualize(self):
        """Beautiful graph visualization"""
        print("\n" + "="*80)
        print("🧠 MEMENTO KNOWLEDGE GRAPH DEMO")
        print("="*80)

        # Layer 1: Raw Mementos
        print("\n📝 LAYER 1: RAW MEMENTOS (Atomic Knowledge Units)")
        print("-" * 80)
        for m_id, memento in self.mementos.items():
            print(f"  [{m_id}] {memento.content}")
            print(f"         └─ Embedding: {len(memento.embedding)}D vector")

        # Layer 2: Entities by Type (Hierarchical)
        print("\n🎯 LAYER 2: EXTRACTED ENTITIES (Organized by Type)")
        print("-" * 80)
        for entity_type in sorted(self.hierarchy.keys()):
            print(f"\n  📂 {entity_type.upper()}")
            for entity_id in self.hierarchy[entity_type]:
                entity = self.entities[entity_id]
                print(f"     ├─ [{entity.id}] {entity.name}")
                for key, value in entity.properties.items():
                    print(f"     │  └─ {key}: {value}")
                print(f"     └─ Sources: {', '.join(entity.source_mementos)}")

        # Layer 3: Relationships (Graph Connections)
        print("\n🔗 LAYER 3: RELATIONSHIPS (Semantic Connections)")
        print("-" * 80)
        for rel in self.relationships:
            from_name = self.entities[rel.from_entity].name
            to_name = self.entities[rel.to_entity].name
            strength_bar = "█" * int(rel.strength * 10)
            print(f"  {from_name}")
            print(f"     └─[{rel.relation_type}]──> {to_name}")
            print(f"        Strength: {strength_bar} ({rel.strength:.2f})")
            print(f"        Evidence: {', '.join(rel.evidence)}")

        # Bonus: Semantic Search Demo
        print("\n🔍 SEMANTIC SEARCH DEMO")
        print("-" * 80)
        queries = ["What does the user care about?", "User's communication style"]
        for query in queries:
            print(f"\n  Query: '{query}'")
            results = self.find_similar_mementos(query, top_k=2)
            for memento, score in results:
                print(f"    └─ [{memento.id}] (similarity: {score:.3f}) {memento.content}")

        # Stats
        print("\n📊 GRAPH STATISTICS")
        print("-" * 80)
        print(f"  Total Mementos: {len(self.mementos)}")
        print(f"  Total Entities: {len(self.entities)}")
        print(f"  Total Relationships: {len(self.relationships)}")
        print(f"  Entity Types: {len(self.hierarchy)}")
        print(f"  Embedding Dimensions: {self.embedder.dimension()}")
        print("\n" + "="*80 + "\n")


def main():
    print("Loading embedding model...")
    embedder = LocalEmbeddingProvider(
        model_name="all-MiniLM-L6-v2",
        cache_dir=".cache/models"
    )

    print("Building knowledge graph from conversation...\n")
    graph = KnowledgeGraph(embedder)

    # Store raw mementos about the user
    m1 = graph.add_memento("User asked about glob patterns in Claude Code context")
    m2 = graph.add_memento("User uses casual language like 'Aight cool'")
    m3 = graph.add_memento("User is working on Memento project - a knowledge graph system")
    m4 = graph.add_memento("User wants to see hierarchy, entities, and relationships in the demo")
    m5 = graph.add_memento("User emphasizes keeping things simple and efficient")
    m6 = graph.add_memento("User wants WOW factor in the demonstration")
    m7 = graph.add_memento("User mentioned organizing data surgically into structure at different scales")
    m8 = graph.add_memento("User is interested in knowledge graphs with raw 'Mementos' as base layer")

    # Extract entities from mementos
    user = graph.add_entity(
        entity_type="Person",
        name="User",
        properties={
            "communication_style": "casual, direct",
            "technical_level": "advanced",
            "current_focus": "knowledge graphs"
        },
        source_mementos=[m1.id, m2.id, m3.id]
    )

    project = graph.add_entity(
        entity_type="Project",
        name="Memento",
        properties={
            "type": "knowledge graph system",
            "status": "in development",
            "key_feature": "hierarchical memory organization"
        },
        source_mementos=[m3.id, m8.id]
    )

    design_principle_1 = graph.add_entity(
        entity_type="Design Principle",
        name="Simplicity",
        properties={
            "description": "Keep it simple and efficient",
            "priority": "high"
        },
        source_mementos=[m5.id]
    )

    design_principle_2 = graph.add_entity(
        entity_type="Design Principle",
        name="Surgical Organization",
        properties={
            "description": "Organize data surgically at different scales",
            "applies_to": "hierarchy, entities, relationships"
        },
        source_mementos=[m7.id, m4.id]
    )

    concept = graph.add_entity(
        entity_type="Concept",
        name="Multi-Scale Knowledge",
        properties={
            "layers": "raw mementos, entities, relationships, hierarchy",
            "purpose": "organize information at different abstraction levels"
        },
        source_mementos=[m4.id, m7.id, m8.id]
    )

    tool = graph.add_entity(
        entity_type="Tool",
        name="Claude Code",
        properties={
            "type": "AI coding assistant",
            "feature_of_interest": "glob patterns"
        },
        source_mementos=[m1.id]
    )

    # Create relationships
    graph.add_relationship(
        user.id, project.id,
        relation="WORKS_ON",
        strength=1.0,
        evidence=[m3.id]
    )

    graph.add_relationship(
        user.id, design_principle_1.id,
        relation="VALUES",
        strength=0.9,
        evidence=[m5.id]
    )

    graph.add_relationship(
        user.id, design_principle_2.id,
        relation="VALUES",
        strength=0.9,
        evidence=[m7.id, m4.id]
    )

    graph.add_relationship(
        project.id, concept.id,
        relation="IMPLEMENTS",
        strength=1.0,
        evidence=[m8.id, m4.id]
    )

    graph.add_relationship(
        design_principle_2.id, concept.id,
        relation="GUIDES",
        strength=0.8,
        evidence=[m7.id]
    )

    graph.add_relationship(
        user.id, tool.id,
        relation="USES",
        strength=0.7,
        evidence=[m1.id]
    )

    # Visualize the complete graph
    graph.visualize()


if __name__ == "__main__":
    main()
