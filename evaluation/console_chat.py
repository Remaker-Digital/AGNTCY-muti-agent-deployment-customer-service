#!/usr/bin/env python3
"""
Interactive Console Chat for Phase 3.5 Manual Testing

This script provides an interactive chat interface to test the multi-agent
customer service system with Azure OpenAI Service connected.

Features:
- Full agent pipeline simulation (Critic -> Intent -> Response)
- Real-time cost and latency tracking
- Conversation history management
- Debug mode for pipeline visibility
- Mock context data for realistic testing

Usage:
    python -m evaluation.console_chat
    python -m evaluation.console_chat --debug
    python -m evaluation.console_chat --context order

Commands during chat:
    /quit, /exit    - Exit the chat
    /clear          - Clear conversation history
    /stats          - Show usage statistics
    /context        - Show current context data
    /context <type> - Change context (order, return, product, billing, empty)
    /debug          - Toggle debug mode
    /help           - Show available commands
"""

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from evaluation.azure_openai_client import AzureOpenAIClient, ChatResponse
from evaluation.config import Config


# ============================================================================
# Mock Context Data for Testing
# ============================================================================

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
            {"name": "Wireless Bluetooth Headphones", "sku": "WBH-100", "price": 79.99, "in_stock": True, "colors": ["Black", "White", "Blue"]},
            {"name": "Premium Noise-Canceling Headphones", "sku": "PNC-200", "price": 199.99, "in_stock": True, "colors": ["Black", "Silver"]},
            {"name": "Smart Watch Pro", "sku": "SWP-300", "price": 299.99, "in_stock": False, "restock_date": "2026-02-01"},
        ],
        "shipping_info": "Free shipping on orders over $50. Standard shipping: 5-7 business days. Express shipping: 2-3 business days (+$15.99).",
        "international_shipping": "We ship to Canada, UK, and EU. International orders typically arrive in 10-14 business days."
    },
    "billing": {
        "customer_name": "David Chen",
        "customer_email": "david.chen@email.com",
        "account_id": "ACC-98765",
        "subscription": "Premium Plan - $19.99/month",
        "next_billing_date": "2026-02-01",
        "payment_method": "Mastercard ending in 5555",
        "recent_charges": [
            {"date": "2026-01-01", "description": "Premium Plan - Monthly", "amount": 19.99},
            {"date": "2025-12-01", "description": "Premium Plan - Monthly", "amount": 19.99},
        ],
        "billing_address": "456 Oak Avenue, Chicago, IL 60601"
    },
    "empty": {
        "customer_name": "Customer",
        "note": "No specific order or account context available. General assistance only."
    }
}


# ============================================================================
# Prompt Loaders
# ============================================================================

def load_prompt(prompt_name: str) -> str:
    """Load a prompt file from the prompts directory."""
    prompts_dir = Path(__file__).parent / "prompts"
    prompt_file = prompts_dir / f"{prompt_name}.txt"

    if not prompt_file.exists():
        raise FileNotFoundError(f"Prompt file not found: {prompt_file}")

    return prompt_file.read_text(encoding="utf-8")


# ============================================================================
# Agent Pipeline
# ============================================================================

