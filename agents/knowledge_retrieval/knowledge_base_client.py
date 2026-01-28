"""
Knowledge Base client for searching policies and FAQs
Phase 2: Coffee/brewing business specific content
"""

import json
from pathlib import Path
from typing import List, Dict, Any, Optional


class KnowledgeBaseClient:
    """Client for searching local knowledge base files."""

    def __init__(self, knowledge_base_path: Path, logger):
        """
        Initialize knowledge base client.

        Args:
            knowledge_base_path: Path to knowledge base directory
            logger: Logger instance
        """
        self.kb_path = knowledge_base_path
        self.logger = logger
        self._cache = {}

    def _load_json(self, filename: str) -> Dict[str, Any]:
        """Load and cache JSON file."""
        if filename not in self._cache:
            filepath = self.kb_path / filename
            if filepath.exists():
                with open(filepath, "r") as f:
                    self._cache[filename] = json.load(f)
            else:
                self.logger.warning(f"Knowledge base file not found: {filename}")
                self._cache[filename] = {}

        return self._cache[filename]

    def search_return_policy(self, query: str) -> List[Dict[str, Any]]:
        """
        Search return/refund policy.

        Args:
            query: Search query

        Returns:
            List of matching policy sections
        """
        policy = self._load_json("return-policy.json")
        query_lower = query.lower()
        results = []

        policy_sections = policy.get("policy_sections", [])

        for section in policy_sections:
            # Check keywords match
            keywords = section.get("keywords", [])
            if any(keyword in query_lower for keyword in keywords):
                results.append(
                    {
                        "source": "return_policy",
                        "type": "policy",
                        "section_id": section.get("section_id"),
                        "title": section.get("title"),
                        "content": section.get("content"),
                        "quick_answer": section.get("quick_answer"),
                        "relevance": 0.9,
                    }
                )

        # If no matches, return general overview
        if not results and policy_sections:
            first_section = policy_sections[0]
            results.append(
                {
                    "source": "return_policy",
                    "type": "policy",
                    "section_id": first_section.get("section_id"),
                    "title": first_section.get("title"),
                    "content": first_section.get("content"),
                    "quick_answer": first_section.get("quick_answer"),
                    "relevance": 0.5,
                }
            )

        # Add auto-approval scenarios if relevant
        if "refund" in query_lower or "return" in query_lower:
            scenarios = policy.get("common_scenarios", [])
            for scenario in scenarios:
                results.append(
                    {
                        "source": "return_policy_scenarios",
                        "type": "business_rule",
                        "scenario": scenario.get("scenario"),
                        "condition": scenario.get("condition"),
                        "auto_approval": scenario.get("auto_approval", False),
                        "action": scenario.get("action"),
                        "relevance": 0.85,
                    }
                )

        return results

    def search_shipping_policy(self, query: str) -> List[Dict[str, Any]]:
        """
        Search shipping policy.

        Args:
            query: Search query

        Returns:
            List of matching policy sections
        """
        policy = self._load_json("shipping-policy.json")
        query_lower = query.lower()
        results = []

        policy_sections = policy.get("policy_sections", [])

        for section in policy_sections:
            # Check keywords match
            keywords = section.get("keywords", [])
            if any(keyword in query_lower for keyword in keywords):
                results.append(
                    {
                        "source": "shipping_policy",
                        "type": "policy",
                        "section_id": section.get("section_id"),
                        "title": section.get("title"),
                        "content": section.get("content"),
                        "quick_answer": section.get("quick_answer"),
                        "relevance": 0.9,
                    }
                )

        # Check common scenarios
        scenarios = policy.get("common_scenarios", [])
        for scenario in scenarios:
            scenario_text = (
                f"{scenario.get('scenario', '')} {scenario.get('recommendation', '')}"
            )
            if any(word in query_lower for word in ["cheap", "fast", "free", "best"]):
                results.append(
                    {
                        "source": "shipping_scenarios",
                        "type": "recommendation",
                        "scenario": scenario.get("scenario"),
                        "recommendation": scenario.get("recommendation"),
                        "typical_cost": scenario.get("typical_cost"),
                        "relevance": 0.8,
                    }
                )

        return results

    def search_loyalty_program(
        self, query: str, customer_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Search loyalty program information.

        Args:
            query: Search query
            customer_id: Optional customer ID for personalized balance info

        Returns:
            List of matching loyalty program sections and customer balance
        """
        program = self._load_json("loyalty-program.json")
        query_lower = query.lower()
        results = []

        # STEP 1: Add customer-specific balance if customer_id provided
        if customer_id:
            test_balances = program.get("test_customer_balances", [])
            for balance in test_balances:
                if balance.get("customer_id") == customer_id:
                    results.append(
                        {
                            "source": "loyalty_balance",
                            "type": "customer_balance",
                            "customer_id": customer_id,
                            "customer_name": balance.get("customer_name"),
                            "current_balance": balance.get("current_balance"),
                            "tier": balance.get("tier"),
                            "points_to_next_tier": balance.get("points_to_next_tier"),
                            "next_tier": balance.get("next_tier"),
                            "points_expiring_30_days": balance.get(
                                "points_expiring_30_days"
                            ),
                            "auto_delivery_subscriber": balance.get(
                                "auto_delivery_subscriber"
                            ),
                            "lifetime_points_earned": balance.get(
                                "lifetime_points_earned"
                            ),
                            "lifetime_points_redeemed": balance.get(
                                "lifetime_points_redeemed"
                            ),
                            "relevance": 1.0,
                        }
                    )
                    break

        # STEP 2: Search program sections based on keywords
        program_sections = program.get("program_sections", [])

        for section in program_sections:
            # Check keywords match
            keywords = section.get("keywords", [])
            if any(keyword in query_lower for keyword in keywords):
                results.append(
                    {
                        "source": "loyalty_program",
                        "type": "policy",
                        "section_id": section.get("section_id"),
                        "title": section.get("title"),
                        "content": section.get("content"),
                        "quick_answer": section.get("quick_answer"),
                        "relevance": 0.9,
                    }
                )

        # STEP 3: Add redemption tiers if query is about redemption
        if any(word in query_lower for word in ["redeem", "use", "discount", "reward"]):
            redemption_tiers = program.get("redemption_tiers", [])
            if redemption_tiers:
                results.append(
                    {
                        "source": "loyalty_redemption",
                        "type": "redemption_tiers",
                        "tiers": redemption_tiers,
                        "relevance": 0.95,
                    }
                )

        # STEP 4: Add membership tiers if query is about tiers or benefits
        if any(
            word in query_lower
            for word in ["tier", "level", "silver", "gold", "bronze", "benefit"]
        ):
            membership_tiers = program.get("membership_tiers", [])
            if membership_tiers:
                results.append(
                    {
                        "source": "loyalty_tiers",
                        "type": "membership_tiers",
                        "tiers": membership_tiers,
                        "relevance": 0.95,
                    }
                )

        # If no specific matches, return general overview
        if not results and program_sections:
            # Return first section (earning points overview)
            first_section = program_sections[0]
            results.append(
                {
                    "source": "loyalty_program",
                    "type": "policy",
                    "section_id": first_section.get("section_id"),
                    "title": first_section.get("title"),
                    "content": first_section.get("content"),
                    "quick_answer": first_section.get("quick_answer"),
                    "relevance": 0.5,
                }
            )

        return results

    def search_all_policies(self, query: str) -> List[Dict[str, Any]]:
        """
        Search across all policy documents.

        Args:
            query: Search query

        Returns:
            Combined results from all policies
        """
        results = []
        query_lower = query.lower()

        # Determine which policies to search based on keywords
        if any(
            word in query_lower
            for word in ["return", "refund", "exchange", "send back"]
        ):
            results.extend(self.search_return_policy(query))

        if any(
            word in query_lower
            for word in ["ship", "delivery", "carrier", "usps", "ups", "fedex"]
        ):
            results.extend(self.search_shipping_policy(query))

        if any(
            word in query_lower
            for word in ["points", "rewards", "loyalty", "balance", "redeem"]
        ):
            results.extend(self.search_loyalty_program(query))

        # Sort by relevance
        results.sort(key=lambda x: x.get("relevance", 0), reverse=True)

        return results

    def get_auto_approval_rules(self, intent: str) -> List[Dict[str, Any]]:
        """
        Get auto-approval business rules for specific intent.

        Args:
            intent: Intent type (e.g., "return_request")

        Returns:
            List of applicable business rules
        """
        if intent in ["return_request", "refund_status"]:
            policy = self._load_json("return-policy.json")
            scenarios = policy.get("common_scenarios", [])

            return [
                {
                    "scenario": s.get("scenario"),
                    "condition": s.get("condition"),
                    "auto_approval": s.get("auto_approval", False),
                    "action": s.get("action"),
                }
                for s in scenarios
                if s.get("auto_approval") == True
            ]

        return []
