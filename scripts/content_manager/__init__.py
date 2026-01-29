# ============================================================================
# Content Manager - RAG Knowledge Base Management Tool
# ============================================================================
# Purpose: CLI tool for merchants to manage knowledge base content for the
#          Retrieval-Augmented Generation (RAG) system.
#
# Features:
#   - Validate markdown content with frontmatter
#   - Preview content chunking before vectorization
#   - Ingest and vectorize content to Cosmos DB
#   - Test retrieval quality with sample queries
#   - Monitor knowledge base status
#
# Usage:
#   python -m scripts.content_manager --help
#   python -m scripts.content_manager validate content/
#   python -m scripts.content_manager ingest content/ --dry-run
#
# Architecture:
#   This tool interfaces with:
#   - Azure OpenAI (text-embedding-3-large) for vector embeddings
#   - Cosmos DB (MongoDB API) for vector storage and search
#   - Local filesystem for markdown content
#
# Cost Impact:
#   - Embedding generation: ~$0.13 per 1M tokens
#   - Typical knowledge base (75 docs): ~$0.01 initial, ~$0.26/month
#
# See: docs/WIKI-Merchant-Content-Management.md for full documentation
# ============================================================================

__version__ = "1.0.0"
