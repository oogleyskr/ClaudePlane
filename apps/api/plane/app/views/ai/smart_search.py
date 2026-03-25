# Copyright (c) 2024-present ClaudePlane contributors
# SPDX-License-Identifier: AGPL-3.0-only

"""
Smart issue search endpoint: natural language search that uses the LLM
to interpret search queries and find matching issues.
"""

import json

from django.db.models import Q
from rest_framework import status
from rest_framework.response import Response

from plane.app.permissions import ROLE, allow_permission
from plane.app.views.external.base import get_llm_config
from plane.db.models import Issue, Project, Workspace
from plane.utils.llm_tracker import tracked_llm_response

from ..base import BaseAPIView


class SmartIssueSearchEndpoint(BaseAPIView):
    """
    POST /api/workspaces/<slug>/projects/<project_id>/ai/smart-search/

    Natural language search for issues.
    Examples: "find all auth bugs from last week", "show urgent unassigned issues"

    Request body:
    - query: natural language search query
    """

    @allow_permission([ROLE.ADMIN, ROLE.MEMBER])
    def post(self, request, slug, project_id):
        api_key, model, provider, base_url = get_llm_config()
        if not api_key or not model or not provider:
            return Response(
                {"error": "LLM provider not configured"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        query = request.data.get("query", "")
        if not query:
            return Response(
                {"error": "Search query is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        task = "You are a search query translator. Convert natural language into structured search filters."
        prompt = f"""Convert this natural language search query into structured filters:
"{query}"

Respond with ONLY a valid JSON object (no markdown, no explanation) with these fields:
- "keywords": array of keywords to search in issue titles and descriptions
- "priority": array of priorities to filter by (from: "urgent", "high", "medium", "low", "none"), or null
- "state_group": array of state groups to filter by (from: "backlog", "unstarted", "started", "completed", "cancelled"), or null
- "date_filter": object with "field" ("created_at" or "updated_at"), "after" (ISO date or null), "before" (ISO date or null), or null
- "has_assignee": true/false/null (null = don't filter)
- "search_text": the core text to search for in titles/descriptions
"""

        text, error = tracked_llm_response(
            task, prompt, api_key, model, provider, base_url,
            user=request.user,
            workspace=Workspace.objects.get(slug=slug),
            project=Project.objects.get(pk=project_id),
            endpoint="ai/smart-search",
        )

        if not text and error:
            return Response(
                {"error": "Failed to get AI response"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        # Parse the LLM-generated filters
        try:
            cleaned = text.strip()
            if cleaned.startswith("```"):
                cleaned = cleaned.split("\n", 1)[1] if "\n" in cleaned else cleaned[3:]
                if cleaned.endswith("```"):
                    cleaned = cleaned[:-3]
            filters = json.loads(cleaned)
        except (json.JSONDecodeError, ValueError):
            # Fallback to simple text search
            filters = {"search_text": query, "keywords": query.split()}

        # Build queryset from parsed filters
        qs = Issue.issue_objects.filter(project_id=project_id)

        search_text = filters.get("search_text", "")
        keywords = filters.get("keywords", [])
        if search_text or keywords:
            q = Q()
            if search_text:
                q |= Q(name__icontains=search_text)
                q |= Q(description_stripped__icontains=search_text)
            for kw in keywords:
                q |= Q(name__icontains=kw)
                q |= Q(description_stripped__icontains=kw)
            qs = qs.filter(q)

        if filters.get("priority"):
            qs = qs.filter(priority__in=filters["priority"])

        if filters.get("state_group"):
            qs = qs.filter(state__group__in=filters["state_group"])

        if filters.get("has_assignee") is True:
            qs = qs.filter(assignees__isnull=False).distinct()
        elif filters.get("has_assignee") is False:
            qs = qs.filter(assignees__isnull=True)

        date_filter = filters.get("date_filter")
        if date_filter and isinstance(date_filter, dict):
            field = date_filter.get("field", "created_at")
            if field in ("created_at", "updated_at"):
                if date_filter.get("after"):
                    qs = qs.filter(**{f"{field}__gte": date_filter["after"]})
                if date_filter.get("before"):
                    qs = qs.filter(**{f"{field}__lte": date_filter["before"]})

        results = qs.order_by("-created_at")[:25]

        issues_data = [
            {
                "id": str(issue.id),
                "name": issue.name,
                "priority": issue.priority,
                "state_id": str(issue.state_id) if issue.state_id else None,
                "created_at": issue.created_at.isoformat(),
                "description_stripped": (issue.description_stripped or "")[:200],
            }
            for issue in results
        ]

        return Response(
            {
                "query": query,
                "parsed_filters": filters,
                "results": issues_data,
                "count": len(issues_data),
            },
            status=status.HTTP_200_OK,
        )
