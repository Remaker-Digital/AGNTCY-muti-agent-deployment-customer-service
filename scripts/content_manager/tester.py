# ============================================================================
# Retrieval Tester - Validate RAG Search Quality
# ============================================================================
# Purpose: Tests retrieval quality for the RAG knowledge base by measuring
#          how well queries retrieve expected documents.
#
# Metrics:
#   - Retrieval@k: Did the expected document appear in top k results?
#   - Mean Reciprocal Rank (MRR): Average position of first relevant result
#   - Precision@k: Fraction of top k results that are relevant
#
# Test Queries Format (JSON):
#   [
#     {
#       "query": "How do I return a product?",
#       "expected_documents": ["Return Policy"],
#       "category": "policy"
#     }
#   ]
#
# Usage:
#   tester = RetrievalTester()
#   results = await tester.run_suite("test-queries.json")
#   print(f"Retrieval@3: {results.retrieval_at_3:.0%}")
#
# See: docs/WIKI-Merchant-Content-Management.md for testing best practices
# ============================================================================

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

from .embedder import ContentEmbedder
from .store import VectorStore, SearchResult


@dataclass
class TestQuery:
    """
    A test query with expected results.

    Attributes:
        query: The search query text
        expected_documents: List of document titles that should be retrieved
        category: Optional category for filtering
    """
    query: str
    expected_documents: List[str]
    category: Optional[str] = None


@dataclass
class CategoryMetrics:
    """Metrics for a single category."""
    passed: int
    total: int


@dataclass
class TestSuiteResults:
    """
    Results from running the full test suite.

    Attributes:
        by_category: Metrics broken down by category
        retrieval_at_1: Fraction of queries with expected doc in top 1
        retrieval_at_3: Fraction of queries with expected doc in top 3
        retrieval_at_5: Fraction of queries with expected doc in top 5
        mrr: Mean Reciprocal Rank
    """
    by_category: Dict[str, CategoryMetrics]
    retrieval_at_1: float
    retrieval_at_3: float
    retrieval_at_5: float
    mrr: float


