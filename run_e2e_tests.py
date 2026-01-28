#!/usr/bin/env python3
"""
Automated End-to-End Testing Suite
====================================

Runs comprehensive automated customer conversation scenarios to validate system behavior
from an end-user perspective. Supports both Phase 2 (mock mode) and Phase 4 (AI model mode).

Usage:
    python run_e2e_tests.py                    # Run all scenarios
    python run_e2e_tests.py --scenario S001    # Run specific scenario
    python run_e2e_tests.py --category "Loyalty Program"  # Run category
    python run_e2e_tests.py --priority high    # Run by priority
    python run_e2e_tests.py --persona persona_001  # Run for specific persona

Output:
    - Console output with real-time results
    - JSON results file: e2e-test-results-{timestamp}.json
    - HTML report: e2e-test-report-{timestamp}.html
    - Detailed logs: e2e-test-logs-{timestamp}.txt

Author: AGNTCY Multi-Agent Platform
Version: 1.0.0
"""

import asyncio
import json
import sys
import time
import argparse
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from shared.models import (
    CustomerMessage,
    Intent,
    Language,
    generate_context_id,
    generate_message_id,
)
from shared import setup_logging

# Import console integration for simulation mode
try:
    sys.path.insert(0, str(project_root / "console"))
    from agntcy_integration import AGNTCYIntegration

    CONSOLE_AVAILABLE = True
except ImportError:
    CONSOLE_AVAILABLE = False
    print("Warning: Console integration not available. Will use direct agent calls.")


@dataclass
class TestTurnResult:
    """Result of a single conversation turn."""

    turn_number: int
    user_message: str
    ai_response: str
    intent_detected: str
    confidence: float
    response_time_ms: float
    escalated: bool
    escalation_reason: Optional[str]
    validation_passed: bool
    validation_failures: List[str]
    timestamp: str


@dataclass
class TestScenarioResult:
    """Result of a complete test scenario."""

    scenario_id: str
    category: str
    persona: Optional[str]
    priority: str
    description: str
    turns: List[TestTurnResult]
    overall_passed: bool
    total_duration_ms: float
    failures: List[str]
    timestamp: str


