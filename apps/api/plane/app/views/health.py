# Copyright (c) 2024-present ClaudePlane contributors
# SPDX-License-Identifier: AGPL-3.0-only

"""
Health check endpoint for ClaudePlane.

Provides a comprehensive health check that verifies connectivity to all
critical services: database, Redis, and (optionally) the configured LLM
provider.  Returns per-service status so operators can quickly pinpoint
which dependency is unhealthy.
"""

import time
import os

from django.db import connection
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from ..views.base import BaseAPIView
from plane.utils.exception_logger import log_exception


class HealthCheckEndpoint(BaseAPIView):
    """
    GET /api/health/
    
    Returns a JSON object with overall health status and individual
    service checks for database, Redis, and the configured LLM provider.
    
    No authentication required — this is meant for load balancers,
    monitoring tools, and operator dashboards.
    """

    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request):
        """
        Perform health checks against all critical services and return
        a structured response with per-service status and latency.
        """
        checks = {}
        overall_healthy = True

        # --- Database check ---
        checks["database"] = self._check_database()
        if checks["database"]["status"] != "healthy":
            overall_healthy = False

        # --- Redis check ---
        checks["redis"] = self._check_redis()
        if checks["redis"]["status"] != "healthy":
            overall_healthy = False

        # --- LLM provider check (non-critical) ---
        checks["llm"] = self._check_llm_config()

        response_data = {
            "status": "healthy" if overall_healthy else "unhealthy",
            "version": "1.0.0-claudeplane",
            "checks": checks,
        }

        http_status = (
            status.HTTP_200_OK if overall_healthy else status.HTTP_503_SERVICE_UNAVAILABLE
        )
        return Response(response_data, status=http_status)

    @staticmethod
    def _check_database():
        """Verify database connectivity with a lightweight query."""
        start = time.monotonic()
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                cursor.fetchone()
            latency_ms = round((time.monotonic() - start) * 1000, 2)
            return {"status": "healthy", "latency_ms": latency_ms}
        except Exception as exc:
            log_exception(exc)
            return {"status": "unhealthy", "error": str(exc)}

    @staticmethod
    def _check_redis():
        """Verify Redis connectivity with a PING command."""
        start = time.monotonic()
        try:
            from plane.settings.redis import redis_instance

            ri = redis_instance()
            ri.ping()
            latency_ms = round((time.monotonic() - start) * 1000, 2)
            return {"status": "healthy", "latency_ms": latency_ms}
        except Exception as exc:
            log_exception(exc)
            return {"status": "unhealthy", "error": str(exc)}

    @staticmethod
    def _check_llm_config():
        """
        Verify that LLM configuration is present.
        Does NOT make an API call — just checks that credentials are configured.
        """
        try:
            from plane.app.views.external.base import get_llm_config

            api_key, model, provider, base_url = get_llm_config()
            if api_key and model and provider:
                return {
                    "status": "configured",
                    "provider": provider,
                    "model": model,
                    "base_url": base_url or "default",
                }
            return {"status": "not_configured"}
        except Exception as exc:
            log_exception(exc)
            return {"status": "error", "error": str(exc)}
