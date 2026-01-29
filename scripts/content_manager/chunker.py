# ============================================================================
# Content Chunker - Split Documents for Vectorization
# ============================================================================
# Purpose: Splits markdown documents into semantic chunks suitable for
#          vector embedding and retrieval.
#
# Chunking Strategy:
#   - Split by markdown headers (##, ###) to preserve semantic boundaries
#   - Include metadata (title, category, keywords) in each chunk
#   - Enforce maximum token limits per chunk
#   - Preserve context by including parent headers
#
# Why Semantic Chunking?
#   Fixed-size chunking (e.g., 500 characters) breaks mid-sentence and
#   loses semantic coherence. Header-based chunking keeps related content
#   together, improving retrieval accuracy.
#
# Token Estimation:
#   We estimate tokens as word_count * 1.3 (approximation for English text).
#   For production accuracy, use tiktoken library with the appropriate model.
#
# See: docs/WIKI-Merchant-Content-Management.md for chunking best practices
# ============================================================================

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

import yaml


@dataclass
class Chunk:
    """
    A single chunk of content for vectorization.

    Attributes:
        title: Section header or derived title
        content: The chunk text content
        token_count: Estimated token count
        metadata: Additional metadata (category, keywords, source file)
    """
    title: str
    content: str
    token_count: int
    metadata: dict = field(default_factory=dict)


@dataclass
class ChunkedDocument:
    """
    A document split into chunks.

    Attributes:
        title: Document title from frontmatter
        source: Source file path
        category: Content category (policy, faq, etc.)
        keywords: Search keywords from frontmatter
        sections: List of content chunks
    """
    title: str
    source: Path
    category: str
    keywords: List[str]
    sections: List[Chunk]