class E2ETestRunner:
    """Automated end-to-end test runner."""

    def __init__(self, scenarios_file: Path, output_dir: Path):
        """
        Initialize test runner.

        Args:
            scenarios_file: Path to e2e-scenarios.json
            output_dir: Directory for test results
        """
        self.scenarios_file = scenarios_file
        self.output_dir = output_dir
        self.output_dir.mkdir(exist_ok=True)

        # Load test scenarios
        with open(scenarios_file, "r") as f:
            self.test_data = json.load(f)

        self.scenarios = self.test_data["test_scenarios"]
        self.personas = {p["id"]: p for p in self.test_data["personas"]}
        self.config = self.test_data["test_configuration"]
        self.thresholds = self.test_data["validation_thresholds"]

        # Setup logging
        self.logger = setup_logging(name="E2ETestRunner", level="INFO")

        # Test results
        self.results: List[TestScenarioResult] = []
        self.start_time = None
        self.end_time = None

        # Initialize console integration (simulation mode)
        if CONSOLE_AVAILABLE:
            self.integration = AGNTCYIntegration()
            self.logger.info("Using console simulation mode for testing")
        else:
            self.integration = None
            self.logger.warning(
                "Console integration not available - some tests may fail"
            )

    def filter_scenarios(
        self,
        scenario_id: Optional[str] = None,
        category: Optional[str] = None,
        priority: Optional[str] = None,
        persona: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Filter scenarios based on criteria."""
        filtered = self.scenarios

        if scenario_id:
            filtered = [s for s in filtered if s["scenario_id"] == scenario_id]

        if category:
            filtered = [
                s for s in filtered if category.lower() in s["category"].lower()
            ]

        if priority:
            filtered = [s for s in filtered if s["priority"] == priority.lower()]

        if persona:
            filtered = [s for s in filtered if s.get("persona") == persona]

        return filtered

    async def run_scenario(self, scenario: Dict[str, Any]) -> TestScenarioResult:
        """
        Run a single test scenario.

        Args:
            scenario: Test scenario definition

        Returns:
            TestScenarioResult with outcomes
        """
        scenario_id = scenario["scenario_id"]
        self.logger.info(f"\n{'='*70}")
        self.logger.info(f"Running Scenario {scenario_id}: {scenario['description']}")
        self.logger.info(f"{'='*70}")

        scenario_start = time.time()
        turn_results = []
        failures = []

        # Get persona data if specified
        persona_id = scenario.get("persona")
        persona_data = self.personas.get(persona_id) if persona_id else None

        # Create new conversation context
        context_id = generate_context_id()

        # Run each conversation turn
        for turn_def in scenario["conversation"]:
            turn_num = turn_def["turn"]
            user_message = turn_def["user_message"]

            self.logger.info(f"\nTurn {turn_num}: {user_message}")

            # Execute turn
            turn_result = await self._execute_turn(
                user_message=user_message,
                persona_data=persona_data,
                context_id=context_id,
                expected=turn_def,
            )

            turn_results.append(turn_result)

            # Log turn result
            if turn_result.validation_passed:
                self.logger.info(
                    f"✓ PASS - Intent: {turn_result.intent_detected} ({turn_result.confidence:.2%})"
                )
            else:
                self.logger.error(
                    f"✗ FAIL - {len(turn_result.validation_failures)} validation errors"
                )
                for error in turn_result.validation_failures:
                    self.logger.error(f"  - {error}")
                failures.extend(turn_result.validation_failures)

        # Calculate overall scenario result
        scenario_duration = (time.time() - scenario_start) * 1000
        all_turns_passed = all(t.validation_passed for t in turn_results)

        result = TestScenarioResult(
            scenario_id=scenario_id,
            category=scenario["category"],
            persona=persona_id,
            priority=scenario["priority"],
            description=scenario["description"],
            turns=turn_results,
            overall_passed=all_turns_passed,
            total_duration_ms=scenario_duration,
            failures=failures,
            timestamp=datetime.now().isoformat(),
        )

        # Log scenario result
        status = "✓ PASSED" if all_turns_passed else "✗ FAILED"
        self.logger.info(
            f"\nScenario {scenario_id}: {status} ({scenario_duration:.0f}ms)"
        )

        return result

    async def _execute_turn(
        self,
        user_message: str,
        persona_data: Optional[Dict],
        context_id: str,
        expected: Dict[str, Any],
    ) -> TestTurnResult:
        """Execute a single conversation turn and validate."""
        turn_start = time.time()
        validation_failures = []

        try:
            # Call console integration (simulation mode)
            if self.integration:
                # Generate session ID for this test
                session_id = context_id  # Use context_id as session_id

                # Build customer context
                customer_context = None
                if persona_data:
                    customer_context = {
                        "customer_id": persona_data["id"],
                        "customer_email": persona_data["email"],
                        "customer_name": persona_data["name"],
                    }

                # Send customer message via console integration
                response_data = await self.integration.send_customer_message(
                    message=user_message,
                    session_id=session_id,
                    customer_context=customer_context,
                )

                ai_response = response_data.get("response", "")
                intent_detected = response_data.get("intent", "unknown")
                confidence = response_data.get("confidence", 0.0)
                escalated = response_data.get("escalated", False)
                escalation_reason = response_data.get("escalation_reason")

            else:
                # Fallback: Direct agent calls (not implemented in this version)
                ai_response = "Error: Console integration not available"
                intent_detected = "error"
                confidence = 0.0
                escalated = False
                escalation_reason = None
                validation_failures.append("Console integration not available")

            response_time_ms = (time.time() - turn_start) * 1000

            # Validate intent
            expected_intent = expected["expected_intent"]
            if intent_detected != expected_intent:
                validation_failures.append(
                    f"Intent mismatch: expected '{expected_intent}', got '{intent_detected}'"
                )

            # Validate confidence
            expected_confidence_min = expected["expected_confidence_min"]
            if confidence < expected_confidence_min:
                validation_failures.append(
                    f"Confidence too low: expected >={expected_confidence_min:.2%}, got {confidence:.2%}"
                )

            # Validate response content
            for required_text in expected.get("expected_response_contains", []):
                if required_text.lower() not in ai_response.lower():
                    validation_failures.append(
                        f"Response missing required text: '{required_text}'"
                    )

            # Validate escalation
            if "expected_no_escalation" in expected:
                if expected["expected_no_escalation"] and escalated:
                    validation_failures.append("Unexpected escalation occurred")
                elif not expected["expected_no_escalation"] and not escalated:
                    validation_failures.append("Expected escalation did not occur")

            if "expected_escalation" in expected and expected["expected_escalation"]:
                if not escalated:
                    validation_failures.append("Expected escalation did not occur")
                elif "expected_escalation_reason" in expected:
                    if escalation_reason != expected["expected_escalation_reason"]:
                        validation_failures.append(
                            f"Escalation reason mismatch: expected '{expected['expected_escalation_reason']}', got '{escalation_reason}'"
                        )

            # Validate response time
            if response_time_ms > 2500:
                validation_failures.append(
                    f"Response time exceeded threshold: {response_time_ms:.0f}ms > 2500ms"
                )

            return TestTurnResult(
                turn_number=expected["turn"],
                user_message=user_message,
                ai_response=ai_response,
                intent_detected=intent_detected,
                confidence=confidence,
                response_time_ms=response_time_ms,
                escalated=escalated,
                escalation_reason=escalation_reason,
                validation_passed=len(validation_failures) == 0,
                validation_failures=validation_failures,
                timestamp=datetime.now().isoformat(),
            )

        except Exception as e:
            self.logger.error(f"Error executing turn: {e}", exc_info=True)
            return TestTurnResult(
                turn_number=expected["turn"],
                user_message=user_message,
                ai_response=f"ERROR: {str(e)}",
                intent_detected="error",
                confidence=0.0,
                response_time_ms=(time.time() - turn_start) * 1000,
                escalated=False,
                escalation_reason=None,
                validation_passed=False,
                validation_failures=[f"Exception: {str(e)}"],
                timestamp=datetime.now().isoformat(),
            )

    async def run_all(
        self,
        scenario_id: Optional[str] = None,
        category: Optional[str] = None,
        priority: Optional[str] = None,
        persona: Optional[str] = None,
    ):
        """Run all test scenarios (with optional filtering)."""
        self.start_time = datetime.now()

        # Filter scenarios
        scenarios_to_run = self.filter_scenarios(
            scenario_id, category, priority, persona
        )

        self.logger.info(f"\n{'='*70}")
        self.logger.info(f"AUTOMATED END-TO-END TEST SUITE")
        self.logger.info(f"{'='*70}")
        self.logger.info(f"Total scenarios: {len(scenarios_to_run)}")
        self.logger.info(f"Start time: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        self.logger.info(
            f"Mode: {'Simulation (Phase 2)' if CONSOLE_AVAILABLE else 'Direct Agent Calls'}"
        )

        # Run scenarios
        for scenario in scenarios_to_run:
            result = await self.run_scenario(scenario)
            self.results.append(result)

            # Optional: delay between scenarios
            if self.config.get("create_new_session_per_scenario"):
                await asyncio.sleep(0.5)

        self.end_time = datetime.now()

        # Generate reports
        self._generate_reports()

    def _generate_reports(self):
        """Generate test result reports."""
        self.logger.info(f"\n{'='*70}")
        self.logger.info(f"TEST RESULTS SUMMARY")
        self.logger.info(f"{'='*70}")

        # Calculate statistics
        total_scenarios = len(self.results)
        passed_scenarios = sum(1 for r in self.results if r.overall_passed)
        failed_scenarios = total_scenarios - passed_scenarios
        pass_rate = passed_scenarios / total_scenarios if total_scenarios > 0 else 0

        # Response time statistics
        all_response_times = []
        for result in self.results:
            for turn in result.turns:
                all_response_times.append(turn.response_time_ms)

        avg_response_time = (
            sum(all_response_times) / len(all_response_times)
            if all_response_times
            else 0
        )
        p95_response_time = (
            sorted(all_response_times)[int(len(all_response_times) * 0.95)]
            if all_response_times
            else 0
        )

        # Log summary
        self.logger.info(f"Total Scenarios: {total_scenarios}")
        self.logger.info(f"Passed: {passed_scenarios} ({pass_rate:.1%})")
        self.logger.info(f"Failed: {failed_scenarios}")
        self.logger.info(f"Avg Response Time: {avg_response_time:.0f}ms")
        self.logger.info(f"P95 Response Time: {p95_response_time:.0f}ms")
        self.logger.info(
            f"Duration: {(self.end_time - self.start_time).total_seconds():.1f}s"
        )

        # Pass/fail by priority
        for priority in ["critical", "high", "medium", "low"]:
            priority_results = [r for r in self.results if r.priority == priority]
            if priority_results:
                priority_passed = sum(1 for r in priority_results if r.overall_passed)
                priority_rate = priority_passed / len(priority_results)
                self.logger.info(
                    f"{priority.upper()}: {priority_passed}/{len(priority_results)} ({priority_rate:.1%})"
                )

        # Save JSON results
        timestamp = self.start_time.strftime("%Y%m%d-%H%M%S")
        json_file = self.output_dir / f"e2e-test-results-{timestamp}.json"

        results_dict = {
            "test_suite": self.test_data["test_suite_name"],
            "version": self.test_data["version"],
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat(),
            "duration_seconds": (self.end_time - self.start_time).total_seconds(),
            "summary": {
                "total_scenarios": total_scenarios,
                "passed": passed_scenarios,
                "failed": failed_scenarios,
                "pass_rate": pass_rate,
                "avg_response_time_ms": avg_response_time,
                "p95_response_time_ms": p95_response_time,
            },
            "results": [asdict(r) for r in self.results],
        }

        with open(json_file, "w") as f:
            json.dump(results_dict, f, indent=2)

        self.logger.info(f"\nJSON results saved to: {json_file}")

        # Generate HTML report
        html_file = self._generate_html_report(results_dict, timestamp)
        self.logger.info(f"HTML report saved to: {html_file}")

        # Check if thresholds met
        overall_threshold = self.thresholds["overall_pass_rate_min"]
        if pass_rate >= overall_threshold:
            self.logger.info(
                f"\n✓ OVERALL PASS RATE THRESHOLD MET: {pass_rate:.1%} >= {overall_threshold:.1%}"
            )
        else:
            self.logger.error(
                f"\n✗ OVERALL PASS RATE THRESHOLD NOT MET: {pass_rate:.1%} < {overall_threshold:.1%}"
            )

    def _generate_html_report(self, results_dict: Dict, timestamp: str) -> Path:
        """Generate HTML report."""
        html_file = self.output_dir / f"e2e-test-report-{timestamp}.html"

        html = f"""
<!DOCTYPE html>
<html>
<head>
    <title>E2E Test Report - {timestamp}</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }}
        .header {{ background: #2c3e50; color: white; padding: 20px; border-radius: 5px; }}
        .summary {{ background: white; padding: 20px; margin: 20px 0; border-radius: 5px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
        .scenario {{ background: white; margin: 10px 0; padding: 15px; border-radius: 5px; border-left: 5px solid #3498db; }}
        .scenario.passed {{ border-left-color: #27ae60; }}
        .scenario.failed {{ border-left-color: #e74c3c; }}
        .turn {{ margin: 10px 0; padding: 10px; background: #f8f9fa; border-radius: 3px; }}
        .metric {{ display: inline-block; margin: 10px 20px 10px 0; }}
        .pass {{ color: #27ae60; font-weight: bold; }}
        .fail {{ color: #e74c3c; font-weight: bold; }}
        .validation-error {{ color: #e74c3c; margin: 5px 0; font-size: 0.9em; }}
        table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
        th, td {{ padding: 10px; text-align: left; border-bottom: 1px solid #ddd; }}
        th {{ background: #34495e; color: white; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>End-to-End Test Report</h1>
        <p>Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
    </div>

    <div class="summary">
        <h2>Summary</h2>
        <div class="metric">Total Scenarios: <strong>{results_dict['summary']['total_scenarios']}</strong></div>
        <div class="metric">Passed: <strong class="pass">{results_dict['summary']['passed']}</strong></div>
        <div class="metric">Failed: <strong class="fail">{results_dict['summary']['failed']}</strong></div>
        <div class="metric">Pass Rate: <strong>{results_dict['summary']['pass_rate']:.1%}</strong></div>
        <div class="metric">Avg Response Time: <strong>{results_dict['summary']['avg_response_time_ms']:.0f}ms</strong></div>
    </div>

    <h2>Scenario Results</h2>
"""

        for result in results_dict["results"]:
            status_class = "passed" if result["overall_passed"] else "failed"
            status_text = "✓ PASSED" if result["overall_passed"] else "✗ FAILED"

            html += f"""
    <div class="scenario {status_class}">
        <h3>{result['scenario_id']}: {result['description']} <span class="{status_class}">{status_text}</span></h3>
        <p><strong>Category:</strong> {result['category']} | <strong>Priority:</strong> {result['priority']} | <strong>Duration:</strong> {result['total_duration_ms']:.0f}ms</p>
"""

            for turn in result["turns"]:
                turn_class = "pass" if turn["validation_passed"] else "fail"
                html += f"""
        <div class="turn">
            <p><strong>Turn {turn['turn_number']}:</strong> {turn['user_message']}</p>
            <p><strong>Intent:</strong> {turn['intent_detected']} ({turn['confidence']:.1%}) | <strong>Time:</strong> {turn['response_time_ms']:.0f}ms | <strong>Status:</strong> <span class="{turn_class}">{'PASS' if turn['validation_passed'] else 'FAIL'}</span></p>
            <p><strong>Response:</strong> {turn['ai_response'][:200]}...</p>
"""
                if turn["validation_failures"]:
                    for error in turn["validation_failures"]:
                        html += f'<p class="validation-error">✗ {error}</p>'

                html += """
        </div>
"""

            html += """
    </div>
"""

        html += """
</body>
</html>
"""

        with open(html_file, "w", encoding="utf-8") as f:
            f.write(html)

        return html_file


async def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Run automated E2E tests for AGNTCY platform"
    )
    parser.add_argument("--scenario", help="Run specific scenario by ID (e.g., S001)")
    parser.add_argument(
        "--category", help="Run scenarios in category (e.g., 'Loyalty Program')"
    )
    parser.add_argument(
        "--priority",
        choices=["critical", "high", "medium", "low"],
        help="Run scenarios by priority",
    )
    parser.add_argument(
        "--persona", help="Run scenarios for specific persona (e.g., persona_001)"
    )
    parser.add_argument("--output", default=".", help="Output directory for results")

    args = parser.parse_args()

    # Initialize test runner
    scenarios_file = Path(__file__).parent / "test-data" / "e2e-scenarios.json"
    output_dir = Path(args.output)

    if not scenarios_file.exists():
        print(f"Error: Scenarios file not found: {scenarios_file}")
        sys.exit(1)

    runner = E2ETestRunner(scenarios_file, output_dir)

    # Run tests
    await runner.run_all(
        scenario_id=args.scenario,
        category=args.category,
        priority=args.priority,
        persona=args.persona,
    )

    # Exit with appropriate code
    passed = sum(1 for r in runner.results if r.overall_passed)
    total = len(runner.results)
    pass_rate = passed / total if total > 0 else 0

    if pass_rate >= runner.thresholds["overall_pass_rate_min"]:
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
