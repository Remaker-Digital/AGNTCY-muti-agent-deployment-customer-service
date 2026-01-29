"""
Rate Limiter with Sliding Window Algorithm

This module provides rate limiting to prevent:
1. API abuse and denial of service
2. Cost overruns from excessive AI API calls
3. Brute force attacks on endpoints

Educational Notes:
- Sliding window is more accurate than fixed window
- We use in-memory storage for simplicity (consider Redis for distributed)
- Rate limits are per-session to allow fair usage
- Configurable via environment variables

Algorithm:
- Track timestamps of requests in a sliding window
- Count requests within the window period
- Allow or deny based on configured limit

See: docs/SECURITY-REMEDIATION-2026-01-28.md
"""

import os
import time
import logging
from collections import defaultdict
from dataclasses import dataclass
from threading import Lock
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class RateLimitConfig:
    """Configuration for rate limiting."""

    # Requests per window
    max_requests: int = 30

    # Window size in seconds
    window_seconds: int = 60

    # Whether to track by session or IP
    track_by_session: bool = True

    # Burst allowance (extra requests for sudden spikes)
    burst_allowance: int = 5

    # Cooldown period after limit hit (seconds)
    cooldown_seconds: int = 30


@dataclass
class RateLimitResult:
    """Result of a rate limit check."""

    allowed: bool
    current_count: int
    limit: int
    remaining: int
    reset_seconds: float
    retry_after: Optional[float] = None
    reason: Optional[str] = None


class RateLimiter:
    """
    Sliding window rate limiter.

    Usage:
        limiter = RateLimiter()
        result = limiter.check("session-123")
        if not result.allowed:
            return f"Rate limited. Retry after {result.retry_after}s"
    """

    def __init__(self, config: Optional[RateLimitConfig] = None):
        """
        Initialize the rate limiter.

        Args:
            config: Rate limit configuration (uses defaults if not provided)
        """
        self.config = config or RateLimitConfig(
            max_requests=int(os.getenv("RATE_LIMIT_REQUESTS", "30")),
            window_seconds=int(os.getenv("RATE_LIMIT_WINDOW_SECONDS", "60")),
            burst_allowance=int(os.getenv("RATE_LIMIT_BURST", "5")),
            cooldown_seconds=int(os.getenv("RATE_LIMIT_COOLDOWN", "30")),
        )

        # Storage: key -> list of timestamps
        self._requests: Dict[str, List[float]] = defaultdict(list)

        # Cooldown tracking: key -> cooldown_end_time
        self._cooldowns: Dict[str, float] = {}

        # Thread safety
        self._lock = Lock()

        logger.info(
            f"Rate limiter initialized: {self.config.max_requests} requests "
            f"per {self.config.window_seconds}s window"
        )

    def check(self, key: str) -> RateLimitResult:
        """
        Check if a request should be allowed.

        Args:
            key: Identifier for rate limiting (session_id or IP)

        Returns:
            RateLimitResult indicating whether request is allowed
        """
        with self._lock:
            now = time.time()

            # Check cooldown first
            if key in self._cooldowns:
                cooldown_end = self._cooldowns[key]
                if now < cooldown_end:
                    retry_after = cooldown_end - now
                    return RateLimitResult(
                        allowed=False,
                        current_count=self.config.max_requests,
                        limit=self.config.max_requests,
                        remaining=0,
                        reset_seconds=retry_after,
                        retry_after=retry_after,
                        reason="Cooldown active after rate limit exceeded",
                    )
                else:
                    # Cooldown expired
                    del self._cooldowns[key]

            # Get current requests and filter to window
            window_start = now - self.config.window_seconds
            self._requests[key] = [
                ts for ts in self._requests[key]
                if ts > window_start
            ]

            current_count = len(self._requests[key])
            effective_limit = self.config.max_requests + self.config.burst_allowance

            # Check if under limit
            if current_count < effective_limit:
                # Allow and record
                self._requests[key].append(now)

                # Calculate remaining (without burst)
                remaining = max(0, self.config.max_requests - current_count - 1)

                # Calculate reset time (oldest request + window)
                if self._requests[key]:
                    oldest = min(self._requests[key])
                    reset_seconds = max(0, oldest + self.config.window_seconds - now)
                else:
                    reset_seconds = self.config.window_seconds

                return RateLimitResult(
                    allowed=True,
                    current_count=current_count + 1,
                    limit=self.config.max_requests,
                    remaining=remaining,
                    reset_seconds=reset_seconds,
                )
            else:
                # Rate limited - set cooldown
                self._cooldowns[key] = now + self.config.cooldown_seconds

                # Log rate limit hit
                logger.warning(
                    f"Rate limit exceeded for key={key[:16]}..., "
                    f"count={current_count}, limit={effective_limit}"
                )

                return RateLimitResult(
                    allowed=False,
                    current_count=current_count,
                    limit=self.config.max_requests,
                    remaining=0,
                    reset_seconds=self.config.cooldown_seconds,
                    retry_after=self.config.cooldown_seconds,
                    reason=f"Rate limit exceeded: {current_count} requests in {self.config.window_seconds}s",
                )

    def reset(self, key: str) -> None:
        """
        Reset rate limit for a key.

        Args:
            key: Identifier to reset
        """
        with self._lock:
            if key in self._requests:
                del self._requests[key]
            if key in self._cooldowns:
                del self._cooldowns[key]

    def get_stats(self, key: str) -> Dict:
        """
        Get current rate limit stats for a key.

        Args:
            key: Identifier to check

        Returns:
            Dict with current stats
        """
        with self._lock:
            now = time.time()
            window_start = now - self.config.window_seconds

            requests = [
                ts for ts in self._requests.get(key, [])
                if ts > window_start
            ]

            return {
                "key": key[:16] + "..." if len(key) > 16 else key,
                "current_count": len(requests),
                "limit": self.config.max_requests,
                "remaining": max(0, self.config.max_requests - len(requests)),
                "window_seconds": self.config.window_seconds,
                "in_cooldown": key in self._cooldowns,
            }

    def cleanup(self, max_age_seconds: int = 3600) -> int:
        """
        Clean up old entries to prevent memory growth.

        Args:
            max_age_seconds: Remove entries older than this

        Returns:
            Number of entries removed
        """
        with self._lock:
            now = time.time()
            cutoff = now - max_age_seconds
            removed = 0

            # Clean old requests
            keys_to_remove = []
            for key, timestamps in self._requests.items():
                # Filter to recent timestamps
                recent = [ts for ts in timestamps if ts > cutoff]
                if not recent:
                    keys_to_remove.append(key)
                else:
                    self._requests[key] = recent

            for key in keys_to_remove:
                del self._requests[key]
                removed += 1

            # Clean expired cooldowns
            expired_cooldowns = [
                key for key, end_time in self._cooldowns.items()
                if end_time < now
            ]
            for key in expired_cooldowns:
                del self._cooldowns[key]

            return removed


# =============================================================================
# Module-level instance
# =============================================================================

_default_limiter: Optional[RateLimiter] = None


def get_rate_limiter() -> RateLimiter:
    """Get or create the default rate limiter instance."""
    global _default_limiter
    if _default_limiter is None:
        _default_limiter = RateLimiter()
    return _default_limiter


def check_rate_limit(key: str) -> RateLimitResult:
    """
    Check rate limit using the default limiter.

    Args:
        key: Identifier for rate limiting

    Returns:
        RateLimitResult
    """
    return get_rate_limiter().check(key)
