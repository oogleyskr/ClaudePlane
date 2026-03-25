# Copyright (c) 2024-present ClaudePlane contributors
# SPDX-License-Identifier: AGPL-3.0-only

"""
Sprint planning AI endpoint: analyzes the backlog and suggests which
issues to include in the next cycle based on priority, complexity,
and team capacity.
"""

import json

from rest_framework import status
from rest_framework.response import Response

from plane.app.permissions import ROLE, allow_permission
from plane.app.views.external.base import get_llm_config
from plane.db.models import Issue, Cycle, CycleIssue, Project, Workspace
from plane.utils.llm_tracker import tracked_llm_response

from ..base import BaseAPIView


class SprintPlannerEndpoint(BaseAPIView):
    """
    POST /api/workspaces/<slug>/projects/<project_id>/ai/sprint-plan/

    Analyzes the project backlog and suggests which issues to include
    in the next sprint/cycle.

    Optional request body fields:
    - cycle_id: target cycle UUID (uses next upcoming cycle if not specified)
    - team_capacity: number of story points the team can handle
    - focus_areas: list of label names to prioritize
    """

    @allow_permission([ROLE.ADMIN, ROLE.MEMBER])
    def post(self, request, slug, project_id):
        api_key, model, provider, base_url = get_llm_config()
        if not api_key or not model or not provider:
            return Response(
                {"error": "LLM provider not configured"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        team_capacity = request.data.get("team_capacity", 40)
        focus_areas = request.data.get("focus_areas", [])

        # Get backlog issues (not in any active cycle, not completed)
        assigned_issue_ids = CycleIssue.objects.filter(
            cycle__project_id=project_id,
        ).values_list("issue_id", flat=True)

        backlog_issues = Issue.issue_objects.filter(
            project_id=project_id,
            completed_at__isnull=True,
        ).exclude(
            id__in=assigned_issue_ids,
        ).order_by("-priority", "-created_at")[:50]

        if not backlog_issues.exists():
            return Response(
                {"error": "No backlog issues found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Format issues for LLM
        issues_text = []
        for issue in backlog_issues:
            issues_text.append(
                f"- [{issue.id}] \"{issue.name}\" | Priority: {issue.priority} | "
                f"Points: {issue.point or 'unestimated'} | "
                f"Created: {issue.created_at.strftime('%Y-%m-%d')}"
            )

        task = "You are a sprint planning AI assistant for agile software teams."
        prompt = f"""Team capacity for next sprint: {team_capacity} story points
{f"Focus areas: {', '.join(focus_areas)}" if focus_areas else "No specific focus areas."}

Backlog Issues:
{chr(10).join(issues_text)}

Select the best issues for the next sprint, respecting the team capacity.

Respond with ONLY a valid JSON object (no markdown, no explanation) with these fields:
- "selected_issues": array of objects, each with:
  - "issue_id": the UUID from the list
  - "reason": why this issue was selected
  - "estimated_points": your estimate if unestimated (1-8 scale)
- "total_estimated_points": sum of all estimated points
- "sprint_goal": a 1-sentence sprint goal based on selected issues
- "risks": array of potential risks for this sprint
- "overflow_issues": array of issue IDs that were close but didn't fit capacity
"""

        workspace = Workspace.objects.get(slug=slug)
        project = Project.objects.get(pk=project_id)

        text, error = tracked_llm_response(
            task, prompt, api_key, model, provider, base_url,
            user=request.user,
            workspace=workspace,
            project=project,
            endpoint="ai/sprint-plan",
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
            {"sprint_plan": result},
            status=status.HTTP_200_OK,
        )
