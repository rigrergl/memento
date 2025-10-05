# [Core] Implement Local Embeddings Provider

**Epic:** Core Components (Phase 1)

## Description

Implement a local embeddings provider using sentence-transformers library that can convert text to vector embeddings without requiring API calls. This will be used for semantic search across memories.

## Goal

Create a production-ready local embedding provider that:
- Generates consistent embeddings for text input
- Uses the all-MiniLM-L6-v2 model (384 dimensions, fast)
- Implements the IEmbeddingProvider interface

## Acceptance Criteria

- [ ] `src/embeddings/local.py` implements `LocalEmbeddingProvider` class
- [ ] Inherits from `IEmbeddingProvider` base class in `src/embeddings/base.py`
- [ ] Implements `generate_embedding(text: str) -> list[float]` method
- [ ] Implements `dimension() -> int` property
- [ ] Handles model loading and caching properly
- [ ] Unit tests in `tests/test_embeddings/test_local_embeddings.py` with >80% coverage
- [ ] Tests verify embedding consistency (same text = same embedding)
- [ ] Tests verify embedding dimensions match model spec
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
- `sentence-transformers>=2.2.0`
- Must define `IEmbeddingProvider` interface in `src/embeddings/base.py` first

## Estimated Complexity

**Medium** - Straightforward implementation but needs proper testing and error handling
