"""
Analytics Agent
Collects metrics and events from all agents for KPI tracking

Phase 1: Mock Google Analytics integration
Phase 2: Coffee/brewing business - KPI tracking (automation rate, response time, sentiment, escalations)

Refactored to use BaseAgent pattern for reduced code duplication.
"""

import asyncio
import httpx
from datetime import datetime
from typing import Dict, List

from shared.base_agent import BaseAgent, run_agent
from shared.models import AnalyticsEvent, create_a2a_message, extract_message_content, generate_message_id


class AnalyticsAgent(BaseAgent):
    """Passive listener collecting metrics from all agent communication."""

    agent_name = "analytics-agent"
    default_topic = "analytics"

    def __init__(self):
        """Initialize the Analytics Agent."""
        super().__init__()
        self.http_client = httpx.AsyncClient(timeout=10.0)

        # Phase 2: KPI Tracking for coffee/brewing business
        self.kpis = {
            "total_conversations": 0,
            "automated_conversations": 0,  # Handled without escalation
            "escalated_conversations": 0,
            "total_response_time_ms": 0,
            "intents_classified": {},  # Count by intent type
            "sentiment_distribution": {"positive": 0, "neutral": 0, "negative": 0, "very_negative": 0},
            "escalation_reasons": {},  # Count by reason
            "auto_approvals": 0,  # Auto-approved refunds
            "avg_confidence": []  # Confidence scores
        }
        self.conversation_start_times = {}  # Track conversation start for response time

    async def process_message(self, content: dict, message: dict) -> None:
        """
        Collect analytics event and update KPIs.

        Args:
            content: Extracted message content
            message: Full A2A message

        Returns:
            None (analytics is fire-and-forget)
        """
        event = AnalyticsEvent(
            event_id=generate_message_id(),
            event_type=content.get("event_type", "unknown"),
            context_id=message.get("contextId", "unknown"),
            agent_source=content.get("agent_source", "unknown"),
            metrics=content.get("metrics", {}),
            metadata=content.get("metadata", {})
        )

        self.logger.debug(f"Collected event: {event.event_type} from {event.agent_source}")

        # Update KPIs based on event type
        self._update_kpis(event)

        # Send to Google Analytics (mock)
        await self._send_to_google_analytics_mock(event)

        return {"status": "collected", "event_id": event.event_id}

    def get_demo_messages(self) -> List[dict]:
        """Return sample messages for demo mode - Phase 2 coffee/brewing KPI tracking examples."""
        # Simulate 3 complete conversation flows as sequential events
        events = []

        # Conversation 1: Order status query - automated
        for event_data in [
            {"event_type": "conversation_started", "agent_source": "system", "metrics": {}},
            {"event_type": "intent_classified", "agent_source": "intent-classifier",
             "metrics": {"intent": "order_status", "confidence": 0.92}},
            {"event_type": "knowledge_retrieved", "agent_source": "knowledge-retrieval",
             "metrics": {"results_found": 1, "search_time_ms": 85}},
            {"event_type": "response_generated", "agent_source": "response-generator",
             "metrics": {"confidence": 0.88}},
            {"event_type": "escalation_decision", "agent_source": "escalation",
             "metrics": {"should_escalate": False, "reason": "Standard query - automated"}}
        ]:
            events.append({
                "contextId": "demo-ctx-001",
                "parts": [{"type": "text", "content": event_data}]
            })

        # Conversation 2: Refund request - auto-approved
        for event_data in [
            {"event_type": "conversation_started", "agent_source": "system", "metrics": {}},
            {"event_type": "intent_classified", "agent_source": "intent-classifier",
             "metrics": {"intent": "refund_status", "confidence": 0.87}},
            {"event_type": "sentiment_detected", "agent_source": "intent-classifier",
             "metrics": {"sentiment": "neutral"}},
            {"event_type": "escalation_decision", "agent_source": "escalation",
             "metrics": {"should_escalate": False, "reason": "Refund auto-approved", "auto_approved": True}},
            {"event_type": "response_generated", "agent_source": "response-generator",
             "metrics": {"confidence": 0.90}}
        ]:
            events.append({
                "contextId": "demo-ctx-002",
                "parts": [{"type": "text", "content": event_data}]
            })

        # Conversation 3: Brewer defect - escalated
        for event_data in [
            {"event_type": "conversation_started", "agent_source": "system", "metrics": {}},
            {"event_type": "intent_classified", "agent_source": "intent-classifier",
             "metrics": {"intent": "brewer_support", "confidence": 0.95}},
            {"event_type": "sentiment_detected", "agent_source": "intent-classifier",
             "metrics": {"sentiment": "negative"}},
            {"event_type": "escalation_decision", "agent_source": "escalation",
             "metrics": {"should_escalate": True, "reason": "Brewer defect - technical support needed"}},
            {"event_type": "response_generated", "agent_source": "response-generator",
             "metrics": {"confidence": 0.85}}
        ]:
            events.append({
                "contextId": "demo-ctx-003",
                "parts": [{"type": "text", "content": event_data}]
            })

        return events

    def cleanup(self) -> None:
        """Cleanup with KPI report."""
        self._log_kpi_summary()
        asyncio.create_task(self.http_client.aclose())
        super().cleanup()

    def _update_kpis(self, event: AnalyticsEvent):
        """Update KPI metrics based on event type."""
        context_id = event.context_id
        event_type = event.event_type
        metrics = event.metrics

        # Track conversation starts
        if event_type == "conversation_started":
            self.kpis["total_conversations"] += 1
            self.conversation_start_times[context_id] = datetime.now()
            self.logger.debug(f"New conversation started: {context_id}")

        # Track intent classification
        elif event_type == "intent_classified":
            intent = metrics.get("intent", "unknown")
            self.kpis["intents_classified"][intent] = self.kpis["intents_classified"].get(intent, 0) + 1

            confidence = metrics.get("confidence", 0)
            if confidence > 0:
                self.kpis["avg_confidence"].append(confidence)

        # Track sentiment
        elif event_type == "sentiment_detected":
            sentiment = metrics.get("sentiment", "neutral")
            if sentiment in self.kpis["sentiment_distribution"]:
                self.kpis["sentiment_distribution"][sentiment] += 1

        # Track escalations
        elif event_type == "escalation_decision":
            should_escalate = metrics.get("should_escalate", False)
            escalation_reason = metrics.get("reason", "unknown")

            if should_escalate:
                self.kpis["escalated_conversations"] += 1
                self.kpis["escalation_reasons"][escalation_reason] = \
                    self.kpis["escalation_reasons"].get(escalation_reason, 0) + 1
            else:
                self.kpis["automated_conversations"] += 1

            # Track auto-approvals
            if metrics.get("auto_approved"):
                self.kpis["auto_approvals"] += 1

        # Track response completion
        elif event_type == "response_generated":
            # Calculate response time if we have start time
            if context_id in self.conversation_start_times:
                start_time = self.conversation_start_times[context_id]
                response_time_ms = (datetime.now() - start_time).total_seconds() * 1000
                self.kpis["total_response_time_ms"] += response_time_ms
                self.logger.debug(f"Response time for {context_id}: {response_time_ms:.2f}ms")

        # Log KPI summary periodically (every 10 events)
        if self.messages_processed % 10 == 0:
            self._log_kpi_summary()

    def _log_kpi_summary(self):
        """Log current KPI metrics."""
        total_conv = self.kpis["total_conversations"]
        automated = self.kpis["automated_conversations"]
        escalated = self.kpis["escalated_conversations"]

        # Calculate automation rate
        automation_rate = (automated / total_conv * 100) if total_conv > 0 else 0

        # Calculate average response time
        avg_response_time = (self.kpis["total_response_time_ms"] / total_conv) if total_conv > 0 else 0

        # Calculate average confidence
        avg_confidence = (sum(self.kpis["avg_confidence"]) / len(self.kpis["avg_confidence"])) \
            if self.kpis["avg_confidence"] else 0

        self.logger.info("=" * 60)
        self.logger.info("KPI SUMMARY")
        self.logger.info("=" * 60)
        self.logger.info(f"Total Conversations: {total_conv}")
        self.logger.info(f"Automated: {automated} ({automation_rate:.1f}%)")
        self.logger.info(f"Escalated: {escalated} ({(escalated/total_conv*100) if total_conv > 0 else 0:.1f}%)")
        self.logger.info(f"Auto-Approvals: {self.kpis['auto_approvals']}")
        self.logger.info(f"Avg Response Time: {avg_response_time:.2f}ms")
        self.logger.info(f"Avg Confidence: {avg_confidence:.2f}")
        self.logger.info(f"Events Collected: {self.messages_processed}")
        self.logger.info("=" * 60)

    def get_kpi_report(self) -> Dict:
        """Generate comprehensive KPI report."""
        total_conv = self.kpis["total_conversations"]
        automated = self.kpis["automated_conversations"]
        escalated = self.kpis["escalated_conversations"]

        return {
            "total_conversations": total_conv,
            "automated_conversations": automated,
            "escalated_conversations": escalated,
            "automation_rate_percent": (automated / total_conv * 100) if total_conv > 0 else 0,
            "escalation_rate_percent": (escalated / total_conv * 100) if total_conv > 0 else 0,
            "auto_approvals": self.kpis["auto_approvals"],
            "avg_response_time_ms": (self.kpis["total_response_time_ms"] / total_conv) if total_conv > 0 else 0,
            "avg_confidence": (sum(self.kpis["avg_confidence"]) / len(self.kpis["avg_confidence"])) \
                if self.kpis["avg_confidence"] else 0,
            "intents_distribution": self.kpis["intents_classified"],
            "sentiment_distribution": self.kpis["sentiment_distribution"],
            "escalation_reasons": self.kpis["escalation_reasons"],
            "events_collected": self.messages_processed
        }

    async def _send_to_google_analytics_mock(self, event: AnalyticsEvent):
        """Send event to mock Google Analytics API."""
        try:
            ga_url = self.config.get("google_analytics_url", "http://localhost:8004")
            # Mock GA4 Measurement Protocol
            response = await self.http_client.post(
                f"{ga_url}/v1beta/properties/123456789/runReport",
                json={
                    "dimensions": [{"name": "eventName"}],
                    "metrics": [{"name": "eventCount"}],
                    "event_data": event.to_dict()
                }
            )
            if response.status_code == 200:
                self.logger.debug(f"Sent analytics event to GA")
        except Exception as e:
            self.logger.error(f"GA send failed: {e}")


if __name__ == "__main__":
    run_agent(AnalyticsAgent)
