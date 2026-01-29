# ============================================================================
# Vector Store - Cosmos DB Vector Search Integration
# ============================================================================
# Purpose: Stores and retrieves vector embeddings using Azure Cosmos DB
#          with MongoDB API vector search capability.
#
# Storage Architecture:
#   - Database: agntcy-knowledge-base
#   - Collection: content-vectors
#   - Index: IVF with cosine similarity
#
# Document Schema:
#   {
#     "_id": "doc-title-chunk-1",
#     "title": "Return Policy - Eligibility",
#     "content": "To be eligible for a return...",
#     "embedding": [0.123, -0.456, ...],  # 1536 dimensions
#     "metadata": {
#       "source": "content/policies/return-policy.md",
#       "category": "policy",
#       "keywords": ["return", "refund", "exchange"],
#       "document_title": "Return Policy"
#     },
#     "content_hash": "abc123def456",
#     "created_at": "2026-01-28T12:00:00Z",
#     "updated_at": "2026-01-28T12:00:00Z"
#   }
#
# Vector Search Query:
#   Uses $vectorSearch aggregation pipeline for semantic similarity.
#
# See: docs/architecture-requirements-phase2-5.md Section 4.3 for vector store config
# ============================================================================

import os
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional

from .embedder import EmbeddedDocument, EmbeddedChunk


@dataclass
class SearchResult:
    """
    A single search result from vector search.

    Attributes:
        document: Source document title
        section: Section/chunk title
        content: Text content
        score: Similarity score (0-1, higher is better)
        metadata: Additional metadata
    """
    document: str
    section: str
    content: str
    score: float
    metadata: dict = field(default_factory=dict)


@dataclass
class CategoryInfo:
    """Category statistics."""
    documents: int
    chunks: int


@dataclass
class StoreStatus:
    """
    Knowledge base status information.

    Attributes:
        total_documents: Number of unique source documents
        total_chunks: Number of stored chunks
        estimated_tokens: Estimated total tokens
        by_category: Stats broken down by category
        last_sync: Last sync timestamp
        index_health: Vector index status
    """
    total_documents: int
    total_chunks: int
    estimated_tokens: int
    by_category: Dict[str, CategoryInfo]
    last_sync: str
    index_health: str


