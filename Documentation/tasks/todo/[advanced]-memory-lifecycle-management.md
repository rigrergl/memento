# [Advanced] Memory Lifecycle Management

**Epic:** Advanced Features (Phase 3)

## Description

Implement intelligent memory lifecycle management including importance scoring, time-based decay, and memory consolidation. This prevents the memory store from becoming cluttered with outdated or low-value information while preserving important memories.

## Goal

Create intelligent memory management that:
- Assigns importance scores to memories based on multiple factors
- Implements time-based decay for memory relevance
- Consolidates related memories into summary memories
- Provides mechanisms for memory pruning and archival
- Maintains memory quality over time

## Acceptance Criteria

- [ ] Importance scoring system implemented
  - Factors: access frequency, recency, confidence, user feedback
  - Normalized 0-1 score
  - Updated dynamically as memories are accessed
- [ ] Time-based decay implemented
  - Importance decreases over time (configurable decay rate)
  - Recent memories weighted higher
  - Critical memories exempt from decay
- [ ] Memory consolidation service implemented
  - Identifies clusters of related memories
  - Uses LLM to generate consolidated summaries
  - Creates new summary memory that supersedes multiple old memories
- [ ] Scheduled background job for lifecycle management
  - Runs periodically (e.g., daily)
  - Applies decay to all memories
  - Identifies consolidation candidates
  - Archives/deletes low-importance memories
- [ ] Memory archival system
  - Moves low-importance memories to archive
  - Archived memories excluded from active search
  - Can be restored if referenced
- [ ] Configuration for lifecycle policies
- [ ] Tests for importance scoring
- [ ] Tests for decay calculations
- [ ] Tests for consolidation logic
- [ ] Documentation for lifecycle management

## Technical Details

**Extended Memory Model:**
```python
@dataclass
class Memory:
    # ... existing fields ...
    importance: float  # 0-1, dynamically updated
    base_importance: float  # Initial importance
    access_count: int  # Number of retrievals
    last_consolidated: Optional[datetime]
    is_archived: bool
    is_critical: bool  # Exempt from decay/archival
```

**Importance Scoring:**
```python
def calculate_importance(memory: Memory) -> float:
    """
    Calculate dynamic importance score based on multiple factors.

    Factors:
    - Base importance (from initial storage)
    - Access frequency (normalized)
    - Recency (time since creation)
    - Confidence level
    - User feedback (if available)
    """
    # Access frequency component (0-1)
    max_access = 100  # Normalization factor
    access_score = min(memory.access_count / max_access, 1.0)

    # Recency component (0-1)
    days_old = (datetime.now() - memory.created_at).days
    recency_score = math.exp(-days_old / 30)  # 30-day half-life

    # Weighted combination
    importance = (
        0.3 * memory.base_importance +
        0.3 * access_score +
        0.2 * recency_score +
        0.2 * memory.confidence
    )

    # Critical memories always score high
    if memory.is_critical:
        importance = max(importance, 0.9)

    return importance
```

**Time-Based Decay:**
```python
def apply_decay(memory: Memory, decay_rate: float = 0.95) -> float:
    """
    Apply time-based decay to memory importance.

    Args:
        decay_rate: Daily decay multiplier (0.95 = 5% decay per day)

    Returns:
        Updated importance score
    """
    if memory.is_critical:
        return memory.importance  # No decay

    days_since_access = (datetime.now() - memory.accessed_at).days
    decay_factor = decay_rate ** days_since_access

    return memory.importance * decay_factor
```

**Memory Consolidation:**
```python
async def consolidate_memories(
    self,
    user_id: str,
    similarity_threshold: float = 0.85
) -> List[Memory]:
    """
    Find clusters of similar memories and consolidate them.

    1. Find clusters of semantically similar memories
    2. Use LLM to generate consolidated summary
    3. Create new summary memory
    4. Supersede old memories with consolidated one
    """
    # 1. Find all active memories
    memories = await self.repository.get_all_user_memories(user_id)

    # 2. Cluster by similarity
    clusters = self._cluster_by_similarity(memories, similarity_threshold)

    # 3. For each cluster with 3+ memories
    consolidated = []
    for cluster in clusters:
        if len(cluster) >= 3:
            # Generate consolidated summary using LLM
            contents = [m.content for m in cluster]
            summary = await self.llm_provider.complete(
                f"Consolidate these related facts into a single coherent statement:\n" +
                "\n".join(f"- {c}" for c in contents)
            )

            # Create consolidated memory
            new_memory = await self.store_memory(
                user_id,
                summary,
                confidence=max(m.confidence for m in cluster),
                source='consolidated'
            )

            # Supersede all cluster memories
            for old_memory in cluster:
                await self.supersede_memory(old_memory.id, new_memory.id)

            consolidated.append(new_memory)

    return consolidated
```

**Background Lifecycle Job:**
```python
class MemoryLifecycleManager:
    def __init__(self, memory_service: GraphMemoryService):
        self.service = memory_service

    async def run_lifecycle_maintenance(self):
        """Run periodic lifecycle maintenance."""
        # 1. Apply decay to all memories
        await self._apply_decay_to_all()

        # 2. Identify consolidation candidates
        await self._consolidate_similar_memories()

        # 3. Archive low-importance memories
        await self._archive_low_importance_memories(threshold=0.1)

    async def _archive_low_importance_memories(self, threshold: float):
        """Move memories below importance threshold to archive."""
        all_memories = await self.service.repository.get_all_memories()

        for memory in all_memories:
            if memory.importance < threshold and not memory.is_critical:
                await self.service.repository.update_memory(
                    memory.id,
                    {'is_archived': True}
                )
```

**Configuration:**
```bash
# .env
MEMORY_DECAY_RATE=0.95  # 5% daily decay
MEMORY_CONSOLIDATION_THRESHOLD=0.85  # Similarity for clustering
MEMORY_ARCHIVE_THRESHOLD=0.1  # Archive below this importance
MEMORY_LIFECYCLE_INTERVAL=86400  # Run every 24 hours (seconds)
```

**Dependencies:**
- Requires LLM provider for consolidation
- Requires enhanced Neo4j queries for bulk operations
- Requires background job scheduler (e.g., APScheduler)

**Testing:**
- Test importance calculation with various inputs
- Test decay over time simulation
- Test consolidation with clusters of similar memories
- Test archival and restoration
- Test background job execution

## Estimated Complexity

**Large** - Complex algorithms, LLM integration, background processing, and comprehensive testing
