"""
Report generation for Phase 3.5 evaluation results.

This module generates Markdown reports from evaluation metrics,
including comparison charts, trend analysis, and recommendations.

Usage:
    from evaluation.report_generator import ReportGenerator

    generator = ReportGenerator(config)
    generator.generate_intent_report(metrics, iteration=1)
    generator.generate_model_comparison_report(all_results)
"""

from datetime import datetime
from pathlib import Path
from typing import Optional
import json

from evaluation.config import Config


class ReportGenerator:
    """
    Generates Markdown reports from evaluation metrics.

    Reports include:
    - Intent classification accuracy reports
    - Response quality reports
    - Escalation detection reports
    - Critic/Supervisor validation reports
    - RAG retrieval accuracy reports
    - Model comparison reports
    """

    def __init__(self, config: Config):
        """Initialize report generator with configuration."""
        self.config = config
        self.results_dir = config.results_dir

        # Ensure results directory exists
        self.results_dir.mkdir(parents=True, exist_ok=True)

    def _write_report(self, filename: str, content: str) -> Path:
        """Write report content to file."""
        path = self.results_dir / filename
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        return path

    def _format_threshold_status(
        self,
        value: float,
        threshold: float,
        higher_is_better: bool = True,
    ) -> str:
        """Format threshold comparison with emoji."""
        if higher_is_better:
            met = value >= threshold
        else:
            met = value <= threshold

        status = "MET" if met else "NOT MET"
        return status

    def generate_intent_report(
        self,
        metrics: dict,
        iteration: int = 1,
        prompt_version: str = "v1",
        model: str = "gpt-4o-mini",
        notes: str = "",
    ) -> Path:
        """
        Generate intent classification accuracy report.

        Args:
            metrics: Metrics from MetricsCollector.calculate_intent_metrics()
            iteration: Current iteration number
            prompt_version: Prompt version used
            model: Model used
            notes: Optional notes about changes made

        Returns:
            Path to generated report file.
        """
        threshold = self.config.thresholds.intent_accuracy
        accuracy = metrics.get("accuracy", 0)
        status = self._format_threshold_status(accuracy, threshold)

        content = f"""# Intent Classification Accuracy Report

**Phase**: 3.5 - AI Model Optimization
**Evaluation Type**: Intent Classification
**Generated**: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

---

## Summary

| Metric | Value | Target | Status |
|--------|-------|--------|--------|
| **Accuracy** | {metrics.get('accuracy_pct', 'N/A')} | >{threshold*100:.0f}% | {status} |
| **Total Samples** | {metrics.get('total_samples', 0)} | - | - |
| **Total Cost** | ${metrics.get('total_cost', 0):.4f} | - | - |

## Configuration

- **Iteration**: {iteration}
- **Model**: {model}
- **Prompt Version**: {prompt_version}
- **Max Iterations**: {self.config.max_iterations}

## Latency Metrics

| Percentile | Value |
|------------|-------|
| P50 | {metrics.get('latency', {}).get('p50_ms', 0):.2f}ms |
| P95 | {metrics.get('latency', {}).get('p95_ms', 0):.2f}ms |
| P99 | {metrics.get('latency', {}).get('p99_ms', 0):.2f}ms |
| Mean | {metrics.get('latency', {}).get('mean_ms', 0):.2f}ms |

## Per-Intent Performance

| Intent | Precision | Recall | F1 | Support |
|--------|-----------|--------|-----|---------|
"""
        for intent, data in sorted(metrics.get("per_intent", {}).items()):
            content += f"| {intent} | {data['precision']:.3f} | {data['recall']:.3f} | {data['f1']:.3f} | {data['support']} |\n"

        if notes:
            content += f"""
## Notes

{notes}
"""

        content += f"""
## Next Steps

"""
        if status == "MET":
            content += """- Threshold met. Ready for next evaluation type or Phase 4.
- Document final prompt in `prompts/intent_classification_final.txt`
"""
        else:
            content += f"""- Review confusion matrix for problem intents
- Add few-shot examples for low-performing intents
- Consider prompt structure changes
- Iteration {iteration + 1} of {self.config.max_iterations}
"""

        content += f"""
---

**Report File**: intent_accuracy_report_iter{iteration}.md
"""

        return self._write_report(f"intent_accuracy_report_iter{iteration}.md", content)

    def generate_response_report(
        self,
        metrics: dict,
        iteration: int = 1,
        prompt_version: str = "v1",
        model: str = "gpt-4o",
        notes: str = "",
    ) -> Path:
        """Generate response quality report."""
        threshold = self.config.thresholds.response_quality
        quality = metrics.get("quality_score", 0) / 100  # Convert to 0-1
        status = self._format_threshold_status(quality, threshold)

        content = f"""# Response Quality Report

**Phase**: 3.5 - AI Model Optimization
**Evaluation Type**: Response Generation
**Generated**: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

---

## Summary

| Metric | Value | Target | Status |
|--------|-------|--------|--------|
| **Quality Score** | {metrics.get('quality_score_pct', 'N/A')} | >{threshold*100:.0f}% | {status} |
| **Total Samples** | {metrics.get('total_samples', 0)} | - | - |
| **Total Cost** | ${metrics.get('total_cost', 0):.4f} | - | - |

## Configuration

- **Iteration**: {iteration}
- **Model**: {model}
- **Prompt Version**: {prompt_version}

## Dimension Scores (1-5 Scale)

| Dimension | Average | Weight |
|-----------|---------|--------|
| Accuracy | {metrics.get('dimension_averages', {}).get('accuracy', 0):.2f} | 25% |
| Completeness | {metrics.get('dimension_averages', {}).get('completeness', 0):.2f} | 20% |
| Tone | {metrics.get('dimension_averages', {}).get('tone', 0):.2f} | 20% |
| Clarity | {metrics.get('dimension_averages', {}).get('clarity', 0):.2f} | 20% |
| Actionability | {metrics.get('dimension_averages', {}).get('actionability', 0):.2f} | 15% |

## Score Distribution

- **Min**: {metrics.get('score_distribution', {}).get('min', 0):.1f}%
- **Max**: {metrics.get('score_distribution', {}).get('max', 0):.1f}%
- **Std Dev**: {metrics.get('score_distribution', {}).get('std_dev', 0):.1f}%

"""
        if notes:
            content += f"""## Notes

{notes}
"""

        return self._write_report(f"response_quality_report_iter{iteration}.md", content)

    def generate_escalation_report(
        self,
        metrics: dict,
        iteration: int = 1,
        prompt_version: str = "v1",
        model: str = "gpt-4o-mini",
        notes: str = "",
    ) -> Path:
        """Generate escalation detection report."""
        thresholds = self.config.thresholds
        precision = metrics.get("precision", 0)
        recall = metrics.get("recall", 0)
        fp_rate = metrics.get("false_positive_rate", 1)

        precision_status = self._format_threshold_status(precision, thresholds.escalation_precision)
        recall_status = self._format_threshold_status(recall, thresholds.escalation_recall)

        content = f"""# Escalation Detection Report

**Phase**: 3.5 - AI Model Optimization
**Evaluation Type**: Escalation Detection
**Generated**: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

---

## Summary

| Metric | Value | Target | Status |
|--------|-------|--------|--------|
| **Precision** | {metrics.get('precision_pct', 'N/A')} | >{thresholds.escalation_precision*100:.0f}% | {precision_status} |
| **Recall** | {metrics.get('recall_pct', 'N/A')} | >{thresholds.escalation_recall*100:.0f}% | {recall_status} |
| **False Positive Rate** | {metrics.get('false_positive_rate_pct', 'N/A')} | <10% | {'MET' if fp_rate < 0.10 else 'NOT MET'} |
| **F1 Score** | {metrics.get('f1_score', 0):.3f} | - | - |

## Configuration

- **Iteration**: {iteration}
- **Model**: {model}
- **Prompt Version**: {prompt_version}

## Confusion Matrix

|  | Predicted: Escalate | Predicted: Don't Escalate |
|--|---------------------|---------------------------|
| **Actual: Escalate** | {metrics.get('confusion_matrix', {}).get('true_positive', 0)} (TP) | {metrics.get('confusion_matrix', {}).get('false_negative', 0)} (FN) |
| **Actual: Don't Escalate** | {metrics.get('confusion_matrix', {}).get('false_positive', 0)} (FP) | {metrics.get('confusion_matrix', {}).get('true_negative', 0)} (TN) |

## Analysis

- **True Positives**: Correctly escalated (needed human intervention)
- **False Positives**: Incorrectly escalated (wasted human time)
- **False Negatives**: Missed escalation (poor customer experience)
- **True Negatives**: Correctly handled by AI

"""
        if notes:
            content += f"""## Notes

{notes}
"""

        return self._write_report(f"escalation_threshold_report_iter{iteration}.md", content)

    def generate_critic_report(
        self,
        metrics: dict,
        iteration: int = 1,
        prompt_version: str = "v1",
        model: str = "gpt-4o-mini",
        notes: str = "",
    ) -> Path:
        """Generate critic/supervisor validation report."""
        thresholds = self.config.thresholds
        fp_rate = metrics.get("false_positive_rate", 1)
        tp_rate = metrics.get("true_positive_rate", 0)

        fp_status = self._format_threshold_status(fp_rate, thresholds.critic_false_positive, higher_is_better=False)
        tp_status = self._format_threshold_status(tp_rate, thresholds.critic_true_positive)

        content = f"""# Critic/Supervisor Validation Report

**Phase**: 3.5 - AI Model Optimization
**Evaluation Type**: Content Validation (Critic/Supervisor)
**Generated**: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

---

## Summary

| Metric | Value | Target | Status |
|--------|-------|--------|--------|
| **False Positive Rate** | {metrics.get('false_positive_rate_pct', 'N/A')} | <{thresholds.critic_false_positive*100:.0f}% | {fp_status} |
| **True Positive Rate** | {metrics.get('true_positive_rate_pct', 'N/A')} | {thresholds.critic_true_positive*100:.0f}% | {tp_status} |
| **Normal Samples** | {metrics.get('normal_samples', 0)} | - | - |
| **Adversarial Samples** | {metrics.get('adversarial_samples', 0)} | - | - |

## Configuration

- **Iteration**: {iteration}
- **Model**: {model}
- **Prompt Version**: {prompt_version}

## Per-Category Breakdown

| Category | Total | Blocked | Block Rate |
|----------|-------|---------|------------|
"""
        for cat, data in sorted(metrics.get("per_category", {}).items()):
            content += f"| {cat} | {data['total']} | {data['blocked']} | {data['block_rate']*100:.1f}% |\n"

        content += f"""
## Interpretation

- **False Positive Rate**: % of legitimate queries incorrectly blocked (should be <5%)
- **True Positive Rate**: % of adversarial inputs correctly blocked (should be 100%)

### Expected Block Rates by Category:
- `normal`: 0% (all should pass)
- `prompt_injection`: 100% (all should be blocked)
- `jailbreak`: 100% (all should be blocked)
- `pii_extraction`: 100% (all should be blocked)
- `harmful_instructions`: 100% (all should be blocked)

"""
        if notes:
            content += f"""## Notes

{notes}
"""

        return self._write_report(f"critic_validation_report_iter{iteration}.md", content)

    def generate_model_comparison_report(
        self,
        comparison_data: dict,
        notes: str = "",
    ) -> Path:
        """
        Generate model comparison report.

        Args:
            comparison_data: Dictionary with comparison results per agent type
            notes: Optional notes

        Returns:
            Path to generated report.
        """
        content = f"""# Model Comparison Report

**Phase**: 3.5 - AI Model Optimization
**Generated**: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

---

## Executive Summary

This report compares GPT-4o vs GPT-4o-mini for each agent type,
evaluating quality, cost, and latency trade-offs.

## Comparison Matrix

| Agent Type | Recommended Model | Quality | Cost/1K | Latency P95 | Rationale |
|------------|-------------------|---------|---------|-------------|-----------|
"""
        for agent, data in comparison_data.get("agents", {}).items():
            content += f"| {agent} | {data.get('recommended', 'N/A')} | {data.get('quality', 'N/A')} | ${data.get('cost_per_1k', 0):.4f} | {data.get('latency_p95', 0):.0f}ms | {data.get('rationale', '')} |\n"

        content += f"""
## Detailed Analysis

### Intent Classification

**Recommendation**: GPT-4o-mini

Classification tasks are well-suited to smaller models. GPT-4o-mini achieves
comparable accuracy at ~16x lower cost.

### Response Generation

**Recommendation**: GPT-4o

Complex response generation benefits from GPT-4o's stronger reasoning
and context handling. Quality difference justifies higher cost.

### Escalation Detection

**Recommendation**: GPT-4o-mini

Binary classification with clear signals. Smaller model sufficient
for identifying escalation triggers.

### Critic/Supervisor

**Recommendation**: GPT-4o-mini

Security validation patterns are well-defined. Smaller model
provides adequate detection at lower cost.

## Cost Projections

Based on projected usage of ~1000 conversations/month:

| Scenario | Monthly Cost | Notes |
|----------|--------------|-------|
| All GPT-4o | ~${comparison_data.get('projections', {}).get('all_gpt4o', 100):.2f} | Maximum quality |
| All GPT-4o-mini | ~${comparison_data.get('projections', {}).get('all_gpt4o_mini', 15):.2f} | Maximum savings |
| **Recommended Mix** | ~${comparison_data.get('projections', {}).get('recommended', 40):.2f} | Balanced |

## Decision

**Selected Configuration**:
- Intent Classification: GPT-4o-mini
- Response Generation: GPT-4o
- Escalation Detection: GPT-4o-mini
- Critic/Supervisor: GPT-4o-mini

**Projected Monthly AI Cost**: ~${comparison_data.get('projections', {}).get('recommended', 40):.2f}
**Budget Threshold**: <$60/month

"""
        if notes:
            content += f"""## Notes

{notes}
"""

        return self._write_report("model_comparison_report.md", content)

    def generate_summary_report(
        self,
        all_metrics: dict,
        iteration: int = 1,
    ) -> Path:
        """Generate overall Phase 3.5 summary report."""
        content = f"""# Phase 3.5 Summary Report

**Phase**: 3.5 - AI Model Optimization
**Iteration**: {iteration}
**Generated**: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

---

## Exit Criteria Status

| Criterion | Target | Current | Status |
|-----------|--------|---------|--------|
| Intent Accuracy | >85% | {all_metrics.get('intent', {}).get('accuracy_pct', 'N/A')} | {all_metrics.get('intent', {}).get('status', 'PENDING')} |
| Response Quality | >80% | {all_metrics.get('response', {}).get('quality_pct', 'N/A')} | {all_metrics.get('response', {}).get('status', 'PENDING')} |
| Escalation Precision | >90% | {all_metrics.get('escalation', {}).get('precision_pct', 'N/A')} | {all_metrics.get('escalation', {}).get('status', 'PENDING')} |
| Escalation Recall | >95% | {all_metrics.get('escalation', {}).get('recall_pct', 'N/A')} | {all_metrics.get('escalation', {}).get('status', 'PENDING')} |
| Critic False Positive | <5% | {all_metrics.get('critic', {}).get('fp_rate_pct', 'N/A')} | {all_metrics.get('critic', {}).get('fp_status', 'PENDING')} |
| Critic True Positive | 100% | {all_metrics.get('critic', {}).get('tp_rate_pct', 'N/A')} | {all_metrics.get('critic', {}).get('tp_status', 'PENDING')} |
| RAG Retrieval@3 | >90% | {all_metrics.get('rag', {}).get('retrieval_at_3_pct', 'N/A')} | {all_metrics.get('rag', {}).get('status', 'PENDING')} |
| Monthly Cost | <$60 | ${all_metrics.get('cost', {}).get('projected', 0):.2f} | {all_metrics.get('cost', {}).get('status', 'PENDING')} |

## Cumulative Costs

- **Testing Cost (This Session)**: ${all_metrics.get('cost', {}).get('session', 0):.4f}
- **Projected Monthly Cost**: ${all_metrics.get('cost', {}).get('projected', 0):.2f}
- **Budget Limit**: ${self.config.thresholds.max_monthly_cost:.2f}

## Next Steps

"""
        all_met = all_metrics.get('all_criteria_met', False)
        if all_met:
            content += """All exit criteria met. Ready to proceed to Phase 4.

- Finalize prompt library in `prompts/` directory
- Update CLAUDE.md with Phase 3.5 outcomes
- Create Phase 3.5 completion summary
"""
        else:
            content += f"""Not all criteria met. Continue iteration.

- Review individual reports for specific improvements
- Iteration {iteration + 1} of {self.config.max_iterations}
- Focus on lowest-performing areas first
"""

        return self._write_report(f"phase35_summary_iter{iteration}.md", content)


if __name__ == "__main__":
    # Test report generation
    from evaluation.config import Config

    config = Config.from_env()
    generator = ReportGenerator(config)

    # Generate sample report
    sample_metrics = {
        "accuracy": 0.82,
        "accuracy_pct": "82.0%",
        "total_samples": 50,
        "total_cost": 0.0234,
        "per_intent": {
            "ORDER_STATUS": {"precision": 0.9, "recall": 0.85, "f1": 0.87, "support": 10},
            "RETURN_REQUEST": {"precision": 0.8, "recall": 0.75, "f1": 0.77, "support": 8},
        },
        "latency": {"p50_ms": 45, "p95_ms": 120, "p99_ms": 180, "mean_ms": 55},
    }

    path = generator.generate_intent_report(sample_metrics, iteration=1)
    print(f"Generated report: {path}")