class VectorStore:
    """
    Manages vector embeddings in Cosmos DB.

    This store:
    - Stores embeddings with metadata
    - Performs vector similarity search
    - Tracks content changes via hash
    - Provides status and health monitoring

    Attributes:
        database_name: Cosmos DB database name
        collection_name: Collection for vectors
    """

    def __init__(
        self,
        database_name: str = "agntcy-knowledge-base",
        collection_name: str = "content-vectors"
    ):
        """
        Initialize the vector store.

        Reads Cosmos DB configuration from environment variables:
        - COSMOS_CONNECTION_STRING
        - COSMOS_DATABASE (optional, defaults to database_name)

        Args:
            database_name: Database name
            collection_name: Collection name
        """
        self.database_name = os.getenv("COSMOS_DATABASE", database_name)
        self.collection_name = collection_name
        self.connection_string = os.getenv("COSMOS_CONNECTION_STRING")

        # In-memory store for development/testing
        self._store: Dict[str, dict] = {}

    async def upsert(self, document: EmbeddedDocument) -> None:
        """
        Insert or update a document's chunks in the store.

        For each chunk:
        - Generates a unique ID from document title and chunk title
        - Stores embedding, content, and metadata
        - Updates timestamp

        Args:
            document: Embedded document with chunks
        """
        for chunk in document.chunks:
            # Generate document ID
            doc_id = self._generate_id(document.title, chunk.title)

            record = {
                "_id": doc_id,
                "title": chunk.title,
                "content": chunk.content,
                "embedding": chunk.embedding,
                "metadata": {
                    **chunk.metadata,
                    "category": document.category,
                    "keywords": document.keywords,
                    "document_title": document.title,
                    "source": document.source
                },
                "content_hash": chunk.content_hash,
                "created_at": self._store.get(doc_id, {}).get("created_at", datetime.utcnow().isoformat()),
                "updated_at": datetime.utcnow().isoformat()
            }

            # In production, upsert to Cosmos DB
            # For now, use in-memory store
            self._store[doc_id] = record

    async def delete(self, document_title: str) -> int:
        """
        Delete all chunks for a document.

        Args:
            document_title: Title of document to delete

        Returns:
            Number of chunks deleted
        """
        to_delete = [
            doc_id for doc_id, record in self._store.items()
            if record["metadata"].get("document_title") == document_title
        ]

        for doc_id in to_delete:
            del self._store[doc_id]

        return len(to_delete)

    async def search(
        self,
        query_embedding: List[float],
        top_k: int = 3,
        category: Optional[str] = None,
        min_score: float = 0.0
    ) -> List[SearchResult]:
        """
        Search for similar content using vector similarity.

        Uses cosine similarity to find the most relevant chunks.
        In production, uses Cosmos DB $vectorSearch pipeline.

        Args:
            query_embedding: Query vector (1536 dimensions)
            top_k: Number of results to return
            category: Optional category filter
            min_score: Minimum similarity score (0-1)

        Returns:
            List of search results sorted by similarity
        """
        results = []

        for record in self._store.values():
            # Apply category filter
            if category and record["metadata"].get("category") != category:
                continue

            # Calculate cosine similarity
            score = self._cosine_similarity(query_embedding, record["embedding"])

            if score >= min_score:
                results.append(SearchResult(
                    document=record["metadata"].get("document_title", "Unknown"),
                    section=record["title"],
                    content=record["content"],
                    score=score,
                    metadata=record["metadata"]
                ))

        # Sort by score descending
        results.sort(key=lambda r: r.score, reverse=True)

        return results[:top_k]

    async def get_status(
        self,
        category: Optional[str] = None
    ) -> StoreStatus:
        """
        Get knowledge base status.

        Returns document counts, chunk counts, and health metrics.

        Args:
            category: Optional category filter

        Returns:
            StoreStatus with current metrics
        """
        # Count documents and chunks by category
        documents_by_category: Dict[str, set] = {}
        chunks_by_category: Dict[str, int] = {}
        total_tokens = 0

        for record in self._store.values():
            cat = record["metadata"].get("category", "unknown")

            if category and cat != category:
                continue

            if cat not in documents_by_category:
                documents_by_category[cat] = set()
                chunks_by_category[cat] = 0

            documents_by_category[cat].add(record["metadata"].get("document_title"))
            chunks_by_category[cat] += 1

            # Estimate tokens (words * 1.3)
            total_tokens += int(len(record["content"].split()) * 1.3)

        # Build category info
        by_category = {}
        for cat in documents_by_category:
            by_category[cat] = CategoryInfo(
                documents=len(documents_by_category[cat]),
                chunks=chunks_by_category[cat]
            )

        # Get last update time
        last_sync = "Never"
        if self._store:
            last_update = max(r["updated_at"] for r in self._store.values())
            last_sync = last_update

        return StoreStatus(
            total_documents=sum(len(docs) for docs in documents_by_category.values()),
            total_chunks=len(self._store),
            estimated_tokens=total_tokens,
            by_category=by_category,
            last_sync=last_sync,
            index_health="Healthy" if self._store else "Empty"
        )

    async def health_check(self) -> bool:
        """
        Check Cosmos DB connectivity.

        Returns:
            True if database is accessible

        Raises:
            Exception if database is unreachable
        """
        if not self.connection_string:
            raise Exception("Cosmos DB not configured (missing COSMOS_CONNECTION_STRING)")

        # In production, ping the database
        # For now, assume healthy if configured
        return True

    def _generate_id(self, document_title: str, chunk_title: str) -> str:
        """
        Generate unique ID for a chunk.

        Uses document title and chunk title to create a stable ID
        that survives re-ingestion.

        Args:
            document_title: Parent document title
            chunk_title: Chunk section title

        Returns:
            Unique document ID
        """
        # Normalize titles to create stable IDs
        doc_slug = document_title.lower().replace(" ", "-")[:30]
        chunk_slug = chunk_title.lower().replace(" ", "-")[:30]
        return f"{doc_slug}_{chunk_slug}"

    def _cosine_similarity(
        self,
        vec_a: List[float],
        vec_b: List[float]
    ) -> float:
        """
        Calculate cosine similarity between two vectors.

        Returns a value between -1 (opposite) and 1 (identical).
        For normalized vectors, this is equivalent to dot product.

        Args:
            vec_a: First vector
            vec_b: Second vector

        Returns:
            Cosine similarity score
        """
        if len(vec_a) != len(vec_b):
            return 0.0

        dot_product = sum(a * b for a, b in zip(vec_a, vec_b))
        magnitude_a = sum(a * a for a in vec_a) ** 0.5
        magnitude_b = sum(b * b for b in vec_b) ** 0.5

        if magnitude_a == 0 or magnitude_b == 0:
            return 0.0

        return dot_product / (magnitude_a * magnitude_b)
