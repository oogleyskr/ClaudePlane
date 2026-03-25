# Copyright (c) 2024-present ClaudePlane contributors
# SPDX-License-Identifier: AGPL-3.0-only

"""
Release notes generator endpoint: auto-generates release notes from
completed issues in a cycle/sprint.
"""

import json

from rest_framework import status
from rest_framework.response import Response

from plane.app.permissions import ROLE, allow_permission
from plane.app.views.external.base import get_llm_config
from plane.db.models import Issue, Cycle, CycleIssue, Project, Workspace
from plane.utils.llm_tracker import tracked_llm_response

from ..base import BaseAPIView


class ReleaseNotesEndpoint(BaseAPIView):
    """
    POST /api/workspaces/<slug>/projects/<project_id>/ai/release-notes/<cycle_id>/

    Generates formatted release notes from all completed issues in a cycle.
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

        # Get completed issues in this cycle
        cycle_issue_ids = CycleIssue.objects.filter(
            cycle=cycle
        ).values_list("issue_id", flat=True)

        completed_issues = Issue.objects.filter(
            id__in=cycle_issue_ids,
            completed_at__isnull=False,
        ).select_related("state")

        if not completed_issues.exists():
            return Response(
                {"error": "No completed issues in this cycle"},
                status=status.HTTP_404_NOT_FOUND,
            )

        issues_text = []
        for issue in completed_issues:
            labels = list(issue.labels.values_list("name", flat=True))
            issues_text.append(
                f"- \"{issue.name}\" | Priority: {issue.priority} | "
                f"Labels: {', '.join(labels) if labels else 'none'}"
            )

        format_style = request.data.get("format", "markdown")

        task = "You are a release notes writer for a software product."
        prompt = f"""Cycle: {cycle.name}
{f"Period: {cycle.start_date.strftime('%Y-%m-%d')} to {cycle.end_date.strftime('%Y-%m-%d')}" if cycle.start_date and cycle.end_date else ""}

Completed Issues:
{chr(10).join(issues_text)}

Generate professional release notes in {format_style} format.

Respond with ONLY a valid JSON object (no markdown fences, no explanation) with these fields:
- "title": release notes title
- "summary": 2-3 sentence high-level summary
- "sections": array of objects, each with:
  - "heading": section heading (e.g., "New Features", "Bug Fixes", "Improvements")
  - "items": array of human-readable bullet points
- "highlights": array of the top 3 most impactful changes
- "markdown": the full release notes as a markdown string
"""

        workspace = Workspace.objects.get(slug=slug)
        project = Project.objects.get(pk=project_id)

        text, error = tracked_llm_response(
            task, prompt, api_key, model, provider, base_url,
            user=request.user,
            workspace=workspace,
            project=project,
            endpoint="ai/release-notes",
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
            result = {"markdown": text}

        return Response(
            {
                "cycle_id": str(cycle.id),
                "cycle_name": cycle.name,
                "release_notes": result,
            },
            status=status.HTTP_200_OK,
        )
