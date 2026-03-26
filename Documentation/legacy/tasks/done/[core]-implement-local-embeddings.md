# [Core] Implement Local Embeddings Provider

**Epic:** Core Components (Phase 1)

## Description

Implement a local embeddings provider using sentence-transformers library that can convert text to vector embeddings without requiring API calls. This will be used for semantic search across memories.

## Goal

Create a production-ready local embedding provider that:
- Generates consistent embeddings for text input
- Uses the all-MiniLM-L6-v2 model (384 dimensions, fast)
- Implements the IEmbeddingProvider interface

## Configuration Approach

**Pydantic Settings + .env files:**

This implementation uses `pydantic-settings` for type-safe configuration management. Configuration is loaded from environment variables or `.env` files, following the YAGNI principle with minimal fields:

- `embedding_provider`: Provider name (default: "local")
- `embedding_model`: Model name (default: "sentence-transformers/all-MiniLM-L6-v2")
- `embedding_cache_dir`: Model cache directory (default: ".cache/models")

All environment variables use the `MEMENTO_` prefix for namespace isolation.

**Files to create:**
- `src/utils/config.py`: Config class definition using Pydantic Settings
- `src/utils/factory.py`: Simple Factory class with static method
- `src/embeddings/base.py`: IEmbeddingProvider interface
- `src/embeddings/local_embedding_provider.py`: Local implementation
- `.env`: Working configuration (gitignored, only embedding config)
- `.env.example`: Updated with proper prefixes and cache directory

**Key design decisions:**
- Factory pattern: Simple `Factory` class with `create_embedder(config)` static method
- Constructor injection: LocalEmbeddingProvider receives model_name and cache_dir from Config
- Factory uses simple if/elif to select provider (YAGNI - only "local" for now)
- No hardcoded model names - all configuration external

## Acceptance Criteria

**Configuration:**
- [ ] `src/utils/config.py` implements `Config` class using Pydantic Settings
- [ ] Config has `embedding_provider`, `embedding_model` and `embedding_cache_dir` fields with defaults
- [ ] Config loads from environment variables with `MEMENTO_` prefix
- [ ] `.env.example` updated with `MEMENTO_` prefix and cache directory
- [ ] `.env` created with minimal embedding configuration

**Provider Implementation:**
- [ ] `src/embeddings/local_embedding_provider.py` implements `LocalEmbeddingProvider` class
- [ ] Inherits from `IEmbeddingProvider` base class in `src/embeddings/base.py`
- [ ] Constructor takes `model_name` and `cache_dir` parameters (not hardcoded)
- [ ] Implements `generate_embedding(text: str) -> list[float]` method
- [ ] Implements `dimension() -> int` property
- [ ] Handles model loading and caching properly

**Factory:**
- [ ] `src/utils/factory.py` implements `Factory` class with simple static method
- [ ] `create_embedder(config: Config)` method uses if/elif to instantiate providers
- [ ] Supports "local" provider that creates LocalEmbeddingProvider
- [ ] Raises ValueError for unsupported providers

**Testing:**
- [ ] Unit tests in `tests/test_embeddings/test_local_embedding_provider.py` with >80% coverage
- [ ] Unit tests in `tests/test_utils/test_config.py` verify Config loading
- [ ] Unit tests in `tests/test_utils/test_factory.py` verify Factory pattern
- [ ] Tests verify embedding consistency (same text = same embedding)
- [ ] Tests verify embedding dimensions match model spec
- [ ] Tests verify LocalEmbeddingProvider uses constructor parameters correctly

**Documentation:**
- [ ] Documentation/docstrings for public methods

## Technical Details

**Model:** sentence-transformers/all-MiniLM-L6-v2
- 384 dimensions
- Fast inference (~100ms on CPU)
- Good quality for semantic search
- No API costs

**Key Implementation Points:**
- Load model once and cache in memory
- Normalize embeddings to unit length for cosine similarity
- Handle edge cases (empty strings, very long text)

**Dependencies:**
- `sentence-transformers>=5.1.0` (already in pyproject.toml)
- `pydantic-settings>=2.11.0` (already added)
- Must define `IEmbeddingProvider` interface in `src/embeddings/base.py` first

## Implementation Steps

1. **Create Config class** (`src/utils/config.py`)
   - Define minimal Pydantic Settings class
   - Three fields: `embedding_provider`, `embedding_model`, `embedding_cache_dir`
   - Load from .env with `MEMENTO_` prefix
   - Set appropriate defaults

2. **Create IEmbeddingProvider interface** (`src/embeddings/base.py`)
   - Define abstract base class
   - Abstract methods: `generate_embedding()` and `dimension()`

3. **Implement LocalEmbeddingProvider** (`src/embeddings/local_embedding_provider.py`)
   - Constructor takes `model_name` and `cache_dir` (from config, not hardcoded)
   - Load SentenceTransformer model with caching
   - Implement interface methods
   - Handle edge cases (empty strings, very long text)

4. **Create Factory** (`src/utils/factory.py`)
   - Simple Factory class with static method
   - Static method `create_embedder(config: Config)`
   - Use if/elif to check config.embedding_provider
   - Return LocalEmbeddingProvider for "local", raise ValueError for unsupported

5. **Update environment files**
   - Update `.env.example` with `MEMENTO_EMBEDDING_PROVIDER`
   - Update `.env` with provider field

6. **Write tests (TDD)**
   - `tests/test_utils/test_config.py`: Test Config loading
   - `tests/test_embeddings/test_local_embedding_provider.py`: Test provider
   - `tests/test_utils/test_factory.py`: Test Factory pattern
   - Test embedding consistency and dimensions

## Estimated Complexity

**Medium** - Straightforward implementation but needs proper testing and error handling
