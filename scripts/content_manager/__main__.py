# ============================================================================
# Content Manager CLI - Entry Point
# ============================================================================
# Purpose: Main entry point for the content manager CLI tool.
#
# This module provides the command-line interface for merchants to manage
# their RAG knowledge base content. It supports:
#   - Content validation (frontmatter, structure)
#   - Chunking preview (see how content will be split)
#   - Content ingestion (vectorize and store)
#   - Retrieval testing (verify search quality)
#   - Status monitoring (view knowledge base health)
#
# Usage:
#   python -m scripts.content_manager <command> [options]
#
# Commands:
#   validate    Check content for formatting issues
#   preview     Preview how content will be chunked
#   ingest      Process and vectorize content
#   status      View knowledge base status
#   test-query  Test retrieval with a sample query
#   test-suite  Run full retrieval test suite
#   watch       Watch for file changes and auto-sync
#   health-check  Verify Azure service connectivity
#
# See: docs/WIKI-Merchant-Content-Management.md for full documentation
# ============================================================================

import argparse
import asyncio
import sys
from pathlib import Path
from typing import Optional

from .validator import ContentValidator
from .chunker import ContentChunker
from .embedder import ContentEmbedder
from .store import VectorStore
from .tester import RetrievalTester


def create_parser() -> argparse.ArgumentParser:
    """
    Create the argument parser for the content manager CLI.

    Returns:
        Configured ArgumentParser with all subcommands
    """
    parser = argparse.ArgumentParser(
        prog="content_manager",
        description="Manage RAG knowledge base content for the customer service platform",
        epilog="See docs/WIKI-Merchant-Content-Management.md for detailed documentation"
    )

    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose output"
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # =========================================================================
    # validate - Check content for formatting issues
    # =========================================================================
    validate_parser = subparsers.add_parser(
        "validate",
        help="Validate content files for formatting issues"
    )
    validate_parser.add_argument(
        "path",
        type=Path,
        help="Path to content file or directory"
    )
    validate_parser.add_argument(
        "--strict",
        action="store_true",
        help="Enable strict validation (warnings become errors)"
    )

    # =========================================================================
    # preview - Preview content chunking
    # =========================================================================
    preview_parser = subparsers.add_parser(
        "preview",
        help="Preview how content will be split into chunks"
    )
    preview_parser.add_argument(
        "file",
        type=Path,
        help="Path to content file"
    )
    preview_parser.add_argument(
        "--max-tokens",
        type=int,
        default=500,
        help="Maximum tokens per chunk (default: 500)"
    )

    # =========================================================================
    # ingest - Process and vectorize content
    # =========================================================================
    ingest_parser = subparsers.add_parser(
        "ingest",
        help="Process and vectorize content for the knowledge base"
    )
    ingest_parser.add_argument(
        "path",
        type=Path,
        help="Path to content file or directory"
    )
    ingest_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be processed without making changes"
    )
    ingest_parser.add_argument(
        "--force",
        action="store_true",
        help="Force re-vectorization even if content unchanged"
    )
    ingest_parser.add_argument(
        "--skip-unchanged",
        action="store_true",
        help="Skip files that haven't changed since last ingestion"
    )

    # =========================================================================
    # status - View knowledge base status
    # =========================================================================
    status_parser = subparsers.add_parser(
        "status",
        help="View current knowledge base status"
    )
    status_parser.add_argument(
        "--category",
        choices=["policy", "faq", "troubleshooting", "article", "product"],
        help="Filter by content category"
    )

    # =========================================================================
    # test-query - Test retrieval with a sample query
    # =========================================================================
    test_query_parser = subparsers.add_parser(
        "test-query",
        help="Test retrieval with a sample query"
    )
    test_query_parser.add_argument(
        "query",
        help="The query to test"
    )
    test_query_parser.add_argument(
        "--top-k",
        type=int,
        default=3,
        help="Number of results to return (default: 3)"
    )

    # =========================================================================
    # test-suite - Run full retrieval test suite
    # =========================================================================
    test_suite_parser = subparsers.add_parser(
        "test-suite",
        help="Run full retrieval quality test suite"
    )
    test_suite_parser.add_argument(
        "--queries",
        type=Path,
        help="Path to test queries JSON file"
    )

    # =========================================================================
    # watch - Watch for file changes
    # =========================================================================
    watch_parser = subparsers.add_parser(
        "watch",
        help="Watch for file changes and auto-sync"
    )
    watch_parser.add_argument(
        "path",
        type=Path,
        help="Path to content directory to watch"
    )

    # =========================================================================
    # health-check - Verify service connectivity
    # =========================================================================
    health_parser = subparsers.add_parser(
        "health-check",
        help="Verify Azure service connectivity"
    )
    health_parser.add_argument(
        "--component",
        choices=["all", "openai", "cosmos"],
        default="all",
        help="Component to check (default: all)"
    )

    # =========================================================================
    # compare - Compare current vs proposed content
    # =========================================================================
    compare_parser = subparsers.add_parser(
        "compare",
        help="Compare retrieval quality between content versions"
    )
    compare_parser.add_argument(
        "--current",
        type=Path,
        required=True,
        help="Path to current content file"
    )
    compare_parser.add_argument(
        "--proposed",
        type=Path,
        required=True,
        help="Path to proposed content file"
    )
    compare_parser.add_argument(
        "--queries",
        type=Path,
        required=True,
        help="Path to test queries JSON file"
    )

    # =========================================================================
    # audit-log - View content change history
    # =========================================================================
    audit_parser = subparsers.add_parser(
        "audit-log",
        help="View content change audit log"
    )
    audit_parser.add_argument(
        "--days",
        type=int,
        default=30,
        help="Number of days to show (default: 30)"
    )

    return parser


