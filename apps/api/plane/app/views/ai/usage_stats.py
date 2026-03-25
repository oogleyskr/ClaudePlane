# Copyright (c) 2024-present ClaudePlane contributors
# SPDX-License-Identifier: AGPL-3.0-only

"""
LLM usage statistics endpoint for admin dashboards.
Provides aggregated usage data including token counts, costs,
request volumes, and per-provider breakdowns.
"""

from datetime import timedelta

from django.db.models import Sum, Count, Avg, F
from django.utils import timezone
from rest_framework import status
from rest_framework.response import Response

from plane.app.permissions import ROLE, allow_permission
from plane.db.models import LLMUsageLog

from ..base import BaseAPIView


class LLMUsageStatsEndpoint(BaseAPIView):
    """
    GET /api/workspaces/<slug>/ai/usage-stats/

    Returns aggregated LLM usage statistics for the workspace.
    
    Query parameters:
    - days: lookback period in days (default: 30)
    """

    @allow_permission(allowed_roles=[ROLE.ADMIN], level="WORKSPACE")
    def get(self, request, slug):
        days = int(request.GET.get("days", 30))
        since = timezone.now() - timedelta(days=days)

        base_qs = LLMUsageLog.objects.filter(
            workspace__slug=slug,
            created_at__gte=since,
        )

        # Overall aggregates
        totals = base_qs.aggregate(
            total_requests=Count("id"),
            total_tokens=Sum("total_tokens"),
            total_prompt_tokens=Sum("prompt_tokens"),
            total_completion_tokens=Sum("completion_tokens"),
            total_cost_cents=Sum("estimated_cost_cents"),
            avg_latency_ms=Avg("latency_ms"),
            success_count=Count("id", filter=F("success")),
        )

        # Per-provider breakdown
        provider_stats = list(
            base_qs.values("provider").annotate(
                requests=Count("id"),
                tokens=Sum("total_tokens"),
                cost_cents=Sum("estimated_cost_cents"),
                avg_latency=Avg("latency_ms"),
            ).order_by("-requests")
        )

        # Per-model breakdown
        model_stats = list(
            base_qs.values("model").annotate(
                requests=Count("id"),
                tokens=Sum("total_tokens"),
                cost_cents=Sum("estimated_cost_cents"),
            ).order_by("-requests")
        )

        # Per-endpoint breakdown
        endpoint_stats = list(
            base_qs.values("endpoint").annotate(
                requests=Count("id"),
                tokens=Sum("total_tokens"),
                cost_cents=Sum("estimated_cost_cents"),
            ).order_by("-requests")
        )

        # Daily trends (last N days)
        from django.db.models.functions import TruncDate
        daily_stats = list(
            base_qs.annotate(
                day=TruncDate("created_at")
            ).values("day").annotate(
                requests=Count("id"),
                tokens=Sum("total_tokens"),
                cost_cents=Sum("estimated_cost_cents"),
            ).order_by("day")
        )

        # Format daily stats for JSON serialization
        for stat in daily_stats:
            stat["day"] = stat["day"].isoformat() if stat["day"] else None

        # Calculate success rate
        total_req = totals["total_requests"] or 0
        success_count = totals.pop("success_count", 0) or 0
        success_rate = round((success_count / total_req * 100), 1) if total_req > 0 else 0

        return Response(
            {
                "period_days": days,
                "totals": {
                    **totals,
                    "success_rate_pct": success_rate,
                    "estimated_cost_usd": round((totals["total_cost_cents"] or 0) / 100, 4),
                },
                "by_provider": provider_stats,
                "by_model": model_stats,
                "by_endpoint": endpoint_stats,
                "daily_trend": daily_stats,
            },
            status=status.HTTP_200_OK,
        )
