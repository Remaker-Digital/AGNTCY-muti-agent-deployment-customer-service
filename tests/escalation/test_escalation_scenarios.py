"""
# ============================================================================
# Escalation Scenario Testing - Phase 5 Validation
# ============================================================================
# Purpose: Validate escalation detection and handling for frustrated customers,
#          high-value orders, and sensitive situations.
#
# Why this test?
# - Phase 5 requirement: Validate escalation scenarios work correctly
# - Enterprise quality: Ensures frustrated customers get human attention
# - Trust: High-value and sensitive situations are handled appropriately
#
# Test Coverage:
# - Scenario 5: Frustrated Customer (Alex persona)
# - Scenario 6: High-Value Order Issue (Taylor persona)
# - Scenario 7: Sensitive Topic (bereavement handling)
#
# Architecture:
# - Tests against Production API Gateway
# - API Gateway -> SLIM Gateway -> Agent Pipeline -> Azure OpenAI
# - Escalation Detection Agent determines if human intervention needed
#
# Usage:
#   python tests/escalation/test_escalation_scenarios.py
#   python tests/escalation/test_escalation_scenarios.py --local
#   python tests/escalation/test_escalation_scenarios.py --detailed
#
# See: docs/PHASE-5-TEST-USER-STRATEGY.md (Scenarios 5-7)
# See: docs/PHASE-5-COMPLETION-CHECKLIST.md (Task #9)
# ============================================================================
"""

import json
import os
import sys
import time
import argparse
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, List, Any
import urllib.request
import urllib.error
import ssl

# ============================================================================
# CONFIGURATION
# ============================================================================

# Production API Gateway endpoint
PROD_API_GATEWAY = os.getenv(
    "API_GATEWAY_URL", "https://agntcy-cs-prod-rc6vcp.eastus2.cloudapp.azure.com"
)

# Local development endpoint (fallback)
LOCAL_API_GATEWAY = "http://localhost:8080"

# SSL context for self-signed certificates
SSL_CONTEXT = ssl.create_default_context()
SSL_CONTEXT.check_hostname = False
SSL_CONTEXT.verify_mode = ssl.CERT_NONE

# ============================================================================
# ESCALATION TEST SCENARIOS
# ============================================================================
# Based on PHASE-5-TEST-USER-STRATEGY.md Scenarios 5-7