class AgentPipeline:
    """
    Simulates the multi-agent pipeline for customer service.

    Pipeline:
    1. Critic/Supervisor - Validate input (block malicious content)
    2. Intent Classification - Determine customer intent
    3. Response Generation - Generate appropriate response
    """

    def __init__(self, client: AzureOpenAIClient, debug: bool = False):
        self.client = client
        self.debug = debug
        self.conversation_history: list[dict] = []
        self.context = MOCK_CONTEXTS["order"]  # Default context

        # Load prompts
        self.critic_prompt = load_prompt("critic_input_validation_final")
        self.intent_prompt = load_prompt("intent_classification_final")
        self.response_prompt = load_prompt("response_generation_final")

    def set_context(self, context_type: str) -> bool:
        """Set the mock context data."""
        if context_type in MOCK_CONTEXTS:
            self.context = MOCK_CONTEXTS[context_type]
            return True
        return False

    def get_context_str(self) -> str:
        """Get context as formatted string."""
        return json.dumps(self.context, indent=2)

    def clear_history(self) -> None:
        """Clear conversation history."""
        self.conversation_history = []

    def _debug_print(self, stage: str, content: str) -> None:
        """Print debug information if debug mode is enabled."""
        if self.debug:
            print(f"\n{'='*60}")
            print(f"[DEBUG] {stage}")
            print(f"{'='*60}")
            print(content[:500] + "..." if len(content) > 500 else content)
            print()

    def _run_critic(self, user_input: str) -> tuple[bool, str, ChatResponse]:
        """
        Run the Critic/Supervisor agent to validate input.

        Returns:
            (allowed, reason, response)
        """
        response = self.client.chat_completion(
            model="gpt-4o-mini",
            system_prompt=self.critic_prompt,
            user_message=user_input,
            json_mode=True,
            temperature=0.0,
        )

        self._debug_print("CRITIC/SUPERVISOR", f"Input: {user_input}\nResponse: {response.content}")

        if response.error:
            # Treat errors as blocked (fail safe)
            if "content_filter" in response.error.lower():
                return False, "Content blocked by Azure safety filter", response
            return False, f"Validation error: {response.error}", response

        try:
            result = json.loads(response.content)
            allowed = result.get("action", "BLOCK").upper() == "ALLOW"
            reason = result.get("reason", "No reason provided")
            return allowed, reason, response
        except json.JSONDecodeError:
            # If JSON parsing fails, be cautious and block
            return False, "Unable to validate input", response

    def _run_intent_classification(self, user_input: str) -> tuple[str, float, ChatResponse]:
        """
        Run the Intent Classification agent.

        Returns:
            (intent, confidence, response)
        """
        response = self.client.chat_completion(
            model="gpt-4o-mini",
            system_prompt=self.intent_prompt,
            user_message=user_input,
            json_mode=True,
            temperature=0.0,
        )

        self._debug_print("INTENT CLASSIFICATION", f"Input: {user_input}\nResponse: {response.content}")

        if response.error:
            return "GENERAL_INQUIRY", 0.5, response

        try:
            result = json.loads(response.content)
            intent = result.get("intent", "GENERAL_INQUIRY")
            confidence = result.get("confidence", 0.5)
            return intent, confidence, response
        except json.JSONDecodeError:
            return "GENERAL_INQUIRY", 0.5, response

    def _run_response_generation(
        self,
        user_input: str,
        intent: str,
        conversation_history: list[dict]
    ) -> tuple[str, ChatResponse]:
        """
        Run the Response Generation agent.

        Returns:
            (response_text, response_obj)
        """
        # Build context for response generation
        context_str = f"""
CUSTOMER CONTEXT:
{json.dumps(self.context, indent=2)}

DETECTED INTENT: {intent}

CONVERSATION HISTORY:
{self._format_history(conversation_history)}
"""

        # Build messages with conversation history
        messages = [
            {"role": "system", "content": self.response_prompt + "\n\n" + context_str}
        ]

        # Add recent conversation history (last 5 turns)
        for turn in conversation_history[-10:]:  # Last 5 customer + 5 agent messages
            messages.append(turn)

        # Add current user message
        messages.append({"role": "user", "content": user_input})

        response = self.client.chat_completion(
            model="gpt-4o-mini",
            messages=messages,
            temperature=0.7,  # Slightly more creative for natural responses
        )

        self._debug_print("RESPONSE GENERATION", f"Intent: {intent}\nResponse: {response.content}")

        if response.error:
            return f"I apologize, but I'm having trouble processing your request. Error: {response.error}", response

        return response.content, response

    def _format_history(self, history: list[dict]) -> str:
        """Format conversation history for context."""
        if not history:
            return "(No previous messages)"

        lines = []
        for msg in history[-6:]:  # Last 3 turns
            role = "Customer" if msg["role"] == "user" else "Agent"
            lines.append(f"{role}: {msg['content'][:100]}...")
        return "\n".join(lines)

    def process_message(self, user_input: str) -> dict:
        """
        Process a user message through the full agent pipeline.

        Returns:
            Dict with pipeline results including response, intent, costs, etc.
        """
        result = {
            "input": user_input,
            "timestamp": datetime.now().isoformat(),
            "blocked": False,
            "block_reason": None,
            "intent": None,
            "intent_confidence": None,
            "response": None,
            "total_cost": 0.0,
            "total_latency_ms": 0.0,
            "pipeline_steps": []
        }

        # Step 1: Critic/Supervisor validation
        allowed, reason, critic_response = self._run_critic(user_input)
        result["pipeline_steps"].append({
            "agent": "Critic/Supervisor",
            "result": "ALLOW" if allowed else "BLOCK",
            "reason": reason,
            "cost": critic_response.cost,
            "latency_ms": critic_response.latency_ms
        })
        result["total_cost"] += critic_response.cost
        result["total_latency_ms"] += critic_response.latency_ms

        if not allowed:
            result["blocked"] = True
            result["block_reason"] = reason
            result["response"] = f"I'm sorry, but I can't process that request. {reason}"
            return result

        # Step 2: Intent Classification
        intent, confidence, intent_response = self._run_intent_classification(user_input)
        result["intent"] = intent
        result["intent_confidence"] = confidence
        result["pipeline_steps"].append({
            "agent": "Intent Classification",
            "intent": intent,
            "confidence": confidence,
            "cost": intent_response.cost,
            "latency_ms": intent_response.latency_ms
        })
        result["total_cost"] += intent_response.cost
        result["total_latency_ms"] += intent_response.latency_ms

        # Step 3: Response Generation
        response_text, gen_response = self._run_response_generation(
            user_input, intent, self.conversation_history
        )
        result["response"] = response_text
        result["pipeline_steps"].append({
            "agent": "Response Generation",
            "cost": gen_response.cost,
            "latency_ms": gen_response.latency_ms
        })
        result["total_cost"] += gen_response.cost
        result["total_latency_ms"] += gen_response.latency_ms

        # Update conversation history
        self.conversation_history.append({"role": "user", "content": user_input})
        self.conversation_history.append({"role": "assistant", "content": response_text})

        return result


