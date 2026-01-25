"""
Stress Testing Script for Phase 3 Week 2 (Day 10)

This script tests the system under extreme load conditions to validate:
1. Breaking point identification (max concurrent users before failure)
2. Graceful degradation (system behavior under excessive load)
3. Error handling under stress (no crashes, appropriate errors)
4. Recovery after failures (system can recover from overload)
5. Resource exhaustion scenarios (memory, CPU limits)

Test Scenarios:
1. Extreme Concurrency (500-1000 users) - Find breaking point
2. Rapid Spike Load - Sudden traffic increase
3. Sustained Overload - Long-duration extreme load
4. Error Injection - Simulate agent failures
5. Resource Monitoring - Track system limits

Educational Notes:
- Phase 3 testing validates agent logic resilience
- Phase 4 will have different stress characteristics (API rate limits)
- Focus on graceful degradation, not absolute breaking point
- Validate error handling, not just happy path
"""

import asyncio
import sys
import time
import statistics
from pathlib import Path
from typing import List, Dict, Optional
from dataclasses import dataclass, field
from datetime import datetime
import psutil
import random

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from shared.models import (
    CustomerMessage,
    Intent,
    Language,
    generate_message_id,
    generate_context_id,
    create_a2a_message
)


# =============================================================================
# Stress Test Result Data Classes
# =============================================================================

@dataclass
class StressTestResult:
    """Container for stress test results."""
    test_name: str
    concurrent_users: int
    total_requests: int
    successful_requests: int
    failed_requests: int
    total_duration: float  # seconds
    response_times: List[float]  # milliseconds
    cpu_usage_samples: List[float]  # percentage
    memory_usage_samples: List[float]  # MB
    errors: List[str]  # Error messages
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
        return sorted_times[index] if index < len(sorted_times) else sorted_times[-1]

    @property
    def p99(self) -> float:
        """99th percentile response time."""
        if not self.response_times:
            return 0.0
        sorted_times = sorted(self.response_times)
        index = int(len(sorted_times) * 0.99)
        return sorted_times[index] if index < len(sorted_times) else sorted_times[-1]

    @property
    def avg(self) -> float:
        """Average response time."""
        return statistics.mean(self.response_times) if self.response_times else 0.0

    @property
    def cpu_avg(self) -> float:
        """Average CPU usage."""
        return statistics.mean(self.cpu_usage_samples) if self.cpu_usage_samples else 0.0

    @property
    def cpu_max(self) -> float:
        """Peak CPU usage."""
        return max(self.cpu_usage_samples) if self.cpu_usage_samples else 0.0

    @property
    def memory_avg(self) -> float:
        """Average memory usage."""
        return statistics.mean(self.memory_usage_samples) if self.memory_usage_samples else 0.0

    @property
    def memory_max(self) -> float:
        """Peak memory usage."""
        return max(self.memory_usage_samples) if self.memory_usage_samples else 0.0


# =============================================================================
# Stress Test Runner
# =============================================================================