ESCALATION_SCENARIOS = [
    # Scenario 5: Frustrated Customer (Alex persona)
    {
        "id": "esc-001",
        "name": "Frustrated Customer - Repeat Issue",
        "persona": "Alex (Frustrated Customer)",
        "description": "Customer has contacted multiple times about the same issue",
        "messages": [
            "I've called three times and STILL haven't gotten my refund!",
        ],
        "expect_escalation": True,
        "escalation_reasons": [
            "repeated frustration",
            "multiple contacts",
            "refund issue",
        ],
        "empathy_keywords": ["understand", "frustrat", "sorry", "apolog", "help"],
    },
    {
        "id": "esc-002",
        "name": "Frustrated Customer - Unacceptable Service",
        "persona": "Alex (Frustrated Customer)",
        "description": "Customer expressing strong dissatisfaction",
        "messages": [
            "This is absolutely unacceptable service!",
        ],
        "expect_escalation": True,
        "escalation_reasons": ["strong frustration", "service complaint"],
        "empathy_keywords": ["understand", "concern", "sorry", "apolog", "right away"],
    },
    {
        "id": "esc-003",
        "name": "Frustrated Customer - Manager Request",
        "persona": "Alex (Frustrated Customer)",
        "description": "Customer explicitly requesting manager/supervisor",
        "messages": [
            "I want to speak to a manager NOW!",
        ],
        "expect_escalation": True,
        "escalation_reasons": [
            "manager request",
            "supervisor request",
            "explicit escalation",
        ],
        "empathy_keywords": [
            "understand",
            "connect",
            "supervisor",
            "manager",
            "right away",
        ],
    },
    # Scenario 6: High-Value Order Issue (Taylor persona)
    {
        "id": "esc-004",
        "name": "High-Value Order - Large Amount",
        "persona": "Taylor (High-Value Customer)",
        "description": "Customer with high-value order issue",
        "messages": [
            "I placed a $5000 order for my company last week and half the items were missing!",
        ],
        "expect_escalation": True,
        "escalation_reasons": [
            "high-value order",
            "large order",
            "missing items",
            "corporate",
        ],
        "empathy_keywords": [
            "sorry",
            "understand",
            "priority",
            "resolve",
            "immediately",
        ],
    },
    {
        "id": "esc-005",
        "name": "High-Value Order - Time Sensitive",
        "persona": "Taylor (High-Value Customer)",
        "description": "Time-sensitive corporate event with order issue",
        "messages": [
            "This order is for a corporate event tomorrow and it hasn't arrived yet. We spent over $3000!",
        ],
        "expect_escalation": True,
        "escalation_reasons": [
            "time-sensitive",
            "corporate event",
            "urgent",
            "high-value",
        ],
        "empathy_keywords": ["urgent", "priority", "immediately", "expedite", "sorry"],
    },
    # Scenario 7: Sensitive Topic (Bereavement)
    {
        "id": "esc-006",
        "name": "Sensitive Topic - Bereavement",
        "persona": "Anonymous Customer",
        "description": "Customer dealing with loss of a loved one",
        "messages": [
            "I recently lost my husband and I'm trying to cancel his subscription.",
        ],
        "expect_escalation": True,
        "escalation_reasons": [
            "bereavement",
            "sensitive situation",
            "loss",
            "compassion needed",
        ],
        "empathy_keywords": [
            "sorry",
            "loss",
            "condolence",
            "understand",
            "difficult",
            "help",
        ],
    },
    {
        "id": "esc-007",
        "name": "Sensitive Topic - Medical Situation",
        "persona": "Anonymous Customer",
        "description": "Customer with medical emergency affecting order",
        "messages": [
            "I was in the hospital for emergency surgery and missed my delivery. Can you help?",
        ],
        "expect_escalation": True,
        "escalation_reasons": ["medical", "hospital", "emergency", "sensitive"],
        "empathy_keywords": ["sorry", "health", "understand", "help", "hope"],
    },
    # Additional frustration escalation scenarios
    {
        "id": "esc-008",
        "name": "Escalation Keyword - Supervisor",
        "persona": "Alex (Frustrated Customer)",
        "description": "Customer using supervisor escalation keyword",
        "messages": [
            "Get me your supervisor. This conversation is going nowhere.",
        ],
        "expect_escalation": True,
        "escalation_reasons": ["supervisor request", "explicit escalation"],
        "empathy_keywords": ["understand", "connect", "supervisor", "help"],
    },
    # Control scenario - should NOT escalate
    {
        "id": "esc-009",
        "name": "Normal Inquiry - No Escalation Expected",
        "persona": "Mike (Convenience Seeker)",
        "description": "Regular order status inquiry - no escalation needed",
        "messages": [
            "Hi, I'd like to check on my order status please. Order number 12345.",
        ],
        "expect_escalation": False,
        "escalation_reasons": [],
        "empathy_keywords": [],
    },
    {
        "id": "esc-010",
        "name": "Product Question - No Escalation Expected",
        "persona": "Jennifer (Gift Buyer)",
        "description": "Normal product question - no escalation needed",
        "messages": [
            "What coffee would you recommend for someone who likes medium roast?",
        ],
        "expect_escalation": False,
        "escalation_reasons": [],
        "empathy_keywords": [],
    },
]


# ============================================================================
# API COMMUNICATION
# ============================================================================


