# ADR-004: Remove MongoDB from Architecture

## Status
Accepted

## Date
2025-09-16

## Context

ADR-003 proposed using MongoDB Atlas alongside Neo4j for user authentication and management in cloud mode. Upon review, MongoDB adds unnecessary complexity without providing essential functionality for the MVP.

## Decision

**Remove MongoDB entirely from the architecture.** Use Neo4j as the single database for all data storage needs.

## Rationale

### Auth0 Already Provides User Management
- **User IDs**: Auth0's `sub` claim provides consistent user identifiers (e.g., `auth0|507f1f77bcf86cd799439011`)
- **JWT Validation**: Can validate JWTs using Auth0's public keys without database lookups
- **User Profiles**: Auth0 stores user metadata (name, email, etc.)
- **Session Management**: Handled through JWT expiration

### Neo4j Can Store Additional User Data
```cypher
// User preferences and settings
CREATE (u:User {
  user_id: "auth0|507f1f77bcf86cd799439011",
  created_at: datetime(),
  preferences: {theme: 'dark', language: 'en'}
})
```

### Simplified Architecture
- **One database** instead of two
- **Lower latency**: No extra network hop
- **Easier deployment**: Fewer services to provision
- **Reduced costs**: Even though MongoDB Atlas has a free tier

## Consequences

### Positive
- Simpler MVP that ships faster
- Unified data model across local and cloud modes
- Fewer dependencies and potential failure points
- All data in one queryable graph

### Negative
- Less separation of concerns (acceptable for MVP)
- May need to add a dedicated user database later if user management becomes complex

### Migration Path
If MongoDB becomes necessary later (e.g., for billing, complex user analytics), it can be added without breaking changes to the MCP interface.

## References
- Supersedes user management aspects of ADR-003
- Auth0 documentation on JWT claims and user profiles