class StressTestRunner:
    """Manages stress testing with extreme load and failure scenarios."""

    def __init__(self):
        """Initialize stress test runner."""
        self.agents = None
        self.process = psutil.Process()
        self._init_agents()

    def _init_agents(self):
        """Initialize agent instances."""
        try:
            from agents.intent_classification.agent import IntentClassificationAgent
            from agents.knowledge_retrieval.agent import KnowledgeRetrievalAgent
            from agents.response_generation.agent import ResponseGenerationAgent

            self.agents = {
                'intent': IntentClassificationAgent(),
                'knowledge': KnowledgeRetrievalAgent(),
                'response': ResponseGenerationAgent(),
            }
            print("Agents initialized successfully")
        except Exception as e:
            print(f"Error initializing agents: {e}")
            self.agents = None

    async def simulate_user_request(
        self,
        user_id: int,
        inject_error: bool = False
    ) -> Dict:
        """
        Simulate a single user request.

        Args:
            user_id: Unique user identifier
            inject_error: Whether to inject an error (for failure testing)

        Returns:
            Dictionary with request results
        """
        start_time = time.perf_counter()

        try:
            # Inject error if requested (for failure testing)
            if inject_error:
                raise Exception("Simulated error for stress testing")

            customer_msg = CustomerMessage(
                message_id=generate_message_id(),
                customer_id=f"stress-test-user-{user_id}",
                context_id=generate_context_id(),
                content=f"Where is my order #{10000 + (user_id % 1000)}?",
                channel="chat",
                language=Language.EN
            )

            a2a_msg = create_a2a_message(
                role="user",
                content=customer_msg.to_dict(),
                context_id=customer_msg.context_id
            )

            result = await self.agents['intent'].handle_message(a2a_msg)

            end_time = time.perf_counter()
            response_time = (end_time - start_time) * 1000

            return {
                "success": True,
                "response_time": response_time,
                "error": None
            }

        except Exception as e:
            end_time = time.perf_counter()
            response_time = (end_time - start_time) * 1000

            return {
                "success": False,
                "response_time": response_time,
                "error": str(e)
            }

    async def monitor_resources(self, results_container: Dict, interval: float = 0.5):
        """
        Monitor system resources during test.

        Args:
            results_container: Dictionary to store results
            interval: Sampling interval in seconds
        """
        while True:
            try:
                cpu = self.process.cpu_percent(interval=0.1)
                memory = self.process.memory_info().rss / 1024 / 1024  # MB
                results_container["cpu_samples"].append(cpu)
                results_container["memory_samples"].append(memory)
                await asyncio.sleep(interval)
            except asyncio.CancelledError:
                break

    async def test_extreme_concurrency(self, num_users: int = 500) -> StressTestResult:
        """
        Test 1: Extreme Concurrency - Find breaking point.

        Args:
            num_users: Number of concurrent users (default 500)

        Returns:
            StressTestResult with performance metrics
        """
        print(f"\n{'='*70}")
        print(f"STRESS TEST 1: Extreme Concurrency ({num_users} users)")
        print(f"{'='*70}")
        print(f"Objective: Find system breaking point with extreme concurrent load")
        print(f"Expected: Some failures may occur at this scale")

        resources = {"cpu_samples": [], "memory_samples": []}
        errors = []

        # Create tasks
        tasks = []
        for user_id in range(num_users):
            task = self.simulate_user_request(user_id)
            tasks.append(task)

        # Start monitoring
        monitor_task = asyncio.create_task(
            self.monitor_resources(resources)
        )

        # Execute
        start_time = time.perf_counter()

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
                errors.append(str(result))
            elif result.get("success"):
                successful += 1
                response_times.append(result["response_time"])
            else:
                failed += 1
                if result.get("error"):
                    errors.append(result["error"])
                response_times.append(result["response_time"])

        return StressTestResult(
            test_name="Extreme Concurrency",
            concurrent_users=num_users,
            total_requests=len(tasks),
            successful_requests=successful,
            failed_requests=failed,
            total_duration=total_duration,
            response_times=response_times,
            cpu_usage_samples=resources["cpu_samples"],
            memory_usage_samples=resources["memory_samples"],
            errors=errors[:10]  # Keep first 10 errors
        )

    async def test_rapid_spike_load(self) -> StressTestResult:
        """
        Test 2: Rapid Spike Load - Sudden traffic increase.

        Simulates flash traffic (e.g., product launch, marketing campaign).

        Returns:
            StressTestResult with performance metrics
        """
        print(f"\n{'='*70}")
        print(f"STRESS TEST 2: Rapid Spike Load")
        print(f"{'='*70}")
        print(f"Objective: Validate system handles sudden traffic spike")
        print(f"Pattern: 10 -> 100 -> 500 users in rapid succession")

        resources = {"cpu_samples": [], "memory_samples": []}
        errors = []
        all_response_times = []

        monitor_task = asyncio.create_task(
            self.monitor_resources(resources)
        )

        start_time = time.perf_counter()

        try:
            # Phase 1: Normal load (10 users)
            print("  Phase 1: Normal load (10 users)...")
            tasks_1 = [self.simulate_user_request(i) for i in range(10)]
            results_1 = await asyncio.gather(*tasks_1, return_exceptions=True)

            # Phase 2: Spike begins (100 users)
            print("  Phase 2: Traffic spike (100 users)...")
            await asyncio.sleep(0.5)  # Small delay
            tasks_2 = [self.simulate_user_request(i + 10) for i in range(100)]
            results_2 = await asyncio.gather(*tasks_2, return_exceptions=True)

            # Phase 3: Peak spike (500 users)
            print("  Phase 3: Peak traffic (500 users)...")
            await asyncio.sleep(0.5)
            tasks_3 = [self.simulate_user_request(i + 110) for i in range(500)]
            results_3 = await asyncio.gather(*tasks_3, return_exceptions=True)

            all_results = results_1 + results_2 + results_3

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

        for result in all_results:
            if isinstance(result, Exception):
                failed += 1
                errors.append(str(result))
            elif result.get("success"):
                successful += 1
                all_response_times.append(result["response_time"])
            else:
                failed += 1
                if result.get("error"):
                    errors.append(result["error"])
                all_response_times.append(result["response_time"])

        return StressTestResult(
            test_name="Rapid Spike Load",
            concurrent_users=610,  # Total unique users
            total_requests=len(all_results),
            successful_requests=successful,
            failed_requests=failed,
            total_duration=total_duration,
            response_times=all_response_times,
            cpu_usage_samples=resources["cpu_samples"],
            memory_usage_samples=resources["memory_samples"],
            errors=errors[:10]
        )

    async def test_sustained_overload(self, duration: int = 10) -> StressTestResult:
        """
        Test 3: Sustained Overload - Long-duration extreme load.

        Args:
            duration: Test duration in seconds

        Returns:
            StressTestResult with performance metrics
        """
        print(f"\n{'='*70}")
        print(f"STRESS TEST 3: Sustained Overload ({duration}s)")
        print(f"{'='*70}")
        print(f"Objective: Validate system stability under prolonged extreme load")
        print(f"Pattern: Continuous 200 concurrent users for {duration} seconds")

        resources = {"cpu_samples": [], "memory_samples": []}
        errors = []
        all_response_times = []
        total_requests = 0

        monitor_task = asyncio.create_task(
            self.monitor_resources(resources)
        )

        start_time = time.perf_counter()
        successful = 0
        failed = 0

        try:
            # Run continuous load for specified duration
            while (time.perf_counter() - start_time) < duration:
                # Batch of 200 concurrent requests
                tasks = [self.simulate_user_request(i) for i in range(200)]
                results = await asyncio.gather(*tasks, return_exceptions=True)

                for result in results:
                    total_requests += 1
                    if isinstance(result, Exception):
                        failed += 1
                        errors.append(str(result))
                    elif result.get("success"):
                        successful += 1
                        all_response_times.append(result["response_time"])
                    else:
                        failed += 1
                        if result.get("error"):
                            errors.append(result["error"])
                        all_response_times.append(result["response_time"])

                # Small delay between batches
                await asyncio.sleep(0.1)

        finally:
            monitor_task.cancel()
            try:
                await monitor_task
            except asyncio.CancelledError:
                pass

        end_time = time.perf_counter()
        total_duration = end_time - start_time

        return StressTestResult(
            test_name="Sustained Overload",
            concurrent_users=200,
            total_requests=total_requests,
            successful_requests=successful,
            failed_requests=failed,
            total_duration=total_duration,
            response_times=all_response_times,
            cpu_usage_samples=resources["cpu_samples"],
            memory_usage_samples=resources["memory_samples"],
            errors=errors[:10]
        )

    async def test_error_injection(self, error_rate: float = 0.1) -> StressTestResult:
        """
        Test 4: Error Injection - Simulate agent failures.

        Args:
            error_rate: Percentage of requests to inject errors (0.0-1.0)

        Returns:
            StressTestResult with performance metrics
        """
        print(f"\n{'='*70}")
        print(f"STRESS TEST 4: Error Injection ({error_rate*100:.0f}% error rate)")
        print(f"{'='*70}")
        print(f"Objective: Validate graceful error handling under load")
        print(f"Pattern: 100 users with {error_rate*100:.0f}% simulated failures")

        resources = {"cpu_samples": [], "memory_samples": []}
        errors = []
        all_response_times = []

        num_users = 100
        tasks = []

        for user_id in range(num_users):
            # Randomly inject errors based on error_rate
            inject_error = random.random() < error_rate
            task = self.simulate_user_request(user_id, inject_error=inject_error)
            tasks.append(task)

        monitor_task = asyncio.create_task(
            self.monitor_resources(resources)
        )

        start_time = time.perf_counter()

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

        for result in results:
            if isinstance(result, Exception):
                failed += 1
                errors.append(str(result))
            elif result.get("success"):
                successful += 1
                all_response_times.append(result["response_time"])
            else:
                failed += 1
                if result.get("error"):
                    errors.append(result["error"])
                all_response_times.append(result["response_time"])

        return StressTestResult(
            test_name="Error Injection",
            concurrent_users=num_users,
            total_requests=len(tasks),
            successful_requests=successful,
            failed_requests=failed,
            total_duration=total_duration,
            response_times=all_response_times,
            cpu_usage_samples=resources["cpu_samples"],
            memory_usage_samples=resources["memory_samples"],
            errors=errors[:10]
        )

    async def test_resource_limits(self) -> StressTestResult:
        """
        Test 5: Resource Limits - Monitor resource exhaustion.

        Gradually increase load until resource limits are hit.

        Returns:
            StressTestResult with performance metrics
        """
        print(f"\n{'='*70}")
        print(f"STRESS TEST 5: Resource Limits")
        print(f"{'='*70}")
        print(f"Objective: Identify memory/CPU exhaustion point")
        print(f"Pattern: Gradual load increase (100 -> 1000 users)")

        resources = {"cpu_samples": [], "memory_samples": []}
        errors = []
        all_response_times = []
        total_requests = 0
        successful = 0
        failed = 0

        monitor_task = asyncio.create_task(
            self.monitor_resources(resources, interval=0.2)
        )

        start_time = time.perf_counter()

        try:
            # Gradually increase load
            for batch_size in [100, 200, 300, 500, 1000]:
                print(f"  Testing with {batch_size} concurrent users...")

                tasks = [self.simulate_user_request(i) for i in range(batch_size)]
                results = await asyncio.gather(*tasks, return_exceptions=True)

                for result in results:
                    total_requests += 1
                    if isinstance(result, Exception):
                        failed += 1
                        errors.append(str(result))
                    elif result.get("success"):
                        successful += 1
                        all_response_times.append(result["response_time"])
                    else:
                        failed += 1
                        if result.get("error"):
                            errors.append(result["error"])
                        all_response_times.append(result["response_time"])

                # Check if we're hitting resource limits
                current_memory = self.process.memory_info().rss / 1024 / 1024
                if current_memory > 500:  # 500 MB threshold
                    print(f"  WARNING: High memory usage ({current_memory:.2f} MB)")

                await asyncio.sleep(1)  # Brief pause between batches

        finally:
            monitor_task.cancel()
            try:
                await monitor_task
            except asyncio.CancelledError:
                pass

        end_time = time.perf_counter()
        total_duration = end_time - start_time

        return StressTestResult(
            test_name="Resource Limits",
            concurrent_users=1000,  # Max tested
            total_requests=total_requests,
            successful_requests=successful,
            failed_requests=failed,
            total_duration=total_duration,
            response_times=all_response_times,
            cpu_usage_samples=resources["cpu_samples"],
            memory_usage_samples=resources["memory_samples"],
            errors=errors[:10]
        )