class ContentChunker:
    """
    Splits markdown documents into semantic chunks for vectorization.

    This chunker:
    - Preserves semantic boundaries (sections)
    - Enforces token limits
    - Includes metadata for filtering
    - Handles nested headers

    Attributes:
        max_tokens: Maximum tokens per chunk (default 500)
        min_tokens: Minimum tokens before merging (default 50)
    """

    def __init__(
        self,
        max_tokens: int = 500,
        min_tokens: int = 50
    ):
        """
        Initialize the chunker.

        Args:
            max_tokens: Maximum tokens per chunk. Larger chunks provide more
                        context but may dilute retrieval precision.
            min_tokens: Minimum tokens per chunk. Smaller sections will be
                        merged with adjacent sections.
        """
        self.max_tokens = max_tokens
        self.min_tokens = min_tokens

    def chunk_file(self, file_path: Path) -> ChunkedDocument:
        """
        Chunk a markdown file into sections.

        Process:
        1. Parse frontmatter for metadata
        2. Split body by headers
        3. Estimate token counts
        4. Merge small sections
        5. Split large sections

        Args:
            file_path: Path to markdown file

        Returns:
            ChunkedDocument with sections ready for embedding
        """
        content = file_path.read_text(encoding="utf-8")

        # Parse frontmatter
        frontmatter, body = self._parse_frontmatter(content)

        title = frontmatter.get("title", file_path.stem)
        category = frontmatter.get("category", "unknown")
        keywords = frontmatter.get("keywords", [])

        # Split into sections
        raw_sections = self._split_by_headers(body)

        # Process sections
        chunks = []
        for section_title, section_content in raw_sections:
            token_count = self._estimate_tokens(section_content)

            # Skip empty sections
            if token_count == 0:
                continue

            # Create chunk with metadata
            chunk = Chunk(
                title=section_title or title,
                content=section_content.strip(),
                token_count=token_count,
                metadata={
                    "source": str(file_path),
                    "category": category,
                    "keywords": keywords,
                    "document_title": title
                }
            )
            chunks.append(chunk)

        # Merge small sections
        chunks = self._merge_small_sections(chunks)

        # Split large sections
        chunks = self._split_large_sections(chunks)

        return ChunkedDocument(
            title=title,
            source=file_path,
            category=category,
            keywords=keywords,
            sections=chunks
        )

    def _parse_frontmatter(self, content: str) -> tuple:
        """
        Parse YAML frontmatter from markdown content.

        Args:
            content: Full markdown content

        Returns:
            Tuple of (frontmatter dict, body string)
        """
        pattern = r"^---\s*\n(.*?)\n---\s*\n(.*)$"
        match = re.match(pattern, content, re.DOTALL)

        if not match:
            return {}, content

        try:
            frontmatter = yaml.safe_load(match.group(1))
            body = match.group(2)
            return frontmatter or {}, body
        except yaml.YAMLError:
            return {}, content

    def _split_by_headers(self, body: str) -> List[tuple]:
        """
        Split markdown body into sections by headers.

        Handles both ## and ### headers. Each section includes
        the header and all content until the next header.

        Args:
            body: Markdown body content

        Returns:
            List of (title, content) tuples
        """
        sections = []

        # Pattern matches ## or ### headers
        # Captures header text and content until next header
        pattern = r"(#{2,3})\s+(.+?)\n([\s\S]*?)(?=\n#{2,3}\s|\Z)"

        matches = re.findall(pattern, body)

        if not matches:
            # No headers found, treat entire body as one section
            return [("Overview", body)]

        for level, title, content in matches:
            sections.append((title.strip(), content.strip()))

        return sections

    def _estimate_tokens(self, text: str) -> int:
        """
        Estimate token count for text.

        Uses approximation: tokens ~= words * 1.3
        For production, use tiktoken with the embedding model.

        Args:
            text: Text to estimate

        Returns:
            Estimated token count
        """
        words = len(text.split())
        return int(words * 1.3)

    def _merge_small_sections(self, chunks: List[Chunk]) -> List[Chunk]:
        """
        Merge sections that are too small.

        Small sections lack context for effective retrieval.
        Merges consecutive small sections until they reach min_tokens.

        Args:
            chunks: List of chunks to process

        Returns:
            List with small sections merged
        """
        if not chunks:
            return chunks

        merged = []
        current = None

        for chunk in chunks:
            if current is None:
                current = chunk
                continue

            # If current chunk is small, merge with next
            if current.token_count < self.min_tokens:
                current = Chunk(
                    title=current.title,  # Keep original title
                    content=f"{current.content}\n\n{chunk.content}",
                    token_count=current.token_count + chunk.token_count,
                    metadata=current.metadata
                )
            else:
                merged.append(current)
                current = chunk

        if current:
            merged.append(current)

        return merged

    def _split_large_sections(self, chunks: List[Chunk]) -> List[Chunk]:
        """
        Split sections that exceed max_tokens.

        Large sections dilute retrieval precision. Splits by paragraph
        boundaries while preserving the section title.

        Args:
            chunks: List of chunks to process

        Returns:
            List with large sections split
        """
        result = []

        for chunk in chunks:
            if chunk.token_count <= self.max_tokens:
                result.append(chunk)
                continue

            # Split by paragraphs (double newline)
            paragraphs = chunk.content.split("\n\n")

            current_content = []
            current_tokens = 0
            part_num = 1

            for para in paragraphs:
                para_tokens = self._estimate_tokens(para)

                if current_tokens + para_tokens > self.max_tokens and current_content:
                    # Create chunk from current content
                    result.append(Chunk(
                        title=f"{chunk.title} (Part {part_num})",
                        content="\n\n".join(current_content),
                        token_count=current_tokens,
                        metadata=chunk.metadata
                    ))
                    current_content = [para]
                    current_tokens = para_tokens
                    part_num += 1
                else:
                    current_content.append(para)
                    current_tokens += para_tokens

            # Add remaining content
            if current_content:
                title = f"{chunk.title} (Part {part_num})" if part_num > 1 else chunk.title
                result.append(Chunk(
                    title=title,
                    content="\n\n".join(current_content),
                    token_count=current_tokens,
                    metadata=chunk.metadata
                ))

        return result

    def chunk_directory(self, dir_path: Path) -> List[ChunkedDocument]:
        """
        Chunk all markdown files in a directory.

        Args:
            dir_path: Path to directory containing markdown files

        Returns:
            List of ChunkedDocument objects
        """
        documents = []

        for file_path in dir_path.glob("**/*.md"):
            doc = self.chunk_file(file_path)
            documents.append(doc)

        return documents
