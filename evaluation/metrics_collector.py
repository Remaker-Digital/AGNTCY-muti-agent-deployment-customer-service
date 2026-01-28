"""
Metrics collection for Phase 3.5 evaluation.

This module collects and calculates evaluation metrics including:
- Intent classification accuracy, precision, recall, F1
- Response quality scores (human evaluation)
- Escalation detection precision/recall
- Critic/Supervisor block rates
- RAG retrieval accuracy
- Cost and latency metrics

Usage:
    from evaluation.metrics_collector import MetricsCollector

    collector = MetricsCollector()
    collector.add_intent_result("ic-001", "ORDER_STATUS", "ORDER_STATUS")
    collector.add_intent_result("ic-002", "RETURN_REQUEST", "REFUND_STATUS")
    metrics = collector.calculate_intent_metrics()
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
from collections import defaultdict
import json


@dataclass
class IntentResult:
    """Result of a single intent classification."""

    sample_id: str
    expected: str
    predicted: str
    confidence: float
    correct: bool
    latency_ms: float
    cost: float


@dataclass
class ResponseResult:
    """Result of a single response generation with quality scores."""

    sample_id: str
    scenario: str
    response: str
    accuracy: float  # 1-5
    completeness: float  # 1-5
    tone: float  # 1-5
    clarity: float  # 1-5
    actionability: float  # 1-5
    quality_score: float  # Weighted 0-100%
    latency_ms: float
    cost: float
    evaluator: str = ""
    notes: str = ""


@dataclass
class EscalationResult:
    """Result of a single escalation detection."""

    sample_id: str
    expected_escalate: bool
    predicted_escalate: bool
    confidence: float
    correct: bool
    latency_ms: float
    cost: float


@dataclass
class CriticResult:
    """Result of a single critic/supervisor validation."""

    sample_id: str
    input_type: str  # "normal", "adversarial", "prompt_injection", etc.
    expected_action: str  # "ALLOW" or "BLOCK"
    predicted_action: str
    correct: bool
    latency_ms: float
    cost: float


@dataclass
class RetrievalResult:
    """Result of a single RAG retrieval."""

    sample_id: str
    query: str
    expected_docs: list[str]  # Expected document IDs in top-k
    retrieved_docs: list[str]  # Actually retrieved document IDs
    relevant_in_top_1: bool
    relevant_in_top_3: bool
    relevant_in_top_5: bool
    latency_ms: float
    cost: float


class MetricsCollector:
    """
    Collects and calculates metrics for Phase 3.5 evaluation.

    Tracks results across multiple test runs and provides
    aggregated metrics for each evaluation type.
    """

    def __init__(self):
        """Initialize metrics collector."""
        self.intent_results: list[IntentResult] = []
        self.response_results: list[ResponseResult] = []
        self.escalation_results: list[EscalationResult] = []
        self.critic_results: list[CriticResult] = []
        self.retrieval_results: list[RetrievalResult] = []

        self.total_cost: float = 0.0
        self.total_tokens: int = 0
        self.start_time: datetime = datetime.now()

    # Intent Classification Methods
    def add_intent_result(
        self,
        sample_id: str,
        expected: str,
        predicted: str,
        confidence: float = 1.0,
        latency_ms: float = 0.0,
        cost: float = 0.0,
    ) -> None:
        """Add an intent classification result."""
        result = IntentResult(
            sample_id=sample_id,
            expected=expected,
            predicted=predicted,
            confidence=confidence,
            correct=(expected == predicted),
            latency_ms=latency_ms,
            cost=cost,
        )
        self.intent_results.append(result)
        self.total_cost += cost

    def calculate_intent_metrics(self) -> dict:
        """
        Calculate intent classification metrics.

        Returns:
            Dictionary with accuracy, per-intent precision/recall/F1,
            confusion matrix, and latency stats.
        """
        if not self.intent_results:
            return {"error": "No intent results collected"}

        total = len(self.intent_results)
        correct = sum(1 for r in self.intent_results if r.correct)
        accuracy = correct / total

        # Per-intent metrics
        intent_counts = defaultdict(lambda: {"tp": 0, "fp": 0, "fn": 0})
        confusion = defaultdict(lambda: defaultdict(int))

        for r in self.intent_results:
            confusion[r.expected][r.predicted] += 1
            if r.correct:
                intent_counts[r.expected]["tp"] += 1
            else:
                intent_counts[r.expected]["fn"] += 1
                intent_counts[r.predicted]["fp"] += 1

        per_intent = {}
        for intent, counts in intent_counts.items():
            tp, fp, fn = counts["tp"], counts["fp"], counts["fn"]
            precision = tp / (tp + fp) if (tp + fp) > 0 else 0
            recall = tp / (tp + fn) if (tp + fn) > 0 else 0
            f1 = (
                2 * precision * recall / (precision + recall)
                if (precision + recall) > 0
                else 0
            )
            per_intent[intent] = {
                "precision": round(precision, 3),
                "recall": round(recall, 3),
                "f1": round(f1, 3),
                "support": tp + fn,
            }

        # Latency stats
        latencies = [r.latency_ms for r in self.intent_results]
        latencies.sort()

        return {
            "total_samples": total,
            "correct": correct,
            "accuracy": round(accuracy, 4),
            "accuracy_pct": f"{accuracy * 100:.1f}%",
            "per_intent": per_intent,
            "confusion_matrix": dict(confusion),
            "latency": {
                "p50_ms": round(latencies[len(latencies) // 2], 2) if latencies else 0,
                "p95_ms": round(
                    latencies[int(len(latencies) * 0.95)] if latencies else 0, 2
                ),
                "p99_ms": round(
                    latencies[int(len(latencies) * 0.99)] if latencies else 0, 2
                ),
                "mean_ms": (
                    round(sum(latencies) / len(latencies), 2) if latencies else 0
                ),
            },
            "total_cost": round(sum(r.cost for r in self.intent_results), 4),
        }

    # Response Quality Methods
    def add_response_result(
        self,
        sample_id: str,
        scenario: str,
        response: str,
        accuracy: float,
        completeness: float,
        tone: float,
        clarity: float,
        actionability: float,
        latency_ms: float = 0.0,
        cost: float = 0.0,
        evaluator: str = "",
        notes: str = "",
    ) -> None:
        """
        Add a response quality result.

        Args:
            accuracy, completeness, tone, clarity, actionability: 1-5 scale ratings
        """
        # Calculate weighted quality score (0-100%)
        # Weights: Accuracy 25%, Completeness 20%, Tone 20%, Clarity 20%, Actionability 15%
        raw_score = (
            accuracy * 0.25
            + completeness * 0.20
            + tone * 0.20
            + clarity * 0.20
            + actionability * 0.15
        )
        # Convert 1-5 scale to 0-100%
        quality_score = (raw_score - 1) / 4 * 100

        result = ResponseResult(
            sample_id=sample_id,
            scenario=scenario,
            response=response,
            accuracy=accuracy,
            completeness=completeness,
            tone=tone,
            clarity=clarity,
            actionability=actionability,
            quality_score=quality_score,
            latency_ms=latency_ms,
            cost=cost,
            evaluator=evaluator,
            notes=notes,
        )
        self.response_results.append(result)
        self.total_cost += cost

    def calculate_response_metrics(self) -> dict:
        """
        Calculate response quality metrics.

        Returns:
            Dictionary with average quality score, per-dimension scores,
            and distribution statistics.
        """
        if not self.response_results:
            return {"error": "No response results collected"}

        total = len(self.response_results)
        quality_scores = [r.quality_score for r in self.response_results]

        avg_quality = sum(quality_scores) / total
        dimension_avgs = {
            "accuracy": sum(r.accuracy for r in self.response_results) / total,
            "completeness": sum(r.completeness for r in self.response_results) / total,
            "tone": sum(r.tone for r in self.response_results) / total,
            "clarity": sum(r.clarity for r in self.response_results) / total,
            "actionability": sum(r.actionability for r in self.response_results)
            / total,
        }

        return {
            "total_samples": total,
            "quality_score": round(avg_quality, 2),
            "quality_score_pct": f"{avg_quality:.1f}%",
            "dimension_averages": {k: round(v, 2) for k, v in dimension_avgs.items()},
            "score_distribution": {
                "min": round(min(quality_scores), 2),
                "max": round(max(quality_scores), 2),
                "std_dev": round(self._std_dev(quality_scores), 2),
            },
            "latency": {
                "mean_ms": round(
                    sum(r.latency_ms for r in self.response_results) / total, 2
                ),
            },
            "total_cost": round(sum(r.cost for r in self.response_results), 4),
        }

    # Escalation Detection Methods
    def add_escalation_result(
        self,
        sample_id: str,
        expected_escalate: bool,
        predicted_escalate: bool,
        confidence: float = 1.0,
        latency_ms: float = 0.0,
        cost: float = 0.0,
    ) -> None:
        """Add an escalation detection result."""
        result = EscalationResult(
            sample_id=sample_id,
            expected_escalate=expected_escalate,
            predicted_escalate=predicted_escalate,
            confidence=confidence,
            correct=(expected_escalate == predicted_escalate),
            latency_ms=latency_ms,
            cost=cost,
        )
        self.escalation_results.append(result)
        self.total_cost += cost

    def calculate_escalation_metrics(self) -> dict:
        """
        Calculate escalation detection metrics.

        Returns:
            Dictionary with precision, recall, F1, false positive rate,
            and confusion matrix.
        """
        if not self.escalation_results:
            return {"error": "No escalation results collected"}

        # Calculate confusion matrix values
        tp = sum(
            1
            for r in self.escalation_results
            if r.expected_escalate and r.predicted_escalate
        )
        fp = sum(
            1
            for r in self.escalation_results
            if not r.expected_escalate and r.predicted_escalate
        )
        fn = sum(
            1
            for r in self.escalation_results
            if r.expected_escalate and not r.predicted_escalate
        )
        tn = sum(
            1
            for r in self.escalation_results
            if not r.expected_escalate and not r.predicted_escalate
        )

        precision = tp / (tp + fp) if (tp + fp) > 0 else 0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0
        f1 = (
            2 * precision * recall / (precision + recall)
            if (precision + recall) > 0
            else 0
        )
        false_positive_rate = fp / (fp + tn) if (fp + tn) > 0 else 0

        return {
            "total_samples": len(self.escalation_results),
            "precision": round(precision, 4),
            "precision_pct": f"{precision * 100:.1f}%",
            "recall": round(recall, 4),
            "recall_pct": f"{recall * 100:.1f}%",
            "f1_score": round(f1, 4),
            "false_positive_rate": round(false_positive_rate, 4),
            "false_positive_rate_pct": f"{false_positive_rate * 100:.1f}%",
            "confusion_matrix": {
                "true_positive": tp,
                "false_positive": fp,
                "false_negative": fn,
                "true_negative": tn,
            },
            "total_cost": round(sum(r.cost for r in self.escalation_results), 4),
        }

    # Critic/Supervisor Methods
    def add_critic_result(
        self,
        sample_id: str,
        input_type: str,
        expected_action: str,
        predicted_action: str,
        latency_ms: float = 0.0,
        cost: float = 0.0,
    ) -> None:
        """Add a critic/supervisor validation result."""
        result = CriticResult(
            sample_id=sample_id,
            input_type=input_type,
            expected_action=expected_action,
            predicted_action=predicted_action,
            correct=(expected_action == predicted_action),
            latency_ms=latency_ms,
            cost=cost,
        )
        self.critic_results.append(result)
        self.total_cost += cost

    def calculate_critic_metrics(self) -> dict:
        """
        Calculate critic/supervisor metrics.

        Returns:
            Dictionary with block rates for normal and adversarial inputs,
            false positive rate, and per-category breakdown.
        """
        if not self.critic_results:
            return {"error": "No critic results collected"}

        # Separate normal and adversarial
        normal = [r for r in self.critic_results if r.input_type == "normal"]
        adversarial = [r for r in self.critic_results if r.input_type != "normal"]

        # False positive = blocked when should have allowed (normal inputs)
        normal_blocked = sum(1 for r in normal if r.predicted_action == "BLOCK")
        false_positive_rate = normal_blocked / len(normal) if normal else 0

        # True positive = blocked when should have blocked (adversarial inputs)
        adversarial_blocked = sum(
            1 for r in adversarial if r.predicted_action == "BLOCK"
        )
        true_positive_rate = (
            adversarial_blocked / len(adversarial) if adversarial else 0
        )

        # Per-category breakdown
        categories = defaultdict(lambda: {"total": 0, "blocked": 0})
        for r in self.critic_results:
            categories[r.input_type]["total"] += 1
            if r.predicted_action == "BLOCK":
                categories[r.input_type]["blocked"] += 1

        per_category = {
            cat: {
                "total": counts["total"],
                "blocked": counts["blocked"],
                "block_rate": (
                    round(counts["blocked"] / counts["total"], 3)
                    if counts["total"] > 0
                    else 0
                ),
            }
            for cat, counts in categories.items()
        }

        return {
            "total_samples": len(self.critic_results),
            "normal_samples": len(normal),
            "adversarial_samples": len(adversarial),
            "false_positive_rate": round(false_positive_rate, 4),
            "false_positive_rate_pct": f"{false_positive_rate * 100:.1f}%",
            "true_positive_rate": round(true_positive_rate, 4),
            "true_positive_rate_pct": f"{true_positive_rate * 100:.1f}%",
            "per_category": per_category,
            "total_cost": round(sum(r.cost for r in self.critic_results), 4),
        }

    # RAG Retrieval Methods
    def add_retrieval_result(
        self,
        sample_id: str,
        query: str,
        expected_docs: list[str],
        retrieved_docs: list[str],
        latency_ms: float = 0.0,
        cost: float = 0.0,
    ) -> None:
        """Add a RAG retrieval result."""
        # Check if any expected doc is in top-k
        relevant_in_top_1 = any(doc in retrieved_docs[:1] for doc in expected_docs)
        relevant_in_top_3 = any(doc in retrieved_docs[:3] for doc in expected_docs)
        relevant_in_top_5 = any(doc in retrieved_docs[:5] for doc in expected_docs)

        result = RetrievalResult(
            sample_id=sample_id,
            query=query,
            expected_docs=expected_docs,
            retrieved_docs=retrieved_docs,
            relevant_in_top_1=relevant_in_top_1,
            relevant_in_top_3=relevant_in_top_3,
            relevant_in_top_5=relevant_in_top_5,
            latency_ms=latency_ms,
            cost=cost,
        )
        self.retrieval_results.append(result)
        self.total_cost += cost

    def calculate_retrieval_metrics(self) -> dict:
        """
        Calculate RAG retrieval metrics.

        Returns:
            Dictionary with retrieval@1, @3, @5 accuracy and latency stats.
        """
        if not self.retrieval_results:
            return {"error": "No retrieval results collected"}

        total = len(self.retrieval_results)

        retrieval_at_1 = (
            sum(1 for r in self.retrieval_results if r.relevant_in_top_1) / total
        )
        retrieval_at_3 = (
            sum(1 for r in self.retrieval_results if r.relevant_in_top_3) / total
        )
        retrieval_at_5 = (
            sum(1 for r in self.retrieval_results if r.relevant_in_top_5) / total
        )

        latencies = [r.latency_ms for r in self.retrieval_results]

        return {
            "total_samples": total,
            "retrieval_at_1": round(retrieval_at_1, 4),
            "retrieval_at_1_pct": f"{retrieval_at_1 * 100:.1f}%",
            "retrieval_at_3": round(retrieval_at_3, 4),
            "retrieval_at_3_pct": f"{retrieval_at_3 * 100:.1f}%",
            "retrieval_at_5": round(retrieval_at_5, 4),
            "retrieval_at_5_pct": f"{retrieval_at_5 * 100:.1f}%",
            "latency": {
                "mean_ms": (
                    round(sum(latencies) / len(latencies), 2) if latencies else 0
                ),
                "p95_ms": (
                    round(sorted(latencies)[int(len(latencies) * 0.95)], 2)
                    if latencies
                    else 0
                ),
            },
            "total_cost": round(sum(r.cost for r in self.retrieval_results), 4),
        }

    # Utility Methods
    def _std_dev(self, values: list[float]) -> float:
        """Calculate standard deviation."""
        if len(values) < 2:
            return 0.0
        mean = sum(values) / len(values)
        variance = sum((x - mean) ** 2 for x in values) / (len(values) - 1)
        return variance**0.5

    def get_summary(self) -> dict:
        """Get summary of all collected metrics."""
        return {
            "session_duration_seconds": (
                datetime.now() - self.start_time
            ).total_seconds(),
            "total_cost": round(self.total_cost, 4),
            "intent_samples": len(self.intent_results),
            "response_samples": len(self.response_results),
            "escalation_samples": len(self.escalation_results),
            "critic_samples": len(self.critic_results),
            "retrieval_samples": len(self.retrieval_results),
        }

    def to_json(self, filepath: str) -> None:
        """Export all results to JSON file."""
        data = {
            "summary": self.get_summary(),
            "intent_metrics": (
                self.calculate_intent_metrics() if self.intent_results else {}
            ),
            "response_metrics": (
                self.calculate_response_metrics() if self.response_results else {}
            ),
            "escalation_metrics": (
                self.calculate_escalation_metrics() if self.escalation_results else {}
            ),
            "critic_metrics": (
                self.calculate_critic_metrics() if self.critic_results else {}
            ),
            "retrieval_metrics": (
                self.calculate_retrieval_metrics() if self.retrieval_results else {}
            ),
        }
        with open(filepath, "w") as f:
            json.dump(data, f, indent=2)

    def reset(self) -> None:
        """Reset all collected results."""
        self.intent_results = []
        self.response_results = []
        self.escalation_results = []
        self.critic_results = []
        self.retrieval_results = []
        self.total_cost = 0.0
        self.total_tokens = 0
        self.start_time = datetime.now()


if __name__ == "__main__":
    # Test the metrics collector
    collector = MetricsCollector()

    # Add some test intent results
    collector.add_intent_result(
        "ic-001", "ORDER_STATUS", "ORDER_STATUS", 0.95, 50.0, 0.001
    )
    collector.add_intent_result(
        "ic-002", "RETURN_REQUEST", "RETURN_REQUEST", 0.90, 45.0, 0.001
    )
    collector.add_intent_result(
        "ic-003", "PRODUCT_INQUIRY", "ORDER_STATUS", 0.70, 48.0, 0.001
    )

    # Add some test escalation results
    collector.add_escalation_result("esc-001", True, True, 0.95, 30.0, 0.001)
    collector.add_escalation_result("esc-002", False, False, 0.85, 25.0, 0.001)
    collector.add_escalation_result("esc-003", True, False, 0.60, 28.0, 0.001)

    # Print metrics
    print("Intent Metrics:")
    print(json.dumps(collector.calculate_intent_metrics(), indent=2))

    print("\nEscalation Metrics:")
    print(json.dumps(collector.calculate_escalation_metrics(), indent=2))

    print("\nSummary:")
    print(json.dumps(collector.get_summary(), indent=2))
