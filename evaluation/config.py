"""
Configuration management for Phase 3.5 evaluation framework.

This module handles environment variables, API configuration, and
evaluation settings. Configuration is loaded from .env.phase3.5 file
or environment variables.

Environment Variables:
    AZURE_OPENAI_ENDPOINT: Azure OpenAI resource endpoint
    AZURE_OPENAI_API_KEY: API key for authentication
    AZURE_OPENAI_API_VERSION: API version (default: 2024-02-15-preview)
    AZURE_OPENAI_GPT4O_MINI_DEPLOYMENT: GPT-4o-mini deployment name
    AZURE_OPENAI_GPT4O_DEPLOYMENT: GPT-4o deployment name
    AZURE_OPENAI_EMBEDDING_DEPLOYMENT: Embedding model deployment name
    PHASE35_BUDGET_LIMIT: Monthly budget limit (default: 50.00)
    PHASE35_ALERT_THRESHOLD: Alert threshold percentage (default: 0.80)
"""

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional
import json


@dataclass
class ModelConfig:
    """Configuration for a specific model deployment."""
    deployment_name: str
    cost_per_1k_input: float  # Cost per 1K input tokens
    cost_per_1k_output: float  # Cost per 1K output tokens
    max_tokens: int = 4096
    temperature: float = 0.0  # Deterministic for testing


@dataclass
class EvaluationThresholds:
    """Quality thresholds for Phase 3.5 exit criteria."""
    intent_accuracy: float = 0.85  # >85%
    response_quality: float = 0.80  # >80%
    escalation_precision: float = 0.90  # >90%
    escalation_recall: float = 0.95  # >95%
    critic_false_positive: float = 0.05  # <5%
    critic_true_positive: float = 1.00  # 100%
    rag_retrieval_at_3: float = 0.90  # >90%
    max_monthly_cost: float = 60.00  # <$60/month


