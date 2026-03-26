/**
 * Copyright (c) 2024-present Glider contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 *
 * React hooks for AI action endpoints.
 * Provides reusable hooks with loading states, error handling,
 * and caching for all Glider AI features.
 */

"use client";

import { useState, useCallback, useRef } from "react";
import {
  AIActionsService,
  type ITriageResponse,
  type IDecomposeResponse,
  type IComplexityEstimate,
  type ISmartSearchResponse,
  type IDuplicateCheckResponse,
  type ISprintPlanResponse,
  type IReleaseNotesResponse,
  type IDigestResponse,
} from "@/services/ai-actions.service";

/** Generic hook state for async AI operations */
interface AIActionState<T> {
  data: T | null;
  loading: boolean;
  error: string | null;
}

/** Factory for creating AI action hooks with consistent state management */
function useAIAction<TArgs extends unknown[], TResult>() {
  const [state, setState] = useState<AIActionState<TResult>>({
    data: null,
    loading: false,
    error: null,
  });

  const serviceRef = useRef<AIActionsService | null>(null);

  const getService = useCallback(() => {
    if (!serviceRef.current) {
      serviceRef.current = new AIActionsService();
    }
    return serviceRef.current;
  }, []);

  const execute = useCallback(
    async (fn: (service: AIActionsService) => Promise<TResult>) => {
      setState({ data: null, loading: true, error: null });
      try {
        const result = await fn(getService());
        setState({ data: result, loading: false, error: null });
        return result;
      } catch (err: unknown) {
        const message = err instanceof Error
          ? err.message
          : typeof err === "object" && err !== null && "error" in err
            ? String((err as Record<string, unknown>).error)
            : "AI action failed";
        setState({ data: null, loading: false, error: message });
        throw err;
      }
    },
    [getService]
  );

  const reset = useCallback(() => {
    setState({ data: null, loading: false, error: null });
  }, []);

  return { ...state, execute, reset };
}

/** Hook for auto-triaging an issue */
export function useAITriage() {
  const action = useAIAction<[string, string, string], ITriageResponse>();

  const triage = useCallback(
    (workspaceSlug: string, projectId: string, issueId: string) =>
      action.execute((svc) => svc.triageIssue(workspaceSlug, projectId, issueId)),
    [action.execute]
  );

  return { ...action, triage };
}

/** Hook for decomposing an issue into subtasks */
export function useAIDecompose() {
  const action = useAIAction<[string, string, string, number?], IDecomposeResponse>();

  const decompose = useCallback(
    (workspaceSlug: string, projectId: string, issueId: string, maxSubtasks?: number) =>
      action.execute((svc) => svc.decomposeIssue(workspaceSlug, projectId, issueId, maxSubtasks)),
    [action.execute]
  );

  return { ...action, decompose };
}

/** Hook for AI complexity estimation */
export function useAIEstimate() {
  const action = useAIAction<[string, string, string], IComplexityEstimate>();

  const estimate = useCallback(
    (workspaceSlug: string, projectId: string, issueId: string) =>
      action.execute((svc) => svc.estimateComplexity(workspaceSlug, projectId, issueId)),
    [action.execute]
  );

  return { ...action, estimate };
}

/** Hook for natural language smart search */
export function useAISmartSearch() {
  const action = useAIAction<[string, string, string], ISmartSearchResponse>();

  const search = useCallback(
    (workspaceSlug: string, projectId: string, query: string) =>
      action.execute((svc) => svc.smartSearch(workspaceSlug, projectId, query)),
    [action.execute]
  );

  return { ...action, search };
}

/** Hook for duplicate detection */
export function useAIDuplicateCheck() {
  const action = useAIAction<[string, string, { title: string; description?: string }], IDuplicateCheckResponse>();

  const checkDuplicates = useCallback(
    (workspaceSlug: string, projectId: string, data: { title: string; description?: string }) =>
      action.execute((svc) => svc.checkDuplicates(workspaceSlug, projectId, data)),
    [action.execute]
  );

  return { ...action, checkDuplicates };
}

/** Hook for sprint planning */
export function useAISprintPlan() {
  const action = useAIAction<
    [string, string, { team_capacity?: number; focus_areas?: string[] }?],
    ISprintPlanResponse
  >();

  const planSprint = useCallback(
    (workspaceSlug: string, projectId: string, data?: { team_capacity?: number; focus_areas?: string[] }) =>
      action.execute((svc) => svc.planSprint(workspaceSlug, projectId, data)),
    [action.execute]
  );

  return { ...action, planSprint };
}

/** Hook for generating release notes */
export function useAIReleaseNotes() {
  const action = useAIAction<[string, string, string, string?], IReleaseNotesResponse>();

  const generateReleaseNotes = useCallback(
    (workspaceSlug: string, projectId: string, cycleId: string, format?: string) =>
      action.execute((svc) => svc.generateReleaseNotes(workspaceSlug, projectId, cycleId, format)),
    [action.execute]
  );

  return { ...action, generateReleaseNotes };
}

/** Hook for generating daily/weekly digests */
export function useAIDigest() {
  const action = useAIAction<[string, string, number?], IDigestResponse>();

  const generateDigest = useCallback(
    (workspaceSlug: string, projectId: string, days?: number) =>
      action.execute((svc) => svc.generateDigest(workspaceSlug, projectId, days)),
    [action.execute]
  );

  return { ...action, generateDigest };
}
