"""
Locust Load Testing Script for Phase 3 Week 2 (Days 8-9)

This script simulates realistic customer service user scenarios to test system
performance under load and identify breaking points.

User Scenarios:
1. Order Status Check - Most common scenario (50% of traffic)
2. Product Information Inquiry - Second most common (25%)
3. Return Request - Medium frequency (15%)
4. Account Support - Lower frequency (10%)

Test Objectives:
- Measure system throughput under increasing load (10, 50, 100 concurrent users)
- Identify performance degradation patterns
- Monitor resource utilization (CPU, memory)
- Determine breaking point (max concurrent users before failure)
- Validate graceful degradation (no crashes, errors handled)

Educational Notes:
- Phase 3 testing uses mock agents (local, fast response times)
- Phase 4 will have dramatically different performance (LLM API calls)
- Focus on relative performance, not absolute response times
- Baseline established here will help capacity planning for Phase 4
"""

import asyncio
import sys
import time
from pathlib import Path
from locust import HttpUser, task, between, events
from locust.env import Environment
from locust.stats import stats_printer, stats_history
import gevent

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from shared.models import (
    CustomerMessage,
    Intent,
    Language,
    generate_message_id,
    generate_context_id,
    create_a2a_message,
)

# =============================================================================
# Custom Locust User: Multi-Agent Customer Service User
# =============================================================================