def send_message(
    api_url: str, message: str, session_id: str = None, timeout: int = 60
) -> Dict[str, Any]:
    """
    Send a message to the API Gateway.

    Args:
        api_url: API Gateway URL
        message: Customer message to send
        session_id: Session ID for conversation continuity
        timeout: Request timeout in seconds

    Returns:
        Dict with 'success', 'response', 'escalated', 'intent', etc.
    """
    endpoint = f"{api_url}/api/v1/chat"
    start_time = time.time()

    if session_id is None:
        session_id = f"escalation-test-{int(time.time())}"

    payload = json.dumps(
        {"message": message, "session_id": session_id, "language": "en"}
    ).encode("utf-8")

    headers = {"Content-Type": "application/json"}

    try:
        request = urllib.request.Request(
            endpoint, data=payload, headers=headers, method="POST"
        )

        with urllib.request.urlopen(
            request, timeout=timeout, context=SSL_CONTEXT
        ) as response:
            latency_ms = (time.time() - start_time) * 1000
            response_text = response.read().decode("utf-8")

            try:
                response_json = json.loads(response_text)
            except json.JSONDecodeError:
                response_json = {"response": response_text}

            return {
                "success": True,
                "response": response_json.get("response", ""),
                "intent": response_json.get("intent", "UNKNOWN"),
                "confidence": response_json.get("confidence", 0.0),
                "escalated": response_json.get("escalated", False),
                "full_response": response_json,
                "error": None,
                "latency_ms": latency_ms,
            }

    except urllib.error.HTTPError as e:
        latency_ms = (time.time() - start_time) * 1000
        error_body = ""
        try:
            error_body = e.read().decode("utf-8")
        except:
            pass

        return {
            "success": False,
            "response": "",
            "intent": None,
            "confidence": 0.0,
            "escalated": False,
            "full_response": None,
            "error": f"HTTP {e.code}: {error_body[:200]}",
            "latency_ms": latency_ms,
        }

    except urllib.error.URLError as e:
        latency_ms = (time.time() - start_time) * 1000
        return {
            "success": False,
            "response": "",
            "intent": None,
            "confidence": 0.0,
            "escalated": False,
            "full_response": None,
            "error": f"Connection error: {str(e)}",
            "latency_ms": latency_ms,
        }

    except Exception as e:
        latency_ms = (time.time() - start_time) * 1000
        return {
            "success": False,
            "response": "",
            "intent": None,
            "confidence": 0.0,
            "escalated": False,
            "full_response": None,
            "error": f"Error: {str(e)}",
            "latency_ms": latency_ms,
        }


def check_empathy_keywords(response_text: str, keywords: List[str]) -> Dict[str, Any]:
    """
    Check if response contains empathy keywords.

    Args:
        response_text: The response to check
        keywords: List of empathy keywords to look for

    Returns:
        Dict with match count and matched keywords
    """
    if not keywords:
        return {"matched": [], "score": 1.0, "required": 0}

    text_lower = response_text.lower()
    matched = [kw for kw in keywords if kw.lower() in text_lower]

    return {
        "matched": matched,
        "score": len(matched) / len(keywords) if keywords else 1.0,
        "required": len(keywords),
    }


# ============================================================================
# TEST EXECUTION
# ============================================================================


