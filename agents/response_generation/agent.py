"""
Response Generation Agent
Generates customer-facing responses based on intent and knowledge context

Phase 1: Canned template responses
Phase 2: LLM-powered response generation (Azure OpenAI, etc.)
"""

import sys, asyncio
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from shared import get_factory, shutdown_factory, setup_logging, load_config, handle_graceful_shutdown
from shared.models import (ResponseRequest, GeneratedResponse, Intent, Sentiment, create_a2a_message,
                           extract_message_content, generate_message_id)

class ResponseGenerationAgent:
    """Generates customer responses using templates (Phase 1) or LLM (Phase 2+)."""
    
    def __init__(self):
        self.config = load_config()
        self.agent_topic = self.config["agent_topic"]
        self.logger = setup_logging(self.agent_topic, self.config["log_level"])
        self.logger.info(f"Initializing Response Generation Agent: {self.agent_topic}")
        self.factory = get_factory()
        self.transport, self.client, self.container = None, None, None
        self.responses_generated = 0
    
    async def initialize(self):
        self.logger.info("Creating SLIM transport and A2A client...")
        try:
            self.transport = self.factory.create_slim_transport(f"{self.agent_topic}-transport")
            if self.transport:
                self.client = self.factory.create_a2a_client(self.agent_topic, self.transport)
                self.logger.info("Agent initialized successfully")
        except Exception as e:
            self.logger.error(f"Initialization failed: {e}", exc_info=True)
    
    async def handle_message(self, message: dict) -> dict:
        self.responses_generated += 1
        try:
            content = extract_message_content(message)
            request = ResponseRequest(
                request_id=content.get("request_id", generate_message_id()),
                context_id=message.get("contextId", "unknown"),
                customer_message=content.get("customer_message", ""),
                intent=Intent(content.get("intent", "general_inquiry")),
                knowledge_context=content.get("knowledge_context", []),
                sentiment=Sentiment(content.get("sentiment", "neutral")) if content.get("sentiment") else None
            )
            
            self.logger.info(f"Generating response for intent: {request.intent.value}")
            response_text = self._generate_canned_response(request)
            
            result = GeneratedResponse(
                request_id=request.request_id,
                context_id=request.context_id,
                response_text=response_text,
                confidence=0.75,
                requires_escalation=request.sentiment == Sentiment.VERY_NEGATIVE if request.sentiment else False
            )
            
            return create_a2a_message("assistant", result, request.context_id, message.get("taskId"),
                                     {"agent": self.agent_topic, "responses_generated": self.responses_generated})
        except Exception as e:
            self.logger.error(f"Error generating response: {e}", exc_info=True)
            return create_a2a_message("assistant", {"error": str(e)}, message.get("contextId", "unknown"))
    
    def _generate_canned_response(self, request: ResponseRequest) -> str:
        """Phase 1: Template-based responses. Phase 2: Replace with LLM."""
        templates = {
            Intent.ORDER_STATUS: "Thank you for contacting us about your order. Let me check the status for you.",
            Intent.PRODUCT_INQUIRY: "I'd be happy to help you learn more about our products.",
            Intent.RETURN_REQUEST: "I can assist you with your return. We accept returns within 30 days.",
            Intent.SHIPPING_QUESTION: "Our standard shipping takes 5-7 business days. Express options are available.",
            Intent.PAYMENT_ISSUE: "I understand you're having a payment issue. Let me help resolve this for you.",
            Intent.ACCOUNT_SUPPORT: "I can help you with your account. What specifically do you need assistance with?",
            Intent.COMPLAINT: "I sincerely apologize for the inconvenience. Let me see how I can make this right.",
        }
        return templates.get(request.intent, "Thank you for contacting us. How can I assist you today?")
    
    def cleanup(self):
        self.logger.info("Cleaning up Response Generation Agent...")
        shutdown_factory()
    
    async def run_demo_mode(self):
        self.logger.info("Running in DEMO MODE")
        samples = [{"contextId": "demo-001", "parts": [{"type": "text", "content": {"customer_message": "Where is my order?", "intent": "order_status"}}]}]
        for msg in samples:
            result = await self.handle_message(msg)
            self.logger.info(f"Demo Result: {extract_message_content(result)}")
            await asyncio.sleep(2)
        while True: await asyncio.sleep(30)

async def main():
    agent = ResponseGenerationAgent()
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
