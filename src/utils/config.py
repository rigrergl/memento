"""Configuration management using Pydantic Settings."""
from pydantic import Field
from pydantic_settings import BaseSettings


class Config(BaseSettings):
    """
    Application configuration loaded from environment variables.

    All environment variables must be prefixed with MEMENTO_.

    Example:
        MEMENTO_EMBEDDING_PROVIDER=local
        MEMENTO_EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
    """

    # Embedding configuration
    embedding_provider: str = Field(
        description="Embedding provider type (e.g., 'local' for local transformers)"
    )
    embedding_model: str = Field(
        description="Model identifier for embeddings (e.g., 'sentence-transformers/all-MiniLM-L6-v2')"
    )
    embedding_cache_dir: str = Field(
        default=".cache/models",
        description="Directory path for caching downloaded models"
    )

    # Neo4j configuration
    neo4j_uri: str = Field(
        description="Neo4j connection URI (e.g., 'neo4j+s://xxxxx.databases.neo4j.io')"
    )
    neo4j_user: str = Field(
        description="Neo4j database username"
    )
    neo4j_password: str = Field(
        description="Neo4j database password"
    )

    # Memory validation
    max_memory_length: int = Field(
        default=4000,
        ge=1,
        le=100000,
        description="Maximum allowed memory text length in characters"
    )

    model_config = {
        "env_prefix": "MEMENTO_",
        "env_file": ".env",
        "env_file_encoding": "utf-8",
    }