def run_escalation_tests(
    api_url: str, verbose: bool = True, detailed: bool = False
) -> Dict[str, Any]:
    """
    Run escalation scenario tests against the API Gateway.

    Args:
        api_url: API Gateway URL
        verbose: Print progress output
        detailed: Print detailed response analysis

    Returns:
        Dict with test results and metrics
    """
    results = []
    escalation_true_positives = 0
    escalation_false_negatives = 0
    escalation_true_negatives = 0
    escalation_false_positives = 0
    empathy_scores = []
    error_count = 0

    print(f"\n{'='*70}")
    print("ESCALATION SCENARIO TESTING - Phase 5 Validation")
    print(f"{'='*70}")
    print(f"API Endpoint: {api_url}")
    print(f"Total Scenarios: {len(ESCALATION_SCENARIOS)}")
    print(f"{'='*70}\n")

    for scenario in ESCALATION_SCENARIOS:
        scenario_id = scenario["id"]
        scenario_name = scenario["name"]
        persona = scenario["persona"]
        messages = scenario["messages"]
        expect_escalation = scenario["expect_escalation"]
        empathy_keywords = scenario.get("empathy_keywords", [])

        if verbose:
            print(f"\n[{scenario_id}] {scenario_name}")
            print(f"  Persona: {persona}")
            print(f"  Expect Escalation: {expect_escalation}")

        # Send all messages in the scenario
        session_id = f"esc-test-{scenario_id}-{int(time.time())}"
        final_result = None
        total_latency = 0

        for msg in messages:
            if verbose:
                print(
                    f'  Message: "{msg[:50]}..."'
                    if len(msg) > 50
                    else f'  Message: "{msg}"'
                )

            result = send_message(api_url, msg, session_id)
            total_latency += result["latency_ms"]

            if result["error"]:
                if verbose:
                    print(f"  ERROR: {result['error']}")
                error_count += 1
                final_result = result
                break

            final_result = result

        if final_result is None or final_result.get("error"):
            status = "ERROR"
            results.append(
                {
                    "id": scenario_id,
                    "name": scenario_name,
                    "persona": persona,
                    "expect_escalation": expect_escalation,
                    "actual_escalation": None,
                    "status": status,
                    "empathy_score": 0,
                    "latency_ms": total_latency,
                    "error": (
                        final_result.get("error") if final_result else "No response"
                    ),
                }
            )
            continue

        # Check escalation result
        actual_escalation = final_result.get("escalated", False)

        # Calculate metrics
        if expect_escalation and actual_escalation:
            escalation_true_positives += 1
            escalation_correct = True
        elif expect_escalation and not actual_escalation:
            escalation_false_negatives += 1
            escalation_correct = False
        elif not expect_escalation and not actual_escalation:
            escalation_true_negatives += 1
            escalation_correct = True
        else:  # not expect_escalation and actual_escalation
            escalation_false_positives += 1
            escalation_correct = False

        # Check empathy keywords
        empathy_result = check_empathy_keywords(
            final_result["response"], empathy_keywords
        )
        empathy_scores.append(empathy_result["score"])

        # Determine status
        if escalation_correct and (
            empathy_result["score"] >= 0.3 or not empathy_keywords
        ):
            status = "PASS"
        else:
            status = "FAIL"

        if verbose:
            color = "\033[92m" if status == "PASS" else "\033[91m"
            reset = "\033[0m"
            esc_mark = "[OK]" if escalation_correct else "[X]"
            print(f"  Latency: {total_latency:.0f}ms")
            print(
                f"  Escalated: {actual_escalation} (expected: {expect_escalation}) {esc_mark}"
            )
            print(f"  Intent: {final_result.get('intent', 'N/A')}")
            if empathy_keywords:
                print(
                    f"  Empathy Score: {empathy_result['score']:.0%} (matched: {empathy_result['matched']})"
                )
            print(f"  Result: {color}{status}{reset}")

            if detailed:
                print(f"  Response: {final_result['response'][:200]}...")

        results.append(
            {
                "id": scenario_id,
                "name": scenario_name,
                "persona": persona,
                "messages": messages,
                "expect_escalation": expect_escalation,
                "actual_escalation": actual_escalation,
                "escalation_correct": escalation_correct,
                "intent": final_result.get("intent"),
                "empathy": empathy_result,
                "status": status,
                "latency_ms": total_latency,
                "response": final_result["response"][:500],
                "error": None,
            }
        )

    # Calculate final metrics
    total_scenarios = len(ESCALATION_SCENARIOS)
    total_escalation_expected = sum(
        1 for s in ESCALATION_SCENARIOS if s["expect_escalation"]
    )
    total_no_escalation_expected = total_scenarios - total_escalation_expected

    # Escalation precision and recall
    precision = (
        escalation_true_positives
        / (escalation_true_positives + escalation_false_positives)
        if (escalation_true_positives + escalation_false_positives) > 0
        else 0
    )
    recall = (
        escalation_true_positives
        / (escalation_true_positives + escalation_false_negatives)
        if (escalation_true_positives + escalation_false_negatives) > 0
        else 0
    )

    avg_empathy = sum(empathy_scores) / len(empathy_scores) if empathy_scores else 0
    passed = sum(1 for r in results if r["status"] == "PASS")
    failed = sum(1 for r in results if r["status"] == "FAIL")
    errors = sum(1 for r in results if r["status"] == "ERROR")

    # Pass criteria (from PHASE-5-TEST-USER-STRATEGY.md)
    # - Escalation Precision: >90%
    # - Escalation Recall: >95%
    # - Empathy Score: >85%
    precision_pass = precision >= 0.90
    recall_pass = recall >= 0.95
    empathy_pass = (
        avg_empathy >= 0.85
        or len([s for s in ESCALATION_SCENARIOS if s.get("empathy_keywords")]) == 0
    )

    overall_pass = precision_pass and recall_pass and empathy_pass

    print(f"\n{'='*70}")
    print("RESULTS SUMMARY")
    print(f"{'='*70}")
    print(f"Total Scenarios: {total_scenarios}")
    print(f"Passed: {passed}/{total_scenarios} ({passed/total_scenarios*100:.0f}%)")
    print(f"Failed: {failed}/{total_scenarios}")
    print(f"Errors: {errors}/{total_scenarios}")
    print(f"\nESCALATION METRICS:")
    print(f"  True Positives: {escalation_true_positives}/{total_escalation_expected}")
    print(
        f"  False Negatives: {escalation_false_negatives}/{total_escalation_expected}"
    )
    print(
        f"  True Negatives: {escalation_true_negatives}/{total_no_escalation_expected}"
    )
    print(
        f"  False Positives: {escalation_false_positives}/{total_no_escalation_expected}"
    )
    print(f"  Precision: {precision:.0%}")
    print(f"  Recall: {recall:.0%}")
    print(f"\nEMPATHY METRICS:")
    print(f"  Average Empathy Score: {avg_empathy:.0%}")

    print(f"\nPASS CRITERIA:")
    print(
        f"  - Escalation Precision >= 90%: {'PASS' if precision_pass else 'FAIL'} ({precision:.0%})"
    )
    print(
        f"  - Escalation Recall >= 95%: {'PASS' if recall_pass else 'FAIL'} ({recall:.0%})"
    )
    print(
        f"  - Empathy Score >= 85%: {'PASS' if empathy_pass else 'FAIL'} ({avg_empathy:.0%})"
    )
    print(f"\nOVERALL: {'PASS' if overall_pass else 'FAIL'}")
    print(f"{'='*70}")

    return {
        "timestamp": datetime.now().isoformat(),
        "api_url": api_url,
        "total_scenarios": total_scenarios,
        "metrics": {
            "passed": passed,
            "failed": failed,
            "errors": errors,
            "pass_rate": (
                round(passed / total_scenarios, 2) if total_scenarios > 0 else 0
            ),
            "escalation_precision": round(precision, 2),
            "escalation_recall": round(recall, 2),
            "true_positives": escalation_true_positives,
            "false_negatives": escalation_false_negatives,
            "true_negatives": escalation_true_negatives,
            "false_positives": escalation_false_positives,
            "avg_empathy_score": round(avg_empathy, 2),
        },
        "pass_criteria": {
            "precision": precision_pass,
            "recall": recall_pass,
            "empathy": empathy_pass,
            "overall": overall_pass,
        },
        "results": results,
    }


