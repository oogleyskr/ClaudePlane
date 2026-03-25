# Copyright (c) 2024-present ClaudePlane contributors
# SPDX-License-Identifier: AGPL-3.0-only

"""
Issue complexity estimator endpoint: uses LLM to estimate story points
and complexity for issues based on their descriptions.
"""

import json

from rest_framework import status
from rest_framework.response import Response

from plane.app.permissions import ROLE, allow_permission
from plane.app.views.external.base import get_llm_config
from plane.db.models import Issue, Project, Workspace
from plane.utils.llm_tracker import tracked_llm_response

from ..base import BaseAPIView


class IssueComplexityEndpoint(BaseAPIView):
    """
    POST /api/workspaces/<slug>/projects/<project_id>/ai/estimate/<issue_id>/

    Uses LLM to estimate issue complexity (story points) based on the
    issue title, description, and project context.
    """

    @allow_permission([ROLE.ADMIN, ROLE.MEMBER])
    def post(self, request, slug, project_id, issue_id):
        api_key, model, provider, base_url = get_llm_config()
        if not api_key or not model or not provider:
            return Response(
                {"error": "LLM provider not configured"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            issue = Issue.objects.get(pk=issue_id, project_id=project_id)
        except Issue.DoesNotExist:
            return Response({"error": "Issue not found"}, status=status.HTTP_404_NOT_FOUND)

        # Get recently estimated issues for calibration
        calibration_issues = Issue.issue_objects.filter(
            project_id=project_id,
            point__isnull=False,
        ).order_by("-updated_at")[:10]

        cal_text = []
        for ci in calibration_issues:
            cal_text.append(f"- \"{ci.name}\" -> {ci.point} points")

        task = "You are a software estimation AI. Estimate issue complexity using story points."
        prompt = f"""Issue to Estimate:
Title: {issue.name}
Description: {issue.description_stripped or 'No description provided'}
Priority: {issue.priority}

{"Recent estimates for calibration:" + chr(10) + chr(10).join(cal_text) if cal_text else "No previous estimates for calibration."}

Using the Fibonacci scale (1, 2, 3, 5, 8, 13), estimate this issue.

Respond with ONLY a valid JSON object (no markdown, no explanation) with these fields:
- "story_points": integer from Fibonacci scale (1, 2, 3, 5, 8, 13)
- "complexity": one of "trivial", "simple", "moderate", "complex", "very_complex"
- "confidence": 0.0 to 1.0 (how confident the estimate is)
- "reasoning": brief explanation of the estimate
- "risks": array of risk factors that could increase complexity
- "assumptions": array of assumptions made during estimation
"""

        workspace = Workspace.objects.get(slug=slug)
        project = Project.objects.get(pk=project_id)

        text, error = tracked_llm_response(
            task, prompt, api_key, model, provider, base_url,
            user=request.user,
            workspace=workspace,
            project=project,
            endpoint="ai/estimate",
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
                "issue_id": str(issue.id),
                "estimate": result,
            },
            status=status.HTTP_200_OK,
        )
