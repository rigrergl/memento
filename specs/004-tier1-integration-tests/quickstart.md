# Quickstart: Integration Tests

## Prerequisites

- Docker running (the testcontainer starts automatically; Docker must be available)
- `uv` available in PATH
- Python dependencies installed: `uv sync --all-groups`

On first run, sentence-transformers downloads the `all-MiniLM-L6-v2` model (~90MB). Subsequent runs use the cache (`.cache/models/`).

---

## Run the Full Suite (Unit + Integration)

```bash
uv run pytest
```

All unit tests and integration tests run together. The Neo4j testcontainer starts automatically and stops when the session ends.

---

## Run Integration Tests Only

```bash
uv run pytest tests/integration/
```

---

## Run a Specific Integration Test File

```bash
uv run pytest tests/integration/test_remember.py
uv run pytest tests/integration/test_recall.py
uv run pytest tests/integration/test_lifespan.py
```

---

## Expected Output (First Run)

```
tests/integration/conftest.py  - starting neo4j container...
...
tests/integration/test_remember.py::test_remember_success PASSED
tests/integration/test_remember.py::test_remember_empty_content PASSED
tests/integration/test_remember.py::test_remember_content_too_long PASSED
tests/integration/test_remember.py::test_remember_invalid_confidence PASSED
tests/integration/test_recall.py::test_recall_returns_matching_memory PASSED
tests/integration/test_recall.py::test_recall_no_results PASSED
tests/integration/test_recall.py::test_recall_limit_honored PASSED
tests/integration/test_recall.py::test_recall_empty_query PASSED
tests/integration/test_lifespan.py::test_vector_index_created PASSED
tests/integration/test_lifespan.py::test_uniqueness_constraint_created PASSED
```

---

## Important Notes

- **Do not run with `pytest-xdist` (`-n auto`)**: Integration tests share a single Neo4j container with per-test cleanup. Parallel execution causes race conditions on the cleanup query.
- **Docker failure**: If Docker is unavailable, the Neo4j container will fail to start and tests fail loudly — no skip logic is in place.
- **Embedding model cache**: Set `MEMENTO_EMBEDDING_CACHE_DIR` env var to override the cache location (default: `.cache/models`).
