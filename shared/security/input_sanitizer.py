"""
Input Sanitization and Prompt Injection Detection

This module provides protection against prompt injection attacks by:
1. Detecting known prompt injection patterns
2. Sanitizing potentially dangerous content
3. Flagging suspicious messages for Critic/Supervisor review

Educational Notes:
- Prompt injection is when users try to manipulate AI behavior via input
- Common patterns include "ignore previous instructions" and role impersonation
- Defense in depth: This is the first layer, Critic/Supervisor is second layer
- We block high-confidence injections but flag borderline cases for review

Pattern Categories:
1. Instruction Override: "ignore previous instructions"
2. Role Impersonation: "you are now a pirate"
3. System Prompt Leakage: attempts to extract system prompts
4. Control Characters: hidden unicode, markup injection
5. Jailbreak Attempts: DAN-style prompts, "pretend" scenarios

See: docs/SECURITY-REMEDIATION-2026-01-28.md
"""

import re
import logging
from dataclasses import dataclass
from enum import Enum
from typing import List, Optional, Tuple

logger = logging.getLogger(__name__)


class ThreatLevel(Enum):
    """Threat level classification for detected patterns."""

    NONE = "none"           # No threat detected
    LOW = "low"             # Minor suspicious pattern, allow with logging
    MEDIUM = "medium"       # Potential injection, flag for review
    HIGH = "high"           # Clear injection attempt, block
    CRITICAL = "critical"   # Severe attack attempt, block and alert


@dataclass
class SanitizationResult:
    """Result of input sanitization."""

    original_message: str
    sanitized_message: str
    threat_level: ThreatLevel
    patterns_detected: List[str]
    should_block: bool
    should_flag_for_review: bool
    explanation: Optional[str] = None


# =============================================================================
# Prompt Injection Patterns
# =============================================================================

# High-confidence injection patterns (block immediately)
HIGH_THREAT_PATTERNS = [
    # Instruction override attempts
    (r"ignore\s+(all\s+)?(previous|prior|above|earlier)\s+instructions?", "instruction_override"),
    (r"disregard\s+(all\s+)?(previous|prior|above)\s+", "instruction_override"),
    (r"forget\s+(everything|all|what)\s+", "instruction_override"),

    # Role impersonation
    (r"you\s+are\s+(now|a|an)\s+(?!customer|user|human)", "role_impersonation"),
    (r"act\s+as\s+(if\s+you\s+are\s+)?a\s+", "role_impersonation"),
    (r"pretend\s+(to\s+be|you\s+are)\s+", "role_impersonation"),
    (r"roleplay\s+as\s+", "role_impersonation"),

    # System prompt extraction
    (r"(show|reveal|display|print|output)\s+(me\s+)?(your|the)\s+(system|initial|original)\s+(prompt|instructions?)", "system_extraction"),
    (r"what\s+(are|is)\s+your\s+(system|initial)\s+(prompt|instructions?)", "system_extraction"),

    # DAN/jailbreak patterns
    (r"(DAN|STAN|DUDE)\s*mode", "jailbreak"),
    (r"developer\s+mode\s*(enabled|on|activated)?", "jailbreak"),
    (r"unlock\s+(your|all)\s+(capabilities|restrictions|features)", "jailbreak"),
]

# Medium-confidence patterns (flag for review)
MEDIUM_THREAT_PATTERNS = [
    # Indirect instruction manipulation
    (r"(new|updated|revised)\s+instructions?\s*:", "indirect_instruction"),
    (r"from\s+now\s+on\s*,?\s*(you|always)", "behavior_change"),
    (r"(always|never)\s+(respond|answer|say)\s+", "behavior_change"),

    # Boundary probing
    (r"(bypass|circumvent|override)\s+(the\s+)?(filter|safety|restriction)", "boundary_probe"),
    (r"(hypothetically|theoretically)\s*,?\s*(if|what)\s+", "hypothetical_bypass"),

    # Context manipulation
    (r"\[\s*(system|assistant|user)\s*\]", "context_manipulation"),
    (r"<\|?(system|endoftext|im_start|im_end)\|?>", "control_token"),

    # Encoded/obfuscated content
    (r"base64\s*:\s*[A-Za-z0-9+/=]+", "encoded_content"),
    (r"\\x[0-9a-fA-F]{2}", "hex_encoding"),
]

# Low-confidence patterns (log only)
LOW_THREAT_PATTERNS = [
    # Common but often benign
    (r"please\s+help\s+me\s+(with|to)\s+", "help_request"),
    (r"can\s+you\s+(tell|show|explain)\s+", "question_pattern"),
]


