"""
Phase 2 Test Execution Script with Metrics and Tracing

This script executes all Phase 2 integration tests sequentially and generates:
1. Test execution metrics (pass/fail, duration, coverage)
2. Agent collaboration traces (message flow through the system)
3. Mock API call traces (Shopify, Knowledge Base)
4. Detailed performance metrics
5. Comprehensive HTML report

Educational Project: Multi-Agent AI Customer Service Platform
Phase: 2 - Business Logic Implementation
Purpose: Validate agent collaboration and business logic correctness

Usage:
    python run_phase2_tests.py

Output:
    - Console: Real-time test progress and summary
    - phase2-test-report.html: Comprehensive HTML report
    - phase2-test-traces.json: Machine-readable trace data
    - phase2-test-metrics.json: Performance and coverage metrics

Author: Claude Sonnet 4.5 (AI Assistant)
License: MIT (Educational Use)
"""

import sys
import json
import time
import subprocess
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional
import re


class Phase2TestRunner:
    """
    Executes Phase 2 integration tests and collects comprehensive metrics.

    This runner provides:
    - Sequential test execution with isolation
    - Detailed timing and performance metrics
    - Agent trace collection from logs
    - Mock API call tracking
    - Coverage analysis
    - HTML report generation
    """

    def __init__(self):
        self.project_root = Path(__file__).parent
        self.results = {
            "execution_time": None,
            "timestamp": datetime.now().isoformat(),
            "phase": "Phase 2 - Business Logic Implementation",
            "total_tests": 0,
            "passed": 0,
            "failed": 0,
            "skipped": 0,
            "coverage": 0.0,
            "test_suites": [],
        }

        # Test suites to execute
        self.test_suites = [
            {
                "name": "Issue #24 - Order Status Flow",
                "file": "tests/integration/test_order_status_flow.py",
                "description": "Customer order status inquiries with multi-agent collaboration",
                "agents": [
                    "Intent Classification",
                    "Knowledge Retrieval",
                    "Response Generation",
                ],
                "mock_apis": ["Shopify Orders API"],
                "acceptance_criteria": [
                    "Intent classification accuracy >90%",
                    "Order lookup <500ms P95",
                    "Full conversation context maintained",
                ],
            },
            {
                "name": "Issue #29 - Return/Refund Flow",
                "file": "tests/integration/test_return_refund_flow.py",
                "description": "Customer return/refund requests with $50 auto-approval threshold",
                "agents": [
                    "Intent Classification",
                    "Knowledge Retrieval",
                    "Response Generation",
                ],
                "mock_apis": ["Shopify Orders API", "Knowledge Base"],
                "acceptance_criteria": [
                    "Auto-approval threshold accuracy: 100%",
                    "Order lookup <500ms P95",
                    "RMA number generation for approved returns",
                    "Escalation for high-value returns (>$50)",
                ],
            },
            {
                "name": "Issue #25 - Product Information Flow",
                "file": "tests/integration/test_product_info_flow.py",
                "description": "Customer product information inquiries with search and stock availability",
                "agents": [
                    "Intent Classification",
                    "Knowledge Retrieval",
                    "Response Generation",
                ],
                "mock_apis": ["Shopify Products API"],
                "acceptance_criteria": [
                    "Product search <200ms P95",
                    "Stock availability included",
                    "Price and feature information accurate",
                ],
            },
        ]

    def run_all_tests(self) -> Dict[str, Any]:
        """
        Execute all test suites sequentially and collect metrics.

        Returns:
            Dictionary with complete test results, metrics, and traces
        """
        print("=" * 80)
        print("PHASE 2 TEST EXECUTION - MULTI-AGENT CUSTOMER SERVICE PLATFORM")
        print("=" * 80)
        print(f"Timestamp: {self.results['timestamp']}")
        print(f"Project Root: {self.project_root}")
        print(f"Test Suites: {len(self.test_suites)}")
        print("=" * 80)
        print()

        start_time = time.time()

        for idx, suite in enumerate(self.test_suites, 1):
            print(f"\n[{idx}/{len(self.test_suites)}] Running: {suite['name']}")
            print("-" * 80)

            suite_result = self._run_test_suite(suite)
            self.results["test_suites"].append(suite_result)

            # Update overall stats
            self.results["total_tests"] += suite_result["total_tests"]
            self.results["passed"] += suite_result["passed"]
            self.results["failed"] += suite_result["failed"]
            self.results["skipped"] += suite_result["skipped"]

            # Print suite summary
            self._print_suite_summary(suite_result)

        # Calculate overall metrics
        self.results["execution_time"] = time.time() - start_time
        self.results["pass_rate"] = (
            (self.results["passed"] / self.results["total_tests"] * 100)
            if self.results["total_tests"] > 0
            else 0.0
        )

        # Get final coverage
        self.results["coverage"] = self._get_coverage()

        # Print final summary
        self._print_final_summary()

        # Generate reports
        self._generate_reports()

        return self.results

    def _run_test_suite(self, suite: Dict[str, Any]) -> Dict[str, Any]:
        """
        Run a single test suite and collect detailed metrics.

        Args:
            suite: Test suite configuration

        Returns:
            Dictionary with suite results and traces
        """
        suite_result = {
            "name": suite["name"],
            "file": suite["file"],
            "description": suite["description"],
            "agents": suite["agents"],
            "mock_apis": suite["mock_apis"],
            "acceptance_criteria": suite["acceptance_criteria"],
            "start_time": time.time(),
            "duration": 0.0,
            "total_tests": 0,
            "passed": 0,
            "failed": 0,
            "skipped": 0,
            "test_cases": [],
            "agent_traces": [],
            "mock_api_calls": [],
            "performance_metrics": {},
            "stdout": "",
            "stderr": "",
        }

        # Run pytest with verbose output and coverage
        test_file = self.project_root / suite["file"]

        cmd = [
            sys.executable,
            "-m",
            "pytest",
            str(test_file),
            "-v",  # Verbose
            "-s",  # Show print statements
            "--tb=short",  # Short traceback
            "--capture=no",  # Don't capture output (we want logs)
            "-p",
            "no:warnings",  # Suppress warnings for cleaner output
        ]

        try:
            result = subprocess.run(
                cmd,
                cwd=str(self.project_root),
                capture_output=True,
                text=True,
                timeout=300,  # 5 minute timeout per suite
            )

            suite_result["stdout"] = result.stdout
            suite_result["stderr"] = result.stderr
            suite_result["exit_code"] = result.returncode

            # Parse pytest output for test results
            self._parse_pytest_output(result.stdout, suite_result)

            # Extract agent traces from logs
            self._extract_agent_traces(result.stdout, suite_result)

            # Extract mock API calls
            self._extract_mock_api_calls(result.stdout, suite_result)

            # Extract performance metrics
            self._extract_performance_metrics(result.stdout, suite_result)

        except subprocess.TimeoutExpired:
            suite_result["error"] = "Test suite timed out after 300 seconds"
            suite_result["failed"] = suite_result["total_tests"] = 1
        except Exception as e:
            suite_result["error"] = f"Test execution failed: {e}"
            suite_result["failed"] = suite_result["total_tests"] = 1

        suite_result["duration"] = time.time() - suite_result["start_time"]

        return suite_result

    def _parse_pytest_output(self, output: str, suite_result: Dict[str, Any]):
        """Parse pytest output to extract test case results."""

        # Extract individual test results
        # Pattern: tests/integration/test_file.py::TestClass::test_method PASSED
        test_pattern = re.compile(
            r"(tests/integration/\S+)::([\w:]+)\s+(PASSED|FAILED|SKIPPED)"
        )

        for match in test_pattern.finditer(output):
            file_path, test_name, status = match.groups()

            test_case = {
                "name": test_name,
                "status": status.lower(),
                "file": file_path,
                "duration": 0.0,  # Will be extracted if available
                "error": None,
            }

            # Extract error message if failed
            if status == "FAILED":
                error_pattern = re.compile(
                    rf"{re.escape(test_name)}.*?AssertionError: ([^\n]+)", re.DOTALL
                )
                error_match = error_pattern.search(output)
                if error_match:
                    test_case["error"] = error_match.group(1).strip()

            suite_result["test_cases"].append(test_case)
            suite_result["total_tests"] += 1

            if status == "PASSED":
                suite_result["passed"] += 1
            elif status == "FAILED":
                suite_result["failed"] += 1
            elif status == "SKIPPED":
                suite_result["skipped"] += 1

    def _extract_agent_traces(self, output: str, suite_result: Dict[str, Any]):
        """
        Extract agent collaboration traces from log output.

        Traces show message flow: Intent → Knowledge → Response
        """

        # Pattern: INFO agent:file.py:line Message text
        log_pattern = re.compile(r"INFO\s+(\S+):(\S+):(\d+)\s+(.+)")

        traces = []
        current_trace = None

        for match in log_pattern.finditer(output):
            agent, file, line, message = match.groups()

            # Start new trace on customer message processing
            if "Processing message" in message:
                if current_trace:
                    traces.append(current_trace)

                current_trace = {
                    "start_time": None,
                    "steps": [],
                    "total_duration_ms": 0.0,
                }

            if current_trace is not None:
                step = {
                    "agent": agent,
                    "file": file,
                    "line": int(line),
                    "message": message,
                }

                # Extract timing information
                timing_match = re.search(r"(\d+\.\d+)ms", message)
                if timing_match:
                    step["duration_ms"] = float(timing_match.group(1))

                current_trace["steps"].append(step)

        # Add final trace
        if current_trace:
            traces.append(current_trace)

        suite_result["agent_traces"] = traces

    def _extract_mock_api_calls(self, output: str, suite_result: Dict[str, Any]):
        """Extract mock API call traces from log output."""

        api_calls = []

        # Pattern for Shopify API calls
        shopify_pattern = re.compile(
            r"Fetching (order|products) from Shopify: (http://\S+)"
        )

        for match in shopify_pattern.finditer(output):
            resource_type, url = match.groups()
            api_calls.append(
                {
                    "api": "Shopify",
                    "resource": resource_type,
                    "url": url,
                    "method": "GET",
                }
            )

        # Pattern for search operations
        search_pattern = re.compile(
            r'(Found|Searching) (\d+) (products|orders) matching [\'"]([^\'"]+)[\'"]'
        )

        for match in search_pattern.finditer(output):
            action, count, resource, query = match.groups()
            api_calls.append(
                {
                    "api": "Shopify",
                    "resource": resource,
                    "action": action.lower(),
                    "query": query,
                    "result_count": int(count),
                }
            )

        suite_result["mock_api_calls"] = api_calls

    def _extract_performance_metrics(self, output: str, suite_result: Dict[str, Any]):
        """Extract performance metrics from test output."""

        metrics = {
            "agent_latencies": [],
            "api_latencies": [],
            "total_flow_duration": [],
        }

        # Extract latency measurements
        latency_pattern = re.compile(r"(\d+\.\d+)ms")

        for match in latency_pattern.finditer(output):
            latency_ms = float(match.group(1))
            metrics["agent_latencies"].append(latency_ms)

        # Calculate statistics
        if metrics["agent_latencies"]:
            metrics["avg_latency_ms"] = sum(metrics["agent_latencies"]) / len(
                metrics["agent_latencies"]
            )
            metrics["max_latency_ms"] = max(metrics["agent_latencies"])
            metrics["min_latency_ms"] = min(metrics["agent_latencies"])

        suite_result["performance_metrics"] = metrics

    def _get_coverage(self) -> float:
        """Get code coverage percentage from pytest-cov output."""

        # Run pytest with coverage to get final metrics
        cmd = [
            sys.executable,
            "-m",
            "pytest",
            "tests/integration/",
            "--cov=.",
            "--cov-report=term",
            "-q",
        ]

        try:
            result = subprocess.run(
                cmd,
                cwd=str(self.project_root),
                capture_output=True,
                text=True,
                timeout=60,
            )

            # Extract coverage percentage
            # Pattern: TOTAL    1234   567    45%
            coverage_pattern = re.compile(r"TOTAL\s+\d+\s+\d+\s+(\d+)%")
            match = coverage_pattern.search(result.stdout)

            if match:
                return float(match.group(1))

        except Exception:
            pass

        return 0.0

    def _print_suite_summary(self, suite_result: Dict[str, Any]):
        """Print summary for a single test suite."""

        print(f"  Tests: {suite_result['passed']}/{suite_result['total_tests']} passed")
        print(f"  Duration: {suite_result['duration']:.2f}s")
        print(f"  Agent Traces: {len(suite_result['agent_traces'])}")
        print(f"  Mock API Calls: {len(suite_result['mock_api_calls'])}")

        if suite_result["performance_metrics"].get("avg_latency_ms"):
            print(
                f"  Avg Latency: {suite_result['performance_metrics']['avg_latency_ms']:.2f}ms"
            )

        if suite_result["failed"] > 0:
            print(f"  [!] Failed Tests:")
            for test_case in suite_result["test_cases"]:
                if test_case["status"] == "failed":
                    print(f"    - {test_case['name']}")
                    if test_case.get("error"):
                        print(f"      Error: {test_case['error']}")

    def _print_final_summary(self):
        """Print final test execution summary."""

        print("\n" + "=" * 80)
        print("FINAL TEST SUMMARY")
        print("=" * 80)
        print(f"Total Tests: {self.results['total_tests']}")
        print(f"Passed: {self.results['passed']} ({self.results['pass_rate']:.1f}%)")
        print(f"Failed: {self.results['failed']}")
        print(f"Skipped: {self.results['skipped']}")
        print(f"Code Coverage: {self.results['coverage']:.1f}%")
        print(f"Total Duration: {self.results['execution_time']:.2f}s")
        print("=" * 80)

        # Print agent collaboration summary
        total_traces = sum(len(s["agent_traces"]) for s in self.results["test_suites"])
        total_api_calls = sum(
            len(s["mock_api_calls"]) for s in self.results["test_suites"]
        )

        print(f"\nAgent Collaboration:")
        print(f"  Total Traces: {total_traces}")
        print(f"  Total Mock API Calls: {total_api_calls}")

        # Print per-suite breakdown
        print(f"\nTest Suite Breakdown:")
        for suite in self.results["test_suites"]:
            status = (
                "[PASS]"
                if suite["failed"] == 0
                else f"[FAIL] ({suite['failed']} failed)"
            )
            print(f"  {suite['name']}: {status}")
            print(f"    Tests: {suite['passed']}/{suite['total_tests']} passed")
            print(f"    Duration: {suite['duration']:.2f}s")

    def _generate_reports(self):
        """Generate comprehensive test reports."""

        print(f"\nGenerating reports...")

        # Generate JSON reports
        metrics_file = self.project_root / "phase2-test-metrics.json"
        traces_file = self.project_root / "phase2-test-traces.json"

        with open(metrics_file, "w") as f:
            json.dump(self.results, f, indent=2)
        print(f"  [OK] Metrics: {metrics_file}")

        with open(traces_file, "w") as f:
            traces_data = {
                "timestamp": self.results["timestamp"],
                "test_suites": [
                    {
                        "name": s["name"],
                        "agent_traces": s["agent_traces"],
                        "mock_api_calls": s["mock_api_calls"],
                    }
                    for s in self.results["test_suites"]
                ],
            }
            json.dump(traces_data, f, indent=2)
        print(f"  [OK] Traces: {traces_file}")

        # Generate HTML report
        html_file = self.project_root / "phase2-test-report.html"
        self._generate_html_report(html_file)
        print(f"  [OK] HTML Report: {html_file}")

    def _generate_html_report(self, output_file: Path):
        """Generate comprehensive HTML test report."""

        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Phase 2 Test Report - Multi-Agent Customer Service</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif;
            background: #f5f5f5;
            padding: 20px;
            line-height: 1.6;
        }}
        .container {{ max-width: 1400px; margin: 0 auto; }}
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            border-radius: 10px;
            margin-bottom: 30px;
        }}
        .header h1 {{ font-size: 28px; margin-bottom: 10px; }}
        .header p {{ opacity: 0.9; }}
        .summary {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }}
        .metric-card {{
            background: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .metric-card h3 {{
            color: #666;
            font-size: 14px;
            margin-bottom: 10px;
        }}
        .metric-card .value {{
            font-size: 32px;
            font-weight: bold;
            color: #333;
        }}
        .metric-card .sub {{
            font-size: 14px;
            color: #999;
            margin-top: 5px;
        }}
        .pass {{ color: #10b981; }}
        .fail {{ color: #ef4444; }}
        .test-suite {{
            background: white;
            padding: 25px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            margin-bottom: 20px;
        }}
        .test-suite h2 {{
            color: #333;
            margin-bottom: 10px;
            font-size: 20px;
        }}
        .test-suite .description {{
            color: #666;
            margin-bottom: 20px;
        }}
        .test-cases {{
            margin: 20px 0;
        }}
        .test-case {{
            padding: 15px;
            margin: 10px 0;
            border-left: 4px solid #ddd;
            background: #f9f9f9;
        }}
        .test-case.passed {{ border-left-color: #10b981; }}
        .test-case.failed {{ border-left-color: #ef4444; background: #fef2f2; }}
        .test-case .name {{ font-weight: bold; margin-bottom: 5px; }}
        .test-case .error {{
            color: #ef4444;
            font-family: monospace;
            font-size: 13px;
            margin-top: 10px;
            padding: 10px;
            background: white;
            border-radius: 4px;
        }}
        .traces {{
            margin: 20px 0;
        }}
        .trace {{
            background: #f9f9f9;
            padding: 15px;
            border-radius: 6px;
            margin: 10px 0;
            font-family: monospace;
            font-size: 13px;
        }}
        .trace .step {{
            padding: 8px 0;
            border-bottom: 1px solid #eee;
        }}
        .trace .step:last-child {{ border-bottom: none; }}
        .trace .agent {{ color: #667eea; font-weight: bold; }}
        .trace .duration {{ color: #10b981; float: right; }}
        .api-calls {{
            margin: 20px 0;
        }}
        .api-call {{
            padding: 10px 15px;
            background: #f0f9ff;
            border-left: 4px solid #3b82f6;
            margin: 5px 0;
            font-family: monospace;
            font-size: 13px;
        }}
        .performance {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            gap: 15px;
            margin: 20px 0;
        }}
        .perf-metric {{
            background: #f0fdf4;
            padding: 15px;
            border-radius: 6px;
            text-align: center;
        }}
        .perf-metric .label {{
            font-size: 12px;
            color: #666;
            margin-bottom: 5px;
        }}
        .perf-metric .value {{
            font-size: 24px;
            font-weight: bold;
            color: #10b981;
        }}
        .section-title {{
            font-size: 18px;
            font-weight: bold;
            margin: 20px 0 10px 0;
            color: #333;
        }}
        .badge {{
            display: inline-block;
            padding: 4px 12px;
            border-radius: 12px;
            font-size: 12px;
            font-weight: bold;
        }}
        .badge.passed {{ background: #d1fae5; color: #065f46; }}
        .badge.failed {{ background: #fee2e2; color: #991b1b; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Phase 2 Test Execution Report</h1>
            <p>Multi-Agent AI Customer Service Platform</p>
            <p>Generated: {self.results['timestamp']}</p>
        </div>

        <div class="summary">
            <div class="metric-card">
                <h3>Total Tests</h3>
                <div class="value">{self.results['total_tests']}</div>
                <div class="sub">Across 3 test suites</div>
            </div>
            <div class="metric-card">
                <h3>Pass Rate</h3>
                <div class="value pass">{self.results['pass_rate']:.1f}%</div>
                <div class="sub">{self.results['passed']}/{self.results['total_tests']} passed</div>
            </div>
            <div class="metric-card">
                <h3>Code Coverage</h3>
                <div class="value">{self.results['coverage']:.1f}%</div>
                <div class="sub">Phase 2 baseline</div>
            </div>
            <div class="metric-card">
                <h3>Duration</h3>
                <div class="value">{self.results['execution_time']:.1f}s</div>
                <div class="sub">Sequential execution</div>
            </div>
        </div>
"""

        # Add test suite details
        for suite in self.results["test_suites"]:
            status_badge = "passed" if suite["failed"] == 0 else "failed"

            html += f"""
        <div class="test-suite">
            <h2>{suite['name']} <span class="badge {status_badge}">{suite['passed']}/{suite['total_tests']} PASSED</span></h2>
            <div class="description">{suite['description']}</div>

            <div class="section-title">Test Cases</div>
            <div class="test-cases">
"""

            for test_case in suite["test_cases"]:
                error_html = ""
                if test_case.get("error"):
                    error_html = f'<div class="error">Error: {test_case["error"]}</div>'

                html += f"""
                <div class="test-case {test_case['status']}">
                    <div class="name">{test_case['name']}</div>
                    {error_html}
                </div>
"""

            html += "</div>"

            # Add agent traces
            if suite["agent_traces"]:
                html += f"""
            <div class="section-title">Agent Collaboration Traces ({len(suite["agent_traces"])})</div>
            <div class="traces">
"""
                for idx, trace in enumerate(
                    suite["agent_traces"][:5], 1
                ):  # Show first 5 traces
                    html += f'<div class="trace"><strong>Trace #{idx}</strong><br>'
                    for step in trace["steps"][:10]:  # Show first 10 steps per trace
                        duration = (
                            f'<span class="duration">{step["duration_ms"]:.2f}ms</span>'
                            if "duration_ms" in step
                            else ""
                        )
                        html += f'<div class="step"><span class="agent">{step["agent"]}</span>: {step["message"][:100]} {duration}</div>'
                    html += "</div>"

                html += "</div>"

            # Add mock API calls
            if suite["mock_api_calls"]:
                html += f"""
            <div class="section-title">Mock API Calls ({len(suite["mock_api_calls"])})</div>
            <div class="api-calls">
"""
                for api_call in suite["mock_api_calls"][:20]:  # Show first 20 calls
                    call_text = f"{api_call['api']} - {api_call['resource']}"
                    if "query" in api_call:
                        call_text += f" (query: '{api_call['query']}')"
                    if "result_count" in api_call:
                        call_text += f" → {api_call['result_count']} results"
                    html += f'<div class="api-call">{call_text}</div>'

                html += "</div>"

            # Add performance metrics
            if suite["performance_metrics"]:
                metrics = suite["performance_metrics"]
                html += f"""
            <div class="section-title">Performance Metrics</div>
            <div class="performance">
"""
                if "avg_latency_ms" in metrics:
                    html += f"""
                <div class="perf-metric">
                    <div class="label">Avg Latency</div>
                    <div class="value">{metrics['avg_latency_ms']:.1f}ms</div>
                </div>
                <div class="perf-metric">
                    <div class="label">Max Latency</div>
                    <div class="value">{metrics.get('max_latency_ms', 0):.1f}ms</div>
                </div>
                <div class="perf-metric">
                    <div class="label">Min Latency</div>
                    <div class="value">{metrics.get('min_latency_ms', 0):.1f}ms</div>
                </div>
"""

                html += f"""
                <div class="perf-metric">
                    <div class="label">Duration</div>
                    <div class="value">{suite['duration']:.2f}s</div>
                </div>
            </div>
"""

            html += "</div>"

        html += """
    </div>
</body>
</html>
"""

        with open(output_file, "w", encoding="utf-8") as f:
            f.write(html)


def main():
    """Main entry point for test execution."""

    runner = Phase2TestRunner()
    results = runner.run_all_tests()

    # Exit with appropriate code
    exit_code = 0 if results["failed"] == 0 else 1

    print(f"\nTest execution complete. Exit code: {exit_code}")
    print(f"\nReports generated:")
    print(f"  - phase2-test-report.html (open in browser)")
    print(f"  - phase2-test-metrics.json (machine readable)")
    print(f"  - phase2-test-traces.json (agent traces)")

    sys.exit(exit_code)


if __name__ == "__main__":
    main()
