"""
Escalation Agent
Determines when to escalate to human agents based on sentiment and complexity

Phase 1: Simple rule-based escalation
Phase 2: ML-based sentiment analysis and complexity scoring
"""

import sys, asyncio, httpx
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from shared import get_factory, shutdown_factory, setup_logging, load_config, handle_graceful_shutdown
from shared.models import (EscalationDecision, Sentiment, Priority, create_a2a_message,
                           extract_message_content, generate_message_id)

class EscalationAgent:
    """Decides when to escalate conversations to human agents."""
    
    def __init__(self):
        self.config = load_config()
        self.agent_topic = self.config["agent_topic"]
        self.logger = setup_logging(self.agent_topic, self.config["log_level"])
        self.logger.info(f"Initializing Escalation Agent: {self.agent_topic}")
        self.factory = get_factory()
        self.transport, self.client = None, None
        self.decisions_made = 0
        self.http_client = httpx.AsyncClient(timeout=10.0)
    
    async def initialize(self):
        self.logger.info("Creating SLIM transport and A2A client...")
        try:
            self.transport = self.factory.create_slim_transport(f"{self.agent_topic}-transport")
            if self.transport:
                self.client = self.factory.create_a2a_client(self.agent_topic, self.transport)
                self.logger.info("Agent initialized")
        except Exception as e:
            self.logger.error(f"Init failed: {e}", exc_info=True)
    
    async def handle_message(self, message: dict) -> dict:
        self.decisions_made += 1
        try:
            content = extract_message_content(message)
            customer_message = content.get("customer_message", "")
            
            # Phase 1: Simple sentiment detection
            sentiment, complexity = self._analyze_mock(customer_message)
            should_escalate = sentiment == Sentiment.VERY_NEGATIVE or complexity > 0.8
            
            decision = EscalationDecision(
                decision_id=generate_message_id(),
                context_id=message.get("contextId", "unknown"),
                should_escalate=should_escalate,
                reason=f"Sentiment: {sentiment.value}, Complexity: {complexity:.2f}",
                priority=Priority.URGENT if sentiment == Sentiment.VERY_NEGATIVE else Priority.NORMAL,
                sentiment=sentiment,
                complexity_score=complexity
            )
            
            self.logger.info(f"Escalation decision: {'ESCALATE' if should_escalate else 'CONTINUE'} "
                           f"(sentiment={sentiment.value}, complexity={complexity:.2f})")
            
            # If escalating, create Zendesk ticket (mock)
            if should_escalate:
                ticket_id = await self._create_zendesk_ticket_mock(customer_message)
                decision.zendesk_ticket_id = ticket_id
            
            return create_a2a_message("assistant", decision, decision.context_id, message.get("taskId"))
        except Exception as e:
            self.logger.error(f"Error: {e}", exc_info=True)
            return create_a2a_message("assistant", {"error": str(e)}, message.get("contextId", "unknown"))
    
    def _analyze_mock(self, text: str) -> tuple:
        """Phase 1: Keyword-based sentiment. Phase 2: Real ML model."""
        text_lower = text.lower()
        if any(w in text_lower for w in ["angry", "terrible", "worst", "unacceptable"]):
            return Sentiment.VERY_NEGATIVE, 0.9
        elif any(w in text_lower for w in ["problem", "issue", "not working"]):
            return Sentiment.NEGATIVE, 0.7
        elif any(w in text_lower for w in ["thanks", "great", "love"]):
            return Sentiment.POSITIVE, 0.3
        return Sentiment.NEUTRAL, 0.5
    
    async def _create_zendesk_ticket_mock(self, message: str) -> int:
        """Create Zendesk ticket via mock API."""
        try:
            zendesk_url = self.config["zendesk_url"]
            response = await self.http_client.post(
                f"{zendesk_url}/api/v2/tickets.json",
                json={"subject": "Escalated Customer Issue", "description": message,
                      "priority": "high", "type": "problem", "requester_id": 5001}
            )
            if response.status_code == 200:
                ticket = response.json().get("ticket", {})
                self.logger.info(f"Created Zendesk ticket: {ticket.get('id')}")
                return ticket.get("id", 9999)
        except Exception as e:
            self.logger.error(f"Zendesk ticket creation failed: {e}")
        return 9999  # Mock ticket ID
    
    def cleanup(self):
        self.logger.info("Cleaning up...")
        asyncio.create_task(self.http_client.aclose())
        shutdown_factory()
    
    async def run_demo_mode(self):
        self.logger.info("DEMO MODE")
        samples = [{"contextId": "demo-001", "parts": [{"type": "text", "content": {"customer_message": "This is terrible! I'm very angry!"}}]}]
        for msg in samples:
            result = await self.handle_message(msg)
            self.logger.info(f"Result: {extract_message_content(result)}")
            await asyncio.sleep(2)
        while True: await asyncio.sleep(30)

async def main():
    agent = EscalationAgent()
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