# =============================================================================
# Main Test Execution
# =============================================================================

async def run_stress_tests():
    """Execute all stress tests."""
    print("\n" + "="*70)
    print("MULTI-AGENT CUSTOMER SERVICE - STRESS TEST SUITE")
    print("Phase 3, Week 2, Day 10")
    print("="*70 + "\n")

    runner = StressTestRunner()

    if not runner.agents:
        print("ERROR: Could not initialize agents. Exiting.")
        return []

    all_results = []

    # Test 1: Extreme Concurrency
    result_1 = await runner.test_extreme_concurrency(num_users=500)
    all_results.append(result_1)
    print_result(result_1)
    await asyncio.sleep(2)

    # Test 2: Rapid Spike Load
    result_2 = await runner.test_rapid_spike_load()
    all_results.append(result_2)
    print_result(result_2)
    await asyncio.sleep(2)

    # Test 3: Sustained Overload
    result_3 = await runner.test_sustained_overload(duration=10)
    all_results.append(result_3)
    print_result(result_3)
    await asyncio.sleep(2)

    # Test 4: Error Injection
    result_4 = await runner.test_error_injection(error_rate=0.1)
    all_results.append(result_4)
    print_result(result_4)
    await asyncio.sleep(2)

    # Test 5: Resource Limits
    result_5 = await runner.test_resource_limits()
    all_results.append(result_5)
    print_result(result_5)

    # Print summary
    print_summary(all_results)

    return all_results


