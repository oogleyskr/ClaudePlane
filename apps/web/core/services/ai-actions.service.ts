/**
 * Copyright (c) 2024-present ClaudePlane contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 *
 * Service layer for ClaudePlane AI action endpoints.
 * Provides typed methods for all AI-native features:
 * triage, decompose, sprint planning, duplicate detection, etc.
 */

import { API_BASE_URL } from "@plane/constants";
import { APIService } from "@/services/api.service";

// --- Response Types ---

export interface ITriageSuggestion {
  priority: "urgent" | "high" | "medium" | "low" | "none";
  priority_reason: string;
  suggested_labels: string[];
  suggested_assignee: string | null;
  assignee_reason: string | null;
  category: "bug" | "feature" | "improvement" | "task" | "question";
}

export interface ITriageResponse {
  issue_id: string;
  suggestions: ITriageSuggestion;
}

export interface ISubtask {
  title: string;
  description: string;
  priority: string;
  complexity: string;
  order: number;
}

export interface IDecomposeResponse {
  issue_id: string;
  decomposition: {
    subtasks: ISubtask[];
    rationale: string;
  };
}

export interface ISprintPlanResponse {
  sprint_plan: {
    selected_issues: Array<{
      issue_id: string;
      reason: string;
      estimated_points: number;
    }>;
    total_estimated_points: number;
    sprint_goal: string;
    risks: string[];
    overflow_issues: string[];
  };
}

export interface IDuplicateCheckResponse {
  has_duplicates: boolean;
  duplicates: Array<{
    issue_id: string;
    title: string;
    similarity_score: number;
    reason: string;
  }>;
  recommendation: "create" | "review" | "duplicate";
}

export interface ISmartSearchResponse {
  query: string;
  parsed_filters: Record<string, unknown>;
  results: Array<{
    id: string;
    name: string;
    priority: string;
    state_id: string | null;
    created_at: string;
    description_stripped: string;
  }>;
  count: number;
}

export interface IComplexityEstimate {
  issue_id: string;
  estimate: {
    story_points: number;
    complexity: string;
    confidence: number;
    reasoning: string;
    risks: string[];
    assumptions: string[];
  };
}

export interface IReleaseNotesResponse {
  cycle_id: string;
  cycle_name: string;
  release_notes: {
    title: string;
    summary: string;
    sections: Array<{ heading: string; items: string[] }>;
    highlights: string[];
    markdown: string;
  };
}

export interface IDigestResponse {
  period_days: number;
  digest: {
    summary: string;
    highlights: string[];
    metrics: { new_count: number; completed_count: number; updated_count: number };
    concerns: string[];
    momentum: string;
    suggested_focus: string;
  };
}

export interface ICommitLinkResult {
  commits_processed: number;
  total_issues_linked: number;
  results: Array<{
    sha: string;
    message: string;
    linked_issues: Array<{
      issue_id: string;
      issue_name: string;
      sequence_id: number;
      identifier: string;
      link_type: "reference" | "closing";
    }>;
    issues_found: number;
  }>;
}

// --- Service Class ---

export class AIActionsService extends APIService {
  constructor() {
    super(API_BASE_URL);
  }

  /** Auto-triage: suggest priority, labels, assignee for an issue */
  async triageIssue(workspaceSlug: string, projectId: string, issueId: string): Promise<ITriageResponse> {
    return this.post(`/api/workspaces/${workspaceSlug}/projects/${projectId}/ai/triage/${issueId}/`, {})
      .then((res) => res?.data)
      .catch((error) => { throw error?.response?.data; });
  }

  /** Decompose: break an issue into subtasks */
  async decomposeIssue(
    workspaceSlug: string,
    projectId: string,
    issueId: string,
    maxSubtasks?: number,
  ): Promise<IDecomposeResponse> {
    return this.post(`/api/workspaces/${workspaceSlug}/projects/${projectId}/ai/decompose/${issueId}/`, {
      max_subtasks: maxSubtasks ?? 8,
    })
      .then((res) => res?.data)
      .catch((error) => { throw error?.response?.data; });
  }

  /** Sprint planning: suggest issues for next cycle */
  async planSprint(
    workspaceSlug: string,
    projectId: string,
    data?: { team_capacity?: number; focus_areas?: string[] },
  ): Promise<ISprintPlanResponse> {
    return this.post(`/api/workspaces/${workspaceSlug}/projects/${projectId}/ai/sprint-plan/`, data ?? {})
      .then((res) => res?.data)
      .catch((error) => { throw error?.response?.data; });
  }

  /** Duplicate detection: check for similar existing issues */
  async checkDuplicates(
    workspaceSlug: string,
    projectId: string,
    data: { title: string; description?: string },
  ): Promise<IDuplicateCheckResponse> {
    return this.post(`/api/workspaces/${workspaceSlug}/projects/${projectId}/ai/duplicate-check/`, data)
      .then((res) => res?.data)
      .catch((error) => { throw error?.response?.data; });
  }

  /** Smart search: natural language issue search */
  async smartSearch(
    workspaceSlug: string,
    projectId: string,
    query: string,
  ): Promise<ISmartSearchResponse> {
    return this.post(`/api/workspaces/${workspaceSlug}/projects/${projectId}/ai/smart-search/`, { query })
      .then((res) => res?.data)
      .catch((error) => { throw error?.response?.data; });
  }

  /** Complexity estimation: AI-powered story point estimation */
  async estimateComplexity(
    workspaceSlug: string,
    projectId: string,
    issueId: string,
  ): Promise<IComplexityEstimate> {
    return this.post(`/api/workspaces/${workspaceSlug}/projects/${projectId}/ai/estimate/${issueId}/`, {})
      .then((res) => res?.data)
      .catch((error) => { throw error?.response?.data; });
  }

  /** Release notes: generate from completed cycle issues */
  async generateReleaseNotes(
    workspaceSlug: string,
    projectId: string,
    cycleId: string,
    format?: string,
  ): Promise<IReleaseNotesResponse> {
    return this.post(
      `/api/workspaces/${workspaceSlug}/projects/${projectId}/ai/release-notes/${cycleId}/`,
      { format: format ?? "markdown" },
    )
      .then((res) => res?.data)
      .catch((error) => { throw error?.response?.data; });
  }

  /** Daily digest: project activity summary */
  async generateDigest(
    workspaceSlug: string,
    projectId: string,
    days?: number,
  ): Promise<IDigestResponse> {
    return this.post(`/api/workspaces/${workspaceSlug}/projects/${projectId}/ai/digest/`, {
      days: days ?? 1,
    })
      .then((res) => res?.data)
      .catch((error) => { throw error?.response?.data; });
  }

  /** Commit linker: parse commits for issue references */
  async linkCommits(
    workspaceSlug: string,
    projectId: string,
    commits: Array<{ message: string; sha?: string }>,
  ): Promise<ICommitLinkResult> {
    return this.post(`/api/workspaces/${workspaceSlug}/projects/${projectId}/ai/link-commits/`, { commits })
      .then((res) => res?.data)
      .catch((error) => { throw error?.response?.data; });
  }
}
