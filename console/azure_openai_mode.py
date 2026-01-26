#!/usr/bin/env python3
"""
Azure OpenAI Integration Mode for AGNTCY Development Console
=============================================================

Provides real AI-powered responses using Azure OpenAI Service with
the Phase 3.5 optimized prompts.

This module:
- Connects to Azure OpenAI Service using Phase 3.5 evaluation framework
- Runs the full agent pipeline (Critic -> Intent -> Response)
- Tracks costs and latencies for each request
- Integrates with the existing console UI

Author: AGNTCY Multi-Agent Platform
Version: 1.0.0
"""

import json
import sys
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass

# Add project root to path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Try to import the Phase 3.5 evaluation framework
try:
    from evaluation.azure_openai_client import AzureOpenAIClient, ChatResponse
    from evaluation.config import Config
    AZURE_OPENAI_AVAILABLE = True
except ImportError as e:
    AZURE_OPENAI_AVAILABLE = False
    print(f"Azure OpenAI not available: {e}")


@dataclass
class PipelineStep:
    """Represents a single step in the agent pipeline."""
    agent_name: str
    action: str
    input_summary: str
    output_summary: str
    latency_ms: float
    cost_usd: float
    success: bool
    details: Dict[str, Any]


@dataclass
class PipelineResult:
    """Result of running the full agent pipeline."""
    success: bool
    response: str
    intent: str
    intent_confidence: float
    blocked: bool
    block_reason: Optional[str]
    escalation_needed: bool
    escalation_reason: Optional[str]
    total_cost_usd: float
    total_latency_ms: float
    pipeline_steps: List[PipelineStep]
    trace_id: str
    session_id: str
    message_id: str


