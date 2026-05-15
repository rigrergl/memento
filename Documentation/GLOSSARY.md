# Glossary

Shared vocabulary for the Memento project. Use these terms consistently in code, docs, and conversation. Start here when a term feels overloaded or ambiguous.

## Cloud Mode

Roadmap deployment model: Memento running against a managed Neo4j Aura instance with Auth0-backed multi-tenant authentication. Not yet implemented. Contrast with [Local Mode](#local-mode).

## Developer

A person making code changes to Memento itself — contributing, debugging, or experimenting with the server's internals. Runs Memento natively via `uv` (Neo4j still in Docker) so edits hot-reload. See the Developer Setup section of `README.md`. Contrast with [Power User](#power-user).

## Embedding Provider

A pluggable component that converts memory content into vector embeddings for semantic search. Implementations live in `src/embeddings/` and are constructed by a factory. The only current implementation uses local Sentence Transformers.

## Local Mode

The currently supported deployment model: Memento and Neo4j run together via Docker Compose on a single machine, serving a single user. No authentication. This is what [Power User](#power-user) setup provisions. Contrast with [Cloud Mode](#cloud-mode).

## MCP (Model Context Protocol)

The open protocol Memento speaks to expose its memory tools to LLM clients. Memento is built on FastMCP and serves MCP over HTTP at `http://localhost:8000/mcp/` by default.

## MCP Client

An LLM-facing application that connects to an MCP server to use its tools — e.g. Claude Code, Claude Desktop, Gemini CLI. From Memento's perspective, the MCP Client is the consumer of `remember` and `recall`.

## MCP Server

A process that exposes tools to MCP Clients over the MCP protocol. Memento is itself an MCP Server.

## Memento

This project: an MCP server that gives LLMs persistent, semantically-searchable memory backed by Neo4j.

## Memory

The core domain entity — a single stored fact or piece of knowledge. Carries `content` (the text), `confidence` (0–1), and a vector embedding used for semantic search. Persisted as a `Memory` node in Neo4j.

## Power User

A person who *runs* Memento as a memory backend for their MCP client without modifying its code. Needs only Docker; no Python toolchain. See the Power-User Setup section of `README.md`. Contrast with [Developer](#developer).

## Recall

One of Memento's two MCP tools. Performs semantic search over stored memories and returns the most relevant matches. Params: `query` (string), `limit` (int, default 10).

## Remember

One of Memento's two MCP tools. Stores a new memory. Params: `content` (string), `confidence` (float 0–1).

## Semantic Search

Retrieval by meaning rather than keyword match: a query is embedded into the same vector space as stored memories, and nearest-neighbor search ranks results by cosine similarity. Powers [Recall](#recall).
