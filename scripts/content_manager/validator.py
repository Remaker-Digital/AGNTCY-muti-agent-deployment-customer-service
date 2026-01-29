# ============================================================================
# Content Validator - Validate Markdown Content for RAG
# ============================================================================
# Purpose: Validates merchant content files for proper formatting before
#          ingestion into the RAG knowledge base.
#
# Validation Rules:
#   1. File must be valid Markdown
#   2. Must have YAML frontmatter with required fields
#   3. Category must be one of: policy, faq, troubleshooting, article, product
#   4. Keywords must be a non-empty list
#   5. Sections should be reasonable size (50-1000 tokens)
#
# Usage:
#   validator = ContentValidator()
#   result = validator.validate(Path("content/return-policy.md"))
#   if result.is_valid:
#       print("Content is valid")
#   else:
#       print(f"Error: {result.error}")
#
# See: docs/WIKI-Merchant-Content-Management.md for content format specification
# ============================================================================

import re
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

import yaml


@dataclass
class ValidationResult:
    """
    Result of content validation.

    Attributes:
        is_valid: True if content passed all validation rules
        error: Error message if validation failed
        warnings: List of non-critical issues
    """
    is_valid: bool
    error: Optional[str] = None
    warnings: List[str] = None

    def __post_init__(self):
        if self.warnings is None:
            self.warnings = []


# Required frontmatter fields for all content
REQUIRED_FIELDS = ["title", "category", "keywords", "last_updated"]

# Valid category values
VALID_CATEGORIES = ["policy", "faq", "troubleshooting", "article", "product"]

# Token count thresholds for warnings
MIN_TOKENS_PER_SECTION = 50
MAX_TOKENS_PER_SECTION = 1000


class ContentValidator:
    """
    Validates markdown content files for RAG knowledge base ingestion.

    This validator checks:
    - YAML frontmatter presence and required fields
    - Category values
    - Keyword list format
    - Section size recommendations

    Attributes:
        strict: If True, warnings are treated as errors
    """

    def __init__(self, strict: bool = False):
        """
        Initialize the validator.

        Args:
            strict: If True, warnings become validation errors
        """
        self.strict = strict

    def validate(self, file_path: Path) -> ValidationResult:
        """
        Validate a markdown content file.

        Checks the file for:
        - Valid markdown format
        - YAML frontmatter with required fields
        - Valid category value
        - Non-empty keywords list
        - Reasonable section sizes

        Args:
            file_path: Path to the markdown file

        Returns:
            ValidationResult with is_valid status and any error/warnings
        """
        try:
            content = file_path.read_text(encoding="utf-8")
        except Exception as e:
            return ValidationResult(is_valid=False, error=f"Cannot read file: {e}")

        # Check for frontmatter
        frontmatter, body = self._parse_frontmatter(content)
        if frontmatter is None:
            return ValidationResult(
                is_valid=False,
                error="Missing YAML frontmatter (must start with ---)"
            )

        # Validate required fields
        for field in REQUIRED_FIELDS:
            if field not in frontmatter:
                return ValidationResult(
                    is_valid=False,
                    error=f"Missing required field: {field}"
                )

        # Validate category
        category = frontmatter.get("category")
        if category not in VALID_CATEGORIES:
            return ValidationResult(
                is_valid=False,
                error=f"Invalid category '{category}'. Must be one of: {', '.join(VALID_CATEGORIES)}"
            )

        # Validate keywords
        keywords = frontmatter.get("keywords", [])
        if not isinstance(keywords, list) or len(keywords) == 0:
            return ValidationResult(
                is_valid=False,
                error="Keywords must be a non-empty list"
            )

        # Check section sizes (warnings)
        warnings = self._check_section_sizes(body)

        # In strict mode, warnings become errors
        if self.strict and warnings:
            return ValidationResult(
                is_valid=False,
                error=f"Strict validation failed: {warnings[0]}"
            )

        return ValidationResult(is_valid=True, warnings=warnings)

    def _parse_frontmatter(self, content: str) -> tuple:
        """
        Parse YAML frontmatter from markdown content.

        Frontmatter is delimited by --- at the start and end.
        Example:
            ---
            title: "My Document"
            category: policy
            ---

        Args:
            content: Full markdown file content

        Returns:
            Tuple of (frontmatter dict, body string) or (None, content)
            if no frontmatter found
        """
        # Match frontmatter pattern: starts with ---, ends with ---
        pattern = r"^---\s*\n(.*?)\n---\s*\n(.*)$"
        match = re.match(pattern, content, re.DOTALL)

        if not match:
            return None, content

        try:
            frontmatter = yaml.safe_load(match.group(1))
            body = match.group(2)
            return frontmatter, body
        except yaml.YAMLError:
            return None, content

    def _check_section_sizes(self, body: str) -> List[str]:
        """
        Check section sizes and return warnings for sections that are
        too small or too large.

        Sections are identified by markdown headers (# or ##).
        Token count is estimated as word count * 1.3 (rough approximation).

        Args:
            body: Markdown body content (without frontmatter)

        Returns:
            List of warning messages
        """
        warnings = []

        # Split by headers (## Section)
        sections = re.split(r"\n(?=#{1,3}\s)", body)

        for section in sections:
            if not section.strip():
                continue

            # Extract section title
            header_match = re.match(r"#{1,3}\s+(.+)\n", section)
            title = header_match.group(1) if header_match else "Untitled"

            # Estimate token count (words * 1.3)
            words = len(section.split())
            estimated_tokens = int(words * 1.3)

            if estimated_tokens < MIN_TOKENS_PER_SECTION:
                warnings.append(
                    f"Section '{title}' is very short ({estimated_tokens} tokens). "
                    f"Consider combining with another section."
                )
            elif estimated_tokens > MAX_TOKENS_PER_SECTION:
                warnings.append(
                    f"Section '{title}' is very long ({estimated_tokens} tokens). "
                    f"Consider splitting into multiple sections."
                )

        return warnings

    def validate_directory(self, dir_path: Path) -> List[tuple]:
        """
        Validate all markdown files in a directory.

        Args:
            dir_path: Path to directory containing markdown files

        Returns:
            List of (file_path, ValidationResult) tuples
        """
        results = []

        for file_path in dir_path.glob("**/*.md"):
            result = self.validate(file_path)
            results.append((file_path, result))

        return results
