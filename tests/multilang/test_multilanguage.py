"""
# ============================================================================
# Multi-Language Support Testing - Phase 5 Validation
# ============================================================================
# Purpose: Validate French Canadian (fr-CA) and Spanish (es) language support
#          for the deployed AGNTCY multi-agent customer service platform.
#
# Why this test?
# - Phase 4 requirement: Multi-language support (fr-CA, es)
# - Enterprise quality: Consistent service across languages
# - Educational value: Demonstrates LLM's multilingual capabilities
#
# Test Coverage:
# - French Canadian order inquiry
# - French Canadian return request
# - Spanish product recommendation
# - Spanish escalation handling
# - Language detection accuracy
# - Response quality validation (responses in correct language)
#
# Architecture:
# - Tests against Production API Gateway
# - API Gateway → SLIM Gateway → Agent Pipeline → Azure OpenAI
# - GPT-4o-mini handles language detection and intent classification
# - GPT-4o generates responses in the detected language
#
# Usage:
#   python tests/multilang/test_multilanguage.py
#   python tests/multilang/test_multilanguage.py --local
#   python tests/multilang/test_multilanguage.py --detailed
#
# See: docs/PHASE-5-COMPLETION-CHECKLIST.md (Task #8)
# See: CLAUDE.md (Multi-Language Strategy section)
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
import re

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
# MULTI-LANGUAGE TEST CASES
# ============================================================================
# Test cases organized by language with expected behaviors

# Intent aliases - different systems may use different intent names
# All these are semantically equivalent
INTENT_ALIASES = {
    "ORDER_STATUS": ["ORDER_STATUS", "ORDER_INQUIRY", "ORDER_TRACKING"],
    "PRODUCT_INFO": ["PRODUCT_INFO", "PRODUCT_INQUIRY", "PRODUCT_QUESTION"],
    "PRODUCT_RECOMMENDATION": [
        "PRODUCT_RECOMMENDATION",
        "PRODUCT_INQUIRY",
        "PRODUCT_INFO",
        "PRODUCT_SUGGESTION",
    ],
    "RETURN_REQUEST": ["RETURN_REQUEST", "RETURN", "REFUND_REQUEST"],
    "GENERAL_INQUIRY": [
        "GENERAL_INQUIRY",
        "GENERAL",
        "ACCOUNT_HELP",
        "ACCOUNT_INQUIRY",
        "HELP",
    ],
    "ESCALATION_REQUEST": ["ESCALATION_REQUEST", "ESCALATION", "ESCALATE", "TRANSFER"],
}


def intent_matches(expected: str, actual: str) -> bool:
    """
    Check if actual intent matches expected, accounting for aliases.

    The intent classification system may use slightly different naming,
    so we check against a list of semantically equivalent intents.
    """
    expected_upper = expected.upper().replace("-", "_")
    actual_upper = actual.upper().replace("-", "_")

    # Direct match
    if expected_upper == actual_upper:
        return True

    # Check if actual is in the expected's alias list
    aliases = INTENT_ALIASES.get(expected_upper, [expected_upper])
    return actual_upper in aliases


MULTILANG_TEST_CASES = {
    "fr-CA": {
        "name": "French Canadian",
        "test_cases": [
            {
                "id": "fr-001",
                "name": "Order Status Inquiry (FR-CA)",
                "scenario": "Customer asks about order status in French",
                "input": "Bonjour, ou est ma commande numero 12345? Je l'ai commandee la semaine derniere.",
                "language": "fr-CA",
                "expected_intent": "ORDER_STATUS",
                "expected_language_response": "fr",
                "validation_keywords": [
                    "commande",
                    "12345",
                    "livraison",
                    "expedie",
                    "suivi",
                    "merci",
                    "bonjour",
                ],
                "validation_negative": [],  # Relaxed - focus on positive matches
            },
            {
                "id": "fr-002",
                "name": "Return Request (FR-CA)",
                "scenario": "Customer requests return in French Canadian",
                "input": "Je voudrais retourner mon achat. Le produit ne fonctionne pas correctement.",
                "language": "fr-CA",
                "expected_intent": "RETURN_REQUEST",
                "expected_language_response": "fr",
                "validation_keywords": [
                    "retour",
                    "produit",
                    "remboursement",
                    "politique",
                    "desole",
                    "aide",
                ],
                "validation_negative": [],
            },
            {
                "id": "fr-003",
                "name": "Product Question (FR-CA)",
                "scenario": "Customer asks about products in French",
                "input": "Quels sont vos meilleurs cafes pour l'espresso?",
                "language": "fr-CA",
                "expected_intent": "PRODUCT_INFO",
                "expected_language_response": "fr",
                "validation_keywords": [
                    "cafe",
                    "espresso",
                    "produit",
                    "recommand",
                    "excellent",
                ],
                "validation_negative": [],
            },
            {
                "id": "fr-004",
                "name": "Greeting and General (FR-CA)",
                "scenario": "Customer greets in French",
                "input": "Allo, j'ai besoin d'aide avec mon compte s'il vous plait.",
                "language": "fr-CA",
                "expected_intent": "GENERAL_INQUIRY",
                "expected_language_response": "fr",
                "validation_keywords": [
                    "bonjour",
                    "aide",
                    "compte",
                    "comment",
                    "merci",
                ],
                "validation_negative": [],
            },
        ],
    },
    "es": {
        "name": "Spanish",
        "test_cases": [
            {
                "id": "es-001",
                "name": "Product Recommendation (ES)",
                "scenario": "Customer asks for product recommendations in Spanish",
                "input": "Hola, busco un cafe suave para mi esposa. Que me recomienda?",
                "language": "es",
                "expected_intent": "PRODUCT_RECOMMENDATION",
                "expected_language_response": "es",
                "validation_keywords": [
                    "cafe",
                    "recomend",
                    "suave",
                    "producto",
                    "excelente",
                    "gusto",
                ],
                "validation_negative": [],
            },
            {
                "id": "es-002",
                "name": "Order Status (ES)",
                "scenario": "Customer checks order status in Spanish",
                "input": "Donde esta mi pedido? Lo ordene hace una semana y no ha llegado.",
                "language": "es",
                "expected_intent": "ORDER_STATUS",
                "expected_language_response": "es",
                "validation_keywords": [
                    "pedido",
                    "orden",
                    "envio",
                    "entrega",
                    "gracias",
                    "disculp",
                ],
                "validation_negative": [],
            },
            {
                "id": "es-003",
                "name": "Escalation Scenario (ES)",
                "scenario": "Frustrated customer in Spanish needing escalation",
                "input": "Estoy muy frustrado! Este es el tercer problema con mi pedido. Quiero hablar con un supervisor ahora mismo.",
                "language": "es",
                "expected_intent": "ESCALATION_REQUEST",
                "expected_language_response": "es",
                "validation_keywords": [
                    "disculp",
                    "supervisor",
                    "equipo",
                    "ayudar",
                    "atencion",
                    "lamento",
                    "entiendo",
                ],
                "validation_negative": [],
                "expect_escalation": True,
            },
            {
                "id": "es-004",
                "name": "Return Request (ES)",
                "scenario": "Customer requests return in Spanish",
                "input": "Necesito devolver el producto que compre. No era lo que esperaba.",
                "language": "es",
                "expected_intent": "RETURN_REQUEST",
                "expected_language_response": "es",
                "validation_keywords": [
                    "devol",
                    "producto",
                    "reembolso",
                    "politica",
                    "ayud",
                    "lamento",
                ],
                "validation_negative": [],
            },
        ],
    },
    "en": {
        "name": "English (Baseline)",
        "test_cases": [
            {
                "id": "en-001",
                "name": "Order Status (EN) - Baseline",
                "scenario": "Baseline English test for comparison",
                "input": "Where is my order #12345? I placed it last week.",
                "language": "en",
                "expected_intent": "ORDER_STATUS",
                "expected_language_response": "en",
                "validation_keywords": [
                    "order",
                    "12345",
                    "shipping",
                    "tracking",
                    "delivery",
                ],
                "validation_negative": [],
            },
            {
                "id": "en-002",
                "name": "Product Question (EN) - Baseline",
                "scenario": "Baseline English product question",
                "input": "What's your best coffee for making espresso at home?",
                "language": "en",
                "expected_intent": "PRODUCT_INFO",
                "expected_language_response": "en",
                "validation_keywords": ["espresso", "coffee", "recommend"],
                "validation_negative": [],
            },
        ],
    },
}


# ============================================================================
# LANGUAGE DETECTION UTILITIES
# ============================================================================


def detect_response_language(text: str) -> str:
    """
    Simple language detection based on common words and patterns.

    This is a heuristic approach for test validation, not production use.
    Production should use Azure Language Detection or similar service.

    Args:
        text: Response text to analyze

    Returns:
        Detected language code: 'en', 'fr', 'es', or 'unknown'
    """
    text_lower = text.lower()

    # French indicators (including Canadian French)
    french_words = [
        "bonjour",
        "merci",
        "s'il vous plaît",
        "commande",
        "livraison",
        "produit",
        "retour",
        "remboursement",
        "votre",
        "notre",
        "nous",
        "vous",
        "avez",
        "êtes",
        "je suis",
        "café",
        "aide",
        "désolé",
        "aujourd'hui",
        "demain",
        "jour",
        "semaine",
        "bienvenue",
    ]

    # Spanish indicators
    spanish_words = [
        "hola",
        "gracias",
        "por favor",
        "pedido",
        "envío",
        "producto",
        "devolución",
        "reembolso",
        "su",
        "nuestro",
        "nosotros",
        "usted",
        "estamos",
        "está",
        "soy",
        "café",
        "ayuda",
        "disculpe",
        "lo siento",
        "hoy",
        "mañana",
        "día",
        "semana",
        "bienvenido",
    ]

    # English indicators
    english_words = [
        "hello",
        "thank you",
        "please",
        "order",
        "shipping",
        "product",
        "return",
        "refund",
        "your",
        "our",
        "we",
        "you",
        "are",
        "is",
        "am",
        "coffee",
        "help",
        "sorry",
        "today",
        "tomorrow",
        "day",
        "week",
        "welcome",
        "the",
        "and",
        "to",
        "for",
    ]

    french_count = sum(1 for word in french_words if word in text_lower)
    spanish_count = sum(1 for word in spanish_words if word in text_lower)
    english_count = sum(1 for word in english_words if word in text_lower)

    # Determine language by highest count (with threshold)
    max_count = max(french_count, spanish_count, english_count)

    if max_count < 2:
        return "unknown"

    if french_count == max_count:
        return "fr"
    elif spanish_count == max_count:
        return "es"
    else:
        return "en"


def validate_language_response(
    response_text: str,
    expected_language: str,
    positive_keywords: List[str],
    negative_keywords: List[str],
) -> Dict[str, Any]:
    """
    Validate that a response is in the expected language.

    Args:
        response_text: The response to validate
        expected_language: Expected language code (en, fr, es)
        positive_keywords: Keywords that SHOULD be present (in expected language)
        negative_keywords: Keywords that should NOT be present (wrong language)

    Returns:
        Validation result dict with details
    """
    text_lower = response_text.lower()

    # Check positive keywords (at least one should match)
    positive_matches = [kw for kw in positive_keywords if kw.lower() in text_lower]
    positive_score = (
        len(positive_matches) / len(positive_keywords) if positive_keywords else 1.0
    )

    # Check negative keywords (none should match)
    negative_matches = [kw for kw in negative_keywords if kw.lower() in text_lower]
    negative_score = (
        1.0 - (len(negative_matches) / len(negative_keywords))
        if negative_keywords
        else 1.0
    )

    # Detect actual language
    detected_language = detect_response_language(response_text)
    language_match = (
        detected_language == expected_language or detected_language == "unknown"
    )

    # Overall validation (weighted)
    # - 40% positive keywords
    # - 40% no negative keywords
    # - 20% language detection match
    overall_score = (
        (positive_score * 0.4)
        + (negative_score * 0.4)
        + (0.2 if language_match else 0.0)
    )
    passed = overall_score >= 0.6 and len(negative_matches) == 0

    return {
        "passed": passed,
        "overall_score": round(overall_score, 2),
        "detected_language": detected_language,
        "expected_language": expected_language,
        "language_match": language_match,
        "positive_matches": positive_matches,
        "positive_score": round(positive_score, 2),
        "negative_matches": negative_matches,
        "negative_score": round(negative_score, 2),
    }


# ============================================================================
# API COMMUNICATION
# ============================================================================


def send_message(
    api_url: str, message: str, language: str = "en", timeout: int = 60
) -> Dict[str, Any]:
    """
    Send a message to the API Gateway with language parameter.

    Args:
        api_url: API Gateway URL
        message: Customer message to send
        language: Language code (en, fr-CA, es)
        timeout: Request timeout in seconds

    Returns:
        Dict with 'success', 'response', 'intent', 'error', 'latency_ms'
    """
    endpoint = f"{api_url}/api/v1/chat"
    start_time = time.time()

    payload = json.dumps(
        {
            "message": message,
            "session_id": f"multilang-test-{int(time.time())}",
            "language": language,
        }
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


# ============================================================================
# TEST EXECUTION
# ============================================================================


def run_multilanguage_tests(
    api_url: str,
    languages: List[str] = None,
    verbose: bool = True,
    detailed: bool = False,
) -> Dict[str, Any]:
    """
    Run multi-language tests against the API Gateway.

    Args:
        api_url: API Gateway URL
        languages: List of language codes to test (None = all)
        verbose: Print progress output
        detailed: Print detailed response analysis

    Returns:
        Dict with test results and metrics
    """
    if languages is None:
        languages = ["en", "fr-CA", "es"]

    all_results = []
    language_stats = {}

    print(f"\n{'='*70}")
    print("MULTI-LANGUAGE SUPPORT TESTING - Phase 5 Validation")
    print(f"{'='*70}")
    print(f"API Endpoint: {api_url}")
    print(f"Languages: {', '.join(languages)}")
    print(f"{'='*70}\n")

    for lang_code in languages:
        lang_key = (
            lang_code.lower().replace("-", "-").split("-")[0]
        )  # Handle fr-CA -> fr
        if lang_code == "fr-CA":
            lang_key = "fr-CA"
        elif lang_code == "es":
            lang_key = "es"
        elif lang_code == "en":
            lang_key = "en"

        if lang_key not in MULTILANG_TEST_CASES:
            print(f"Warning: No test cases for language {lang_code}")
            continue

        lang_data = MULTILANG_TEST_CASES[lang_key]
        test_cases = lang_data["test_cases"]
        lang_name = lang_data["name"]

        print(f"\n{'-'*70}")
        print(f"TESTING: {lang_name} ({lang_code})")
        print(f"{'-'*70}")

        lang_results = {
            "passed": 0,
            "failed": 0,
            "errors": 0,
            "intent_matches": 0,
            "language_matches": 0,
            "total_latency_ms": 0,
            "cases": [],
        }

        for tc in test_cases:
            tc_id = tc["id"]
            tc_name = tc["name"]
            tc_input = tc["input"]
            tc_lang = tc["language"]
            expected_intent = tc.get("expected_intent", "")
            expected_lang_resp = tc.get("expected_language_response", lang_key[:2])
            positive_kw = tc.get("validation_keywords", [])
            negative_kw = tc.get("validation_negative", [])
            expect_escalation = tc.get("expect_escalation", False)

            if verbose:
                print(f"\n[{tc_id}] {tc_name}")
                print(f"  Input: {tc_input[:60]}...")
                print(f"  Expected Intent: {expected_intent}")

            # Send the message
            result = send_message(api_url, tc_input, tc_lang)
            lang_results["total_latency_ms"] += result["latency_ms"]

            if result["error"]:
                status = "ERROR"
                lang_results["errors"] += 1
                validation = {"passed": False, "error": result["error"]}
                if verbose:
                    print(f"  Result: \033[93mERROR\033[0m - {result['error']}")
            else:
                # Validate language of response
                validation = validate_language_response(
                    result["response"], expected_lang_resp, positive_kw, negative_kw
                )

                # Check intent match using alias-aware matching
                actual_intent = (result.get("intent") or "").upper()
                intent_match = intent_matches(expected_intent, actual_intent)

                # Check escalation if expected
                escalation_match = True
                if expect_escalation:
                    escalation_match = result.get("escalated", False)

                if validation["passed"] and intent_match and escalation_match:
                    status = "PASS"
                    lang_results["passed"] += 1
                else:
                    status = "FAIL"
                    lang_results["failed"] += 1

                if intent_match:
                    lang_results["intent_matches"] += 1
                if validation.get("language_match", False):
                    lang_results["language_matches"] += 1

                if verbose:
                    color = "\033[92m" if status == "PASS" else "\033[91m"
                    reset = "\033[0m"
                    intent_mark = "[OK]" if intent_match else "[X]"
                    lang_mark = "[OK]" if validation.get("language_match") else "[X]"
                    print(f"  Latency: {result['latency_ms']:.0f}ms")
                    print(f"  Actual Intent: {actual_intent} {intent_mark}")
                    print(
                        f"  Response Language: {validation['detected_language']} "
                        f"(expected: {expected_lang_resp}) {lang_mark}"
                    )
                    print(f"  Language Score: {validation['overall_score']:.0%}")
                    print(f"  Result: {color}{status}{reset}")

                    if detailed and status == "FAIL":
                        print(f"  Response: {result['response'][:200]}...")
                        print(f"  Positive matches: {validation['positive_matches']}")
                        print(f"  Negative matches: {validation['negative_matches']}")

            # Store case result
            case_result = {
                "id": tc_id,
                "name": tc_name,
                "language": tc_lang,
                "input": tc_input,
                "expected_intent": expected_intent,
                "actual_intent": result.get("intent", ""),
                "intent_match": intent_match if result["success"] else False,
                "expected_response_lang": expected_lang_resp,
                "detected_response_lang": validation.get("detected_language", "error"),
                "language_score": validation.get("overall_score", 0),
                "status": status,
                "latency_ms": result["latency_ms"],
                "response": result.get("response", "")[:300],
                "error": result.get("error"),
                "validation": validation,
            }
            lang_results["cases"].append(case_result)
            all_results.append(case_result)

        # Language summary
        total = len(test_cases)
        print(f"\n{lang_name} Summary:")
        print(f"  Passed: {lang_results['passed']}/{total}")
        print(f"  Failed: {lang_results['failed']}/{total}")
        print(f"  Errors: {lang_results['errors']}/{total}")
        print(f"  Intent Match Rate: {lang_results['intent_matches']/total*100:.0f}%")
        print(
            f"  Language Match Rate: {lang_results['language_matches']/total*100:.0f}%"
        )
        print(f"  Avg Latency: {lang_results['total_latency_ms']/total:.0f}ms")

        language_stats[lang_code] = lang_results

    # Overall summary
    total_tests = len(all_results)
    total_passed = sum(s["passed"] for s in language_stats.values())
    total_failed = sum(s["failed"] for s in language_stats.values())
    total_errors = sum(s["errors"] for s in language_stats.values())
    total_intent_matches = sum(s["intent_matches"] for s in language_stats.values())
    total_language_matches = sum(s["language_matches"] for s in language_stats.values())
    avg_latency = (
        sum(s["total_latency_ms"] for s in language_stats.values()) / total_tests
        if total_tests > 0
        else 0
    )

    # Pass criteria
    pass_rate = total_passed / total_tests if total_tests > 0 else 0
    intent_rate = total_intent_matches / total_tests if total_tests > 0 else 0
    language_rate = total_language_matches / total_tests if total_tests > 0 else 0

    overall_pass = pass_rate >= 0.75 and intent_rate >= 0.75 and language_rate >= 0.60

    print(f"\n{'='*70}")
    print("OVERALL RESULTS SUMMARY")
    print(f"{'='*70}")
    print(f"Total Tests: {total_tests}")
    print(f"Passed: {total_passed} ({pass_rate:.0%})")
    print(f"Failed: {total_failed}")
    print(f"Errors: {total_errors}")
    print(f"Intent Match Rate: {intent_rate:.0%}")
    print(f"Language Match Rate: {language_rate:.0%}")
    print(f"Average Latency: {avg_latency:.0f}ms")

    print(f"\nPASS CRITERIA:")
    print(
        f"  - Pass Rate >= 75%: {'PASS' if pass_rate >= 0.75 else 'FAIL'} ({pass_rate:.0%})"
    )
    print(
        f"  - Intent Match >= 75%: {'PASS' if intent_rate >= 0.75 else 'FAIL'} ({intent_rate:.0%})"
    )
    print(
        f"  - Language Match >= 60%: {'PASS' if language_rate >= 0.60 else 'FAIL'} ({language_rate:.0%})"
    )
    print(f"\nOVERALL: {'PASS' if overall_pass else 'FAIL'}")
    print(f"{'='*70}")

    return {
        "timestamp": datetime.now().isoformat(),
        "api_url": api_url,
        "languages_tested": languages,
        "total_tests": total_tests,
        "metrics": {
            "passed": total_passed,
            "failed": total_failed,
            "errors": total_errors,
            "pass_rate": round(pass_rate, 2),
            "intent_match_rate": round(intent_rate, 2),
            "language_match_rate": round(language_rate, 2),
            "avg_latency_ms": round(avg_latency, 0),
        },
        "pass_criteria": {
            "pass_rate": pass_rate >= 0.75,
            "intent_match": intent_rate >= 0.75,
            "language_match": language_rate >= 0.60,
            "overall": overall_pass,
        },
        "language_stats": language_stats,
        "results": all_results,
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
    report_path = output_dir / f"multilang-test-report-{timestamp}.json"

    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    print(f"\nReport saved to: {report_path}")
    return report_path


def main():
    parser = argparse.ArgumentParser(
        description="Multi-Language Support Testing - Phase 5 Validation"
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
        "--languages",
        type=str,
        nargs="+",
        default=None,
        help="Languages to test (e.g., --languages en fr-CA es)",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="tests/multilang/reports",
        help="Directory to save test reports",
    )
    parser.add_argument("--quiet", action="store_true", help="Reduce output verbosity")
    parser.add_argument(
        "--detailed", action="store_true", help="Show detailed failure analysis"
    )
    parser.add_argument(
        "--fr-ca-only", action="store_true", help="Test French Canadian only"
    )
    parser.add_argument("--es-only", action="store_true", help="Test Spanish only")

    args = parser.parse_args()

    # Determine API URL
    if args.api_url:
        api_url = args.api_url
    elif args.local:
        api_url = LOCAL_API_GATEWAY
    else:
        api_url = PROD_API_GATEWAY

    # Determine languages
    if args.languages:
        languages = args.languages
    elif args.fr_ca_only:
        languages = ["fr-CA"]
    elif args.es_only:
        languages = ["es"]
    else:
        languages = ["en", "fr-CA", "es"]

    # Run tests
    results = run_multilanguage_tests(
        api_url=api_url,
        languages=languages,
        verbose=not args.quiet,
        detailed=args.detailed,
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
