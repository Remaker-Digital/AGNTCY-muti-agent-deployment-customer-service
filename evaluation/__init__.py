"""
Phase 3.5: AI Model Optimization - Evaluation Framework

This package provides tools for testing and optimizing AI model interactions
before full Azure deployment. The goal is to achieve quality thresholds at
~$20-50/month instead of ~$310-360/month.

Directory Structure:
    evaluation/
    ├── __init__.py              # This file
    ├── config.py                # Configuration management
    ├── test_harness.py          # Main test orchestrator
    ├── azure_openai_client.py   # Azure OpenAI API wrapper
    ├── metrics_collector.py     # Metrics collection
    ├── report_generator.py      # Report generation
    │
    ├── datasets/                # Evaluation data (JSON)
    │   ├── intent_classification.json
    │   ├── response_quality.json
    │   ├── escalation_scenarios.json
    │   ├── adversarial_inputs.json
    │   └── knowledge_base.json
    │
    ├── prompts/                 # Prompt versions (TXT)
    │   ├── intent_classification_v1.txt
    │   ├── response_generation_v1.txt
    │   ├── escalation_detection_v1.txt
    │   ├── critic_input_validation.txt
    │   └── critic_output_validation.txt
    │
    ├── rag/                     # RAG testing
    │   ├── local_faiss_store.py
    │   ├── embedding_client.py
    │   └── retrieval_tester.py
    │
    └── results/                 # Evaluation results (MD, JSON)
        ├── intent_accuracy_report.md
        ├── response_quality_report.md
        └── model_comparison_report.md

Exit Criteria (Phase 3.5):
    - Intent Classification: >85% accuracy
    - Response Generation: >80% quality score
    - Escalation Detection: <10% false positive, >95% true positive
    - Critic/Supervisor: <5% false positive, 100% adversarial block
    - RAG Retrieval: >90% retrieval@3
    - Cost Projection: <$60/month

Usage:
    from evaluation import TestHarness, AzureOpenAIClient

    client = AzureOpenAIClient.from_env()
    harness = TestHarness(client)
    results = harness.run_intent_evaluation()
    harness.generate_report(results)
"""

__version__ = "0.1.0"
__author__ = "Development Team"
__phase__ = "3.5"

# Re-export main classes for convenience
from evaluation.config import Config
from evaluation.azure_openai_client import AzureOpenAIClient
from evaluation.test_harness import TestHarness
from evaluation.metrics_collector import MetricsCollector
from evaluation.report_generator import ReportGenerator

__all__ = [
    "Config",
    "AzureOpenAIClient",
    "TestHarness",
    "MetricsCollector",
    "ReportGenerator",
]