class RetrievalTester:
    """
    Tests RAG retrieval quality.

    This tester:
    - Generates embeddings for test queries
    - Searches the vector store
    - Compares results against expected documents
    - Calculates retrieval metrics

    Attributes:
        embedder: Content embedder for query vectors
        store: Vector store for searching
    """

    def __init__(self):
        """Initialize the tester with embedder and store."""
        self.embedder = ContentEmbedder()
        self.store = VectorStore()

    async def test_query(
        self,
        query: str,
        top_k: int = 3,
        category: Optional[str] = None
    ) -> List[SearchResult]:
        """
        Test a single query and return results.

        Args:
            query: The search query
            top_k: Number of results to return
            category: Optional category filter

        Returns:
            List of search results
        """
        # Generate query embedding
        embedding = await self.embedder._generate_embedding(query)

        # Search
        results = await self.store.search(
            query_embedding=embedding,
            top_k=top_k,
            category=category
        )

        return results

    async def run_suite(
        self,
        queries_file: Optional[Path] = None
    ) -> TestSuiteResults:
        """
        Run the full test suite.

        Args:
            queries_file: Path to test queries JSON file.
                         If None, uses default test queries.

        Returns:
            TestSuiteResults with all metrics
        """
        # Load test queries
        if queries_file and queries_file.exists():
            queries = self._load_queries(queries_file)
        else:
            queries = self._default_queries()

        # Track metrics
        by_category: Dict[str, Dict[str, int]] = {}
        retrieval_at_1_hits = 0
        retrieval_at_3_hits = 0
        retrieval_at_5_hits = 0
        reciprocal_ranks = []

        for test in queries:
            # Get results
            results = await self.test_query(
                test.query,
                top_k=5,
                category=test.category
            )

            # Extract document titles from results
            result_docs = [r.document for r in results]

            # Check if expected document was retrieved
            found_at = None
            for expected in test.expected_documents:
                if expected in result_docs:
                    found_at = result_docs.index(expected) + 1
                    break

            # Update metrics
            category = test.category or "general"
            if category not in by_category:
                by_category[category] = {"passed": 0, "total": 0}

            by_category[category]["total"] += 1

            if found_at:
                if found_at <= 1:
                    retrieval_at_1_hits += 1
                if found_at <= 3:
                    retrieval_at_3_hits += 1
                    by_category[category]["passed"] += 1
                if found_at <= 5:
                    retrieval_at_5_hits += 1
                reciprocal_ranks.append(1.0 / found_at)
            else:
                reciprocal_ranks.append(0.0)

        # Calculate final metrics
        total = len(queries)

        return TestSuiteResults(
            by_category={
                cat: CategoryMetrics(passed=m["passed"], total=m["total"])
                for cat, m in by_category.items()
            },
            retrieval_at_1=retrieval_at_1_hits / total if total > 0 else 0,
            retrieval_at_3=retrieval_at_3_hits / total if total > 0 else 0,
            retrieval_at_5=retrieval_at_5_hits / total if total > 0 else 0,
            mrr=sum(reciprocal_ranks) / len(reciprocal_ranks) if reciprocal_ranks else 0
        )

    def _load_queries(self, file_path: Path) -> List[TestQuery]:
        """
        Load test queries from JSON file.

        Expected format:
        [
          {"query": "...", "expected_documents": ["..."], "category": "..."}
        ]

        Args:
            file_path: Path to JSON file

        Returns:
            List of TestQuery objects
        """
        with open(file_path) as f:
            data = json.load(f)

        return [
            TestQuery(
                query=item["query"],
                expected_documents=item["expected_documents"],
                category=item.get("category")
            )
            for item in data
        ]

    def _default_queries(self) -> List[TestQuery]:
        """
        Return default test queries for basic validation.

        These queries cover common customer service scenarios.

        Returns:
            List of default TestQuery objects
        """
        return [
            # Policy queries
            TestQuery(
                query="How do I return a product?",
                expected_documents=["Return Policy"],
                category="policy"
            ),
            TestQuery(
                query="What is the shipping time?",
                expected_documents=["Shipping Policy"],
                category="policy"
            ),
            TestQuery(
                query="Can I get a refund?",
                expected_documents=["Return Policy"],
                category="policy"
            ),

            # FAQ queries
            TestQuery(
                query="How do I track my order?",
                expected_documents=["Order Tracking FAQ"],
                category="faq"
            ),
            TestQuery(
                query="How do I change my password?",
                expected_documents=["Account FAQ"],
                category="faq"
            ),

            # Troubleshooting queries
            TestQuery(
                query="My coffee maker is not working",
                expected_documents=["Equipment Troubleshooting"],
                category="troubleshooting"
            ),
            TestQuery(
                query="Coffee tastes bitter",
                expected_documents=["Brewing Troubleshooting"],
                category="troubleshooting"
            ),

            # General queries
            TestQuery(
                query="What are your business hours?",
                expected_documents=["Contact Information", "Store Hours"],
                category=None
            ),
            TestQuery(
                query="Do you have a loyalty program?",
                expected_documents=["Loyalty Program"],
                category=None
            ),
            TestQuery(
                query="How do I earn rewards points?",
                expected_documents=["Loyalty Program"],
                category=None
            )
        ]

    async def compare_versions(
        self,
        current_file: Path,
        proposed_file: Path,
        queries_file: Path
    ) -> Dict:
        """
        Compare retrieval quality between two content versions.

        Useful for A/B testing content changes before deployment.

        Args:
            current_file: Path to current content
            proposed_file: Path to proposed content
            queries_file: Path to test queries

        Returns:
            Comparison results with per-query improvements
        """
        queries = self._load_queries(queries_file)

        results = {
            "queries": [],
            "current_score": 0.0,
            "proposed_score": 0.0,
            "improvement": 0.0
        }

        # This would require a more complex implementation
        # to temporarily ingest different versions and compare
        # For now, return placeholder

        return results
