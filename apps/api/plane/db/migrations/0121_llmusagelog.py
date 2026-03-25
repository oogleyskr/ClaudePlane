# Copyright (c) 2024-present ClaudePlane contributors
# SPDX-License-Identifier: AGPL-3.0-only

"""
Migration to create the LLMUsageLog table for tracking AI API usage
including token counts, costs, latency, and request context.
"""

import uuid
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("db", "0120_issueview_archived_at"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="LLMUsageLog",
            fields=[
                (
                    "created_at",
                    models.DateTimeField(auto_now_add=True, verbose_name="Created At"),
                ),
                (
                    "updated_at",
                    models.DateTimeField(auto_now=True, verbose_name="Last Modified At"),
                ),
                (
                    "id",
                    models.UUIDField(
                        db_index=True,
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                        unique=True,
                    ),
                ),
                (
                    "provider",
                    models.CharField(
                        help_text="LLM provider key (e.g. openai, anthropic, claude-max)",
                        max_length=50,
                    ),
                ),
                (
                    "model",
                    models.CharField(
                        help_text="Model identifier used for the request",
                        max_length=100,
                    ),
                ),
                (
                    "base_url",
                    models.CharField(
                        blank=True,
                        help_text="Custom base URL if used",
                        max_length=500,
                        null=True,
                    ),
                ),
                (
                    "prompt_tokens",
                    models.IntegerField(
                        default=0,
                        help_text="Number of tokens in the prompt",
                    ),
                ),
                (
                    "completion_tokens",
                    models.IntegerField(
                        default=0,
                        help_text="Number of tokens in the completion",
                    ),
                ),
                (
                    "total_tokens",
                    models.IntegerField(
                        default=0,
                        help_text="Total tokens consumed",
                    ),
                ),
                (
                    "estimated_cost_cents",
                    models.FloatField(
                        default=0.0,
                        help_text="Estimated cost in USD cents",
                    ),
                ),
                (
                    "latency_ms",
                    models.FloatField(
                        default=0.0,
                        help_text="Request latency in milliseconds",
                    ),
                ),
                (
                    "endpoint",
                    models.CharField(
                        help_text="The API endpoint that triggered this LLM call",
                        max_length=200,
                    ),
                ),
                (
                    "success",
                    models.BooleanField(
                        default=True,
                        help_text="Whether the LLM call succeeded",
                    ),
                ),
                (
                    "error_message",
                    models.TextField(
                        blank=True,
                        help_text="Error message if the call failed",
                        null=True,
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="llm_usage_logs",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "workspace",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="llm_usage_logs",
                        to="db.workspace",
                    ),
                ),
                (
                    "project",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="llm_usage_logs",
                        to="db.project",
                    ),
                ),
                (
                    "created_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="%(class)s_created_by",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="Created By",
                    ),
                ),
                (
                    "updated_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="%(class)s_updated_by",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="Last Modified By",
                    ),
                ),
            ],
            options={
                "verbose_name": "LLM Usage Log",
                "verbose_name_plural": "LLM Usage Logs",
                "db_table": "llm_usage_logs",
                "ordering": ("-created_at",),
            },
        ),
        migrations.AddIndex(
            model_name="llmusagelog",
            index=models.Index(
                fields=["provider", "created_at"],
                name="llm_usage_provider_created_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="llmusagelog",
            index=models.Index(
                fields=["workspace", "created_at"],
                name="llm_usage_workspace_created_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="llmusagelog",
            index=models.Index(
                fields=["user", "created_at"],
                name="llm_usage_user_created_idx",
            ),
        ),
    ]
