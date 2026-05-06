# Planning

Short notes on work that is intentionally out of current scope. Each entry points to the spec, ADR, or tech-debt entry where it is (or will be) tracked in more detail. Update as items land, get re-scoped, or are pulled into active specs.

## Currently deferred

### Cloud Run deployment (future spec 003)

Terraform-managed GCP Cloud Run deployment, Artifact Registry mirror of the ghcr.io image, Neo4j Aura Free for storage, secret wiring through GCP Secret Manager. Carved out of spec 002 because it has its own infra surface (Terraform, service accounts, IAM, Aura provisioning) and because it is gated on the embedding-distribution decision below — Cloud Run cold starts pay the full model cost otherwise.

Includes the **multi-registry publish pipeline**: extend the GitHub Actions workflow to push each pinned semver tag to both `ghcr.io` and GCP Artifact Registry in a single build. Auth to AR uses Workload Identity Federation (GitHub OIDC → GCP IAM) rather than long-lived service-account JSON keys. Deferred until Cloud Run lands — no value publishing to AR before there is a consumer for it.

### Embedding model distribution and provider refinement

Spec 002 bakes `all-MiniLM-L6-v2` into the image (FR-003) as the interim answer for power users. Longer term we need to decide between: named-volume cache, hosted embedding API (Voyage, OpenAI, Cohere, …), or a hybrid that lets users bring their own provider. Intersects with a separate requirement to let users configure their own embedding provider. Tracked as **TD-004** in `Documentation/known-tech-debt.md`; warrants its own ADR before spec 003 so Cloud Run has a coherent story.

### Refined dev loop for autonomous agent iteration

Spec 002 ships the basic dev loop: `fastmcp run --reload`, committed `.mcp.json`, Neo4j MCP for self-validation. A follow-up spec will refine this so a coding agent can make code changes and self-verify end-to-end — including handling the stdio drop on `--reload` restarts, shaping tool responses to be agent-friendly on failure, and tightening the feedback loop between "edit file" and "see effect in tool call."

### CLI interface

LLMs can consume CLI tools efficiently, sometimes with lower token overhead than MCP, and a CLI opens non-LLM use cases (e.g. manually adding memories outside a session). Deferred while the MCP path bakes; the two can coexist later without much rework since both would wrap `MemoryService`.

### Image digest pinning

Spec 002 pins the Memento image by semver tag (`ghcr.io/rigrergl/memento:v0.2.0`) in `docker-compose.yml`. Digest pinning (`@sha256:...`) is strictly more secure — tags can be reassigned in a registry, digests cannot — but overkill at current scale. Revisit if/when supply-chain guarantees matter (e.g. SLSA provenance, or a public deployment with external trust requirements). Low priority.

### Structured logging + typed error handling

MCP tools currently swallow exceptions behind a generic string to avoid leaking Neo4j connection URIs. Before any public or multi-tenant deployment, add structured logging (`structlog` or stdlib `logging`) with a credential scrubber, catch specific driver/embedding exceptions at `ERROR` level, and keep the raw `str(e)` out of both client responses and log sinks. Tracked as **TD-001**.
