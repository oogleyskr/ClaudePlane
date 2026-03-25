# Copyright (c) 2024-present ClaudePlane contributors
# SPDX-License-Identifier: AGPL-3.0-only

"""
Commit message to issue linker endpoint: parses commit messages for
issue references and returns matching issues for auto-linking.
"""

import re

from rest_framework import status
from rest_framework.response import Response

from plane.app.permissions import ROLE, allow_permission
from plane.db.models import Issue, Project

from ..base import BaseAPIView


class CommitIssueLinkerEndpoint(BaseAPIView):
    """
    POST /api/workspaces/<slug>/projects/<project_id>/ai/link-commits/

    Parses commit messages for issue references (e.g., #123, PROJECT-123,
    "fixes #45") and returns matching issues for auto-linking.

    Request body:
    - commits: array of objects with "message" and optional "sha" fields
    """

    @allow_permission([ROLE.ADMIN, ROLE.MEMBER])
    def post(self, request, slug, project_id):
        commits = request.data.get("commits", [])
        if not commits:
            return Response(
                {"error": "Commits array is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            project = Project.objects.get(pk=project_id)
        except Project.DoesNotExist:
            return Response(
                {"error": "Project not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        identifier = project.identifier

        # Patterns to match issue references
        patterns = [
            # PROJECT-123 format
            re.compile(rf'\b{re.escape(identifier)}-(\d+)\b', re.IGNORECASE),
            # #123 format
            re.compile(r'#(\d+)\b'),
            # Common keywords: fixes, closes, resolves, refs
            re.compile(r'(?:fix(?:es|ed)?|clos(?:es|ed)|resolv(?:es|ed)|refs?)\s+#?(\d+)\b', re.IGNORECASE),
        ]

        results = []
        for commit in commits:
            message = commit.get("message", "")
            sha = commit.get("sha", "")
            linked_issues = []
            seen_sequences = set()

            for pattern in patterns:
                for match in pattern.finditer(message):
                    seq_id = int(match.group(1))
                    if seq_id in seen_sequences:
                        continue
                    seen_sequences.add(seq_id)

                    try:
                        issue = Issue.objects.get(
                            project_id=project_id,
                            sequence_id=seq_id,
                        )
                        # Determine link type from keywords
                        link_type = "reference"
                        lower_msg = message.lower()
                        if any(kw in lower_msg for kw in ["fix", "close", "resolve"]):
                            link_type = "closing"

                        linked_issues.append({
                            "issue_id": str(issue.id),
                            "issue_name": issue.name,
                            "sequence_id": seq_id,
                            "identifier": f"{identifier}-{seq_id}",
                            "link_type": link_type,
                        })
                    except Issue.DoesNotExist:
                        continue

            results.append({
                "sha": sha,
                "message": message[:200],
                "linked_issues": linked_issues,
                "issues_found": len(linked_issues),
            })

        total_links = sum(r["issues_found"] for r in results)
        return Response(
            {
                "commits_processed": len(results),
                "total_issues_linked": total_links,
                "results": results,
            },
            status=status.HTTP_200_OK,
        )
