# Copyright (c) 2024-present ClaudePlane contributors
# SPDX-License-Identifier: AGPL-3.0-only

"""
AI endpoint rate limiting.

Provides configurable per-provider rate limits for AI API endpoints
to prevent runaway LLM costs and ensure fair usage across users.
Rate limits are configured via environment variables.
"""

import os

from rest_framework.throttling import UserRateThrottle


class AIEndpointThrottle(UserRateThrottle):
    """
    Rate limiter for AI endpoints.
    
    Configurable via AI_RATE_LIMIT env var.
    Default: 30 requests per minute per user.
    Format: "<count>/<period>" (e.g., "30/minute", "100/hour")
    """

    scope = "ai_endpoint"

    def get_rate(self):
        """Return the rate limit from environment or default."""
        return os.environ.get("AI_RATE_LIMIT", "30/minute")


class AIBurstThrottle(UserRateThrottle):
    """
    Burst rate limiter for AI endpoints.
    
    Prevents rapid-fire AI requests. Configurable via AI_BURST_LIMIT.
    Default: 5 requests per 10 seconds per user.
    """

    scope = "ai_burst"

    def get_rate(self):
        """Return the burst rate limit from environment or default."""
        return os.environ.get("AI_BURST_LIMIT", "5/minute")


class WebhookThrottle(UserRateThrottle):
    """
    Rate limiter for webhook endpoints.
    
    Configurable via WEBHOOK_RATE_LIMIT env var.
    Default: 60 requests per minute.
    """

    scope = "webhook"

    def get_rate(self):
        """Return the webhook rate limit from environment or default."""
        return os.environ.get("WEBHOOK_RATE_LIMIT", "60/minute")
