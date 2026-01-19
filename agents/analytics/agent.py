"""
Analytics Agent
Collects metrics and events from all agents for KPI tracking

Phase 1: Mock Google Analytics integration
Phase 2: Real analytics with Azure Application Insights
"""

import sys, asyncio, httpx
from pathlib import Path
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
        """Collect analytics event (passive - no response needed)."""
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
            
            # Send to Google Analytics (mock)
            await self._send_to_google_analytics_mock(event)
            
        except Exception as e:
            self.logger.error(f"Error collecting event: {e}")
    
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
        self.logger.info("DEMO MODE - Passive event collection")
        self.logger.info("Simulating analytics event collection...")
        # Simulate collecting events
        for i in range(3):
            mock_event = {
                "contextId": f"demo-{i}",
                "parts": [{"type": "text", "content": {
                    "event_type": "intent_classified",
                    "agent_source": "intent-classifier",
                    "metrics": {"confidence": 0.85, "processing_time_ms": 150}
                }}]
            }
            await self.handle_message(mock_event)
            await asyncio.sleep(1)
        
        self.logger.info(f"Demo complete. Collected {self.events_collected} events. Keeping alive...")
        while True: await asyncio.sleep(30)

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
