"""Shared fixtures for integration tests: real Neo4j testcontainer + FastMCP in-memory client."""
import os

import pytest
import pytest_asyncio
from fastmcp import Client
from neo4j import GraphDatabase
from testcontainers.neo4j import Neo4jContainer

from src.mcp.server import mcp

os.environ["MEMENTO_EMBEDDING_PROVIDER"] = "local"
os.environ["MEMENTO_EMBEDDING_MODEL"] = "all-MiniLM-L6-v2"


@pytest.fixture(scope="session")
def neo4j_container():
    with Neo4jContainer("neo4j:2026.03.1") as container:
        os.environ["MEMENTO_NEO4J_URI"] = container.get_connection_url()
        os.environ["MEMENTO_NEO4J_USER"] = container.username
        os.environ["MEMENTO_NEO4J_PASSWORD"] = container.password
        yield container


@pytest.fixture(scope="session")
def neo4j_driver(neo4j_container):
    uri = os.environ["MEMENTO_NEO4J_URI"]
    user = os.environ["MEMENTO_NEO4J_USER"]
    password = os.environ["MEMENTO_NEO4J_PASSWORD"]
    driver = GraphDatabase.driver(uri, auth=(user, password))
    yield driver
    driver.close()


@pytest_asyncio.fixture(scope="session", loop_scope="session")
async def client(neo4j_container):
    async with Client(mcp) as c:
        yield c


@pytest.fixture(autouse=True)
def clean_db(neo4j_driver):
    yield
    with neo4j_driver.session() as session:
        session.run("MATCH (n:Memory) DETACH DELETE n")