async def run_validate(args: argparse.Namespace) -> int:
    """
    Run content validation.

    Validates markdown files for:
    - Required frontmatter fields (title, category, keywords, last_updated)
    - Valid category values
    - Proper markdown structure
    - Reasonable chunk sizes

    Args:
        args: Parsed command-line arguments

    Returns:
        Exit code (0 for success, 1 for validation errors)
    """
    validator = ContentValidator(strict=args.strict)

    if args.path.is_file():
        files = [args.path]
    else:
        files = list(args.path.glob("**/*.md"))

    valid_count = 0
    error_count = 0

    for file in files:
        result = validator.validate(file)
        if result.is_valid:
            print(f"✓ {file.relative_to(args.path.parent)} - Valid")
            valid_count += 1
        else:
            print(f"✗ {file.relative_to(args.path.parent)} - {result.error}")
            error_count += 1

    print(f"\nSummary: {valid_count} valid, {error_count} errors")
    return 0 if error_count == 0 else 1


async def run_preview(args: argparse.Namespace) -> int:
    """
    Preview content chunking.

    Shows how a document will be split into chunks for vectorization,
    including estimated token counts per chunk.

    Args:
        args: Parsed command-line arguments

    Returns:
        Exit code (0 for success)
    """
    chunker = ContentChunker(max_tokens=args.max_tokens)

    chunks = chunker.chunk_file(args.file)

    print(f"Document: {chunks.title}")
    print(f"Chunks: {len(chunks.sections)}\n")

    for i, chunk in enumerate(chunks.sections, 1):
        print(f"Chunk {i} ({chunk.title}): {chunk.token_count} tokens")
        preview = chunk.content[:100] + "..." if len(chunk.content) > 100 else chunk.content
        print(f'"{preview}"\n')

    return 0


async def run_ingest(args: argparse.Namespace) -> int:
    """
    Ingest and vectorize content.

    Processes markdown files, generates vector embeddings via Azure OpenAI,
    and stores them in Cosmos DB for vector search.

    Args:
        args: Parsed command-line arguments

    Returns:
        Exit code (0 for success, 1 for errors)
    """
    embedder = ContentEmbedder()
    store = VectorStore()

    if args.path.is_file():
        files = [args.path]
    else:
        files = list(args.path.glob("**/*.md"))

    if args.dry_run:
        print("DRY RUN - No changes will be made\n")

    for file in files:
        print(f"Processing: {file.name}")

        if args.dry_run:
            print(f"  Would ingest: {file}")
            continue

        try:
            # Generate embeddings and store
            doc = await embedder.embed_file(file, force=args.force)
            await store.upsert(doc)
            print(f"  ✓ Ingested: {doc.chunk_count} chunks")
        except Exception as e:
            print(f"  ✗ Error: {e}")
            return 1

    return 0


