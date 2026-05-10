"""MCP server exposing remember and recall tools via HTTP transport."""
import asyncio
from contextlib import asynccontextmanager
from typing import Annotated

from fastmcp import FastMCP
from pydantic import Field
from starlette.requests import Request
from starlette.responses import JSONResponse

from src.graph.neo4j import Neo4jRepository
from src.memory.service import MemoryService
from src.utils.config import Config
from src.utils.factory import Factory

service: MemoryService | None = None


@asynccontextmanager
async def lifespan(_mcp):
    global service
    config = Config()
    embedder = Factory.create_embedder(config)
    repository = Neo4jRepository(uri=config.neo4j_uri, user=config.neo4j_user, password=config.neo4j_password)
    try:
        await asyncio.to_thread(repository.ensure_vector_index)
        service = MemoryService(config=config, embedder=embedder, repository=repository)
        yield
    finally:
        await asyncio.to_thread(repository.close)


mcp = FastMCP("Memento", lifespan=lifespan)


@mcp.custom_route("/health", methods=["GET"])
async def health_check(request: Request) -> JSONResponse:
    return JSONResponse({"status": "ok"})


@mcp.tool()
def remember(
    content: Annotated[str, Field(description="The text to store as a memory. Must be non-empty and at most 4000 characters.")],
    confidence: Annotated[float, Field(description="How confident you are in this memory, from 0.0 (uncertain) to 1.0 (certain). Values outside [0, 1] are rejected.")],
) -> str:
    """Store a memory with the given content and confidence score."""
    try:
        memory = service.store_memory(content, confidence)
        return f"Memory stored with id: {memory.id}"
    except ValueError as e:
        return str(e)
    except Exception:
        return "Failed to store memory: unexpected error. Please try again."


@mcp.tool()
def recall(
    query: Annotated[str, Field(description="The search query used to find semantically similar memories.")],
    limit: Annotated[int, Field(description="Maximum number of matching memories to return, ordered by relevance.")] = 10,
) -> str:
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
