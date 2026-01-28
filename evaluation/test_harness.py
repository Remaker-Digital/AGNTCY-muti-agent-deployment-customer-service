"""
Main test harness for Phase 3.5 AI Model Optimization.

This module orchestrates evaluation tests against Azure OpenAI,
coordinates metrics collection, and generates reports.

Usage:
    from evaluation.test_harness import TestHarness

    harness = TestHarness.from_env()

    # Run all evaluations
    harness.run_all()

    # Or run individual evaluations
    harness.run_intent_evaluation()
    harness.run_response_evaluation()
    harness.run_escalation_evaluation()
    harness.run_critic_evaluation()
    harness.run_rag_evaluation()

    # Generate reports
    harness.generate_all_reports()
"""

import json
from pathlib import Path
from datetime import datetime
from typing import Optional

from evaluation.config import Config
from evaluation.azure_openai_client import AzureOpenAIClient
from evaluation.metrics_collector import MetricsCollector
from evaluation.report_generator import ReportGenerator


class TestHarness:
    """
    Main test harness for Phase 3.5 evaluation.

    Coordinates running evaluations, collecting metrics, and
    generating reports for all evaluation types.
    """

    def __init__(
        self,
        client: AzureOpenAIClient,
        config: Optional[Config] = None,
    ):
        """
        Initialize test harness.

        Args:
            client: Azure OpenAI client instance
            config: Optional configuration (uses client's config if not provided)
        """
        self.client = client
        self.config = config or client.config
        self.metrics = MetricsCollector()
        self.report_generator = ReportGenerator(self.config)

        # Track iterations
        self.current_iteration = 1
        self.max_iterations = self.config.max_iterations

        # Load datasets
        self._load_datasets()

    @classmethod
    def from_env(cls) -> "TestHarness":
        """Create test harness from environment configuration."""
        client = AzureOpenAIClient.from_env()
        return cls(client)

    def _load_datasets(self) -> None:
        """Load evaluation datasets from JSON files."""
        datasets_dir = self.config.datasets_dir

        self.intent_dataset = self._load_json(
            datasets_dir / "intent_classification.json"
        )
        self.response_dataset = self._load_json(datasets_dir / "response_quality.json")
        self.escalation_dataset = self._load_json(
            datasets_dir / "escalation_scenarios.json"
        )
        self.adversarial_dataset = self._load_json(
            datasets_dir / "adversarial_inputs.json"
        )
        self.knowledge_base = self._load_json(datasets_dir / "knowledge_base.json")
        self.rag_queries = self._load_json(datasets_dir / "rag_queries.json")
        self.robustness_dataset = self._load_json(
            datasets_dir / "robustness_inputs.json"
        )

    def _load_json(self, path: Path) -> dict:
        """Load JSON file, return empty dict if not found."""
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        return {}

    def _load_prompt(self, name: str) -> str:
        """Load prompt template from file."""
        prompt_path = self.config.prompts_dir / f"{name}.txt"
        if prompt_path.exists():
            with open(prompt_path, "r", encoding="utf-8") as f:
                return f.read()
        return ""

    # Intent Classification Evaluation
    def run_intent_evaluation(
        self,
        model: str = "gpt-4o-mini",
        prompt_version: str = "intent_classification_v1",
    ) -> dict:
        """
        Run intent classification evaluation.

        Args:
            model: Model to use (gpt-4o-mini or gpt-4o)
            prompt_version: Prompt version to use

        Returns:
            Dictionary with evaluation results and metrics.
        """
        print(f"\n{'='*50}")
        print(f"Running Intent Classification Evaluation")
        print(f"Model: {model}, Prompt: {prompt_version}")
        print(f"{'='*50}\n")

        # Load prompt
        system_prompt = self._load_prompt(prompt_version)
        if not system_prompt:
            return {"error": f"Prompt not found: {prompt_version}"}

        samples = self.intent_dataset.get("samples", [])
        if not samples:
            return {"error": "No intent samples found in dataset"}

        print(f"Processing {len(samples)} samples...")

        for i, sample in enumerate(samples):
            sample_id = sample.get("id", f"ic-{i+1:03d}")
            input_text = sample.get("input", "")
            expected_intent = sample.get("expected_intent", "")

            # Call API
            response = self.client.chat_completion(
                model=model,
                system_prompt=system_prompt,
                user_message=input_text,
                json_mode=True,
            )

            if response.error:
                print(f"  [{sample_id}] ERROR: {response.error}")
                predicted_intent = "ERROR"
                confidence = 0.0
            else:
                # Parse response
                try:
                    result = json.loads(response.content)
                    predicted_intent = result.get("intent", "UNKNOWN")
                    confidence = result.get("confidence", 0.0)
                except json.JSONDecodeError:
                    predicted_intent = response.content.strip().upper()
                    confidence = 0.5

            # Record result
            self.metrics.add_intent_result(
                sample_id=sample_id,
                expected=expected_intent,
                predicted=predicted_intent,
                confidence=confidence,
                latency_ms=response.latency_ms,
                cost=response.cost,
            )

            # Progress indicator (using ASCII for Windows compatibility)
            correct = "OK" if expected_intent == predicted_intent else "MISS"
            print(
                f"  [{sample_id}] {correct:4} Expected: {expected_intent}, Got: {predicted_intent}"
            )

        # Calculate and return metrics
        metrics = self.metrics.calculate_intent_metrics()
        print(f"\nIntent Accuracy: {metrics.get('accuracy_pct', 'N/A')}")
        print(f"Total Cost: ${metrics.get('total_cost', 0):.4f}")

        return {
            "evaluation_type": "intent_classification",
            "model": model,
            "prompt_version": prompt_version,
            "iteration": self.current_iteration,
            "metrics": metrics,
            "threshold": self.config.thresholds.intent_accuracy,
            "threshold_met": metrics.get("accuracy", 0)
            >= self.config.thresholds.intent_accuracy,
        }

    # Response Generation Evaluation
    def run_response_evaluation(
        self,
        model: str = "gpt-4o",
        prompt_version: str = "response_generation_v1",
    ) -> dict:
        """
        Run response generation evaluation.

        Note: This prepares responses for human evaluation.
        Quality scores must be added separately via add_human_evaluation().

        Args:
            model: Model to use (gpt-4o recommended)
            prompt_version: Prompt version to use

        Returns:
            Dictionary with generated responses for evaluation.
        """
        print(f"\n{'='*50}")
        print(f"Running Response Generation Evaluation")
        print(f"Model: {model}, Prompt: {prompt_version}")
        print(f"{'='*50}\n")

        system_prompt = self._load_prompt(prompt_version)
        if not system_prompt:
            return {"error": f"Prompt not found: {prompt_version}"}

        conversations = self.response_dataset.get("conversations", [])
        if not conversations:
            return {"error": "No response samples found in dataset"}

        print(f"Generating responses for {len(conversations)} scenarios...")

        responses = []
        for i, conv in enumerate(conversations):
            sample_id = conv.get("id", f"rq-{i+1:03d}")
            context = conv.get("context", {})
            customer_message = conv.get("customer_message", "")

            # Build context string
            context_str = "\n".join([f"{k}: {v}" for k, v in context.items()])
            full_message = (
                f"CONTEXT:\n{context_str}\n\nCUSTOMER MESSAGE:\n{customer_message}"
            )

            # Call API
            response = self.client.chat_completion(
                model=model,
                system_prompt=system_prompt,
                user_message=full_message,
            )

            if response.error:
                print(f"  [{sample_id}] ERROR: {response.error}")
                generated_response = f"ERROR: {response.error}"
            else:
                generated_response = response.content

            responses.append(
                {
                    "sample_id": sample_id,
                    "scenario": conv.get("scenario", ""),
                    "context": context,
                    "customer_message": customer_message,
                    "generated_response": generated_response,
                    "expected_elements": conv.get("expected_elements", []),
                    "latency_ms": response.latency_ms,
                    "cost": response.cost,
                }
            )

            print(
                f"  [{sample_id}] Generated ({response.latency_ms:.0f}ms, ${response.cost:.4f})"
            )

        # Save responses for human evaluation
        output_path = (
            self.config.results_dir / f"responses_for_evaluation_{prompt_version}.json"
        )
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(responses, f, indent=2)

        print(f"\nResponses saved to: {output_path}")
        print("Complete human evaluation using add_human_evaluation() method.")

        return {
            "evaluation_type": "response_generation",
            "model": model,
            "prompt_version": prompt_version,
            "iteration": self.current_iteration,
            "samples_generated": len(responses),
            "output_file": str(output_path),
            "next_step": "Complete human evaluation and call add_human_evaluation()",
        }

    def add_human_evaluation(
        self,
        sample_id: str,
        accuracy: float,
        completeness: float,
        tone: float,
        clarity: float,
        actionability: float,
        evaluator: str = "",
        notes: str = "",
    ) -> None:
        """
        Add human evaluation scores for a response.

        Args:
            sample_id: Response sample ID
            accuracy, completeness, tone, clarity, actionability: 1-5 ratings
            evaluator: Name/ID of human evaluator
            notes: Optional evaluation notes
        """
        # Find the response in saved data
        # For now, just record the metrics
        self.metrics.add_response_result(
            sample_id=sample_id,
            scenario="",
            response="",
            accuracy=accuracy,
            completeness=completeness,
            tone=tone,
            clarity=clarity,
            actionability=actionability,
            evaluator=evaluator,
            notes=notes,
        )

    def run_response_evaluation_with_judge(
        self,
        generation_model: str = "gpt-4o",
        judge_model: str = "gpt-4o",
        generation_prompt: str = "response_generation_v1",
        judge_prompt: str = "response_judge_v1",
    ) -> dict:
        """
        Run response generation with automated LLM-as-a-judge evaluation.

        This generates responses and then uses another LLM to evaluate them,
        providing automated quality scoring without human intervention.

        Args:
            generation_model: Model for generating responses
            judge_model: Model for judging response quality
            generation_prompt: Prompt for response generation
            judge_prompt: Prompt for quality evaluation

        Returns:
            Dictionary with evaluation results and metrics.
        """
        print(f"\n{'='*50}")
        print(f"Running Response Quality Evaluation (LLM-as-Judge)")
        print(f"Generator: {generation_model}, Judge: {judge_model}")
        print(f"{'='*50}\n")

        gen_system_prompt = self._load_prompt(generation_prompt)
        judge_system_prompt = self._load_prompt(judge_prompt)

        if not gen_system_prompt:
            return {"error": f"Generation prompt not found: {generation_prompt}"}
        if not judge_system_prompt:
            return {"error": f"Judge prompt not found: {judge_prompt}"}

        scenarios = self.response_dataset.get("scenarios", [])
        if not scenarios:
            return {"error": "No response scenarios found in dataset"}

        print(f"Processing {len(scenarios)} scenarios...")

        total_gen_cost = 0
        total_judge_cost = 0

        for i, scenario in enumerate(scenarios):
            sample_id = scenario.get("id", f"rq-{i+1:03d}")
            category = scenario.get("category", "unknown")
            customer_name = scenario.get("customer_name", "Customer")
            customer_message = scenario.get("customer_message", "")
            context = scenario.get("context", {})
            key_requirements = scenario.get("key_requirements", [])

            # Build context string
            context_str = "\n".join([f"- {k}: {v}" for k, v in context.items()])
            full_message = f"""CUSTOMER NAME: {customer_name}

CONTEXT INFORMATION:
{context_str}

CUSTOMER MESSAGE:
{customer_message}

KEY REQUIREMENTS TO ADDRESS:
{', '.join(key_requirements)}"""

            # Step 1: Generate response
            gen_response = self.client.chat_completion(
                model=generation_model,
                system_prompt=gen_system_prompt,
                user_message=full_message,
            )

            if gen_response.error:
                print(f"  [{sample_id}] GEN_ERROR: {gen_response.error}")
                continue

            generated_response = gen_response.content
            total_gen_cost += gen_response.cost

            # Step 2: Judge the response
            judge_message = f"""CUSTOMER MESSAGE:
{customer_message}

CONTEXT PROVIDED TO AGENT:
{context_str}

KEY REQUIREMENTS:
{', '.join(key_requirements)}

AI RESPONSE TO EVALUATE:
{generated_response}

Evaluate this response on all 5 dimensions."""

            judge_response = self.client.chat_completion(
                model=judge_model,
                system_prompt=judge_system_prompt,
                user_message=judge_message,
                json_mode=True,
            )

            if judge_response.error:
                print(f"  [{sample_id}] JUDGE_ERROR: {judge_response.error}")
                continue

            total_judge_cost += judge_response.cost

            # Parse judge scores
            try:
                scores = json.loads(judge_response.content)
                accuracy = float(scores.get("accuracy", 3))
                completeness = float(scores.get("completeness", 3))
                tone = float(scores.get("tone", 3))
                clarity = float(scores.get("clarity", 3))
                actionability = float(scores.get("actionability", 3))
            except (json.JSONDecodeError, ValueError):
                print(f"  [{sample_id}] PARSE_ERROR: Could not parse judge response")
                accuracy = completeness = tone = clarity = actionability = 3.0

            # Record result
            self.metrics.add_response_result(
                sample_id=sample_id,
                scenario=category,
                response=generated_response,
                accuracy=accuracy,
                completeness=completeness,
                tone=tone,
                clarity=clarity,
                actionability=actionability,
                latency_ms=gen_response.latency_ms + judge_response.latency_ms,
                cost=gen_response.cost + judge_response.cost,
                evaluator="LLM-as-Judge",
                notes=scores.get("reasoning", ""),
            )

            # Calculate quality score for display
            quality = (
                accuracy * 0.25
                + completeness * 0.20
                + tone * 0.20
                + clarity * 0.20
                + actionability * 0.15
            )
            quality_pct = (quality - 1) / 4 * 100

            status = (
                "OK" if quality_pct >= 80 else ("FAIR" if quality_pct >= 60 else "LOW")
            )
            print(
                f"  [{sample_id}] {status} [{category}] Quality: {quality_pct:.0f}% (A:{accuracy:.0f} C:{completeness:.0f} T:{tone:.0f} Cl:{clarity:.0f} Act:{actionability:.0f})"
            )

        # Calculate and return metrics
        metrics = self.metrics.calculate_response_metrics()
        print(f"\nAverage Quality Score: {metrics.get('average_quality_pct', 'N/A')}")
        print(f"Generation Cost: ${total_gen_cost:.4f}")
        print(f"Judge Cost: ${total_judge_cost:.4f}")

        # Target: >80% average quality
        threshold = 80.0
        quality_met = metrics.get("quality_score", 0) >= threshold

        return {
            "evaluation_type": "response_quality",
            "generation_model": generation_model,
            "judge_model": judge_model,
            "generation_prompt": generation_prompt,
            "judge_prompt": judge_prompt,
            "iteration": self.current_iteration,
            "metrics": metrics,
            "costs": {
                "generation": total_gen_cost,
                "judging": total_judge_cost,
                "total": total_gen_cost + total_judge_cost,
            },
            "threshold": threshold,
            "threshold_met": quality_met,
        }

    # Escalation Detection Evaluation
    def run_escalation_evaluation(
        self,
        model: str = "gpt-4o-mini",
        prompt_version: str = "escalation_detection_v1",
    ) -> dict:
        """
        Run escalation detection evaluation.

        Args:
            model: Model to use
            prompt_version: Prompt version to use

        Returns:
            Dictionary with evaluation results and metrics.
        """
        print(f"\n{'='*50}")
        print(f"Running Escalation Detection Evaluation")
        print(f"Model: {model}, Prompt: {prompt_version}")
        print(f"{'='*50}\n")

        system_prompt = self._load_prompt(prompt_version)
        if not system_prompt:
            return {"error": f"Prompt not found: {prompt_version}"}

        scenarios = self.escalation_dataset.get("scenarios", [])
        if not scenarios:
            return {"error": "No escalation scenarios found in dataset"}

        print(f"Processing {len(scenarios)} scenarios...")

        for i, scenario in enumerate(scenarios):
            sample_id = scenario.get("id", f"esc-{i+1:03d}")
            category = scenario.get("category", "unknown")
            expected_escalate = scenario.get("expected_escalate", False)

            # Build conversation context from conversation array
            conv_messages = scenario.get("conversation", [])
            conversation_parts = []
            for msg in conv_messages:
                role = msg.get("role", "customer").title()
                content = msg.get("content", "")
                conversation_parts.append(f"{role}: {content}")
            conversation = "\n".join(conversation_parts)

            # Call API
            response = self.client.chat_completion(
                model=model,
                system_prompt=system_prompt,
                user_message=conversation,
                json_mode=True,
            )

            if response.error:
                # Azure content filter triggers should be treated as needing escalation
                # (content too sensitive for AI to handle)
                if "content_filter" in response.error:
                    print(
                        f"  [{sample_id}] AZURE_FILTER [{category}] Content filter triggered - treating as escalate"
                    )
                    predicted_escalate = True
                    confidence = 1.0
                else:
                    print(f"  [{sample_id}] ERROR: {response.error}")
                    predicted_escalate = False
                    confidence = 0.0
            else:
                try:
                    result = json.loads(response.content)
                    predicted_escalate = result.get("escalate", False)
                    confidence = result.get("confidence", 0.0)
                except json.JSONDecodeError:
                    predicted_escalate = "escalate" in response.content.lower()
                    confidence = 0.5

            # Record result
            self.metrics.add_escalation_result(
                sample_id=sample_id,
                expected_escalate=expected_escalate,
                predicted_escalate=predicted_escalate,
                confidence=confidence,
                latency_ms=response.latency_ms,
                cost=response.cost,
            )

            correct = "OK" if expected_escalate == predicted_escalate else "MISS"
            print(
                f"  [{sample_id}] {correct} [{category}] Expected: {expected_escalate}, Got: {predicted_escalate}"
            )

        # Calculate and return metrics
        metrics = self.metrics.calculate_escalation_metrics()
        print(f"\nPrecision: {metrics.get('precision_pct', 'N/A')}")
        print(f"Recall: {metrics.get('recall_pct', 'N/A')}")
        print(f"False Positive Rate: {metrics.get('false_positive_rate_pct', 'N/A')}")

        thresholds = self.config.thresholds
        precision_met = metrics.get("precision", 0) >= thresholds.escalation_precision
        recall_met = metrics.get("recall", 0) >= thresholds.escalation_recall

        return {
            "evaluation_type": "escalation_detection",
            "model": model,
            "prompt_version": prompt_version,
            "iteration": self.current_iteration,
            "metrics": metrics,
            "thresholds": {
                "precision": thresholds.escalation_precision,
                "recall": thresholds.escalation_recall,
            },
            "threshold_met": precision_met and recall_met,
        }

    # Critic/Supervisor Evaluation
    def run_critic_evaluation(
        self,
        model: str = "gpt-4o-mini",
        input_prompt_version: str = "critic_input_validation",
        output_prompt_version: str = "critic_output_validation",
    ) -> dict:
        """
        Run critic/supervisor validation evaluation.

        Args:
            model: Model to use
            input_prompt_version: Prompt for input validation
            output_prompt_version: Prompt for output validation

        Returns:
            Dictionary with evaluation results and metrics.
        """
        print(f"\n{'='*50}")
        print(f"Running Critic/Supervisor Evaluation")
        print(f"Model: {model}")
        print(f"{'='*50}\n")

        system_prompt = self._load_prompt(input_prompt_version)
        if not system_prompt:
            return {"error": f"Prompt not found: {input_prompt_version}"}

        adversarial = self.adversarial_dataset.get("adversarial", [])
        if not adversarial:
            return {"error": "No adversarial samples found in dataset"}

        print(f"Processing {len(adversarial)} samples...")

        for i, sample in enumerate(adversarial):
            sample_id = sample.get("id", f"adv-{i+1:03d}")
            input_type = sample.get("type", "unknown")
            input_text = sample.get("input", "")
            expected_action = sample.get("expected_action", "ALLOW")

            # Call API
            response = self.client.chat_completion(
                model=model,
                system_prompt=system_prompt,
                user_message=input_text,
                json_mode=True,
            )

            if response.error:
                # Check if Azure content filter blocked the input
                # This counts as a successful BLOCK (defense in depth)
                if "content_filter" in response.error or "jailbreak" in response.error:
                    predicted_action = "BLOCK"
                    print(
                        f"  [{sample_id}] AZURE_FILTER [{input_type}] Blocked by Azure content filter"
                    )
                else:
                    print(f"  [{sample_id}] ERROR: {response.error}")
                    predicted_action = "ERROR"
            else:
                try:
                    result = json.loads(response.content)
                    predicted_action = result.get("action", "ALLOW").upper()
                except json.JSONDecodeError:
                    if "block" in response.content.lower():
                        predicted_action = "BLOCK"
                    else:
                        predicted_action = "ALLOW"

            # Record result
            self.metrics.add_critic_result(
                sample_id=sample_id,
                input_type=input_type,
                expected_action=expected_action,
                predicted_action=predicted_action,
                latency_ms=response.latency_ms,
                cost=response.cost,
            )

            correct = "OK" if expected_action == predicted_action else "MISS"
            print(
                f"  [{sample_id}] {correct} [{input_type}] Expected: {expected_action}, Got: {predicted_action}"
            )

        # Calculate and return metrics
        metrics = self.metrics.calculate_critic_metrics()
        print(f"\nFalse Positive Rate: {metrics.get('false_positive_rate_pct', 'N/A')}")
        print(f"True Positive Rate: {metrics.get('true_positive_rate_pct', 'N/A')}")

        thresholds = self.config.thresholds
        fp_met = (
            metrics.get("false_positive_rate", 1) <= thresholds.critic_false_positive
        )
        tp_met = metrics.get("true_positive_rate", 0) >= thresholds.critic_true_positive

        return {
            "evaluation_type": "critic_supervisor",
            "model": model,
            "input_prompt_version": input_prompt_version,
            "iteration": self.current_iteration,
            "metrics": metrics,
            "thresholds": {
                "false_positive": thresholds.critic_false_positive,
                "true_positive": thresholds.critic_true_positive,
            },
            "threshold_met": fp_met and tp_met,
        }

    # RAG Retrieval Evaluation
    def run_rag_evaluation(
        self,
        model: str = "gpt-4o-mini",
        top_k: int = 5,
    ) -> dict:
        """
        Run RAG retrieval evaluation using embedding similarity.

        This simulates RAG retrieval by using the model to rank document
        relevance to queries. In production, this would use vector embeddings.

        Args:
            model: Model to use for relevance scoring
            top_k: Number of top documents to retrieve

        Returns:
            Dictionary with retrieval@1, @3, @5 metrics.
        """
        print(f"\n{'='*50}")
        print(f"Running RAG Retrieval Evaluation")
        print(f"Model: {model}, Top-K: {top_k}")
        print(f"{'='*50}\n")

        documents = self.knowledge_base.get("documents", [])
        queries = self.rag_queries.get("queries", [])

        if not documents:
            return {"error": "No documents in knowledge base"}
        if not queries:
            return {"error": "No RAG queries found"}

        # Build document index (id -> content)
        doc_index = {doc["id"]: doc for doc in documents}

        # Create document summaries for ranking
        doc_summaries = "\n".join(
            [f"- {doc['id']}: {doc['title']}" for doc in documents]
        )

        system_prompt = f"""You are a document retrieval system for customer service.

Given a customer query, rank the most relevant documents from our knowledge base.

AVAILABLE DOCUMENTS:
{doc_summaries}

TASK:
For the given query, return the top {top_k} most relevant document IDs, ranked by relevance.

OUTPUT FORMAT:
Return ONLY a JSON object with a "ranked_docs" array of document IDs:
{{"ranked_docs": ["doc-XXX", "doc-YYY", "doc-ZZZ", ...]}}

Return exactly {top_k} document IDs, ordered from most to least relevant.
Do not include any other text."""

        print(
            f"Processing {len(queries)} queries against {len(documents)} documents..."
        )

        for i, query_item in enumerate(queries):
            query_id = query_item.get("id", f"rag-{i+1:03d}")
            query = query_item.get("query", "")
            expected_docs = query_item.get("expected_docs", [])
            category = query_item.get("category", "unknown")

            # Call API
            response = self.client.chat_completion(
                model=model,
                system_prompt=system_prompt,
                user_message=f"Query: {query}",
                json_mode=True,
            )

            if response.error:
                print(f"  [{query_id}] ERROR: {response.error}")
                retrieved_docs = []
            else:
                try:
                    result = json.loads(response.content)
                    retrieved_docs = result.get("ranked_docs", [])[:top_k]
                except json.JSONDecodeError:
                    retrieved_docs = []

            # Record result (metrics collector calculates relevance internally)
            self.metrics.add_retrieval_result(
                sample_id=query_id,
                query=query,
                expected_docs=expected_docs,
                retrieved_docs=retrieved_docs,
                latency_ms=response.latency_ms,
                cost=response.cost,
            )

            # Check for display
            relevant_in_top_1 = any(doc in retrieved_docs[:1] for doc in expected_docs)
            relevant_in_top_3 = any(doc in retrieved_docs[:3] for doc in expected_docs)
            relevant_in_top_5 = any(doc in retrieved_docs[:5] for doc in expected_docs)
            hit_at = (
                "1"
                if relevant_in_top_1
                else ("3" if relevant_in_top_3 else ("5" if relevant_in_top_5 else "-"))
            )
            status = "OK" if relevant_in_top_5 else "MISS"
            print(
                f"  [{query_id}] {status} [{category}] Hit@{hit_at} Expected: {expected_docs[0]}, Got: {retrieved_docs[:3]}"
            )

        # Calculate and return metrics
        metrics = self.metrics.calculate_retrieval_metrics()
        print(f"\nRetrieval@1: {metrics.get('retrieval_at_1_pct', 'N/A')}")
        print(f"Retrieval@3: {metrics.get('retrieval_at_3_pct', 'N/A')}")
        print(f"Retrieval@5: {metrics.get('retrieval_at_5_pct', 'N/A')}")

        # Target: >90% retrieval accuracy
        threshold = 0.90
        retrieval_met = metrics.get("retrieval_at_5", 0) >= threshold

        return {
            "evaluation_type": "rag_retrieval",
            "model": model,
            "top_k": top_k,
            "iteration": self.current_iteration,
            "metrics": metrics,
            "threshold": threshold,
            "threshold_met": retrieval_met,
        }

    # Robustness Evaluation
    def run_robustness_evaluation(
        self,
        generation_model: str = "gpt-4o-mini",
        judge_model: str = "gpt-4o-mini",
        response_prompt_version: str = "response_generation_v1",
    ) -> dict:
        """
        Run robustness evaluation testing comprehension and appropriateness
        on edge case inputs (misspellings, slang, jargon, formal language).

        Args:
            generation_model: Model for generating responses
            judge_model: Model for judging comprehension and appropriateness
            response_prompt_version: Which response generation prompt to use

        Returns:
            Dictionary with robustness metrics by dimension and severity.
        """
        print(f"\n{'='*60}")
        print(f"Running Robustness Evaluation Suite")
        print(f"Generator: {generation_model}, Judge: {judge_model}")
        print(f"Response Prompt: {response_prompt_version}")
        print(f"{'='*60}\n")

        # Load prompts
        response_prompt = self._load_prompt(response_prompt_version)
        comprehension_judge = self._load_prompt("robustness_comprehension_judge")
        appropriateness_judge = self._load_prompt("robustness_appropriateness_judge")

        if not all([response_prompt, comprehension_judge, appropriateness_judge]):
            return {"error": "Missing required prompts"}

        samples = self.robustness_dataset.get("samples", [])
        if not samples:
            return {"error": "No robustness samples found"}

        print(f"Processing {len(samples)} robustness samples...")

        results = []
        dimension_stats = {}
        severity_stats = {}

        for sample in samples:
            sample_id = sample.get("id", "unknown")
            dimension = sample.get("dimension", "unknown")
            severity = sample.get("severity", "unknown")
            customer_input = sample.get("input", "")
            intended_meaning = sample.get("intended_meaning", "")
            context = sample.get("context", {})

            # Initialize stats tracking
            if dimension not in dimension_stats:
                dimension_stats[dimension] = {
                    "total": 0,
                    "comprehension_sum": 0,
                    "appropriateness_sum": 0,
                }
            if severity not in severity_stats:
                severity_stats[severity] = {
                    "total": 0,
                    "comprehension_sum": 0,
                    "appropriateness_sum": 0,
                }

            # Step 1: Generate response to the difficult input
            context_str = (
                "\n".join([f"- {k}: {v}" for k, v in context.items()])
                if context
                else "No additional context"
            )
            gen_message = f"""CONTEXT:
{context_str}

CUSTOMER MESSAGE:
{customer_input}"""

            gen_response = self.client.chat_completion(
                model=generation_model,
                system_prompt=response_prompt,
                user_message=gen_message,
            )

            if gen_response.error:
                print(f"  [{sample_id}] GEN_ERROR: {gen_response.error}")
                continue

            generated_response = gen_response.content

            # Step 2: Judge comprehension
            comp_message = f"""ORIGINAL CUSTOMER MESSAGE (may be garbled/unusual):
{customer_input}

WHAT CUSTOMER ACTUALLY MEANT:
{intended_meaning}

AGENT'S RESPONSE:
{generated_response}

Evaluate if the agent correctly understood what the customer meant."""

            comp_response = self.client.chat_completion(
                model=judge_model,
                system_prompt=comprehension_judge,
                user_message=comp_message,
                json_mode=True,
            )

            # Step 3: Judge appropriateness
            approp_message = f"""CUSTOMER'S MESSAGE STYLE:
{customer_input}

CUSTOMER'S DIMENSION: {dimension} (severity: {severity})

AGENT'S RESPONSE:
{generated_response}

Evaluate if the agent's response style was appropriate for this customer."""

            approp_response = self.client.chat_completion(
                model=judge_model,
                system_prompt=appropriateness_judge,
                user_message=approp_message,
                json_mode=True,
            )

            # Parse results
            try:
                comp_scores = json.loads(comp_response.content)
                comprehension = float(comp_scores.get("comprehension", 3))
                intent_match = comp_scores.get("intent_match", False)
                asked_clarification = comp_scores.get("asked_clarification", False)
                recovery_quality = comp_scores.get("recovery_quality")
            except (json.JSONDecodeError, ValueError):
                comprehension = 3.0
                intent_match = False
                asked_clarification = False
                recovery_quality = None

            try:
                approp_scores = json.loads(approp_response.content)
                appropriateness = float(approp_scores.get("appropriateness_score", 3))
                tone_match = float(approp_scores.get("tone_match", 3))
                register_appropriate = float(
                    approp_scores.get("register_appropriate", 3)
                )
                empathy_appropriate = float(approp_scores.get("empathy_appropriate", 3))
                professionalism = approp_scores.get("professionalism_maintained", True)
            except (json.JSONDecodeError, ValueError):
                appropriateness = 3.0
                tone_match = 3.0
                register_appropriate = 3.0
                empathy_appropriate = 3.0
                professionalism = True

            # Update stats
            dimension_stats[dimension]["total"] += 1
            dimension_stats[dimension]["comprehension_sum"] += comprehension
            dimension_stats[dimension]["appropriateness_sum"] += appropriateness

            severity_stats[severity]["total"] += 1
            severity_stats[severity]["comprehension_sum"] += comprehension
            severity_stats[severity]["appropriateness_sum"] += appropriateness

            # Determine status
            combined = (comprehension + appropriateness) / 2
            if combined >= 4.0:
                status = "OK"
            elif combined >= 3.0:
                status = "FAIR"
            elif combined >= 2.0:
                status = "WEAK"
            else:
                status = "FAIL"

            # Record result
            result = {
                "sample_id": sample_id,
                "dimension": dimension,
                "severity": severity,
                "comprehension": comprehension,
                "appropriateness": appropriateness,
                "intent_match": intent_match,
                "asked_clarification": asked_clarification,
                "recovery_quality": recovery_quality,
                "tone_match": tone_match,
                "register_appropriate": register_appropriate,
                "empathy_appropriate": empathy_appropriate,
                "professionalism": professionalism,
                "generated_response": (
                    generated_response[:200] + "..."
                    if len(generated_response) > 200
                    else generated_response
                ),
                "cost": gen_response.cost + comp_response.cost + approp_response.cost,
            }
            results.append(result)

            clarify_flag = " [CLARIFIED]" if asked_clarification else ""
            print(
                f"  [{sample_id}] {status} [{dimension}/{severity}] Comp:{comprehension:.0f} Appr:{appropriateness:.0f}{clarify_flag}"
            )

        # Calculate summary statistics
        total_samples = len(results)
        avg_comprehension = (
            sum(r["comprehension"] for r in results) / total_samples if results else 0
        )
        avg_appropriateness = (
            sum(r["appropriateness"] for r in results) / total_samples if results else 0
        )
        intent_match_rate = (
            sum(1 for r in results if r["intent_match"]) / total_samples
            if results
            else 0
        )
        clarification_rate = (
            sum(1 for r in results if r["asked_clarification"]) / total_samples
            if results
            else 0
        )

        # Calculate per-dimension averages
        dimension_avgs = {}
        for dim, stats in dimension_stats.items():
            if stats["total"] > 0:
                dimension_avgs[dim] = {
                    "comprehension": round(
                        stats["comprehension_sum"] / stats["total"], 2
                    ),
                    "appropriateness": round(
                        stats["appropriateness_sum"] / stats["total"], 2
                    ),
                    "samples": stats["total"],
                }

        # Calculate per-severity averages
        severity_avgs = {}
        for sev, stats in severity_stats.items():
            if stats["total"] > 0:
                severity_avgs[sev] = {
                    "comprehension": round(
                        stats["comprehension_sum"] / stats["total"], 2
                    ),
                    "appropriateness": round(
                        stats["appropriateness_sum"] / stats["total"], 2
                    ),
                    "samples": stats["total"],
                }

        # Find failure cases (comprehension or appropriateness < 3)
        failures = [
            r for r in results if r["comprehension"] < 3 or r["appropriateness"] < 3
        ]

        print(f"\n{'='*60}")
        print(f"ROBUSTNESS EVALUATION SUMMARY")
        print(f"{'='*60}")
        print(f"Total Samples: {total_samples}")
        print(f"Avg Comprehension: {avg_comprehension:.2f}/5")
        print(f"Avg Appropriateness: {avg_appropriateness:.2f}/5")
        print(f"Intent Match Rate: {intent_match_rate*100:.1f}%")
        print(f"Clarification Rate: {clarification_rate*100:.1f}%")
        print(f"Failure Cases: {len(failures)}")

        print(f"\nBy Dimension:")
        for dim, avgs in dimension_avgs.items():
            print(
                f"  {dim}: Comp={avgs['comprehension']:.2f}, Appr={avgs['appropriateness']:.2f} (n={avgs['samples']})"
            )

        print(f"\nBy Severity:")
        for sev, avgs in sorted(
            severity_avgs.items(), key=lambda x: x[1]["comprehension"], reverse=True
        ):
            print(
                f"  {sev}: Comp={avgs['comprehension']:.2f}, Appr={avgs['appropriateness']:.2f} (n={avgs['samples']})"
            )

        total_cost = sum(r["cost"] for r in results)

        return {
            "evaluation_type": "robustness",
            "generation_model": generation_model,
            "judge_model": judge_model,
            "total_samples": total_samples,
            "metrics": {
                "avg_comprehension": round(avg_comprehension, 2),
                "avg_appropriateness": round(avg_appropriateness, 2),
                "intent_match_rate": round(intent_match_rate, 4),
                "clarification_rate": round(clarification_rate, 4),
                "failure_count": len(failures),
            },
            "by_dimension": dimension_avgs,
            "by_severity": severity_avgs,
            "failures": failures,
            "all_results": results,
            "total_cost": round(total_cost, 4),
        }

    # Run All Evaluations
    def run_all(
        self,
        models: Optional[dict] = None,
    ) -> dict:
        """
        Run all evaluation types.

        Args:
            models: Optional dict mapping evaluation type to model name

        Returns:
            Dictionary with all evaluation results.
        """
        if models is None:
            models = {
                "intent": "gpt-4o-mini",
                "response": "gpt-4o",
                "escalation": "gpt-4o-mini",
                "critic": "gpt-4o-mini",
            }

        print(f"\n{'#'*60}")
        print(f"# Phase 3.5 Full Evaluation Suite")
        print(f"# Iteration: {self.current_iteration}")
        print(f"# Started: {datetime.now().isoformat()}")
        print(f"{'#'*60}")

        results = {
            "iteration": self.current_iteration,
            "started_at": datetime.now().isoformat(),
        }

        # Run each evaluation
        results["intent"] = self.run_intent_evaluation(model=models["intent"])
        results["escalation"] = self.run_escalation_evaluation(
            model=models["escalation"]
        )
        results["critic"] = self.run_critic_evaluation(model=models["critic"])
        results["response"] = self.run_response_evaluation(model=models["response"])

        # Check overall thresholds
        results["completed_at"] = datetime.now().isoformat()
        results["usage"] = self.client.get_usage_stats()
        results["all_thresholds_met"] = all(
            [
                results.get("intent", {}).get("threshold_met", False),
                results.get("escalation", {}).get("threshold_met", False),
                results.get("critic", {}).get("threshold_met", False),
                # Response requires human evaluation
            ]
        )

        # Save results
        output_path = (
            self.config.results_dir
            / f"full_evaluation_iter{self.current_iteration}.json"
        )
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2, default=str)

        print(f"\n{'#'*60}")
        print(f"# Evaluation Complete")
        print(f"# Results saved to: {output_path}")
        print(f"# Total cost: ${results['usage']['total_cost']:.4f}")
        print(f"{'#'*60}")

        return results

    # Report Generation
    def generate_all_reports(self) -> None:
        """Generate all evaluation reports."""
        self.report_generator.generate_intent_report(
            self.metrics.calculate_intent_metrics(),
            self.current_iteration,
        )
        self.report_generator.generate_escalation_report(
            self.metrics.calculate_escalation_metrics(),
            self.current_iteration,
        )
        self.report_generator.generate_critic_report(
            self.metrics.calculate_critic_metrics(),
            self.current_iteration,
        )
        if self.metrics.response_results:
            self.report_generator.generate_response_report(
                self.metrics.calculate_response_metrics(),
                self.current_iteration,
            )

    def next_iteration(self) -> None:
        """Move to next iteration (resets metrics)."""
        if self.current_iteration >= self.max_iterations:
            print(f"WARNING: Max iterations ({self.max_iterations}) reached")
        self.current_iteration += 1
        self.metrics.reset()


if __name__ == "__main__":
    print("Phase 3.5 Test Harness")
    print("-" * 40)

    try:
        harness = TestHarness.from_env()
        success, msg = harness.client.test_connection()
        print(f"Connection: {msg}")

        if success:
            print("\nTest harness ready. Run evaluations with:")
            print("  harness.run_intent_evaluation()")
            print("  harness.run_all()")
    except Exception as e:
        print(f"Error: {e}")
