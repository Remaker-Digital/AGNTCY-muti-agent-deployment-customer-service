# ============================================================================
# Auto-Scaling Load Test Suite
# ============================================================================
# Purpose: Validate the auto-scaling infrastructure under load conditions
# that simulate the 10,000 daily users requirement.
#
# Test Scenarios:
# 1. Baseline - Verify system handles expected normal load
# 2. Scale-Up Trigger - Verify KEDA triggers scale-up at threshold
# 3. Scale-Down Validation - Verify system scales down during low traffic
# 4. Connection Pool Behavior - Verify pool handles concurrent requests
# 5. Circuit Breaker - Verify circuit breaker activates under stress
# 6. Cold Start - Measure cold start latency from scale-to-zero
#
# Target Metrics (10,000 daily users):
# - Peak load: ~3.5 requests/second
# - Average load: ~0.3 requests/second
# - Concurrent users during peak: 50-100
#
# Related Documentation:
# - Architecture: docs/AUTO-SCALING-ARCHITECTURE.md
# - Evaluation: docs/AUTO-SCALING-WORK-ITEM-EVALUATION.md
# - Container Apps: terraform/phase4_prod/container_apps.tf
#
# Usage:
#     python tests/load/autoscaling_load_test.py --endpoint <url> --scenario baseline
#     python tests/load/autoscaling_load_test.py --endpoint <url> --scenario scale-up
# ============================================================================

import asyncio
import aiohttp
import argparse
import json
import time
import statistics
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import List, Optional, Dict, Any
from enum import Enum
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# =============================================================================
# Test Configuration
# =============================================================================

class TestScenario(Enum):
    """Available test scenarios."""
    BASELINE = "baseline"
    SCALE_UP = "scale-up"
    SCALE_DOWN = "scale-down"
    POOL_STRESS = "pool-stress"
    CIRCUIT_BREAKER = "circuit-breaker"
    COLD_START = "cold-start"
    SUSTAINED = "sustained"


@dataclass
class ScenarioConfig:
    """Configuration for a test scenario."""
    name: str
    description: str
    duration_seconds: int
    concurrent_users: int
    requests_per_second: float
    warmup_seconds: int = 10
    cooldown_seconds: int = 10
    timeout_seconds: float = 60.0


# Pre-defined scenario configurations based on 10K daily users requirement
SCENARIO_CONFIGS = {
    TestScenario.BASELINE: ScenarioConfig(
        name="Baseline",
        description="Normal expected load (10K daily users, average traffic)",
        duration_seconds=60,
        concurrent_users=5,
        requests_per_second=0.5,
        warmup_seconds=5
    ),
    TestScenario.SCALE_UP: ScenarioConfig(
        name="Scale-Up Trigger",
        description="Peak load to trigger KEDA scale-up (3.5 RPS target)",
        duration_seconds=120,
        concurrent_users=30,
        requests_per_second=3.5,
        warmup_seconds=10
    ),
    TestScenario.SCALE_DOWN: ScenarioConfig(
        name="Scale-Down Validation",
        description="Minimal traffic to verify scale-down behavior",
        duration_seconds=180,  # Need time for scale-down
        concurrent_users=1,
        requests_per_second=0.1,
        warmup_seconds=0
    ),
    TestScenario.POOL_STRESS: ScenarioConfig(
        name="Connection Pool Stress",
        description="High concurrency to stress connection pool",
        duration_seconds=60,
        concurrent_users=50,
        requests_per_second=5.0,
        warmup_seconds=5
    ),
    TestScenario.CIRCUIT_BREAKER: ScenarioConfig(
        name="Circuit Breaker Test",
        description="Extreme load to trigger circuit breaker",
        duration_seconds=30,
        concurrent_users=100,
        requests_per_second=10.0,
        warmup_seconds=0,
        timeout_seconds=10.0  # Short timeout to trigger failures
    ),
    TestScenario.COLD_START: ScenarioConfig(
        name="Cold Start Measurement",
        description="Single request after idle period (measure cold start)",
        duration_seconds=10,
        concurrent_users=1,
        requests_per_second=0.1,
        warmup_seconds=0
    ),
    TestScenario.SUSTAINED: ScenarioConfig(
        name="Sustained Load",
        description="Extended test at peak load for stability",
        duration_seconds=300,  # 5 minutes
        concurrent_users=20,
        requests_per_second=2.0,
        warmup_seconds=30
    )
}


# =============================================================================
# Test Data
# =============================================================================

