# Copyright (c) 2024-present ClaudePlane contributors
# SPDX-License-Identifier: AGPL-3.0-only

"""
Duplicate detection endpoint: uses LLM to find similar existing issues
when creating a new issue, helping prevent duplicates.
"""

import json

from rest_framework import status
from rest_framework.response import Response

from plane.app.permissions import ROLE, allow_permission
from plane.app.views.external.base import get_llm_config
from plane.db.models import Issue, Project, Workspace
from plane.utils.llm_tracker import tracked_llm_response

from ..base import BaseAPIView


class DuplicateDetectionEndpoint(BaseAPIView):
    """
    POST /api/workspaces/<slug>/projects/<project_id>/ai/duplicate-check/

    Checks if a proposed issue (title + description) is similar to any
    existing issues in the project. Returns potential duplicates with
    similarity scores.

    Request body:
    - title: proposed issue title
    - description: proposed issue description (optional)
    """

    @allow_permission([ROLE.ADMIN, ROLE.MEMBER])
    def post(self, request, slug, project_id):
        api_key, model, provider, base_url = get_llm_config()
        if not api_key or not model or not provider:
            return Response(
                {"error": "LLM provider not configured"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        title = request.data.get("title", "")
        description = request.data.get("description", "")

        if not title:
            return Response(
                {"error": "Title is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Get recent open issues for comparison
        existing_issues = Issue.issue_objects.filter(
            project_id=project_id,
            completed_at__isnull=True,
        ).order_by("-created_at")[:100]

        if not existing_issues.exists():
            return Response(
                {"duplicates": [], "message": "No existing issues to compare against"},
                status=status.HTTP_200_OK,
            )

        issues_text = []
        for issue in existing_issues:
            issues_text.append(
                f"- [{issue.id}] \"{issue.name}\": {(issue.description_stripped or '')[:200]}"
            )

        task = "You are a duplicate issue detection AI. Compare a new issue against existing ones."
        prompt = f"""New Issue:
Title: {title}
Description: {description or 'No description'}

Existing Issues:
{chr(10).join(issues_text)}

Find any existing issues that are similar or duplicate to the new issue.

Respond with ONLY a valid JSON object (no markdown, no explanation) with these fields:
- "has_duplicates": boolean
- "duplicates": array of objects (empty if no duplicates), each with:
  - "issue_id": UUID of the similar existing issue
  - "title": title of the existing issue
  - "similarity_score": 0.0 to 1.0 (1.0 = exact duplicate)
  - "reason": brief explanation of why it's similar
- "recommendation": "create" (safe to create), "review" (check duplicates first), or "duplicate" (likely duplicate)
"""

        workspace = Workspace.objects.get(slug=slug)
        project = Project.objects.get(pk=project_id)

        text, error = tracked_llm_response(
            task, prompt, api_key, model, provider, base_url,
            user=request.user,
            workspace=workspace,
            project=project,
            endpoint="ai/duplicate-check",
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

        return Response(result, status=status.HTTP_200_OK)
