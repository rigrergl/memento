<!--
  Sync Impact Report
  ===================
  Version change: N/A → 1.0.0 (initial creation)

  Added sections:
  - Core Principles (5 principles)
  - Design Patterns
  - Quality Gates
  - Governance

  Modified principles: N/A (initial creation)
  Removed sections: N/A (initial creation)

  Templates requiring updates:
  - .specify/templates/plan-template.md: ✅ compatible (Constitution Check section exists)
  - .specify/templates/spec-template.md: ✅ compatible (no changes needed)
  - .specify/templates/tasks-template.md: ✅ compatible (checkpoint structure aligns with test gates)

  Follow-up TODOs: None
-->

# Memento Constitution

## Core Principles

### I. YAGNI (You Ain't Gonna Need It)

Do NOT build features, methods, or abstractions until they are actually needed. If there is no concrete use case right now, do not implement it. This keeps the codebase lean and focused.

**Rules:**
- Remove unused methods from interfaces
- Avoid building "might need later" features
- Delete dead code completely - no backwards-compatibility hacks
- Do NOT create files, helpers, or utilities for one-time operations
- Do NOT design for hypothetical future requirements

**Rationale:** Unused code is a maintenance burden. Future requirements often differ from predictions, making speculative code wasted effort or worse - a constraint on actual needs.

### II. KISS (Keep It Simple, Stupid)

Always choose the simplest solution that works. Avoid over-engineering, premature optimization, and unnecessary complexity. Simple code is easier to understand, test, and maintain.

**Rules:**
- Choose simple implementations over clever ones
- Refactor to add complexity ONLY when requirements demand it
- Three similar lines of code are better than a premature abstraction
- Only validate at system boundaries (user input, external APIs)
- Trust internal code and framework guarantees

**Rationale:** Complexity compounds. Each abstraction layer adds cognitive overhead, testing surface, and potential failure points. Start simple; the right time to add complexity is when pain is felt, not before.

### III. Established Design Patterns

Use proven design patterns consistently throughout the codebase. Do NOT invent new patterns when established ones suffice.

**Approved Patterns:**
- **Factory Pattern**: For creating embedding and LLM providers
- **Repository Pattern**: For database operations abstraction
- **Interface Segregation**: Separate interfaces for distinct responsibilities (e.g., embedding vs LLM providers)
- **Plugin Architecture**: Swappable providers for different AI services

**Rules:**
- New patterns MUST be justified with a concrete use case
- Pattern usage MUST be consistent across similar components
- Prefer composition over inheritance

**Rationale:** Established patterns provide shared vocabulary and proven solutions. Consistency reduces onboarding time and makes the codebase predictable.

### IV. Layered Architecture

The system follows a strict layered architecture. Dependencies flow downward only.

**Layers (top to bottom):**
1. **MCP Server Layer**: Entry point, tool registration, request handling
2. **Service Layer**: Core business logic, orchestration
3. **Repository Layer**: Database operations, data access
4. **Provider Layer**: External integrations (LLM, embeddings)

**Rules:**
- Upper layers MAY depend on lower layers
- Lower layers MUST NOT depend on upper layers
- Cross-layer calls MUST go through defined interfaces
- Each layer MUST have a single responsibility

**Rationale:** Layered architecture enables independent testing, clear boundaries, and substitutability. It prevents circular dependencies and makes the impact of changes predictable.

### V. Mandatory Testing (NON-NEGOTIABLE)

All implementation phases MUST conclude with passing unit tests. This is a hard gate - no exceptions.

**Rules:**
- After completing any implementation phase, run: `uv run pytest`
- All tests MUST pass before moving to the next phase
- Failing tests MUST be fixed immediately - do NOT defer
- New functionality MUST include corresponding tests
- Tests MUST be independent and repeatable

**Rationale:** Tests are the safety net that enables refactoring, prevents regressions, and documents expected behavior. Skipping tests creates technical debt that compounds over time.

## Design Patterns

The following patterns are standard for this project:

| Pattern | Use Case | Example |
|---------|----------|---------|
| Factory | Creating provider instances | `EmbeddingFactory`, `LLMFactory` |
| Repository | Database abstraction | `Neo4jRepository` |
| Interface Segregation | Provider contracts | `IEmbeddingProvider`, `ILLMProvider` |
| Plugin | Swappable implementations | OpenAI/Ollama/local providers |

**Anti-patterns to avoid:**
- God objects that do too much
- Deep inheritance hierarchies
- Circular dependencies between modules
- Global mutable state

## Quality Gates

These gates MUST pass before implementation phases are considered complete:

1. **Code Gate**: All new code follows YAGNI and KISS principles
2. **Pattern Gate**: Design patterns used correctly and consistently
3. **Architecture Gate**: Layer boundaries respected
4. **Test Gate**: `uv run pytest` passes with no failures
5. **Clean Code Gate**: No unused imports, no dead code, no TODO comments without linked issues

## Governance

This constitution supersedes all other practices. All implementation work MUST comply.

**Amendment Process:**
1. Propose amendment with rationale
2. Document impact on existing code
3. Update constitution version
4. Update dependent artifacts (templates, documentation)
5. Migrate existing code if needed

**Versioning Policy:**
- MAJOR: Backward-incompatible principle changes or removals
- MINOR: New principles, sections, or material expansions
- PATCH: Clarifications, wording improvements, typo fixes

**Compliance:**
- All PRs/reviews MUST verify compliance with these principles
- Complexity MUST be justified against YAGNI/KISS
- Use CLAUDE.md for runtime development guidance

**Version**: 1.0.0 | **Ratified**: 2025-12-23 | **Last Amended**: 2025-12-23
