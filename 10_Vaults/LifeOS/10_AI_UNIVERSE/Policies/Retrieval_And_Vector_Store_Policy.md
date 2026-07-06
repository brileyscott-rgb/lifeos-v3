# Retrieval and Vector Store Policy

## Recommendation

Use Qdrant for semantic memory and retrieval.

Use SQLite first for structured event/workflow state. Move to Postgres later if service complexity justifies it.

## Qdrant Uses

- vault note embeddings
- document summaries
- project context packs
- codebase context chunks
- migration duplicate detection
- Semantic Janitor similarity checks

## Operational Notes

- Qdrant is planned and inactive in Phase 1B.
- Embedding model changes must be recorded.
- Collections need backup and rebuild strategy.
