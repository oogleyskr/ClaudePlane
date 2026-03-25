# Copyright (c) 2024-present ClaudePlane contributors
# SPDX-License-Identifier: AGPL-3.0-only

"""
URL configuration for ClaudePlane AI endpoints.

All AI endpoints are scoped under workspaces/<slug>/projects/<project_id>/ai/
and require ADMIN or MEMBER permission.
"""

from django.urls import path

from plane.app.views.ai import (
    IssueAutoTriageEndpoint,
    IssueDecomposeEndpoint,
    SprintPlannerEndpoint,
    DuplicateDetectionEndpoint,
    SmartIssueSearchEndpoint,
    IssueComplexityEndpoint,
    ReleaseNotesEndpoint,
    RetrospectiveEndpoint,
    DailyDigestEndpoint,
    CommitIssueLinkerEndpoint,
)


urlpatterns = [
    # Issue-level AI actions
    path(
        "workspaces/<str:slug>/projects/<uuid:project_id>/ai/triage/<uuid:issue_id>/",
        IssueAutoTriageEndpoint.as_view(),
        name="ai-triage",
    ),
    path(
        "workspaces/<str:slug>/projects/<uuid:project_id>/ai/decompose/<uuid:issue_id>/",
        IssueDecomposeEndpoint.as_view(),
        name="ai-decompose",
    ),
    path(
        "workspaces/<str:slug>/projects/<uuid:project_id>/ai/estimate/<uuid:issue_id>/",
        IssueComplexityEndpoint.as_view(),
        name="ai-estimate",
    ),
    # Project-level AI actions
    path(
        "workspaces/<str:slug>/projects/<uuid:project_id>/ai/sprint-plan/",
        SprintPlannerEndpoint.as_view(),
        name="ai-sprint-plan",
    ),
    path(
        "workspaces/<str:slug>/projects/<uuid:project_id>/ai/duplicate-check/",
        DuplicateDetectionEndpoint.as_view(),
        name="ai-duplicate-check",
    ),
    path(
        "workspaces/<str:slug>/projects/<uuid:project_id>/ai/smart-search/",
        SmartIssueSearchEndpoint.as_view(),
        name="ai-smart-search",
    ),
    path(
        "workspaces/<str:slug>/projects/<uuid:project_id>/ai/digest/",
        DailyDigestEndpoint.as_view(),
        name="ai-digest",
    ),
    path(
        "workspaces/<str:slug>/projects/<uuid:project_id>/ai/link-commits/",
        CommitIssueLinkerEndpoint.as_view(),
        name="ai-link-commits",
    ),
    # Cycle-level AI actions
    path(
        "workspaces/<str:slug>/projects/<uuid:project_id>/ai/release-notes/<uuid:cycle_id>/",
        ReleaseNotesEndpoint.as_view(),
        name="ai-release-notes",
    ),
    path(
        "workspaces/<str:slug>/projects/<uuid:project_id>/ai/retrospective/<uuid:cycle_id>/",
        RetrospectiveEndpoint.as_view(),
        name="ai-retrospective",
    ),
]