# ============================================================================
# Console Chat Interface
# ============================================================================

class ConsoleChatInterface:
    """Interactive console chat interface."""

    COMMANDS = {
        "/quit": "Exit the chat",
        "/exit": "Exit the chat",
        "/clear": "Clear conversation history",
        "/stats": "Show usage statistics",
        "/context": "Show current context data",
        "/context <type>": "Change context (order, return, product, billing, empty)",
        "/debug": "Toggle debug mode",
        "/help": "Show available commands",
    }

    def __init__(self, debug: bool = False, context_type: str = "order"):
        self.client: Optional[AzureOpenAIClient] = None
        self.pipeline: Optional[AgentPipeline] = None
        self.debug = debug
        self.initial_context = context_type
        self.running = False

    def initialize(self) -> bool:
        """Initialize the Azure OpenAI client and pipeline."""
        print("\n" + "="*60)
        print("  Phase 3.5 Interactive Chat - Manual Testing Interface")
        print("="*60)
        print("\nInitializing Azure OpenAI connection...")

        try:
            self.client = AzureOpenAIClient.from_env()

            # Test connection
            success, message = self.client.test_connection()
            if not success:
                print(f"\n[ERROR] Connection failed: {message}")
                return False

            print(f"[OK] {message}")

            # Initialize pipeline
            self.pipeline = AgentPipeline(self.client, debug=self.debug)
            self.pipeline.set_context(self.initial_context)

            print(f"[OK] Agent pipeline initialized")
            print(f"[OK] Context: {self.initial_context}")
            print(f"[OK] Debug mode: {'ON' if self.debug else 'OFF'}")

            return True

        except Exception as e:
            print(f"\n[ERROR] Initialization failed: {e}")
            print("\nMake sure you have set the following environment variables:")
            print("  - AZURE_OPENAI_ENDPOINT")
            print("  - AZURE_OPENAI_API_KEY")
            print("  - AZURE_OPENAI_API_VERSION")
            print("  - AZURE_OPENAI_GPT4O_MINI_DEPLOYMENT")
            return False

    def print_help(self) -> None:
        """Print available commands."""
        print("\n" + "-"*40)
        print("Available Commands:")
        print("-"*40)
        for cmd, desc in self.COMMANDS.items():
            print(f"  {cmd:20} - {desc}")
        print("-"*40)
        print("Context types: order, return, product, billing, empty")
        print("-"*40 + "\n")

    def print_stats(self) -> None:
        """Print usage statistics."""
        stats = self.client.get_usage_stats()
        within_budget, budget_msg = self.client.check_budget()

        print("\n" + "-"*40)
        print("Usage Statistics:")
        print("-"*40)
        print(f"  Requests:        {stats['request_count']}")
        print(f"  Input Tokens:    {stats['total_input_tokens']:,}")
        print(f"  Output Tokens:   {stats['total_output_tokens']:,}")
        print(f"  Total Cost:      ${stats['total_cost']:.4f}")
        print(f"  Session Time:    {stats['session_duration_seconds']:.1f}s")
        print(f"  Budget Status:   {budget_msg}")
        print("-"*40 + "\n")

    def handle_command(self, command: str) -> bool:
        """
        Handle a command input.

        Returns:
            True if chat should continue, False if should exit.
        """
        parts = command.lower().split()
        cmd = parts[0]

        if cmd in ("/quit", "/exit"):
            return False

        elif cmd == "/clear":
            self.pipeline.clear_history()
            print("\n[OK] Conversation history cleared.\n")

        elif cmd == "/stats":
            self.print_stats()

        elif cmd == "/context":
            if len(parts) > 1:
                context_type = parts[1]
                if self.pipeline.set_context(context_type):
                    print(f"\n[OK] Context changed to: {context_type}\n")
                else:
                    print(f"\n[ERROR] Unknown context type: {context_type}")
                    print("Available: order, return, product, billing, empty\n")
            else:
                print("\nCurrent Context:")
                print("-"*40)
                print(self.pipeline.get_context_str())
                print("-"*40 + "\n")

        elif cmd == "/debug":
            self.debug = not self.debug
            self.pipeline.debug = self.debug
            print(f"\n[OK] Debug mode: {'ON' if self.debug else 'OFF'}\n")

        elif cmd == "/help":
            self.print_help()

        else:
            print(f"\n[ERROR] Unknown command: {cmd}")
            print("Type /help for available commands.\n")

        return True

    def format_response(self, result: dict) -> str:
        """Format the pipeline result for display."""
        lines = []

        # Show intent if not blocked
        if not result["blocked"] and result["intent"]:
            lines.append(f"[Intent: {result['intent']} ({result['intent_confidence']:.0%})]")

        # Show response
        lines.append("")
        lines.append(result["response"])
        lines.append("")

        # Show metrics
        lines.append(f"[Cost: ${result['total_cost']:.4f} | Latency: {result['total_latency_ms']:.0f}ms]")

        return "\n".join(lines)

    def run(self) -> None:
        """Run the interactive chat loop."""
        if not self.initialize():
            return

        self.running = True
        self.print_help()

        print("\nChat started. Type your message or /help for commands.\n")
        print(f"Customer Context: {self.pipeline.context.get('customer_name', 'Customer')}")
        print("-"*60 + "\n")

        while self.running:
            try:
                # Get user input
                user_input = input("You: ").strip()

                if not user_input:
                    continue

                # Handle commands
                if user_input.startswith("/"):
                    if not self.handle_command(user_input):
                        break
                    continue

                # Process message through pipeline
                print("\n[Processing...]")
                result = self.pipeline.process_message(user_input)

                # Display response
                print("\nAgent:", self.format_response(result))
                print()

            except KeyboardInterrupt:
                print("\n\n[Interrupted]")
                break
            except EOFError:
                break
            except Exception as e:
                print(f"\n[ERROR] {e}\n")

        # Print final stats
        print("\n" + "="*60)
        print("Session ended.")
        self.print_stats()
        print("Thank you for testing!")
        print("="*60 + "\n")


# ============================================================================
# Main Entry Point
# ============================================================================

def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Interactive console chat for Phase 3.5 manual testing",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python -m evaluation.console_chat
    python -m evaluation.console_chat --debug
    python -m evaluation.console_chat --context product
    python -m evaluation.console_chat --debug --context billing

Context Types:
    order   - Customer with shipped order (default)
    return  - Customer wanting to return an item
    product - Product catalog and shipping info
    billing - Subscription and billing questions
    empty   - No specific context (general assistance)
"""
    )

    parser.add_argument(
        "--debug", "-d",
        action="store_true",
        help="Enable debug mode (show agent pipeline details)"
    )

    parser.add_argument(
        "--context", "-c",
        choices=["order", "return", "product", "billing", "empty"],
        default="order",
        help="Initial context type (default: order)"
    )

    args = parser.parse_args()

    # Run the chat interface
    chat = ConsoleChatInterface(debug=args.debug, context_type=args.context)
    chat.run()


if __name__ == "__main__":
    main()
