# ============================================================================
# Security Test Suite
# ============================================================================
# Purpose: Production security validation tests for the multi-agent platform
#
# Test Categories:
# - Prompt Injection: Validates Critic/Supervisor blocks injection attacks
# - PII Extraction: Validates no customer data leakage
# - Jailbreak: Validates resistance to role manipulation
# - Harmful Instructions: Validates blocks on fraud/abuse requests
#
# Usage:
#   python -m pytest tests/security/
#   python tests/security/test_prompt_injection.py --checklist-only
#   python tests/security/test_prompt_injection.py --full
#
# See: docs/PHASE-5-COMPLETION-CHECKLIST.md (Task #10)
# See: docs/critic-supervisor-agent-requirements.md
# ============================================================================
