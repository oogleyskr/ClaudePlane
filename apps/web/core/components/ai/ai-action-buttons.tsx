/**
 * Copyright (c) 2024-present ClaudePlane contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 *
 * AI Action Buttons component for the issue detail view.
 * Provides "Ask Claude" style buttons for triage, decompose,
 * and estimate actions directly in the issue context.
 */

import React, { useState, useCallback } from "react";

// Types for the component props
interface AIActionButtonsProps {
  /** Current workspace slug */
  workspaceSlug: string;
  /** Current project ID */
  projectId: string;
  /** Current issue ID */
  issueId: string;
  /** Callback when triage results are available */
  onTriageResult?: (result: unknown) => void;
  /** Callback when decomposition results are available */
  onDecomposeResult?: (result: unknown) => void;
  /** Callback when estimate results are available */
  onEstimateResult?: (result: unknown) => void;
}

type AIAction = "triage" | "decompose" | "estimate" | null;

/**
 * Renders a row of AI action buttons for an issue.
 *
 * Each button triggers an async call to the corresponding AI endpoint
 * and displays loading state. Results are passed back via callbacks
 * so the parent component can decide how to display or apply them.
 */
export const AIActionButtons: React.FC<AIActionButtonsProps> = ({
  workspaceSlug,
  projectId,
  issueId,
  onTriageResult,
  onDecomposeResult,
  onEstimateResult,
}) => {
  const [loading, setLoading] = useState<AIAction>(null);
  const [result, setResult] = useState<{ action: AIAction; data: unknown } | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleAction = useCallback(
    async (action: AIAction) => {
      if (!action) return;

      setLoading(action);
      setError(null);
      setResult(null);

      try {
        // Lazy import to avoid circular dependencies and reduce bundle size
        const { AIActionsService } = await import("@/services/ai-actions.service");
        const service = new AIActionsService();

        let data: unknown;
        switch (action) {
          case "triage":
            data = await service.triageIssue(workspaceSlug, projectId, issueId);
            onTriageResult?.(data);
            break;
          case "decompose":
            data = await service.decomposeIssue(workspaceSlug, projectId, issueId);
            onDecomposeResult?.(data);
            break;
          case "estimate":
            data = await service.estimateComplexity(workspaceSlug, projectId, issueId);
            onEstimateResult?.(data);
            break;
        }

        setResult({ action, data });
      } catch (err: unknown) {
        const message = err instanceof Error ? err.message : "AI action failed. Is the LLM provider configured?";
        setError(message);
      } finally {
        setLoading(null);
      }
    },
    [workspaceSlug, projectId, issueId, onTriageResult, onDecomposeResult, onEstimateResult]
  );

  const buttons = [
    {
      key: "triage" as const,
      label: "Auto-Triage",
      description: "Suggest priority, labels, and assignee",
      icon: (
        <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
            d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
        </svg>
      ),
    },
    {
      key: "decompose" as const,
      label: "Decompose",
      description: "Break into subtasks",
      icon: (
        <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
            d="M4 6h16M4 10h16M4 14h16M4 18h16" />
        </svg>
      ),
    },
    {
      key: "estimate" as const,
      label: "Estimate",
      description: "AI story point estimation",
      icon: (
        <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
            d="M9 7h6m0 10v-3m-3 3h.01M9 17h.01M9 14h.01M12 14h.01M15 11h.01M12 11h.01M9 11h.01M7 21h10a2 2 0 002-2V5a2 2 0 00-2-2H7a2 2 0 00-2 2v14a2 2 0 002 2z" />
        </svg>
      ),
    },
  ];

  return (
    <div className="flex flex-col gap-2">
      {/* Button Row */}
      <div className="flex items-center gap-2">
        <span className="text-xs font-medium text-custom-text-300 uppercase tracking-wider">
          Ask Claude
        </span>
        <div className="flex items-center gap-1.5">
          {buttons.map((btn) => (
            <button
              key={btn.key}
              onClick={() => handleAction(btn.key)}
              disabled={loading !== null}
              className={`
                inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs font-medium
                transition-all duration-150
                ${loading === btn.key
                  ? "bg-custom-primary-100/20 text-custom-primary-100 cursor-wait"
                  : "bg-custom-background-90 text-custom-text-200 hover:bg-custom-primary-100/10 hover:text-custom-primary-100"
                }
                ${loading !== null && loading !== btn.key ? "opacity-50 cursor-not-allowed" : ""}
                border border-custom-border-200 hover:border-custom-primary-100/30
              `}
              title={btn.description}
            >
              {loading === btn.key ? (
                <svg className="w-3.5 h-3.5 animate-spin" viewBox="0 0 24 24" fill="none">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                  <path className="opacity-75" fill="currentColor"
                    d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                </svg>
              ) : (
                btn.icon
              )}
              {btn.label}
            </button>
          ))}
        </div>
      </div>

      {/* Error Display */}
      {error && (
        <div className="text-xs text-red-500 bg-red-50 dark:bg-red-900/20 rounded-md px-3 py-2">
          {error}
        </div>
      )}

      {/* Result Preview */}
      {result && (
        <div className="text-xs bg-custom-background-90 rounded-md px-3 py-2 border border-custom-border-200">
          <div className="flex items-center justify-between mb-1">
            <span className="font-medium text-custom-text-100">
              {result.action === "triage" && "Triage Suggestions"}
              {result.action === "decompose" && "Subtask Suggestions"}
              {result.action === "estimate" && "Complexity Estimate"}
            </span>
            <button
              onClick={() => setResult(null)}
              className="text-custom-text-300 hover:text-custom-text-100"
            >
              Dismiss
            </button>
          </div>
          <pre className="text-custom-text-200 whitespace-pre-wrap overflow-auto max-h-48">
            {JSON.stringify(result.data, null, 2)}
          </pre>
        </div>
      )}
    </div>
  );
};

export default AIActionButtons;