def print_result(result: StressTestResult):
    """Print individual test result."""
    print(f"\nRESULTS:")
    print(f"  Total Requests:      {result.total_requests}")
    print(f"  Successful:          {result.successful_requests} ({result.success_rate:.2f}%)")
    print(f"  Failed:              {result.failed_requests} ({result.failure_rate:.2f}%)")
    print(f"  Duration:            {result.total_duration:.2f}s")
    print(f"  Throughput:          {result.throughput:.2f} req/s")
    print(f"  Avg Response Time:   {result.avg:.2f}ms")
    print(f"  P95 Response Time:   {result.p95:.2f}ms")
    print(f"  P99 Response Time:   {result.p99:.2f}ms")
    print(f"  Avg CPU Usage:       {result.cpu_avg:.2f}%")
    print(f"  Peak CPU Usage:      {result.cpu_max:.2f}%")
    print(f"  Avg Memory Usage:    {result.memory_avg:.2f}MB")
    print(f"  Peak Memory Usage:   {result.memory_max:.2f}MB")

    if result.errors:
        print(f"\n  First Errors ({len(result.errors)} total):")
        for error in result.errors[:3]:
            print(f"    - {error}")


def print_summary(results: List[StressTestResult]):
    """Print summary table of all stress tests."""
    print(f"\n\n{'='*70}")
    print("STRESS TEST SUMMARY - ALL TESTS")
    print(f"{'='*70}\n")
    print(f"{'Test':<25} {'Users':<8} {'Reqs':<8} {'Success%':<10} {'P95(ms)':<10} {'RPS':<10} {'Peak CPU%':<12} {'Peak Mem(MB)':<12}")
    print("-" * 105)

    for result in results:
        print(
            f"{result.test_name:<25} "
            f"{result.concurrent_users:<8} "
            f"{result.total_requests:<8} "
            f"{result.success_rate:<10.2f} "
            f"{result.p95:<10.2f} "
            f"{result.throughput:<10.2f} "
            f"{result.cpu_max:<12.2f} "
            f"{result.memory_max:<12.2f}"
        )

    print("\n" + "="*70)
    print("Stress testing complete!")
    print("="*70 + "\n")


if __name__ == "__main__":
    """Run stress tests."""
    results = asyncio.run(run_stress_tests())
