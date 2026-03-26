/**
 * Copyright (c) 2024-present ClaudePlane contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 *
 * AI Provider Status Indicator component for the admin panel.
 * Shows which LLM provider is active, its connection status,
 * and recent usage statistics at a glance.
 */

import React, { useEffect, useState } from "react";

interface HealthCheckResponse {
  status: "healthy" | "unhealthy";
  version: string;
  checks: {
    database: { status: string; latency_ms?: number };
    redis: { status: string; latency_ms?: number };
    llm: {
      status: string;
      provider?: string;
      model?: string;
      base_url?: string;
    };
  };
}

type ConnectionStatus = "loading" | "connected" | "disconnected" | "not_configured";

/**
 * Displays the current AI provider status with a colored indicator dot,
 * provider name, model, and connection health.
 *
 * Fetches from /api/health/ on mount and refreshes every 60 seconds.
 */
export const AIProviderStatus: React.FC = () => {
  const [health, setHealth] = useState<HealthCheckResponse | null>(null);
  const [status, setStatus] = useState<ConnectionStatus>("loading");
  const [lastChecked, setLastChecked] = useState<Date | null>(null);

  const fetchHealth = async () => {
    try {
      const response = await fetch("/api/health/");
      const data: HealthCheckResponse = await response.json();
      setHealth(data);
      setLastChecked(new Date());

      if (data.checks.llm.status === "configured") {
        setStatus("connected");
      } else if (data.checks.llm.status === "not_configured") {
        setStatus("not_configured");
      } else {
        setStatus("disconnected");
      }
    } catch {
      setStatus("disconnected");
    }
  };

  useEffect(() => {
    fetchHealth();
    const interval = setInterval(fetchHealth, 60000);
    return () => clearInterval(interval);
  }, []);

  const statusConfig = {
    loading: { color: "bg-gray-400", label: "Checking..." },
    connected: { color: "bg-green-500", label: "Connected" },
    disconnected: { color: "bg-red-500", label: "Disconnected" },
    not_configured: { color: "bg-yellow-500", label: "Not Configured" },
  };

  const { color, label } = statusConfig[status];

  return (
    <div className="rounded-lg border border-custom-border-200 bg-custom-background-100 p-4">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-sm font-medium text-custom-text-100">
          AI Provider Status
        </h3>
        <div className="flex items-center gap-2">
          <span className={`w-2.5 h-2.5 rounded-full ${color} animate-pulse`} />
          <span className="text-xs text-custom-text-300">{label}</span>
        </div>
      </div>

      {health?.checks.llm && status === "connected" && (
        <div className="space-y-2">
          <div className="flex items-center justify-between text-xs">
            <span className="text-custom-text-300">Provider</span>
            <span className="text-custom-text-100 font-medium">
              {health.checks.llm.provider || "Unknown"}
            </span>
          </div>
          <div className="flex items-center justify-between text-xs">
            <span className="text-custom-text-300">Model</span>
            <span className="text-custom-text-100 font-mono text-[11px]">
              {health.checks.llm.model || "Unknown"}
            </span>
          </div>
          {health.checks.llm.base_url && health.checks.llm.base_url !== "default" && (
            <div className="flex items-center justify-between text-xs">
              <span className="text-custom-text-300">Endpoint</span>
              <span className="text-custom-text-200 font-mono text-[11px] truncate max-w-[200px]">
                {health.checks.llm.base_url}
              </span>
            </div>
          )}
        </div>
      )}

      {status === "not_configured" && (
        <p className="text-xs text-custom-text-300 mt-1">
          No LLM provider is configured. Set LLM_API_KEY and LLM_PROVIDER
          in your environment or instance settings.
        </p>
      )}

      {/* Service Health Summary */}
      {health && (
        <div className="mt-3 pt-3 border-t border-custom-border-200">
          <div className="flex items-center gap-3 text-xs">
            <div className="flex items-center gap-1">
              <span
                className={`w-1.5 h-1.5 rounded-full ${
                  health.checks.database.status === "healthy"
                    ? "bg-green-500"
                    : "bg-red-500"
                }`}
              />
              <span className="text-custom-text-300">DB</span>
              {health.checks.database.latency_ms !== undefined && (
                <span className="text-custom-text-400">
                  {health.checks.database.latency_ms}ms
                </span>
              )}
            </div>
            <div className="flex items-center gap-1">
              <span
                className={`w-1.5 h-1.5 rounded-full ${
                  health.checks.redis.status === "healthy"
                    ? "bg-green-500"
                    : "bg-red-500"
                }`}
              />
              <span className="text-custom-text-300">Redis</span>
              {health.checks.redis.latency_ms !== undefined && (
                <span className="text-custom-text-400">
                  {health.checks.redis.latency_ms}ms
                </span>
              )}
            </div>
          </div>
        </div>
      )}

      {lastChecked && (
        <div className="mt-2 text-[10px] text-custom-text-400">
          Last checked: {lastChecked.toLocaleTimeString()}
        </div>
      )}
    </div>
  );
};

export default AIProviderStatus;
