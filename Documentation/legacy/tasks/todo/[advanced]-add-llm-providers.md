# [Advanced] Add LLM Providers

**Epic:** Advanced Features (Phase 3)

## Description

Implement LLM provider interfaces and concrete implementations (OpenAI, Ollama) to enable advanced features like entity extraction, relationship extraction, and memory synthesis. This provides the intelligence layer for graph-based memory operations.

## Goal

Create production-ready LLM providers that:
- Follow a common interface for different LLM backends
- Support entity extraction from text
- Support relationship extraction from text
- Enable future advanced memory features
- Work with both cloud (OpenAI) and local (Ollama) models

## Acceptance Criteria

- [ ] `src/llms/base.py` defines `ILLMProvider` interface
  - `complete(prompt: str) -> str` method
  - `extract_entities(text: str) -> list[dict]` method
  - `extract_relationships(text: str) -> list[dict]` method
- [ ] `src/llms/openai.py` implements OpenAI provider
  - Uses OpenAI API (gpt-4, gpt-3.5-turbo)
  - Implements all interface methods
  - Handles API errors gracefully
- [ ] `src/llms/ollama.py` implements Ollama provider
  - Uses local Ollama server
  - Implements all interface methods
  - Handles connection errors gracefully
- [ ] `LLMFactory` in `src/llms/__init__.py` for creating providers
  - Factory pattern similar to embedding providers
  - Configuration-based provider selection
- [ ] Entity extraction returns structured format
- [ ] Relationship extraction returns structured triples
- [ ] Unit tests for each provider implementation
- [ ] Integration tests with real LLM calls (mocked in CI)
- [ ] Documentation for using LLM providers

## Technical Details

**ILLMProvider Interface:**
```python
from abc import ABC, abstractmethod
from typing import List, Dict

class ILLMProvider(ABC):
    @abstractmethod
    async def complete(self, prompt: str) -> str:
        """Generate text completion for a prompt."""
        pass

    @abstractmethod
    async def extract_entities(self, text: str) -> List[Dict]:
        """
        Extract named entities from text.

        Returns:
            [
                {"name": "Python", "type": "Technology"},
                {"name": "Seattle", "type": "Location"}
            ]
        """
        pass

    @abstractmethod
    async def extract_relationships(self, text: str) -> List[Dict]:
        """
        Extract relationships/triples from text.

        Returns:
            [
                {
                    "subject": "User",
                    "predicate": "prefers",
                    "object": "Python"
                }
            ]
        """
        pass
```

**OpenAI Implementation:**
```python
class OpenAILLMProvider(ILLMProvider):
    def __init__(self, api_key: str, model: str = "gpt-4"):
        self.client = OpenAI(api_key=api_key)
        self.model = model

    async def extract_entities(self, text: str) -> List[Dict]:
        prompt = f"""
        Extract named entities from the following text.
        Return as JSON array with 'name' and 'type' fields.

        Text: {text}
        """
        response = await self.complete(prompt)
        return json.loads(response)
```

**Ollama Implementation:**
```python
class OllamaLLMProvider(ILLMProvider):
    def __init__(self, base_url: str = "http://localhost:11434", model: str = "llama2"):
        self.base_url = base_url
        self.model = model

    async def complete(self, prompt: str) -> str:
        # Use Ollama HTTP API
        async with aiohttp.ClientSession() as session:
            response = await session.post(
                f"{self.base_url}/api/generate",
                json={"model": self.model, "prompt": prompt}
            )
            return await response.text()
```

**Factory Pattern:**
```python
class LLMFactory:
    @staticmethod
    def create(config: Config) -> ILLMProvider:
        provider_type = config.get("llm_provider", "openai")

        if provider_type == "openai":
            return OpenAILLMProvider(
                api_key=config.get("openai_api_key"),
                model=config.get("openai_model", "gpt-4")
            )
        elif provider_type == "ollama":
            return OllamaLLMProvider(
                base_url=config.get("ollama_base_url"),
                model=config.get("ollama_model", "llama2")
            )
        else:
            raise ValueError(f"Unknown LLM provider: {provider_type}")
```

**Configuration:**
```bash
# .env
LLM_PROVIDER=openai  # or 'ollama'
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4

# OR for local
LLM_PROVIDER=ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama2
```

**Dependencies:**
- `openai>=1.0.0` for OpenAI provider
- `aiohttp>=3.8.0` for async HTTP calls to Ollama
- Requires `src/utils/config.py` for configuration

**Testing Strategy:**
- Unit tests with mocked API responses
- Integration tests with real APIs (optional, use env flag)
- Test error handling (rate limits, network errors)
- Test entity extraction accuracy with sample data
- Test relationship extraction accuracy

## Estimated Complexity

**Large** - Multiple provider implementations, structured extraction, and comprehensive testing
