# Copyright (c) 2024-present ClaudePlane contributors
# SPDX-License-Identifier: AGPL-3.0-only

"""
Auto-triage endpoint: analyzes an issue's title and description to suggest
priority, labels, and assignee using the configured LLM provider.
"""

import json

from rest_framework import status
from rest_framework.response import Response

from plane.app.permissions import ROLE, allow_permission
from plane.app.views.external.base import get_llm_config
from plane.db.models import Issue, Label, Project, Workspace
from plane.utils.exception_logger import log_exception
from plane.utils.llm_tracker import tracked_llm_response

from ..base import BaseAPIView


class IssueAutoTriageEndpoint(BaseAPIView):
    """
    POST /api/workspaces/<slug>/projects/<project_id>/ai/triage/<issue_id>/

    Uses the configured LLM to analyze an issue and suggest:
    - Priority (urgent, high, medium, low, none)
    - Labels (from existing project labels)
    - Assignee suggestion based on recent activity
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
            return Response(
                {"error": "Issue not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Gather project labels for context
        project_labels = list(
            Label.objects.filter(project_id=project_id).values_list("name", flat=True)
        )

        # Gather recent assignees for suggestion
        from plane.db.models import IssueAssignee, User
        recent_assignees = list(
            IssueAssignee.objects.filter(
                issue__project_id=project_id
            ).select_related("assignee").values_list(
                "assignee__display_name", flat=True
            ).distinct()[:20]
        )

        task = "You are a project management AI assistant. Analyze the following issue and suggest triage actions."
        prompt = f"""Issue Title: {issue.name}
Issue Description: {issue.description_stripped or 'No description provided'}

Available Labels: {', '.join(project_labels) if project_labels else 'None'}
Recent Team Members: {', '.join(recent_assignees) if recent_assignees else 'Unknown'}

Respond with ONLY a valid JSON object (no markdown, no explanation) with these fields:
- "priority": one of "urgent", "high", "medium", "low", "none"
- "priority_reason": brief explanation for the priority choice
- "suggested_labels": array of label names from the available labels that apply
- "suggested_assignee": name of the most appropriate team member or null
- "assignee_reason": why this person was suggested or null
- "category": one of "bug", "feature", "improvement", "task", "question"
"""

        workspace = Workspace.objects.get(slug=slug)
        project = Project.objects.get(pk=project_id)

        text, error = tracked_llm_response(
            task, prompt, api_key, model, provider, base_url,
            user=request.user,
            workspace=workspace,
            project=project,
            endpoint="ai/triage",
        )

        if not text and error:
            return Response(
                {"error": "Failed to get AI response"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        # Parse JSON response from LLM
        try:
            # Strip markdown code fences if present
            cleaned = text.strip()
            if cleaned.startswith("```"):
                cleaned = cleaned.split("\n", 1)[1] if "\n" in cleaned else cleaned[3:]
                if cleaned.endswith("```"):
                    cleaned = cleaned[:-3]
            suggestions = json.loads(cleaned)
        except (json.JSONDecodeError, ValueError):
            suggestions = {"raw_response": text}

        return Response(
            {
                "issue_id": str(issue.id),
                "suggestions": suggestions,
            },
            status=status.HTTP_200_OK,
        )