async def run_status(args: argparse.Namespace) -> int:
    """
    Display knowledge base status.

    Shows document counts, chunk counts, and health metrics for the
    vector store.

    Args:
        args: Parsed command-line arguments

    Returns:
        Exit code (0 for success)
    """
    store = VectorStore()

    status = await store.get_status(category=args.category)

    print("Knowledge Base Status")
    print("─" * 40)
    print(f"Total Documents: {status.total_documents}")
    print(f"Total Chunks: {status.total_chunks}")
    print(f"Total Tokens: ~{status.estimated_tokens:,}")
    print()
    print("By Category:")
    for cat, info in status.by_category.items():
        print(f"  - {cat.title()}: {info.documents} documents, {info.chunks} chunks")
    print()
    print(f"Last Sync: {status.last_sync}")
    print(f"Vector Index: {status.index_health}")

    return 0


async def run_test_query(args: argparse.Namespace) -> int:
    """
    Test retrieval with a sample query.

    Generates an embedding for the query and searches the vector store,
    displaying the top results with similarity scores.

    Args:
        args: Parsed command-line arguments

    Returns:
        Exit code (0 for success)
    """
    tester = RetrievalTester()

    results = await tester.test_query(args.query, top_k=args.top_k)

    print(f'Query: "{args.query}"\n')
    print(f"Top {args.top_k} Results:")

    for i, result in enumerate(results, 1):
        print(f"{i}. [Score: {result.score:.2f}] {result.document} - {result.section}")
        preview = result.content[:80] + "..." if len(result.content) > 80 else result.content
        print(f'   "{preview}"\n')

    return 0


async def run_test_suite(args: argparse.Namespace) -> int:
    """
    Run full retrieval quality test suite.

    Executes a set of predefined test queries and measures retrieval
    accuracy (Retrieval@k) across different content categories.

    Args:
        args: Parsed command-line arguments

    Returns:
        Exit code (0 if tests pass, 1 if below threshold)
    """
    tester = RetrievalTester()

    print("Running retrieval tests...\n")

    results = await tester.run_suite(queries_file=args.queries)

    for category, metrics in results.by_category.items():
        passed = metrics.passed
        total = metrics.total
        pct = (passed / total * 100) if total > 0 else 0
        print(f"{category.title()} Queries: {passed}/{total} passed ({pct:.0f}%)")

    print()
    print(f"Overall Retrieval@3: {results.retrieval_at_3:.0%}")
    print(f"Target: >90% {'✓' if results.retrieval_at_3 >= 0.9 else '✗'}")

    return 0 if results.retrieval_at_3 >= 0.9 else 1


async def run_health_check(args: argparse.Namespace) -> int:
    """
    Verify Azure service connectivity.

    Checks connectivity to Azure OpenAI and Cosmos DB services
    used by the content manager.

    Args:
        args: Parsed command-line arguments

    Returns:
        Exit code (0 if healthy, 1 if any service unreachable)
    """
    print("Checking service health...\n")

    all_healthy = True

    if args.component in ["all", "openai"]:
        try:
            embedder = ContentEmbedder()
            await embedder.health_check()
            print("✓ Azure OpenAI: Connected")
        except Exception as e:
            print(f"✗ Azure OpenAI: {e}")
            all_healthy = False

    if args.component in ["all", "cosmos"]:
        try:
            store = VectorStore()
            await store.health_check()
            print("✓ Cosmos DB: Connected")
        except Exception as e:
            print(f"✗ Cosmos DB: {e}")
            all_healthy = False

    return 0 if all_healthy else 1


def main() -> int:
    """
    Main entry point for the content manager CLI.

    Parses command-line arguments and dispatches to the appropriate
    command handler.

    Returns:
        Exit code from the command handler
    """
    parser = create_parser()
    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        return 0

    # Map commands to handlers
    handlers = {
        "validate": run_validate,
        "preview": run_preview,
        "ingest": run_ingest,
        "status": run_status,
        "test-query": run_test_query,
        "test-suite": run_test_suite,
        "health-check": run_health_check,
    }

    handler = handlers.get(args.command)
    if handler is None:
        print(f"Command '{args.command}' not yet implemented")
        return 1

    # Run the async handler
    return asyncio.run(handler(args))


if __name__ == "__main__":
    sys.exit(main())