class CustomerServiceUser(HttpUser):
    """
    Simulates a customer interacting with the multi-agent customer service system.

    This user simulates realistic scenarios with weighted task distribution
    matching expected production traffic patterns.
    """

    # Wait time between requests (1-3 seconds simulates realistic user behavior)
    wait_time = between(1, 3)

    # Base URL will be set when running Locust (e.g., http://localhost:8080)
    # For Phase 3, we'll test agents directly via async calls
    # host = "http://localhost:8080"  # Commented - using direct agent calls

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Initialize agents on user spawn
        self._init_agents()

    def _init_agents(self):
        """Initialize agent instances for direct testing."""
        try:
            from agents.intent_classification.agent import IntentClassificationAgent
            from agents.knowledge_retrieval.agent import KnowledgeRetrievalAgent
            from agents.response_generation.agent import ResponseGenerationAgent

            self.agents = {
                "intent": IntentClassificationAgent(),
                "knowledge": KnowledgeRetrievalAgent(),
                "response": ResponseGenerationAgent(),
            }
        except Exception as e:
            print(f"Warning: Could not initialize agents: {e}")
            self.agents = None

    def on_start(self):
        """
        Called when a simulated user starts.
        Used to simulate login or initialization actions.
        """
        self.customer_id = f"load-test-user-{self.user_id}"
        self.session_context_id = generate_context_id()

    @task(50)  # 50% of traffic - most common scenario
    def check_order_status(self):
        """
        Scenario 1: Customer checks order status.

        Simulates: "Where is my order #10234?"
        Expected: Intent classification → ORDER_STATUS
        Weight: 50% (most common customer inquiry)
        """
        start_time = time.time()

        try:
            # Create customer message
            customer_msg = CustomerMessage(
                message_id=generate_message_id(),
                customer_id=self.customer_id,
                context_id=generate_context_id(),  # New context per request
                content=f"Where is my order #{10000 + (self.user_id % 1000)}?",
                channel="chat",
                language=Language.EN,
            )

            # Process through intent agent
            if self.agents:
                a2a_msg = create_a2a_message(
                    role="user",
                    content=customer_msg.to_dict(),
                    context_id=customer_msg.context_id,
                )

                # Use gevent-compatible async execution
                result = self._run_async(self.agents["intent"].handle_message(a2a_msg))

                # Record success
                total_time = int((time.time() - start_time) * 1000)
                events.request.fire(
                    request_type="agent",
                    name="order_status_check",
                    response_time=total_time,
                    response_length=len(str(result)),
                    exception=None,
                    context={},
                )
            else:
                raise Exception("Agents not initialized")

        except Exception as e:
            total_time = int((time.time() - start_time) * 1000)
            events.request.fire(
                request_type="agent",
                name="order_status_check",
                response_time=total_time,
                response_length=0,
                exception=e,
                context={},
            )

    @task(25)  # 25% of traffic
    def product_information_inquiry(self):
        """
        Scenario 2: Customer asks about product information.

        Simulates: "Tell me about the Colombian Dark Roast"
        Expected: Intent classification → PRODUCT_INFO
        Weight: 25% (second most common)
        """
        start_time = time.time()

        try:
            products = [
                "Colombian Dark Roast",
                "Espresso Blend",
                "French Roast",
                "Light Breakfast Blend",
                "Decaf House Blend",
            ]

            product = products[self.user_id % len(products)]

            customer_msg = CustomerMessage(
                message_id=generate_message_id(),
                customer_id=self.customer_id,
                context_id=generate_context_id(),
                content=f"Tell me about the {product}",
                channel="chat",
                language=Language.EN,
            )

            if self.agents:
                a2a_msg = create_a2a_message(
                    role="user",
                    content=customer_msg.to_dict(),
                    context_id=customer_msg.context_id,
                )

                result = self._run_async(self.agents["intent"].handle_message(a2a_msg))

                total_time = int((time.time() - start_time) * 1000)
                events.request.fire(
                    request_type="agent",
                    name="product_info_inquiry",
                    response_time=total_time,
                    response_length=len(str(result)),
                    exception=None,
                    context={},
                )
            else:
                raise Exception("Agents not initialized")

        except Exception as e:
            total_time = int((time.time() - start_time) * 1000)
            events.request.fire(
                request_type="agent",
                name="product_info_inquiry",
                response_time=total_time,
                response_length=0,
                exception=e,
                context={},
            )

    @task(15)  # 15% of traffic
    def return_request(self):
        """
        Scenario 3: Customer wants to return a product.

        Simulates: "I want to return my grinder"
        Expected: Intent classification → RETURN_REQUEST
        Weight: 15% (medium frequency)
        """
        start_time = time.time()

        try:
            customer_msg = CustomerMessage(
                message_id=generate_message_id(),
                customer_id=self.customer_id,
                context_id=generate_context_id(),
                content="I want to return the product I ordered",
                channel="chat",
                language=Language.EN,
            )

            if self.agents:
                a2a_msg = create_a2a_message(
                    role="user",
                    content=customer_msg.to_dict(),
                    context_id=customer_msg.context_id,
                )

                result = self._run_async(self.agents["intent"].handle_message(a2a_msg))

                total_time = int((time.time() - start_time) * 1000)
                events.request.fire(
                    request_type="agent",
                    name="return_request",
                    response_time=total_time,
                    response_length=len(str(result)),
                    exception=None,
                    context={},
                )
            else:
                raise Exception("Agents not initialized")

        except Exception as e:
            total_time = int((time.time() - start_time) * 1000)
            events.request.fire(
                request_type="agent",
                name="return_request",
                response_time=total_time,
                response_length=0,
                exception=e,
                context={},
            )

    @task(10)  # 10% of traffic
    def account_support(self):
        """
        Scenario 4: Customer needs account help.

        Simulates: "I forgot my password"
        Expected: Intent classification → ACCOUNT_SUPPORT
        Weight: 10% (lower frequency)
        """
        start_time = time.time()

        try:
            account_queries = [
                "I forgot my password",
                "How do I update my email?",
                "Can't log into my account",
                "Need to change my address",
            ]

            query = account_queries[self.user_id % len(account_queries)]

            customer_msg = CustomerMessage(
                message_id=generate_message_id(),
                customer_id=self.customer_id,
                context_id=generate_context_id(),
                content=query,
                channel="chat",
                language=Language.EN,
            )

            if self.agents:
                a2a_msg = create_a2a_message(
                    role="user",
                    content=customer_msg.to_dict(),
                    context_id=customer_msg.context_id,
                )

                result = self._run_async(self.agents["intent"].handle_message(a2a_msg))

                total_time = int((time.time() - start_time) * 1000)
                events.request.fire(
                    request_type="agent",
                    name="account_support",
                    response_time=total_time,
                    response_length=len(str(result)),
                    exception=None,
                    context={},
                )
            else:
                raise Exception("Agents not initialized")

        except Exception as e:
            total_time = int((time.time() - start_time) * 1000)
            events.request.fire(
                request_type="agent",
                name="account_support",
                response_time=total_time,
                response_length=0,
                exception=e,
                context={},
            )

    def _run_async(self, coroutine):
        """
        Run async coroutine in gevent context.

        Locust uses gevent for concurrency, so we need to bridge
        asyncio coroutines to gevent greenlets.
        """
        # Create new event loop for this greenlet
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(coroutine)
        finally:
            loop.close()


# =============================================================================
# Custom Events for Resource Monitoring
# =============================================================================