@dataclass
class Config:
    """
    Main configuration class for Phase 3.5 evaluation framework.

    Loads configuration from environment variables and provides
    sensible defaults for testing.

    Example:
        config = Config.from_env()
        print(f"Using endpoint: {config.azure_endpoint}")
    """
    # Azure OpenAI Settings
    azure_endpoint: str = ""
    azure_api_key: str = ""
    azure_api_version: str = "2024-02-15-preview"

    # Model Deployments
    gpt4o_mini: ModelConfig = field(default_factory=lambda: ModelConfig(
        deployment_name="gpt-4o-mini",
        cost_per_1k_input=0.00015,  # $0.15 per 1M = $0.00015 per 1K
        cost_per_1k_output=0.0006,  # $0.60 per 1M = $0.0006 per 1K
        max_tokens=4096,
        temperature=0.0
    ))

    gpt4o: ModelConfig = field(default_factory=lambda: ModelConfig(
        deployment_name="gpt-4o",
        cost_per_1k_input=0.0025,  # $2.50 per 1M = $0.0025 per 1K
        cost_per_1k_output=0.01,   # $10.00 per 1M = $0.01 per 1K
        max_tokens=4096,
        temperature=0.0
    ))

    embedding: ModelConfig = field(default_factory=lambda: ModelConfig(
        deployment_name="text-embedding-3-large",
        cost_per_1k_input=0.00013,  # $0.13 per 1M = $0.00013 per 1K
        cost_per_1k_output=0.0,     # No output tokens for embeddings
        max_tokens=8191
    ))

    # Budget Settings
    budget_limit: float = 50.00
    alert_threshold: float = 0.80

    # Evaluation Thresholds
    thresholds: EvaluationThresholds = field(default_factory=EvaluationThresholds)

    # Paths
    base_dir: Path = field(default_factory=lambda: Path(__file__).parent)
    datasets_dir: Path = field(default_factory=lambda: Path(__file__).parent / "datasets")
    prompts_dir: Path = field(default_factory=lambda: Path(__file__).parent / "prompts")
    results_dir: Path = field(default_factory=lambda: Path(__file__).parent / "results")
    rag_dir: Path = field(default_factory=lambda: Path(__file__).parent / "rag")

    # Iteration Limits
    max_iterations: int = 5
    min_iterations: int = 2

    @classmethod
    def from_env(cls, env_file: Optional[Path] = None) -> "Config":
        """
        Load configuration from environment variables or .env file.

        Args:
            env_file: Optional path to .env file. If not provided,
                     looks for .env.phase3.5 in project root.

        Returns:
            Config instance with values from environment.

        Raises:
            ValueError: If required environment variables are missing.
        """
        # Try to load .env file if it exists
        if env_file is None:
            env_file = Path(__file__).parent.parent / ".env.phase3.5"

        if env_file.exists():
            cls._load_env_file(env_file)

        # Required settings
        azure_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT", "")
        azure_api_key = os.getenv("AZURE_OPENAI_API_KEY", "")

        if not azure_endpoint or not azure_api_key:
            print("WARNING: Azure OpenAI credentials not found.")
            print("Set AZURE_OPENAI_ENDPOINT and AZURE_OPENAI_API_KEY environment variables.")
            print("Or create a .env.phase3.5 file with these values.")

        # Create config with environment values
        config = cls(
            azure_endpoint=azure_endpoint,
            azure_api_key=azure_api_key,
            azure_api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-15-preview"),
            budget_limit=float(os.getenv("PHASE35_BUDGET_LIMIT", "50.00")),
            alert_threshold=float(os.getenv("PHASE35_ALERT_THRESHOLD", "0.80")),
        )

        # Update model deployment names if provided
        if gpt4o_mini_name := os.getenv("AZURE_OPENAI_GPT4O_MINI_DEPLOYMENT"):
            config.gpt4o_mini.deployment_name = gpt4o_mini_name

        if gpt4o_name := os.getenv("AZURE_OPENAI_GPT4O_DEPLOYMENT"):
            config.gpt4o.deployment_name = gpt4o_name

        if embedding_name := os.getenv("AZURE_OPENAI_EMBEDDING_DEPLOYMENT"):
            config.embedding.deployment_name = embedding_name

        return config

    @staticmethod
    def _load_env_file(env_file: Path) -> None:
        """Load environment variables from a .env file."""
        with open(env_file, "r") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    key = key.strip()
                    value = value.strip().strip('"').strip("'")
                    os.environ.setdefault(key, value)

    def validate(self) -> list[str]:
        """
        Validate configuration and return list of issues.

        Returns:
            List of validation error messages. Empty if valid.
        """
        issues = []

        if not self.azure_endpoint:
            issues.append("AZURE_OPENAI_ENDPOINT is required")

        if not self.azure_api_key:
            issues.append("AZURE_OPENAI_API_KEY is required")

        if self.budget_limit <= 0:
            issues.append("PHASE35_BUDGET_LIMIT must be positive")

        if not 0 < self.alert_threshold <= 1:
            issues.append("PHASE35_ALERT_THRESHOLD must be between 0 and 1")

        return issues

    def is_valid(self) -> bool:
        """Check if configuration is valid for API calls."""
        return len(self.validate()) == 0

    def to_dict(self) -> dict:
        """Convert config to dictionary (excluding sensitive values)."""
        return {
            "azure_endpoint": self.azure_endpoint[:30] + "..." if self.azure_endpoint else None,
            "azure_api_version": self.azure_api_version,
            "gpt4o_mini_deployment": self.gpt4o_mini.deployment_name,
            "gpt4o_deployment": self.gpt4o.deployment_name,
            "embedding_deployment": self.embedding.deployment_name,
            "budget_limit": self.budget_limit,
            "alert_threshold": self.alert_threshold,
            "thresholds": {
                "intent_accuracy": self.thresholds.intent_accuracy,
                "response_quality": self.thresholds.response_quality,
                "escalation_precision": self.thresholds.escalation_precision,
                "escalation_recall": self.thresholds.escalation_recall,
                "critic_false_positive": self.thresholds.critic_false_positive,
                "critic_true_positive": self.thresholds.critic_true_positive,
                "rag_retrieval_at_3": self.thresholds.rag_retrieval_at_3,
                "max_monthly_cost": self.thresholds.max_monthly_cost,
            },
            "max_iterations": self.max_iterations,
        }

    def __str__(self) -> str:
        """String representation (safe for logging)."""
        return json.dumps(self.to_dict(), indent=2)


# Convenience function for quick setup
def get_config() -> Config:
    """Get configuration from environment."""
    return Config.from_env()


if __name__ == "__main__":
    # Test configuration loading
    config = Config.from_env()
    print("Configuration loaded:")
    print(config)

    issues = config.validate()
    if issues:
        print("\nValidation issues:")
        for issue in issues:
            print(f"  - {issue}")
    else:
        print("\nConfiguration is valid!")