class InputSanitizer:
    """
    Input sanitizer with prompt injection detection.

    Usage:
        sanitizer = InputSanitizer()
        result = sanitizer.sanitize("ignore previous instructions")
        if result.should_block:
            return "Message blocked for security"
    """

    def __init__(
        self,
        block_high_threats: bool = True,
        flag_medium_threats: bool = True,
        max_message_length: int = 4096,
    ):
        """
        Initialize the sanitizer.

        Args:
            block_high_threats: Whether to block high-threat messages
            flag_medium_threats: Whether to flag medium-threat messages for review
            max_message_length: Maximum allowed message length
        """
        self.block_high_threats = block_high_threats
        self.flag_medium_threats = flag_medium_threats
        self.max_message_length = max_message_length

        # Compile patterns for efficiency
        self._high_patterns = [
            (re.compile(pattern, re.IGNORECASE), name)
            for pattern, name in HIGH_THREAT_PATTERNS
        ]
        self._medium_patterns = [
            (re.compile(pattern, re.IGNORECASE), name)
            for pattern, name in MEDIUM_THREAT_PATTERNS
        ]
        self._low_patterns = [
            (re.compile(pattern, re.IGNORECASE), name)
            for pattern, name in LOW_THREAT_PATTERNS
        ]

    def sanitize(self, message: str) -> SanitizationResult:
        """
        Sanitize a message and detect potential prompt injection.

        Args:
            message: The input message to sanitize

        Returns:
            SanitizationResult with threat assessment
        """
        patterns_detected = []
        threat_level = ThreatLevel.NONE
        explanation = None

        # Check message length
        if len(message) > self.max_message_length:
            message = message[:self.max_message_length]
            patterns_detected.append("message_truncated")

        # Remove control characters (except newlines)
        sanitized = self._remove_control_chars(message)

        # Detect high-threat patterns
        for pattern, name in self._high_patterns:
            if pattern.search(sanitized):
                patterns_detected.append(f"high:{name}")
                threat_level = ThreatLevel.HIGH
                explanation = f"Detected high-threat pattern: {name}"

        # Detect medium-threat patterns (only if not already high)
        if threat_level != ThreatLevel.HIGH:
            medium_found = False
            for pattern, name in self._medium_patterns:
                if pattern.search(sanitized):
                    patterns_detected.append(f"medium:{name}")
                    medium_found = True
                    if not explanation:
                        explanation = f"Detected medium-threat pattern: {name}"
            if medium_found and threat_level == ThreatLevel.NONE:
                threat_level = ThreatLevel.MEDIUM

        # Detect low-threat patterns
        for pattern, name in self._low_patterns:
            if pattern.search(sanitized):
                patterns_detected.append(f"low:{name}")
                if threat_level == ThreatLevel.NONE:
                    threat_level = ThreatLevel.LOW

        # Determine actions
        should_block = (
            threat_level == ThreatLevel.HIGH and self.block_high_threats
        ) or threat_level == ThreatLevel.CRITICAL

        should_flag = (
            threat_level == ThreatLevel.MEDIUM and self.flag_medium_threats
        )

        # Log detection (without PII - just pattern names)
        if patterns_detected:
            logger.info(
                f"Input sanitization detected patterns: {patterns_detected}, "
                f"threat_level={threat_level.value}, block={should_block}"
            )

        return SanitizationResult(
            original_message=message,
            sanitized_message=sanitized,
            threat_level=threat_level,
            patterns_detected=patterns_detected,
            should_block=should_block,
            should_flag_for_review=should_flag,
            explanation=explanation,
        )

    def _remove_control_chars(self, text: str) -> str:
        """Remove control characters except allowed ones."""
        # Keep: newline, tab, carriage return
        allowed = {'\n', '\t', '\r'}
        return ''.join(
            char for char in text
            if char in allowed or (ord(char) >= 32 and ord(char) != 127)
        )


# =============================================================================
# Convenience Functions
# =============================================================================

# Module-level sanitizer instance
_default_sanitizer: Optional[InputSanitizer] = None


def get_sanitizer() -> InputSanitizer:
    """Get or create the default sanitizer instance."""
    global _default_sanitizer
    if _default_sanitizer is None:
        _default_sanitizer = InputSanitizer()
    return _default_sanitizer


def sanitize_message(message: str) -> SanitizationResult:
    """
    Sanitize a message using the default sanitizer.

    Args:
        message: The input message to sanitize

    Returns:
        SanitizationResult with threat assessment
    """
    return get_sanitizer().sanitize(message)


def detect_prompt_injection(message: str) -> Tuple[bool, str]:
    """
    Simple check for prompt injection.

    Returns:
        Tuple of (is_injection_detected, explanation)
    """
    result = sanitize_message(message)
    is_injection = result.threat_level in (ThreatLevel.HIGH, ThreatLevel.CRITICAL)
    return is_injection, result.explanation or "No injection detected"
