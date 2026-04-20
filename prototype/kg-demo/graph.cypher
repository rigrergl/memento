// Knowledge Graph Demo - Neo4j Cypher Script

// Clean slate
MATCH (n) DETACH DELETE n;

// ============ RAW MEMENTOS ============
CREATE (:m001:Memento {
  id: "m001",
  content: "User is working on a project called Memento",
  timestamp: datetime("2025-11-16T00:01:00Z"),
  source: "conversation"
});
CREATE (:m002:Memento {
  id: "m002",
  content: "Memento is an MCP server that provides persistent memory for LLMs",
  timestamp: datetime("2025-11-16T00:01:30Z"),
  source: "conversation"
});
CREATE (:m003:Memento {
  id: "m003",
  content: "The project uses Python with FastMCP framework",
  timestamp: datetime("2025-11-16T00:02:00Z"),
  source: "conversation"
});
CREATE (:m004:Memento {
  id: "m004",
  content: "The project uses Neo4j for graph-based vector storage",
  timestamp: datetime("2025-11-16T00:02:15Z"),
  source: "conversation"
});
CREATE (:m005:Memento {
  id: "m005",
  content: "User is working in an isolated cloud environment",
  timestamp: datetime("2025-11-16T00:03:00Z"),
  source: "conversation"
});
CREATE (:m006:Memento {
  id: "m006",
  content: "Current branch is claude/knowledge-graph-prototype-016woGkvRjndwTdvaeEGhz73",
  timestamp: datetime("2025-11-16T00:03:15Z"),
  source: "conversation"
});
CREATE (:m007:Memento {
  id: "m007",
  content: "User cares about isolation from other agents",
  timestamp: datetime("2025-11-16T00:04:00Z"),
  source: "conversation"
});
CREATE (:m008:Memento {
  id: "m008",
  content: "The project has two main tasks in progress: local embeddings and basic demo",
  timestamp: datetime("2025-11-16T00:04:30Z"),
  source: "conversation"
});
CREATE (:m009:Memento {
  id: "m009",
  content: "User wants to see knowledge organized with hierarchy, entities, and relationships",
  timestamp: datetime("2025-11-16T00:05:00Z"),
  source: "conversation"
});
CREATE (:m010:Memento {
  id: "m010",
  content: "User values the WOW factor in visualizations",
  timestamp: datetime("2025-11-16T00:05:15Z"),
  source: "conversation"
});
CREATE (:m011:Memento {
  id: "m011",
  content: "The project uses sentence-transformers for local embeddings",
  timestamp: datetime("2025-11-16T00:05:30Z"),
  source: "conversation"
});
CREATE (:m012:Memento {
  id: "m012",
  content: "User distinguishes between raw 'Mementos' and structured knowledge",
  timestamp: datetime("2025-11-16T00:05:45Z"),
  source: "conversation"
});
CREATE (:m013:Memento {
  id: "m013",
  content: "The architecture leverages client LLM instead of server-side LLM (ADR-006)",
  timestamp: datetime("2025-11-16T00:06:00Z"),
  source: "conversation"
});
CREATE (:m014:Memento {
  id: "m014",
  content: "Neo4j supports both graph relationships and vector embeddings in single database",
  timestamp: datetime("2025-11-16T00:06:15Z"),
  source: "conversation"
});
CREATE (:m015:Memento {
  id: "m015",
  content: "User asked about worktrees and operating system - they are technical",
  timestamp: datetime("2025-11-16T00:06:30Z"),
  source: "conversation"
});

// ============ ENTITIES ============
CREATE (:e_user:Person {
  id: "e_user",
  name: "User",
  scale: "domain",
  role: "developer", expertise: "technical"
});
CREATE (:e_ai_memory:Concept {
  id: "e_ai_memory",
  name: "AI Memory Systems",
  scale: "domain",
  domain: "artificial_intelligence", subdomain: "memory"
});
CREATE (:e_memento:Project {
  id: "e_memento",
  name: "Memento Project",
  scale: "system",
  status: "in_development", purpose: "LLM persistent memory"
});
CREATE (:e_neo4j:Technology {
  id: "e_neo4j",
  name: "Neo4j",
  scale: "component",
  category: "database", features: "graph+vector"
});
CREATE (:e_fastmcp:Technology {
  id: "e_fastmcp",
  name: "FastMCP",
  scale: "component",
  category: "framework", language: "python"
});
CREATE (:e_mcp:Technology {
  id: "e_mcp",
  name: "Model Context Protocol",
  scale: "component",
  category: "protocol", purpose: "LLM tool integration"
});
CREATE (:e_embeddings:Technology {
  id: "e_embeddings",
  name: "Local Embeddings",
  scale: "component",
  provider: "sentence-transformers", model: "all-MiniLM-L6-v2"
});
CREATE (:e_branch:Concept {
  id: "e_branch",
  name: "Feature Branch",
  scale: "atomic",
  name: "claude/knowledge-graph-prototype-016woGkvRjndwTdvaeEGhz73"
});
CREATE (:e_isolation:Concept {
  id: "e_isolation",
  name: "Agent Isolation",
  scale: "atomic",
  importance: "high", reason: "prevent interference"
});
CREATE (:e_task_embeddings:Task {
  id: "e_task_embeddings",
  name: "Implement Local Embeddings",
  scale: "atomic",
  status: "in_progress", epic: "core_components"
});
CREATE (:e_task_demo:Task {
  id: "e_task_demo",
  name: "Basic Demo",
  scale: "atomic",
  status: "in_progress", epic: "core_components"
});
CREATE (:e_adr006:Concept {
  id: "e_adr006",
  name: "ADR-006: Leverage Client LLM",
  scale: "atomic",
  decision: "use_client_llm", principle: "YAGNI"
});
CREATE (:e_pref_hierarchy:Preference {
  id: "e_pref_hierarchy",
  name: "Preference: Hierarchical Organization",
  scale: "atomic",
  valued: "hierarchy, entities, relationships"
});
CREATE (:e_pref_wow:Preference {
  id: "e_pref_wow",
  name: "Preference: WOW Factor",
  scale: "atomic",
  valued: "impressive visualizations"
});