TEST_MESSAGES = [
    {"message": "Where is my order #ORD-2026-78432?", "type": "order_status"},
    {"message": "What coffee would you recommend for dark roast lovers?", "type": "product_inquiry"},
    {"message": "I want to return my order, the coffee was stale", "type": "return_request"},
    {"message": "This is TERRIBLE service! I've called 3 times!", "type": "escalation"},
    {"message": "What are your shipping options?", "type": "general_inquiry"},
    {"message": "Do you have any decaf options?", "type": "product_inquiry"},
    {"message": "Can I change my delivery address?", "type": "order_modification"},
    {"message": "What's your return policy?", "type": "policy_inquiry"},
]


# =============================================================================
# Result Models
# =============================================================================

@dataclass
class RequestResult:
    """Result of a single request."""
    success: bool
    status_code: int
    latency_ms: float
    error: Optional[str] = None
    timestamp: float = field(default_factory=time.time)
    message_type: str = ""


@dataclass
class ScenarioResult:
    """Result of a complete test scenario."""
    scenario: str
    start_time: str
    end_time: str
    duration_seconds: float
    total_requests: int
    successful_requests: int
    failed_requests: int
    error_rate: float
    requests_per_second: float
    latency_avg_ms: float
    latency_median_ms: float
    latency_p95_ms: float
    latency_p99_ms: float
    latency_min_ms: float
    latency_max_ms: float
    errors: Dict[str, int] = field(default_factory=dict)
    pool_stats_start: Optional[Dict] = None
    pool_stats_end: Optional[Dict] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# =============================================================================
# Load Test Engine
# =============================================================================

