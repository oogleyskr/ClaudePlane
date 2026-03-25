# Copyright (c) 2024-present ClaudePlane contributors
# SPDX-License-Identifier: AGPL-3.0-only

"""
Daily digest generator endpoint: creates a summary of project activity
over a configurable time window.
"""

import json
from datetime import timedelta

from django.db.models import Count
from django.utils import timezone
from rest_framework import status
from rest_framework.response import Response

from plane.app.permissions import ROLE, allow_permission
from plane.app.views.external.base import get_llm_config
from plane.db.models import Issue, Project, Workspace
from plane.utils.llm_tracker import tracked_llm_response

from ..base import BaseAPIView


class DailyDigestEndpoint(BaseAPIView):
    """
    POST /api/workspaces/<slug>/projects/<project_id>/ai/digest/

    Generates a daily (or custom period) digest of project activity.

    Request body:
    - days: number of days to look back (default: 1)
    """

    @allow_permission([ROLE.ADMIN, ROLE.MEMBER])
    def post(self, request, slug, project_id):
        api_key, model, provider, base_url = get_llm_config()
        if not api_key or not model or not provider:
            return Response(
                {"error": "LLM provider not configured"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        days = request.data.get("days", 1)
        since = timezone.now() - timedelta(days=days)

        # Gather activity data
        new_issues = Issue.issue_objects.filter(
            project_id=project_id,
            created_at__gte=since,
        ).order_by("-created_at")[:30]

        completed_issues = Issue.issue_objects.filter(
            project_id=project_id,
            completed_at__gte=since,
        ).order_by("-completed_at")[:30]

        updated_issues = Issue.issue_objects.filter(
            project_id=project_id,
            updated_at__gte=since,
        ).exclude(
            id__in=[i.id for i in new_issues]
        ).exclude(
            id__in=[i.id for i in completed_issues]
        ).order_by("-updated_at")[:20]

        # Format for LLM
        new_text = [f"- \"{i.name}\" (priority: {i.priority})" for i in new_issues]
        completed_text = [f"- \"{i.name}\" (priority: {i.priority})" for i in completed_issues]
        updated_text = [f"- \"{i.name}\"" for i in updated_issues]

        task = "You are a project status reporter generating a concise activity digest."
        prompt = f"""Project Activity Digest for the last {days} day(s):

New Issues ({len(new_text)}):
{chr(10).join(new_text) if new_text else "None"}

Completed Issues ({len(completed_text)}):
{chr(10).join(completed_text) if completed_text else "None"}

Updated Issues ({len(updated_text)}):
{chr(10).join(updated_text) if updated_text else "None"}

Generate a concise project digest.

Respond with ONLY a valid JSON object (no markdown, no explanation) with these fields:
- "summary": 2-3 sentence overview of activity
- "highlights": array of the most important items (max 5)
- "metrics": object with "new_count", "completed_count", "updated_count"
- "concerns": array of any concerns or blockers noticed
- "momentum": "accelerating", "steady", "slowing", or "stalled"
- "suggested_focus": what the team should focus on next
"""

        workspace = Workspace.objects.get(slug=slug)
        project = Project.objects.get(pk=project_id)

        text, error = tracked_llm_response(
            task, prompt, api_key, model, provider, base_url,
            user=request.user,
            workspace=workspace,
            project=project,
            endpoint="ai/digest",
        )

        if not text and error:
            return Response(
                {"error": "Failed to get AI response"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        try:
            cleaned = text.strip()
            if cleaned.startswith("```"):
                cleaned = cleaned.split("\n", 1)[1] if "\n" in cleaned else cleaned[3:]
                if cleaned.endswith("```"):
                    cleaned = cleaned[:-3]
            result = json.loads(cleaned)
        except (json.JSONDecodeError, ValueError):
            result = {"raw_response": text}

        return Response(
            {
                "period_days": days,
                "digest": result,
            },
            status=status.HTTP_200_OK,
        )
