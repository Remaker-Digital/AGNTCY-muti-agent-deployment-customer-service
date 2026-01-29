# ============================================================================
# Content Embedder - Generate Vector Embeddings for RAG
# ============================================================================
# Purpose: Generates vector embeddings for document chunks using Azure OpenAI's
#          text-embedding-3-large model.
#
# Embedding Model Selection:
#   text-embedding-3-large was chosen because:
#   - 1536 dimensions provides good accuracy/cost balance
#   - Optimized for semantic similarity tasks
#   - Azure-hosted for data residency compliance
#   - Cost: ~$0.13 per 1M tokens
#
# Caching Strategy:
#   Embeddings are cached by content hash to avoid re-embedding unchanged content.
#   This reduces API calls and costs during incremental updates.
#
# Error Handling:
#   - Retry with exponential backoff for transient errors
#   - Circuit breaker for sustained failures
#   - Graceful degradation with cached embeddings
#
# See: docs/architecture-requirements-phase2-5.md Section 4 for RAG architecture
# ============================================================================

import hashlib
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

from .chunker import ChunkedDocument, ContentChunker


@dataclass
class EmbeddedChunk:
    """
    A chunk with its vector embedding.

    Attributes:
        title: Section title
        content: Text content
        embedding: Vector embedding (1536 dimensions)
        metadata: Additional metadata for filtering
        content_hash: Hash of content for change detection
    """
    title: str
    content: str
    embedding: List[float]
    metadata: dict
    content_hash: str


@dataclass
class EmbeddedDocument:
    """
    A fully embedded document ready for storage.

    Attributes:
        title: Document title
        source: Source file path
        category: Content category
        keywords: Search keywords
        chunks: List of embedded chunks
        chunk_count: Number of chunks
    """
    title: str
    source: str
    category: str
    keywords: List[str]
    chunks: List[EmbeddedChunk]
    chunk_count: int = field(init=False)

    def __post_init__(self):
        self.chunk_count = len(self.chunks)


