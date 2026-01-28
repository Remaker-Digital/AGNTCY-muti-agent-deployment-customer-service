"""
Pure Python Load Testing Script for Phase 3 Week 2 (Days 8-9)

This script simulates concurrent users without requiring HTTP endpoints.
Tests agents directly via async calls with concurrent execution.

Test Objectives:
- Measure system throughput under increasing load (10, 50, 100 concurrent users)
- Identify performance degradation patterns
- Monitor resource utilization (CPU, memory)
- Determine breaking point (max concurrent users before failure)
"""

import asyncio
import sys
import time
import statistics
from pathlib import Path
from typing import List, Dict
from dataclasses import dataclass, field
from datetime import datetime
import psutil  # For resource monitoring

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
# Test Result Data Classes
# =============================================================================


@dataclass
class LoadTestResult:
    """Container for load test results."""

    concurrent_users: int
    total_requests: int
    successful_requests: int
    failed_requests: int
    total_duration: float  # seconds
    response_times: List[float]  # milliseconds
    cpu_usage_avg: float  # percentage
    memory_usage_avg: float  # MB
    timestamp: datetime = field(default_factory=datetime.utcnow)

    @property
    def success_rate(self) -> float:
        """Calculate success rate percentage."""
        if self.total_requests == 0:
            return 0.0
        return (self.successful_requests / self.total_requests) * 100

    @property
    def failure_rate(self) -> float:
        """Calculate failure rate percentage."""
        return 100.0 - self.success_rate

    @property
    def throughput(self) -> float:
        """Calculate requests per second."""
        if self.total_duration == 0:
            return 0.0
        return self.total_requests / self.total_duration

    @property
    def p50(self) -> float:
        """Median response time."""
        return statistics.median(self.response_times) if self.response_times else 0.0

    @property
    def p95(self) -> float:
        """95th percentile response time."""
        if not self.response_times:
            return 0.0
        sorted_times = sorted(self.response_times)
        index = int(len(sorted_times) * 0.95)
        return sorted_times[index]

    @property
    def p99(self) -> float:
        """99th percentile response time."""
        if not self.response_times:
            return 0.0
        sorted_times = sorted(self.response_times)
        index = int(len(sorted_times) * 0.99)
        return sorted_times[index]

    @property
    def avg(self) -> float:
        """Average response time."""
        return statistics.mean(self.response_times) if self.response_times else 0.0


# =============================================================================
# Load Test Runner
# =============================================================================


class LoadTestRunner:
    """Manages concurrent load testing of agents."""

    def __init__(self):
        """Initialize load test runner."""
        self.agents = None
        self._init_agents()

    def _init_agents(self):
        """Initialize agent instances."""
        try:
            from agents.intent_classification.agent import IntentClassificationAgent
            from agents.knowledge_retrieval.agent import KnowledgeRetrievalAgent
            from agents.response_generation.agent import ResponseGenerationAgent

            self.agents = {
                "intent": IntentClassificationAgent(),
                "knowledge": KnowledgeRetrievalAgent(),
                "response": ResponseGenerationAgent(),
            }
            print("Agents initialized successfully")
        except Exception as e:
            print(f"Error initializing agents: {e}")
            self.agents = None

    async def simulate_user_request(self, user_id: int, scenario: str) -> Dict:
        """
        Simulate a single user request.

        Args:
            user_id: Unique user identifier
            scenario: Scenario name (order_status, product_info, return_request, account_support)

        Returns:
            Dictionary with request results
        """
        start_time = time.perf_counter()

        try:
            # Generate scenario-specific message
            message_content = self._get_scenario_message(scenario, user_id)

            customer_msg = CustomerMessage(
                message_id=generate_message_id(),
                customer_id=f"load-test-user-{user_id}",
                context_id=generate_context_id(),
                content=message_content,
                channel="chat",
                language=Language.EN,
            )

            # Process through intent agent
            a2a_msg = create_a2a_message(
                role="user",
                content=customer_msg.to_dict(),
                context_id=customer_msg.context_id,
            )

            result = await self.agents["intent"].handle_message(a2a_msg)

            end_time = time.perf_counter()
            response_time = (end_time - start_time) * 1000  # Convert to ms

            return {"success": True, "response_time": response_time, "error": None}

        except Exception as e:
            end_time = time.perf_counter()
            response_time = (end_time - start_time) * 1000

            return {"success": False, "response_time": response_time, "error": str(e)}

    def _get_scenario_message(self, scenario: str, user_id: int) -> str:
        """Get message content for given scenario."""
        scenarios = {
            "order_status": f"Where is my order #{10000 + (user_id % 1000)}?",
            "product_info": "Tell me about the Colombian Dark Roast",
            "return_request": "I want to return the product I ordered",
            "account_support": "I forgot my password",
        }
        return scenarios.get(scenario, "General inquiry")

    async def run_concurrent_users(
        self,
        num_users: int,
        requests_per_user: int = 5,
        scenario_distribution: Dict[str, float] = None,
    ) -> LoadTestResult:
        """
        Run load test with specified number of concurrent users.

        Args:
            num_users: Number of concurrent users
            requests_per_user: Number of requests each user will make
            scenario_distribution: Distribution of scenarios (default weighted)

        Returns:
            LoadTestResult with performance metrics
        """
        if scenario_distribution is None:
            scenario_distribution = {
                "order_status": 0.50,  # 50%
                "product_info": 0.25,  # 25%
                "return_request": 0.15,  # 15%
                "account_support": 0.10,  # 10%
            }

        print(
            f"\nStarting load test: {num_users} concurrent users, {requests_per_user} req/user"
        )
        print(f"Total requests: {num_users * requests_per_user}")

        # Start monitoring resources
        process = psutil.Process()
        cpu_samples = []
        memory_samples = []

        # Create tasks for all users
        tasks = []
        for user_id in range(num_users):
            for req_num in range(requests_per_user):
                # Select scenario based on distribution
                scenario = self._select_scenario(
                    scenario_distribution, user_id, req_num
                )
                task = self.simulate_user_request(user_id, scenario)
                tasks.append(task)

        # Execute all requests concurrently
        start_time = time.perf_counter()

        # Sample resource usage during execution
        async def monitor_resources():
            """Sample CPU and memory usage during test."""
            while True:
                cpu_samples.append(process.cpu_percent(interval=0.1))
                memory_samples.append(process.memory_info().rss / 1024 / 1024)  # MB
                await asyncio.sleep(0.5)

        # Start monitoring
        monitor_task = asyncio.create_task(monitor_resources())

        # Execute all requests
        try:
            results = await asyncio.gather(*tasks, return_exceptions=True)
        finally:
            monitor_task.cancel()
            try:
                await monitor_task
            except asyncio.CancelledError:
                pass

        end_time = time.perf_counter()
        total_duration = end_time - start_time

        # Process results
        successful = 0
        failed = 0
        response_times = []

        for result in results:
            if isinstance(result, Exception):
                failed += 1
            elif result.get("success"):
                successful += 1
                response_times.append(result["response_time"])
            else:
                failed += 1
                response_times.append(result["response_time"])

        # Calculate resource averages
        cpu_avg = statistics.mean(cpu_samples) if cpu_samples else 0.0
        memory_avg = statistics.mean(memory_samples) if memory_samples else 0.0

        return LoadTestResult(
            concurrent_users=num_users,
            total_requests=len(tasks),
            successful_requests=successful,
            failed_requests=failed,
            total_duration=total_duration,
            response_times=response_times,
            cpu_usage_avg=cpu_avg,
            memory_usage_avg=memory_avg,
        )

    def _select_scenario(
        self, distribution: Dict[str, float], user_id: int, req_num: int
    ) -> str:
        """Select scenario based on distribution weights."""
        # Simple deterministic selection based on user_id and req_num
        scenarios = list(distribution.keys())
        index = (user_id + req_num) % len(scenarios)
        return scenarios[index]


