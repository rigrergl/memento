"""MCP server exposing remember and recall tools via HTTP transport."""
from fastmcp import FastMCP

from src.graph.neo4j import Neo4jRepository
from src.memory.service import MemoryService
from src.utils.config import Config
from src.utils.factory import Factory

config = Config()
embedder = Factory.create_embedder(config)
repository = Neo4jRepository(uri=config.neo4j_uri, user=config.neo4j_user, password=config.neo4j_password)
service = MemoryService(config=config, embedder=embedder, repository=repository)

mcp = FastMCP("Memento")


@mcp.tool()
def remember(content: str, confidence: float) -> str:
    """Store a memory with the given content and confidence score."""
    try:
        memory = service.store_memory(content, confidence)
        return f"Memory stored with id: {memory.id}"
    except ValueError as e:
        return str(e)
    except Exception:
        return "Failed to store memory: unexpected error. Please try again."


@mcp.tool()
def recall(query: str, limit: int = 10) -> str:
    """Search stored memories semantically and return matching results."""
    try:
        results = service.search_memory(query, limit)
        if not results:
            return f'No memories found for "{query}".'
        lines = [f'Found {len(results)} result(s) for "{query}":']
        for i, (memory, score) in enumerate(results, 1):
            lines.append(f"{i}. (score: {score:.3f}) {memory.content}")
        return "\n".join(lines)
    except ValueError as e:
        return str(e)
    except Exception:
        return "Failed to search memories: unexpected error. Please try again."


if __name__ == "__main__":
    repository.ensure_vector_index()
    mcp.run(transport="http", host=config.mcp_host, port=config.mcp_port)
