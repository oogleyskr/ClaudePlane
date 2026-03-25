# Copyright (c) 2024-present ClaudePlane contributors
# SPDX-License-Identifier: AGPL-3.0-only

"""
LLM usage tracking model.

Records every AI API call made through ClaudePlane so operators can
monitor token consumption, per-provider costs, and request patterns.
"""

import uuid

from django.conf import settings
from django.db import models

from .base import BaseModel


class LLMUsageLog(BaseModel):
    """
    Tracks individual LLM API calls including provider, model, token counts,
    latency, and the workspace/project context in which the call was made.
    """

    # Who made the request
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="llm_usage_logs",
    )

    # Context
    workspace = models.ForeignKey(
        "db.Workspace",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="llm_usage_logs",
    )
    project = models.ForeignKey(
        "db.Project",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="llm_usage_logs",
    )

    # LLM details
    provider = models.CharField(max_length=50, help_text="LLM provider key (e.g. openai, anthropic, claude-max)")
    model = models.CharField(max_length=100, help_text="Model identifier used for the request")
    base_url = models.CharField(max_length=500, null=True, blank=True, help_text="Custom base URL if used")

    # Token tracking
    prompt_tokens = models.IntegerField(default=0, help_text="Number of tokens in the prompt")
    completion_tokens = models.IntegerField(default=0, help_text="Number of tokens in the completion")
    total_tokens = models.IntegerField(default=0, help_text="Total tokens consumed")

    # Cost estimation (in USD cents)
    estimated_cost_cents = models.FloatField(default=0.0, help_text="Estimated cost in USD cents")

    # Performance
    latency_ms = models.FloatField(default=0.0, help_text="Request latency in milliseconds")

    # Request metadata
    endpoint = models.CharField(max_length=200, help_text="The API endpoint that triggered this LLM call")
    success = models.BooleanField(default=True, help_text="Whether the LLM call succeeded")
    error_message = models.TextField(null=True, blank=True, help_text="Error message if the call failed")

    class Meta:
        verbose_name = "LLM Usage Log"
        verbose_name_plural = "LLM Usage Logs"
        db_table = "llm_usage_logs"
        ordering = ("-created_at",)
        indexes = [
            models.Index(fields=["provider", "created_at"]),
            models.Index(fields=["workspace", "created_at"]),
            models.Index(fields=["user", "created_at"]),
        ]

    def __str__(self):
        return f"{self.provider}/{self.model} - {self.total_tokens} tokens - {self.created_at}"