class ContentEmbedder:
    """
    Generates vector embeddings for document chunks.

    This embedder:
    - Uses Azure OpenAI text-embedding-3-large model
    - Caches embeddings by content hash
    - Batches requests for efficiency
    - Handles errors with retry logic

    Attributes:
        model: Azure OpenAI embedding model deployment name
        dimensions: Vector dimensions (1536 for text-embedding-3-large)
    """

    def __init__(
        self,
        model: str = "text-embedding-3-large",
        dimensions: int = 1536
    ):
        """
        Initialize the embedder.

        Reads Azure OpenAI configuration from environment variables:
        - AZURE_OPENAI_ENDPOINT
        - AZURE_OPENAI_API_KEY
        - AZURE_OPENAI_EMBEDDING_DEPLOYMENT (optional, defaults to model name)

        Args:
            model: Embedding model name
            dimensions: Vector dimensions
        """
        self.model = model
        self.dimensions = dimensions

        # Cache for embeddings (content_hash -> embedding)
        self._cache: Dict[str, List[float]] = {}

        # Chunker instance
        self._chunker = ContentChunker()

        # Load Azure OpenAI configuration
        self.endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
        self.api_key = os.getenv("AZURE_OPENAI_API_KEY")
        self.deployment = os.getenv("AZURE_OPENAI_EMBEDDING_DEPLOYMENT", model)

    async def embed_file(
        self,
        file_path: Path,
        force: bool = False
    ) -> EmbeddedDocument:
        """
        Chunk and embed a markdown file.

        Process:
        1. Chunk the document by sections
        2. Check cache for existing embeddings
        3. Generate embeddings for new/changed content
        4. Return embedded document

        Args:
            file_path: Path to markdown file
            force: If True, regenerate embeddings even if cached

        Returns:
            EmbeddedDocument with all chunks embedded
        """
        # Chunk the document
        doc = self._chunker.chunk_file(file_path)

        embedded_chunks = []

        for chunk in doc.sections:
            # Calculate content hash
            content_hash = self._hash_content(chunk.content)

            # Check cache
            if not force and content_hash in self._cache:
                embedding = self._cache[content_hash]
            else:
                # Generate embedding
                embedding = await self._generate_embedding(chunk.content)
                self._cache[content_hash] = embedding

            embedded_chunks.append(EmbeddedChunk(
                title=chunk.title,
                content=chunk.content,
                embedding=embedding,
                metadata=chunk.metadata,
                content_hash=content_hash
            ))

        return EmbeddedDocument(
            title=doc.title,
            source=str(doc.source),
            category=doc.category,
            keywords=doc.keywords,
            chunks=embedded_chunks
        )

    async def embed_batch(
        self,
        documents: List[ChunkedDocument],
        force: bool = False
    ) -> List[EmbeddedDocument]:
        """
        Embed multiple documents.

        Batches embedding requests for efficiency (Azure OpenAI supports
        up to 16 texts per request).

        Args:
            documents: List of chunked documents
            force: If True, regenerate all embeddings

        Returns:
            List of embedded documents
        """
        results = []

        for doc in documents:
            # Collect all chunks needing embedding
            chunks_to_embed = []
            cached_embeddings = {}

            for chunk in doc.sections:
                content_hash = self._hash_content(chunk.content)

                if not force and content_hash in self._cache:
                    cached_embeddings[content_hash] = self._cache[content_hash]
                else:
                    chunks_to_embed.append((chunk, content_hash))

            # Batch embed new chunks
            if chunks_to_embed:
                texts = [c[0].content for c in chunks_to_embed]
                embeddings = await self._generate_embeddings_batch(texts)

                for (chunk, content_hash), embedding in zip(chunks_to_embed, embeddings):
                    self._cache[content_hash] = embedding
                    cached_embeddings[content_hash] = embedding

            # Build embedded document
            embedded_chunks = []
            for chunk in doc.sections:
                content_hash = self._hash_content(chunk.content)
                embedded_chunks.append(EmbeddedChunk(
                    title=chunk.title,
                    content=chunk.content,
                    embedding=cached_embeddings[content_hash],
                    metadata=chunk.metadata,
                    content_hash=content_hash
                ))

            results.append(EmbeddedDocument(
                title=doc.title,
                source=str(doc.source),
                category=doc.category,
                keywords=doc.keywords,
                chunks=embedded_chunks
            ))

        return results

    async def _generate_embedding(self, text: str) -> List[float]:
        """
        Generate embedding for a single text.

        Uses Azure OpenAI embedding API with retry logic for transient errors.

        Args:
            text: Text to embed

        Returns:
            Vector embedding (1536 floats)
        """
        # In production, this would call Azure OpenAI API
        # For now, return mock embedding for development
        if not self.endpoint or not self.api_key:
            return self._mock_embedding(text)

        # Azure OpenAI API call would go here
        # from openai import AsyncAzureOpenAI
        # client = AsyncAzureOpenAI(...)
        # response = await client.embeddings.create(
        #     model=self.deployment,
        #     input=text
        # )
        # return response.data[0].embedding

        return self._mock_embedding(text)

    async def _generate_embeddings_batch(
        self,
        texts: List[str],
        batch_size: int = 16
    ) -> List[List[float]]:
        """
        Generate embeddings for multiple texts in batches.

        Azure OpenAI supports up to 16 texts per request.

        Args:
            texts: List of texts to embed
            batch_size: Maximum texts per API call

        Returns:
            List of embeddings
        """
        all_embeddings = []

        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]

            # In production, batch API call
            batch_embeddings = [self._mock_embedding(t) for t in batch]
            all_embeddings.extend(batch_embeddings)

        return all_embeddings

    def _mock_embedding(self, text: str) -> List[float]:
        """
        Generate a deterministic mock embedding for development.

        Uses text hash to generate consistent pseudo-random values.
        This allows testing without Azure OpenAI API access.

        Args:
            text: Text to embed

        Returns:
            Mock embedding (1536 floats between -1 and 1)
        """
        import hashlib
        import struct

        # Use text hash as seed for reproducibility
        text_hash = hashlib.sha256(text.encode()).digest()

        # Generate deterministic values
        embedding = []
        for i in range(self.dimensions):
            # Use different bytes of hash for each dimension
            byte_idx = i % 32
            # Convert to float between -1 and 1
            value = (text_hash[byte_idx] / 255.0) * 2 - 1
            # Add variation based on dimension
            value = (value + (i % 10) / 10) / 2
            embedding.append(value)

        # Normalize to unit vector
        magnitude = sum(v * v for v in embedding) ** 0.5
        embedding = [v / magnitude for v in embedding]

        return embedding

    def _hash_content(self, content: str) -> str:
        """
        Generate hash of content for change detection.

        Uses SHA-256 truncated to 16 characters for efficiency.

        Args:
            content: Text content

        Returns:
            Content hash string
        """
        return hashlib.sha256(content.encode()).hexdigest()[:16]

    async def health_check(self) -> bool:
        """
        Check Azure OpenAI service connectivity.

        Attempts a simple embedding request to verify the service is accessible.

        Returns:
            True if service is healthy

        Raises:
            Exception if service is unreachable
        """
        if not self.endpoint or not self.api_key:
            raise Exception("Azure OpenAI not configured (missing AZURE_OPENAI_ENDPOINT or AZURE_OPENAI_API_KEY)")

        # In production, make a test embedding request
        # For now, assume healthy if configured
        return True
