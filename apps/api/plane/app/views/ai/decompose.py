# Copyright (c) 2024-present ClaudePlane contributors
# SPDX-License-Identifier: AGPL-3.0-only

"""
Issue decomposition endpoint: takes a large issue and generates
subtask suggestions using the configured LLM provider.
"""

import json

from rest_framework import status
from rest_framework.response import Response

from plane.app.permissions import ROLE, allow_permission
from plane.app.views.external.base import get_llm_config
from plane.db.models import Issue, Project, Workspace
from plane.utils.llm_tracker import tracked_llm_response

from ..base import BaseAPIView


class IssueDecomposeEndpoint(BaseAPIView):
    """
    POST /api/workspaces/<slug>/projects/<project_id>/ai/decompose/<issue_id>/

    Analyzes a complex issue and suggests a breakdown into smaller,
    actionable subtasks with estimated complexity.
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

        # Get existing sub-issues for context
        existing_subtasks = list(
            Issue.objects.filter(
                parent_id=issue_id, project_id=project_id
            ).values_list("name", flat=True)
        )

        max_subtasks = request.data.get("max_subtasks", 8)

        task = "You are a project management AI that breaks down complex issues into actionable subtasks."
        prompt = f"""Parent Issue Title: {issue.name}
Parent Issue Description: {issue.description_stripped or 'No description provided'}
Priority: {issue.priority}
{"Existing Subtasks: " + ", ".join(existing_subtasks) if existing_subtasks else "No existing subtasks."}

Break this issue into up to {max_subtasks} actionable subtasks.

Respond with ONLY a valid JSON object (no markdown, no explanation) with these fields:
- "subtasks": array of objects, each with:
  - "title": concise subtask title
  - "description": 1-2 sentence description of what needs to be done
  - "priority": one of "urgent", "high", "medium", "low", "none"
  - "complexity": one of "trivial", "small", "medium", "large", "epic"
  - "order": suggested execution order (1-based)
- "rationale": brief explanation of the decomposition strategy
"""

        workspace = Workspace.objects.get(slug=slug)
        project = Project.objects.get(pk=project_id)

        text, error = tracked_llm_response(
            task, prompt, api_key, model, provider, base_url,
            user=request.user,
            workspace=workspace,
            project=project,
            endpoint="ai/decompose",
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
                "decomposition": result,
            },
            status=status.HTTP_200_OK,
        )
