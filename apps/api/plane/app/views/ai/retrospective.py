# Copyright (c) 2024-present ClaudePlane contributors
# SPDX-License-Identifier: AGPL-3.0-only

"""
Sprint retrospective generator endpoint: generates retro reports from
completed cycle data including velocity, completion rates, and insights.
"""

import json

from django.db.models import Count, Q
from rest_framework import status
from rest_framework.response import Response

from plane.app.permissions import ROLE, allow_permission
from plane.app.views.external.base import get_llm_config
from plane.db.models import Issue, Cycle, CycleIssue, Project, Workspace
from plane.utils.llm_tracker import tracked_llm_response

from ..base import BaseAPIView


class RetrospectiveEndpoint(BaseAPIView):
    """
    POST /api/workspaces/<slug>/projects/<project_id>/ai/retrospective/<cycle_id>/

    Generates a sprint retrospective report from cycle data including
    what went well, what didn't, and improvement suggestions.
    """

    @allow_permission([ROLE.ADMIN, ROLE.MEMBER])
    def post(self, request, slug, project_id, cycle_id):
        api_key, model, provider, base_url = get_llm_config()
        if not api_key or not model or not provider:
            return Response(
                {"error": "LLM provider not configured"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            cycle = Cycle.objects.get(pk=cycle_id, project_id=project_id)
        except Cycle.DoesNotExist:
            return Response({"error": "Cycle not found"}, status=status.HTTP_404_NOT_FOUND)

        # Gather cycle statistics
        cycle_issue_ids = CycleIssue.objects.filter(
            cycle=cycle
        ).values_list("issue_id", flat=True)

        all_issues = Issue.objects.filter(id__in=cycle_issue_ids)
        total_count = all_issues.count()
        completed_count = all_issues.filter(completed_at__isnull=False).count()
        
        # Priority breakdown
        priority_stats = dict(
            all_issues.values_list("priority").annotate(count=Count("id")).values_list("priority", "count")
        )

        # Completed issues details
        completed_issues = all_issues.filter(completed_at__isnull=False)
        incomplete_issues = all_issues.filter(completed_at__isnull=True)

        completed_text = [f"- \"{i.name}\" (priority: {i.priority})" for i in completed_issues[:30]]
        incomplete_text = [f"- \"{i.name}\" (priority: {i.priority})" for i in incomplete_issues[:20]]

        task = "You are an agile coach generating a sprint retrospective report."
        prompt = f"""Sprint/Cycle: {cycle.name}
{f"Period: {cycle.start_date.strftime('%Y-%m-%d')} to {cycle.end_date.strftime('%Y-%m-%d')}" if cycle.start_date and cycle.end_date else ""}

Statistics:
- Total issues: {total_count}
- Completed: {completed_count} ({round(completed_count/total_count*100) if total_count else 0}%)
- Incomplete: {total_count - completed_count}
- Priority breakdown: {json.dumps(priority_stats)}

Completed Issues:
{chr(10).join(completed_text) if completed_text else "None"}

Incomplete Issues:
{chr(10).join(incomplete_text) if incomplete_text else "None"}

Generate a retrospective report.

Respond with ONLY a valid JSON object (no markdown, no explanation) with these fields:
- "summary": 2-3 sentence overview of the sprint
- "completion_rate": percentage as integer
- "velocity_assessment": "above_target", "on_target", "below_target"
- "went_well": array of 3-5 things that went well
- "needs_improvement": array of 3-5 things that need improvement
- "action_items": array of specific, actionable improvement suggestions
- "patterns": array of observed patterns or trends
- "team_health": "healthy", "moderate", "at_risk" with brief explanation
"""

        workspace = Workspace.objects.get(slug=slug)
        project = Project.objects.get(pk=project_id)

        text, error = tracked_llm_response(
            task, prompt, api_key, model, provider, base_url,
            user=request.user,
            workspace=workspace,
            project=project,
            endpoint="ai/retrospective",
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
                "cycle_id": str(cycle.id),
                "cycle_name": cycle.name,
                "statistics": {
                    "total_issues": total_count,
                    "completed": completed_count,
                    "completion_rate": round(completed_count / total_count * 100) if total_count else 0,
                    "priority_breakdown": priority_stats,
                },
                "retrospective": result,
            },
            status=status.HTTP_200_OK,
        )