class AzureOpenAIMode:
    """
    Azure OpenAI integration for the AGNTCY Development Console.

    This class provides real AI-powered responses using the Phase 3.5
    optimized prompts and Azure OpenAI Service.
    """

    # Mock context data for testing (same as in console_chat.py)
    MOCK_CONTEXTS = {
        "order": {
            "customer_name": "Alex Johnson",
            "customer_email": "alex.johnson@email.com",
            "order_id": "ORD-2026-78432",
            "order_date": "2026-01-22",
            "order_status": "shipped",
            "tracking_number": "1Z999AA10123456784",
            "carrier": "UPS",
            "estimated_delivery": "2026-01-27",
            "items": [
                {"name": "Wireless Bluetooth Headphones", "sku": "WBH-100", "qty": 1, "price": 79.99},
                {"name": "USB-C Charging Cable", "sku": "USB-C-3FT", "qty": 2, "price": 12.99}
            ],
            "subtotal": 105.97,
            "shipping": 5.99,
            "tax": 8.48,
            "total": 120.44,
            "payment_method": "Visa ending in 4242",
            "shipping_address": "123 Main St, Apt 4B, New York, NY 10001"
        },
        "return": {
            "customer_name": "Maria Garcia",
            "customer_email": "maria.garcia@email.com",
            "order_id": "ORD-2026-65891",
            "order_date": "2026-01-15",
            "order_status": "delivered",
            "delivery_date": "2026-01-18",
            "items": [
                {"name": "Winter Jacket - Blue, Size M", "sku": "WJ-BLU-M", "qty": 1, "price": 149.99}
            ],
            "return_policy": "30-day return window. Item must be unworn with tags attached. Free return shipping label provided.",
            "return_window_ends": "2026-02-17",
            "refund_method": "Original payment method (3-5 business days after receipt)"
        },
        "product": {
            "customer_name": "Customer",
            "product_catalog": [
                {"name": "Wireless Bluetooth Headphones", "sku": "WBH-100", "price": 79.99, "in_stock": True},
                {"name": "Premium Noise-Canceling Headphones", "sku": "PNC-200", "price": 199.99, "in_stock": True},
                {"name": "Smart Watch Pro", "sku": "SWP-300", "price": 299.99, "in_stock": False, "restock_date": "2026-02-01"},
            ],
            "shipping_info": "Free shipping on orders over $50. Standard: 5-7 business days. Express: 2-3 days (+$15.99).",
        },
        "billing": {
            "customer_name": "David Chen",
            "customer_email": "david.chen@email.com",
            "subscription": "Premium Plan - $19.99/month",
            "next_billing_date": "2026-02-01",
            "payment_method": "Mastercard ending in 5555",
        },
        "empty": {
            "customer_name": "Customer",
            "note": "No specific order or account context available."
        }
    }

    def __init__(self):
        """Initialize the Azure OpenAI mode."""
        self.client: Optional[AzureOpenAIClient] = None
        self.prompts: Dict[str, str] = {}
        self.context = self.MOCK_CONTEXTS["order"]
        self.context_type = "order"
        self.conversation_history: List[Dict[str, str]] = []
        self.is_initialized = False
        self.initialization_error: Optional[str] = None

    def initialize(self) -> tuple[bool, str]:
        """
        Initialize the Azure OpenAI client and load prompts.

        Returns:
            (success, message)
        """
        if not AZURE_OPENAI_AVAILABLE:
            self.initialization_error = "Azure OpenAI client not available. Check evaluation module imports."
            return False, self.initialization_error

        try:
            # Initialize Azure OpenAI client
            self.client = AzureOpenAIClient.from_env()

            # Test connection
            success, message = self.client.test_connection()
            if not success:
                self.initialization_error = f"Connection failed: {message}"
                return False, self.initialization_error

            # Load Phase 3.5 optimized prompts
            self._load_prompts()

            self.is_initialized = True
            return True, f"Azure OpenAI connected. {message}"

        except Exception as e:
            self.initialization_error = str(e)
            return False, f"Initialization failed: {e}"

    def _load_prompts(self):
        """Load the Phase 3.5 optimized prompts."""
        prompts_dir = project_root / "evaluation" / "prompts"

        prompt_files = {
            "critic": "critic_input_validation_final.txt",
            "intent": "intent_classification_final.txt",
            "response": "response_generation_final.txt",
            "escalation": "escalation_detection_final.txt",
        }

        for name, filename in prompt_files.items():
            filepath = prompts_dir / filename
            if filepath.exists():
                self.prompts[name] = filepath.read_text(encoding="utf-8")
            else:
                # Fallback to v2 or v1 if final not available
                for fallback in [filename.replace("_final", "_v2"), filename.replace("_final", "_v1"), filename.replace("_final", "")]:
                    fallback_path = prompts_dir / fallback
                    if fallback_path.exists():
                        self.prompts[name] = fallback_path.read_text(encoding="utf-8")
                        break

    def set_context(self, context_type: str) -> bool:
        """Set the mock context data."""
        if context_type in self.MOCK_CONTEXTS:
            self.context = self.MOCK_CONTEXTS[context_type]
            self.context_type = context_type
            return True
        return False

    def clear_history(self):
        """Clear conversation history."""
        self.conversation_history = []

    def get_usage_stats(self) -> Dict[str, Any]:
        """Get usage statistics from the client."""
        if self.client:
            return self.client.get_usage_stats()
        return {}

    def check_budget(self) -> tuple[bool, str]:
        """Check if within budget."""
        if self.client:
            return self.client.check_budget()
        return True, "Client not initialized"

    async def process_message(self, message: str, session_id: str) -> PipelineResult:
        """
        Process a customer message through the full AI agent pipeline.

        Pipeline:
        1. Critic/Supervisor - Validate input
        2. Intent Classification - Determine intent
        3. Escalation Detection - Check if human needed
        4. Response Generation - Generate response

        Args:
            message: Customer message
            session_id: Session identifier

        Returns:
            PipelineResult with full details
        """
        import asyncio

        trace_id = str(uuid.uuid4())
        message_id = f"msg-{uuid.uuid4().hex[:12]}"
        pipeline_steps: List[PipelineStep] = []
        total_cost = 0.0
        total_latency = 0.0

        # Default result for failures
        result = PipelineResult(
            success=False,
            response="",
            intent="unknown",
            intent_confidence=0.0,
            blocked=False,
            block_reason=None,
            escalation_needed=False,
            escalation_reason=None,
            total_cost_usd=0.0,
            total_latency_ms=0.0,
            pipeline_steps=[],
            trace_id=trace_id,
            session_id=session_id,
            message_id=message_id
        )

        if not self.is_initialized:
            result.response = "Azure OpenAI not initialized. Please check configuration."
            return result

        try:
            # Step 1: Critic/Supervisor validation
            critic_result = self._run_critic(message)
            pipeline_steps.append(critic_result["step"])
            total_cost += critic_result["step"].cost_usd
            total_latency += critic_result["step"].latency_ms

            if not critic_result["allowed"]:
                result.blocked = True
                result.block_reason = critic_result["reason"]
                result.response = f"I'm sorry, but I can't process that request. {critic_result['reason']}"
                result.pipeline_steps = pipeline_steps
                result.total_cost_usd = total_cost
                result.total_latency_ms = total_latency
                result.success = True  # Pipeline ran successfully, just blocked
                return result

            # Step 2: Intent Classification
            intent_result = self._run_intent_classification(message)
            pipeline_steps.append(intent_result["step"])
            total_cost += intent_result["step"].cost_usd
            total_latency += intent_result["step"].latency_ms

            # Step 3: Escalation Detection
            escalation_result = self._run_escalation_detection(message)
            pipeline_steps.append(escalation_result["step"])
            total_cost += escalation_result["step"].cost_usd
            total_latency += escalation_result["step"].latency_ms

            # Step 4: Response Generation
            response_result = self._run_response_generation(
                message,
                intent_result["intent"],
                escalation_result["should_escalate"]
            )
            pipeline_steps.append(response_result["step"])
            total_cost += response_result["step"].cost_usd
            total_latency += response_result["step"].latency_ms

            # Update conversation history
            self.conversation_history.append({"role": "user", "content": message})
            self.conversation_history.append({"role": "assistant", "content": response_result["response"]})

            # Build final result
            result.success = True
            result.response = response_result["response"]
            result.intent = intent_result["intent"]
            result.intent_confidence = intent_result["confidence"]
            result.escalation_needed = escalation_result["should_escalate"]
            result.escalation_reason = escalation_result["reason"] if escalation_result["should_escalate"] else None
            result.pipeline_steps = pipeline_steps
            result.total_cost_usd = total_cost
            result.total_latency_ms = total_latency

            return result

        except Exception as e:
            result.response = f"Error processing message: {str(e)}"
            result.pipeline_steps = pipeline_steps
            result.total_cost_usd = total_cost
            result.total_latency_ms = total_latency
            return result

    def _run_critic(self, message: str) -> Dict[str, Any]:
        """Run the Critic/Supervisor validation."""
        start_time = time.perf_counter()

        response = self.client.chat_completion(
            model="gpt-4o-mini",
            system_prompt=self.prompts.get("critic", ""),
            user_message=message,
            json_mode=True,
            temperature=0.0,
        )

        latency_ms = (time.perf_counter() - start_time) * 1000

        # Parse result
        allowed = True
        reason = ""
        try:
            if response.content:
                result = json.loads(response.content)
                allowed = result.get("action", "BLOCK").upper() == "ALLOW"
                reason = result.get("reason", "")
        except json.JSONDecodeError:
            pass

        # Handle Azure content filter
        if response.error and "content_filter" in response.error.lower():
            allowed = False
            reason = "Content blocked by Azure safety filter"

        step = PipelineStep(
            agent_name="Critic/Supervisor",
            action="validate_input",
            input_summary=message[:50] + "..." if len(message) > 50 else message,
            output_summary="ALLOW" if allowed else f"BLOCK: {reason}",
            latency_ms=latency_ms,
            cost_usd=response.cost,
            success=response.error is None,
            details={"allowed": allowed, "reason": reason}
        )

        return {"allowed": allowed, "reason": reason, "step": step}

    def _run_intent_classification(self, message: str) -> Dict[str, Any]:
        """Run the Intent Classification agent."""
        start_time = time.perf_counter()

        response = self.client.chat_completion(
            model="gpt-4o-mini",
            system_prompt=self.prompts.get("intent", ""),
            user_message=message,
            json_mode=True,
            temperature=0.0,
        )

        latency_ms = (time.perf_counter() - start_time) * 1000

        # Parse result
        intent = "GENERAL_INQUIRY"
        confidence = 0.5
        try:
            if response.content:
                result = json.loads(response.content)
                intent = result.get("intent", "GENERAL_INQUIRY")
                confidence = result.get("confidence", 0.5)
        except json.JSONDecodeError:
            pass

        step = PipelineStep(
            agent_name="Intent Classification",
            action="classify_intent",
            input_summary=message[:50] + "..." if len(message) > 50 else message,
            output_summary=f"{intent} ({confidence:.0%})",
            latency_ms=latency_ms,
            cost_usd=response.cost,
            success=response.error is None,
            details={"intent": intent, "confidence": confidence}
        )

        return {"intent": intent, "confidence": confidence, "step": step}

    def _run_escalation_detection(self, message: str) -> Dict[str, Any]:
        """Run the Escalation Detection agent."""
        start_time = time.perf_counter()

        # Build conversation context
        conversation_context = "Customer message:\n" + message
        if self.conversation_history:
            history_str = "\n".join([
                f"{'Customer' if m['role'] == 'user' else 'Agent'}: {m['content'][:100]}..."
                for m in self.conversation_history[-4:]  # Last 2 exchanges
            ])
            conversation_context = f"Previous conversation:\n{history_str}\n\nCurrent message:\n{message}"

        response = self.client.chat_completion(
            model="gpt-4o-mini",
            system_prompt=self.prompts.get("escalation", ""),
            user_message=conversation_context,
            json_mode=True,
            temperature=0.0,
        )

        latency_ms = (time.perf_counter() - start_time) * 1000

        # Parse result
        should_escalate = False
        reason = ""
        try:
            if response.content:
                result = json.loads(response.content)
                should_escalate = result.get("escalate", False)
                reason = result.get("reason", "")
        except json.JSONDecodeError:
            pass

        step = PipelineStep(
            agent_name="Escalation Detection",
            action="detect_escalation",
            input_summary=message[:50] + "..." if len(message) > 50 else message,
            output_summary="ESCALATE" if should_escalate else "NO_ESCALATION",
            latency_ms=latency_ms,
            cost_usd=response.cost,
            success=response.error is None,
            details={"should_escalate": should_escalate, "reason": reason}
        )

        return {"should_escalate": should_escalate, "reason": reason, "step": step}

    def _run_response_generation(self, message: str, intent: str, escalation_needed: bool) -> Dict[str, Any]:
        """Run the Response Generation agent."""
        start_time = time.perf_counter()

        # Build context for response generation
        context_str = f"""
CUSTOMER CONTEXT:
{json.dumps(self.context, indent=2)}

DETECTED INTENT: {intent}
ESCALATION NEEDED: {escalation_needed}

CONVERSATION HISTORY:
{self._format_history()}
"""

        # Build messages with system prompt + context
        system_content = self.prompts.get("response", "") + "\n\n" + context_str

        # Add conversation history
        messages = [{"role": "system", "content": system_content}]
        for turn in self.conversation_history[-6:]:  # Last 3 exchanges
            messages.append(turn)
        messages.append({"role": "user", "content": message})

        response = self.client.chat_completion(
            model="gpt-4o-mini",
            messages=messages,
            temperature=0.7,  # Slightly creative for natural responses
        )

        latency_ms = (time.perf_counter() - start_time) * 1000

        response_text = response.content or "I apologize, but I'm having trouble generating a response."

        step = PipelineStep(
            agent_name="Response Generation",
            action="generate_response",
            input_summary=f"Intent: {intent}",
            output_summary=response_text[:50] + "..." if len(response_text) > 50 else response_text,
            latency_ms=latency_ms,
            cost_usd=response.cost,
            success=response.error is None,
            details={"response_length": len(response_text)}
        )

        return {"response": response_text, "step": step}

    def _format_history(self) -> str:
        """Format conversation history for context."""
        if not self.conversation_history:
            return "(No previous messages)"

        lines = []
        for msg in self.conversation_history[-6:]:
            role = "Customer" if msg["role"] == "user" else "Agent"
            content = msg["content"][:100] + "..." if len(msg["content"]) > 100 else msg["content"]
            lines.append(f"{role}: {content}")
        return "\n".join(lines)


# Global instance for the console
_azure_mode_instance: Optional[AzureOpenAIMode] = None


def get_azure_mode() -> AzureOpenAIMode:
    """Get or create the global Azure OpenAI mode instance."""
    global _azure_mode_instance
    if _azure_mode_instance is None:
        _azure_mode_instance = AzureOpenAIMode()
    return _azure_mode_instance


def is_azure_mode_available() -> bool:
    """Check if Azure OpenAI mode is available."""
    return AZURE_OPENAI_AVAILABLE