@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    """Called when load test starts."""
    print("\n" + "=" * 70)
    print("LOAD TEST STARTING")
    print("=" * 70)
    print(
        f"Target users: {environment.parsed_options.num_users if hasattr(environment, 'parsed_options') else 'N/A'}"
    )
    print(
        f"Spawn rate: {environment.parsed_options.spawn_rate if hasattr(environment, 'parsed_options') else 'N/A'}"
    )
    print(
        f"Duration: {environment.parsed_options.run_time if hasattr(environment, 'parsed_options') else 'N/A'}"
    )
    print("=" * 70 + "\n")


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """Called when load test stops."""
    print("\n" + "=" * 70)
    print("LOAD TEST COMPLETE")
    print("=" * 70)
    print(f"Total requests: {environment.stats.total.num_requests}")
    print(f"Total failures: {environment.stats.total.num_failures}")
    print(f"Failure rate: {environment.stats.total.fail_ratio * 100:.2f}%")
    print(f"Average response time: {environment.stats.total.avg_response_time:.2f}ms")
    print(f"Median response time: {environment.stats.total.median_response_time:.2f}ms")
    print(
        f"95th percentile: {environment.stats.total.get_response_time_percentile(0.95):.2f}ms"
    )
    print(
        f"99th percentile: {environment.stats.total.get_response_time_percentile(0.99):.2f}ms"
    )
    print(f"Requests per second: {environment.stats.total.total_rps:.2f}")
    print("=" * 70 + "\n")


@events.request.add_listener
def on_request(request_type, name, response_time, response_length, exception, **kwargs):
    """Called for each request (for debugging)."""
    if exception:
        print(f"❌ FAILED: {name} - {exception}")


# =============================================================================
# Standalone Test Runner (for programmatic execution)
# =============================================================================


def run_load_test(users=10, spawn_rate=1, duration=60):
    """
    Run load test programmatically (alternative to `locust` CLI).

    Args:
        users: Number of concurrent users to simulate
        spawn_rate: Users to spawn per second
        duration: Test duration in seconds

    Returns:
        Dictionary with test results
    """
    from locust import runners
    from locust.stats import StatsEntry

    print(
        f"\nStarting load test: {users} users, {spawn_rate} spawn/s, {duration}s duration"
    )

    # Create environment
    env = Environment(user_classes=[CustomerServiceUser])

    # Create runner
    runner = env.create_local_runner()

    # Start test
    runner.start(users, spawn_rate=spawn_rate)

    # Run for specified duration
    gevent.spawn(lambda: runner.quit())
    time.sleep(duration)

    # Stop test
    runner.stop()

    # Collect results
    stats = env.stats.total

    results = {
        "users": users,
        "duration": duration,
        "total_requests": stats.num_requests,
        "total_failures": stats.num_failures,
        "failure_rate": stats.fail_ratio,
        "avg_response_time": stats.avg_response_time,
        "median_response_time": stats.median_response_time,
        "p95_response_time": stats.get_response_time_percentile(0.95),
        "p99_response_time": stats.get_response_time_percentile(0.99),
        "requests_per_second": stats.total_rps,
    }

    return results


# =============================================================================
# Main Entry Point
# =============================================================================

if __name__ == "__main__":
    """
    Run load tests programmatically with different user counts.

    Usage:
        python locustfile.py

    Or use Locust CLI:
        locust -f locustfile.py --headless --users 10 --spawn-rate 1 --run-time 60s
    """

    print("\n" + "=" * 70)
    print("MULTI-AGENT CUSTOMER SERVICE - LOAD TEST SUITE")
    print("Phase 3, Week 2, Days 8-9")
    print("=" * 70 + "\n")

    # Test configurations
    test_configs = [
        {"users": 10, "spawn_rate": 2, "duration": 30},  # Light load
        {"users": 50, "spawn_rate": 5, "duration": 30},  # Medium load
        {"users": 100, "spawn_rate": 10, "duration": 30},  # Heavy load
    ]

    all_results = []

    for config in test_configs:
        print(f"\n{'='*70}")
        print(f"TEST {len(all_results) + 1}: {config['users']} concurrent users")
        print(f"{'='*70}")

        results = run_load_test(**config)
        all_results.append(results)

        print(f"\nRESULTS:")
        print(f"  Total Requests: {results['total_requests']}")
        print(
            f"  Failures: {results['total_failures']} ({results['failure_rate']*100:.2f}%)"
        )
        print(f"  Avg Response Time: {results['avg_response_time']:.2f}ms")
        print(f"  P95 Response Time: {results['p95_response_time']:.2f}ms")
        print(f"  Throughput: {results['requests_per_second']:.2f} req/s")

        time.sleep(5)  # Pause between tests

    # Print summary
    print(f"\n\n{'='*70}")
    print("LOAD TEST SUMMARY - ALL CONFIGURATIONS")
    print(f"{'='*70}\n")
    print(
        f"{'Users':<10} {'Requests':<12} {'Failures':<12} {'Avg (ms)':<12} {'P95 (ms)':<12} {'RPS':<10}"
    )
    print("-" * 70)

    for results in all_results:
        print(
            f"{results['users']:<10} "
            f"{results['total_requests']:<12} "
            f"{results['total_failures']:<12} "
            f"{results['avg_response_time']:<12.2f} "
            f"{results['p95_response_time']:<12.2f} "
            f"{results['requests_per_second']:<10.2f}"
        )

    print("\n" + "=" * 70)
    print("Load testing complete!")
    print("=" * 70 + "\n")
