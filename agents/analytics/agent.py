"""
Analytics Agent
Collects metrics and events from all agents for KPI tracking

Phase 1: Mock Google Analytics integration
Phase 2: Coffee/brewing business - KPI tracking (automation rate, response time, sentiment, escalations)
"""

import sys, asyncio, httpx
from pathlib import Path
from typing import Dict
from datetime import datetime
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from shared import get_factory, shutdown_factory, setup_logging, load_config, handle_graceful_shutdown
from shared.models import AnalyticsEvent, create_a2a_message, extract_message_content, generate_message_id

class AnalyticsAgent:
    """Passive listener collecting metrics from all agent communication."""
    
    def __init__(self):
        self.config = load_config()
        self.agent_topic = self.config["agent_topic"]
        self.logger = setup_logging(self.agent_topic, self.config["log_level"])
        self.logger.info(f"Initializing Analytics Agent: {self.agent_topic}")
        self.factory = get_factory()
        self.transport, self.client = None, None
        self.events_collected = 0
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
    
    async def initialize(self):
        self.logger.info("Creating NATS transport for high-throughput analytics...")
        try:
            # Use NATS for analytics (high-throughput pub-sub)
            self.transport = self.factory.create_nats_transport(f"{self.agent_topic}-transport")
            if self.transport:
                self.client = self.factory.create_a2a_client(self.agent_topic, self.transport)
                self.logger.info("Agent initialized with NATS transport")
        except Exception as e:
            self.logger.warning(f"NATS not available, falling back: {e}")
    
    async def handle_message(self, message: dict) -> None:
        """
        Collect analytics event and update KPIs.
        Phase 2: Coffee/brewing business KPI tracking.
        """
        self.events_collected += 1
        try:
            content = extract_message_content(message)
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

        except Exception as e:
            self.logger.error(f"Error collecting event: {e}", exc_info=True)

    def _update_kpis(self, event: AnalyticsEvent):
        """Update KPI metrics based on event type."""
        context_id = event.context_id
        event_type = event.event_type
        metrics = event.metrics
        metadata = event.metadata

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
        if self.events_collected % 10 == 0:
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
        self.logger.info(f"Events Collected: {self.events_collected}")
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
            "events_collected": self.events_collected
        }
    
    async def _send_to_google_analytics_mock(self, event: AnalyticsEvent):
        """Send event to mock Google Analytics API."""
        try:
            ga_url = self.config["google_analytics_url"]
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
    
    def cleanup(self):
        self.logger.info(f"Cleaning up... (collected {self.events_collected} events)")
        asyncio.create_task(self.http_client.aclose())
        shutdown_factory()
    
    async def run_demo_mode(self):
        """Run in demo mode - Phase 2 coffee/brewing KPI tracking examples."""
        self.logger.info("Running in DEMO MODE - Phase 2 Coffee/Brewing KPI Tracking")
        self.logger.info("Simulating multi-agent conversation flow events...")

        # Simulate 3 complete conversation flows
        conversations = [
            {
                "context_id": "demo-ctx-001",
                "scenario": "Order status query - automated",
                "events": [
                    {"event_type": "conversation_started", "agent_source": "system", "metrics": {}},
                    {"event_type": "intent_classified", "agent_source": "intent-classifier",
                     "metrics": {"intent": "order_status", "confidence": 0.92}},
                    {"event_type": "knowledge_retrieved", "agent_source": "knowledge-retrieval",
                     "metrics": {"results_found": 1, "search_time_ms": 85}},
                    {"event_type": "response_generated", "agent_source": "response-generator",
                     "metrics": {"confidence": 0.88}},
                    {"event_type": "escalation_decision", "agent_source": "escalation",
                     "metrics": {"should_escalate": False, "reason": "Standard query - automated"}}
                ]
            },
            {
                "context_id": "demo-ctx-002",
                "scenario": "Refund request - auto-approved",
                "events": [
                    {"event_type": "conversation_started", "agent_source": "system", "metrics": {}},
                    {"event_type": "intent_classified", "agent_source": "intent-classifier",
                     "metrics": {"intent": "refund_status", "confidence": 0.87}},
                    {"event_type": "sentiment_detected", "agent_source": "intent-classifier",
                     "metrics": {"sentiment": "neutral"}},
                    {"event_type": "knowledge_retrieved", "agent_source": "knowledge-retrieval",
                     "metrics": {"results_found": 2, "search_time_ms": 120}},
                    {"event_type": "escalation_decision", "agent_source": "escalation",
                     "metrics": {"should_escalate": False, "reason": "Refund auto-approved", "auto_approved": True}},
                    {"event_type": "response_generated", "agent_source": "response-generator",
                     "metrics": {"confidence": 0.90}}
                ]
            },
            {
                "context_id": "demo-ctx-003",
                "scenario": "Brewer defect - escalated",
                "events": [
                    {"event_type": "conversation_started", "agent_source": "system", "metrics": {}},
                    {"event_type": "intent_classified", "agent_source": "intent-classifier",
                     "metrics": {"intent": "brewer_support", "confidence": 0.95}},
                    {"event_type": "sentiment_detected", "agent_source": "intent-classifier",
                     "metrics": {"sentiment": "negative"}},
                    {"event_type": "knowledge_retrieved", "agent_source": "knowledge-retrieval",
                     "metrics": {"results_found": 1, "search_time_ms": 95}},
                    {"event_type": "escalation_decision", "agent_source": "escalation",
                     "metrics": {"should_escalate": True, "reason": "Brewer defect - technical support needed"}},
                    {"event_type": "response_generated", "agent_source": "response-generator",
                     "metrics": {"confidence": 0.85}}
                ]
            }
        ]

        for conv in conversations:
            self.logger.info(f"\nSimulating: {conv['scenario']}")
            for event_data in conv["events"]:
                mock_message = {
                    "contextId": conv["context_id"],
                    "parts": [{
                        "type": "text",
                        "content": {
                            "event_type": event_data["event_type"],
                            "agent_source": event_data["agent_source"],
                            "metrics": event_data["metrics"],
                            "metadata": {}
                        }
                    }]
                }
                await self.handle_message(mock_message)
                await asyncio.sleep(0.5)

        # Generate final KPI report
        self.logger.info("\n" + "=" * 60)
        self.logger.info("FINAL KPI REPORT")
        self.logger.info("=" * 60)
        report = self.get_kpi_report()
        for key, value in report.items():
            if isinstance(value, dict):
                self.logger.info(f"{key}:")
                for sub_key, sub_value in value.items():
                    self.logger.info(f"  {sub_key}: {sub_value}")
            else:
                self.logger.info(f"{key}: {value}")
        self.logger.info("=" * 60)

        self.logger.info("\nDemo complete. Keeping alive for health checks...")
        while True:
            await asyncio.sleep(30)

async def main():
    agent = AnalyticsAgent()
    handle_graceful_shutdown(agent.logger, agent.cleanup)
    try:
        await agent.initialize()
        await agent.run_demo_mode() if agent.client is None else await asyncio.sleep(float('inf'))
    except KeyboardInterrupt:
        pass
    finally:
        agent.cleanup()

if __name__ == "__main__":
    asyncio.run(main())