// ============ RELATIONSHIPS ============
MATCH (s:e_user), (t:e_memento)
CREATE (s)-[:WORKS_ON {role: "creator"}]->(t);
MATCH (s:e_user), (t:e_isolation)
CREATE (s)-[:VALUES {priority: "high"}]->(t);
MATCH (s:e_user), (t:e_pref_hierarchy)
CREATE (s)-[:HAS_PREFERENCE]->(t);
MATCH (s:e_user), (t:e_pref_wow)
CREATE (s)-[:HAS_PREFERENCE]->(t);
MATCH (s:e_memento), (t:e_ai_memory)
CREATE (s)-[:BELONGS_TO_DOMAIN]->(t);
MATCH (s:e_memento), (t:e_mcp)
CREATE (s)-[:IMPLEMENTS {role: "server"}]->(t);
MATCH (s:e_memento), (t:e_fastmcp)
CREATE (s)-[:USES {purpose: "framework"}]->(t);
MATCH (s:e_memento), (t:e_neo4j)
CREATE (s)-[:USES {purpose: "storage"}]->(t);
MATCH (s:e_memento), (t:e_embeddings)
CREATE (s)-[:USES {purpose: "semantic_search"}]->(t);
MATCH (s:e_neo4j), (t:e_embeddings)
CREATE (s)-[:STORES {data_type: "vector_embeddings"}]->(t);
MATCH (s:e_adr006), (t:e_memento)
CREATE (s)-[:GUIDES {aspect: "architecture"}]->(t);
MATCH (s:e_task_embeddings), (t:e_memento)
CREATE (s)-[:CONTRIBUTES_TO {phase: "1"}]->(t);
MATCH (s:e_task_demo), (t:e_memento)
CREATE (s)-[:CONTRIBUTES_TO {phase: "1"}]->(t);
MATCH (s:e_task_embeddings), (t:e_embeddings)
CREATE (s)-[:IMPLEMENTS]->(t);
MATCH (s:e_branch), (t:e_isolation)
CREATE (s)-[:PROVIDES {mechanism: "git_branch"}]->(t);
MATCH (s:e_user), (t:e_branch)
CREATE (s)-[:WORKS_IN {environment: "cloud"}]->(t);

// ============ MEMENTO -> ENTITY EXTRACTION ============
MATCH (m:m001), (e:e_user)
CREATE (m)-[:EXTRACTED_TO]->(e);
MATCH (m:m007), (e:e_user)
CREATE (m)-[:EXTRACTED_TO]->(e);
MATCH (m:m009), (e:e_user)
CREATE (m)-[:EXTRACTED_TO]->(e);
MATCH (m:m015), (e:e_user)
CREATE (m)-[:EXTRACTED_TO]->(e);
MATCH (m:m002), (e:e_ai_memory)
CREATE (m)-[:EXTRACTED_TO]->(e);
MATCH (m:m012), (e:e_ai_memory)
CREATE (m)-[:EXTRACTED_TO]->(e);
MATCH (m:m001), (e:e_memento)
CREATE (m)-[:EXTRACTED_TO]->(e);
MATCH (m:m002), (e:e_memento)
CREATE (m)-[:EXTRACTED_TO]->(e);
MATCH (m:m003), (e:e_memento)
CREATE (m)-[:EXTRACTED_TO]->(e);
MATCH (m:m004), (e:e_neo4j)
CREATE (m)-[:EXTRACTED_TO]->(e);
MATCH (m:m014), (e:e_neo4j)
CREATE (m)-[:EXTRACTED_TO]->(e);
MATCH (m:m003), (e:e_fastmcp)
CREATE (m)-[:EXTRACTED_TO]->(e);
MATCH (m:m002), (e:e_mcp)
CREATE (m)-[:EXTRACTED_TO]->(e);
MATCH (m:m008), (e:e_embeddings)
CREATE (m)-[:EXTRACTED_TO]->(e);
MATCH (m:m011), (e:e_embeddings)
CREATE (m)-[:EXTRACTED_TO]->(e);
MATCH (m:m006), (e:e_branch)
CREATE (m)-[:EXTRACTED_TO]->(e);
MATCH (m:m005), (e:e_isolation)
CREATE (m)-[:EXTRACTED_TO]->(e);
MATCH (m:m007), (e:e_isolation)
CREATE (m)-[:EXTRACTED_TO]->(e);
MATCH (m:m008), (e:e_task_embeddings)
CREATE (m)-[:EXTRACTED_TO]->(e);
MATCH (m:m008), (e:e_task_demo)
CREATE (m)-[:EXTRACTED_TO]->(e);
MATCH (m:m013), (e:e_adr006)
CREATE (m)-[:EXTRACTED_TO]->(e);
MATCH (m:m009), (e:e_pref_hierarchy)
CREATE (m)-[:EXTRACTED_TO]->(e);
MATCH (m:m010), (e:e_pref_wow)
CREATE (m)-[:EXTRACTED_TO]->(e);