class AutoScalingLoadTest:
    """Load test engine for auto-scaling validation."""

    def __init__(self, endpoint: str, scenario: TestScenario):
        self.endpoint = endpoint.rstrip('/')
        self.scenario = scenario
        self.config = SCENARIO_CONFIGS[scenario]
        self.results: List[RequestResult] = []
        self._stop_flag = False

    async def run(self) -> ScenarioResult:
        """Run the test scenario and return results."""
        logger.info(f"Starting scenario: {self.config.name}")
        logger.info(f"  Description: {self.config.description}")
        logger.info(f"  Duration: {self.config.duration_seconds}s")
        logger.info(f"  Concurrent users: {self.config.concurrent_users}")
        logger.info(f"  Target RPS: {self.config.requests_per_second}")

        # Capture initial pool stats
        pool_stats_start = await self._get_pool_stats()

        start_time = datetime.utcnow()
        start_ts = time.time()

        # Warmup phase
        if self.config.warmup_seconds > 0:
            logger.info(f"Warmup phase: {self.config.warmup_seconds}s")
            await asyncio.sleep(self.config.warmup_seconds)

        # Main test phase
        async with aiohttp.ClientSession() as session:
            await self._run_load(session)

        end_time = datetime.utcnow()
        duration = time.time() - start_ts

        # Capture final pool stats
        pool_stats_end = await self._get_pool_stats()

        # Calculate results
        result = self._calculate_results(
            start_time=start_time.isoformat(),
            end_time=end_time.isoformat(),
            duration=duration,
            pool_stats_start=pool_stats_start,
            pool_stats_end=pool_stats_end
        )

        # Log summary
        self._log_summary(result)

        return result

    async def _run_load(self, session: aiohttp.ClientSession):
        """Generate load according to scenario configuration."""
        tasks = []
        interval = 1.0 / max(self.config.requests_per_second, 0.1)
        end_time = time.time() + self.config.duration_seconds

        # Create worker tasks
        for i in range(self.config.concurrent_users):
            task = asyncio.create_task(
                self._worker(session, i, interval, end_time)
            )
            tasks.append(task)

        # Wait for all workers to complete
        await asyncio.gather(*tasks, return_exceptions=True)

    async def _worker(
        self,
        session: aiohttp.ClientSession,
        worker_id: int,
        interval: float,
        end_time: float
    ):
        """Worker that sends requests at specified interval."""
        while time.time() < end_time and not self._stop_flag:
            message = TEST_MESSAGES[worker_id % len(TEST_MESSAGES)]
            result = await self._send_request(session, message)
            self.results.append(result)

            # Rate limiting
            await asyncio.sleep(interval)

    async def _send_request(
        self,
        session: aiohttp.ClientSession,
        message: Dict
    ) -> RequestResult:
        """Send a single request and measure latency."""
        url = f"{self.endpoint}/api/v1/chat"
        start_time = time.time()

        try:
            async with session.post(
                url,
                json={"message": message["message"]},
                timeout=aiohttp.ClientTimeout(total=self.config.timeout_seconds)
            ) as response:
                latency_ms = (time.time() - start_time) * 1000
                await response.text()  # Consume response

                return RequestResult(
                    success=response.status == 200,
                    status_code=response.status,
                    latency_ms=latency_ms,
                    message_type=message["type"]
                )

        except asyncio.TimeoutError:
            return RequestResult(
                success=False,
                status_code=0,
                latency_ms=(time.time() - start_time) * 1000,
                error="timeout",
                message_type=message["type"]
            )
        except Exception as e:
            return RequestResult(
                success=False,
                status_code=0,
                latency_ms=(time.time() - start_time) * 1000,
                error=str(e),
                message_type=message["type"]
            )

    async def _get_pool_stats(self) -> Optional[Dict]:
        """Get connection pool statistics."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.endpoint}/api/v1/pool/stats",
                    timeout=aiohttp.ClientTimeout(total=5)
                ) as response:
                    if response.status == 200:
                        return await response.json()
        except Exception as e:
            logger.warning(f"Could not fetch pool stats: {e}")
        return None

    def _calculate_results(
        self,
        start_time: str,
        end_time: str,
        duration: float,
        pool_stats_start: Optional[Dict],
        pool_stats_end: Optional[Dict]
    ) -> ScenarioResult:
        """Calculate test results from collected data."""
        successful = [r for r in self.results if r.success]
        failed = [r for r in self.results if not r.success]

        latencies = [r.latency_ms for r in successful] if successful else [0]

        # Count errors by type
        errors = {}
        for r in failed:
            error = r.error or f"status_{r.status_code}"
            errors[error] = errors.get(error, 0) + 1

        return ScenarioResult(
            scenario=self.config.name,
            start_time=start_time,
            end_time=end_time,
            duration_seconds=duration,
            total_requests=len(self.results),
            successful_requests=len(successful),
            failed_requests=len(failed),
            error_rate=len(failed) / max(len(self.results), 1) * 100,
            requests_per_second=len(self.results) / max(duration, 1),
            latency_avg_ms=statistics.mean(latencies),
            latency_median_ms=statistics.median(latencies),
            latency_p95_ms=self._percentile(latencies, 95),
            latency_p99_ms=self._percentile(latencies, 99),
            latency_min_ms=min(latencies),
            latency_max_ms=max(latencies),
            errors=errors,
            pool_stats_start=pool_stats_start,
            pool_stats_end=pool_stats_end
        )

    def _percentile(self, data: List[float], percentile: int) -> float:
        """Calculate percentile of data."""
        if not data:
            return 0.0
        sorted_data = sorted(data)
        index = int(len(sorted_data) * percentile / 100)
        return sorted_data[min(index, len(sorted_data) - 1)]

    def _log_summary(self, result: ScenarioResult):
        """Log test result summary."""
        logger.info("=" * 60)
        logger.info(f"Test Results: {result.scenario}")
        logger.info("=" * 60)
        logger.info(f"Duration: {result.duration_seconds:.1f}s")
        logger.info(f"Total Requests: {result.total_requests}")
        logger.info(f"Successful: {result.successful_requests}")
        logger.info(f"Failed: {result.failed_requests}")
        logger.info(f"Error Rate: {result.error_rate:.2f}%")
        logger.info(f"RPS: {result.requests_per_second:.2f}")
        logger.info("-" * 60)
        logger.info(f"Latency (Avg): {result.latency_avg_ms:.0f}ms")
        logger.info(f"Latency (Median): {result.latency_median_ms:.0f}ms")
        logger.info(f"Latency (P95): {result.latency_p95_ms:.0f}ms")
        logger.info(f"Latency (P99): {result.latency_p99_ms:.0f}ms")
        logger.info(f"Latency (Min): {result.latency_min_ms:.0f}ms")
        logger.info(f"Latency (Max): {result.latency_max_ms:.0f}ms")

        if result.errors:
            logger.info("-" * 60)
            logger.info("Errors:")
            for error, count in result.errors.items():
                logger.info(f"  {error}: {count}")

        if result.pool_stats_end:
            logger.info("-" * 60)
            logger.info("Pool Stats (End):")
            for key, value in result.pool_stats_end.items():
                if key != 'timestamp':
                    logger.info(f"  {key}: {value}")


# =============================================================================
# Main Entry Point
# =============================================================================

async def main():
    parser = argparse.ArgumentParser(
        description="Auto-scaling load test for AGNTCY multi-agent system"
    )
    parser.add_argument(
        "--endpoint",
        required=True,
        help="API Gateway endpoint URL"
    )
    parser.add_argument(
        "--scenario",
        choices=[s.value for s in TestScenario],
        default="baseline",
        help="Test scenario to run"
    )
    parser.add_argument(
        "--output",
        help="Output file for JSON results"
    )

    args = parser.parse_args()

    scenario = TestScenario(args.scenario)
    test = AutoScalingLoadTest(args.endpoint, scenario)
    result = await test.run()

    # Save results if output specified
    if args.output:
        with open(args.output, 'w') as f:
            json.dump(result.to_dict(), f, indent=2)
        logger.info(f"Results saved to {args.output}")


if __name__ == "__main__":
    asyncio.run(main())