# =============================================================================
# Main Test Execution
# =============================================================================


async def run_load_tests():
    """Execute load tests with different user counts."""
    print("\n" + "=" * 70)
    print("MULTI-AGENT CUSTOMER SERVICE - LOAD TEST SUITE")
    print("Phase 3, Week 2, Days 8-9")
    print("=" * 70 + "\n")

    runner = LoadTestRunner()

    if not runner.agents:
        print("ERROR: Could not initialize agents. Exiting.")
        return []

    # Test configurations
    test_configs = [
        {"num_users": 10, "requests_per_user": 5},  # Light load (50 total requests)
        {"num_users": 50, "requests_per_user": 5},  # Medium load (250 total requests)
        {"num_users": 100, "requests_per_user": 5},  # Heavy load (500 total requests)
    ]

    all_results = []

    for i, config in enumerate(test_configs, 1):
        print(f"\n{'='*70}")
        print(f"TEST {i}/{len(test_configs)}: {config['num_users']} concurrent users")
        print(f"{'='*70}")

        result = await runner.run_concurrent_users(**config)
        all_results.append(result)

        # Print results
        print(f"\nRESULTS:")
        print(f"  Total Requests:      {result.total_requests}")
        print(
            f"  Successful:          {result.successful_requests} ({result.success_rate:.2f}%)"
        )
        print(
            f"  Failed:              {result.failed_requests} ({result.failure_rate:.2f}%)"
        )
        print(f"  Duration:            {result.total_duration:.2f}s")
        print(f"  Throughput:          {result.throughput:.2f} req/s")
        print(f"  Avg Response Time:   {result.avg:.2f}ms")
        print(f"  P50 Response Time:   {result.p50:.2f}ms")
        print(f"  P95 Response Time:   {result.p95:.2f}ms")
        print(f"  P99 Response Time:   {result.p99:.2f}ms")
        print(f"  CPU Usage (avg):     {result.cpu_usage_avg:.2f}%")
        print(f"  Memory Usage (avg):  {result.memory_usage_avg:.2f}MB")

        # Pause between tests
        if i < len(test_configs):
            print("\nPausing 5 seconds before next test...")
            await asyncio.sleep(5)

    # Print summary
    print(f"\n\n{'='*70}")
    print("LOAD TEST SUMMARY - ALL CONFIGURATIONS")
    print(f"{'='*70}\n")
    print(
        f"{'Users':<8} {'Requests':<10} {'Success%':<10} {'Avg(ms)':<10} {'P95(ms)':<10} {'RPS':<10} {'CPU%':<8} {'Mem(MB)':<10}"
    )
    print("-" * 88)

    for result in all_results:
        print(
            f"{result.concurrent_users:<8} "
            f"{result.total_requests:<10} "
            f"{result.success_rate:<10.2f} "
            f"{result.avg:<10.2f} "
            f"{result.p95:<10.2f} "
            f"{result.throughput:<10.2f} "
            f"{result.cpu_usage_avg:<8.2f} "
            f"{result.memory_usage_avg:<10.2f}"
        )

    print("\n" + "=" * 70)
    print("Load testing complete!")
    print("=" * 70 + "\n")

    return all_results


if __name__ == "__main__":
    """Run load tests."""
    results = asyncio.run(run_load_tests())