def save_report(results: Dict[str, Any], output_dir: Path) -> Path:
    """
    Save test results to a JSON report file.

    Args:
        results: Test results dictionary
        output_dir: Directory to save report

    Returns:
        Path to saved report file
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    report_path = output_dir / f"escalation-test-report-{timestamp}.json"

    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    print(f"\nReport saved to: {report_path}")
    return report_path


def main():
    parser = argparse.ArgumentParser(
        description="Escalation Scenario Testing - Phase 5 Validation"
    )
    parser.add_argument(
        "--local",
        action="store_true",
        help="Test against local API Gateway instead of production",
    )
    parser.add_argument(
        "--api-url", type=str, default=None, help="Custom API Gateway URL"
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="tests/escalation/reports",
        help="Directory to save test reports",
    )
    parser.add_argument("--quiet", action="store_true", help="Reduce output verbosity")
    parser.add_argument(
        "--detailed", action="store_true", help="Show detailed response analysis"
    )

    args = parser.parse_args()

    # Determine API URL
    if args.api_url:
        api_url = args.api_url
    elif args.local:
        api_url = LOCAL_API_GATEWAY
    else:
        api_url = PROD_API_GATEWAY

    # Run tests
    results = run_escalation_tests(
        api_url=api_url, verbose=not args.quiet, detailed=args.detailed
    )

    # Save report
    script_dir = Path(__file__).parent
    project_root = script_dir.parent.parent
    output_dir = project_root / args.output_dir
    save_report(results, output_dir)

    # Exit with appropriate code
    if results["pass_criteria"]["overall"]:
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()
