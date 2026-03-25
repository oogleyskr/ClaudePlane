# Copyright (c) 2024-present ClaudePlane contributors
# SPDX-License-Identifier: AGPL-3.0-only

"""
LLM usage tracking utilities.

Provides a wrapper around get_llm_response that automatically logs
token usage, latency, and cost estimates to the LLMUsageLog model.
"""

import time
from typing import Optional, Tuple

from plane.utils.exception_logger import log_exception


# Approximate cost per 1K tokens in USD cents (as of 2024)
COST_PER_1K_TOKENS = {
    "gpt-3.5-turbo": {"prompt": 0.05, "completion": 0.15},
    "gpt-4o-mini": {"prompt": 0.015, "completion": 0.06},
    "gpt-4o": {"prompt": 0.25, "completion": 1.0},
    "claude-sonnet-4-6": {"prompt": 0.3, "completion": 1.5},
    "claude-opus-4-6": {"prompt": 1.5, "completion": 7.5},
    "claude-haiku-4-5": {"prompt": 0.025, "completion": 0.125},
}

# Rough token estimation: ~4 chars per token for English text
CHARS_PER_TOKEN = 4


def estimate_tokens(text: str) -> int:
    """Estimate token count from text length."""
    if not text:
        return 0
    return max(1, len(text) // CHARS_PER_TOKEN)


def estimate_cost(model: str, prompt_tokens: int, completion_tokens: int) -> float:
    """
    Estimate cost in USD cents based on model and token counts.
    Returns 0.0 for unknown models.
    """
    rates = COST_PER_1K_TOKENS.get(model)
    if not rates:
        return 0.0
    prompt_cost = (prompt_tokens / 1000) * rates["prompt"]
    completion_cost = (completion_tokens / 1000) * rates["completion"]
    return round(prompt_cost + completion_cost, 4)


def tracked_llm_response(
    task: str,
    prompt: str,
    api_key: str,
    model: str,
    provider: str,
    base_url: str = None,
    user=None,
    workspace=None,
    project=None,
    endpoint: str = "unknown",
) -> Tuple[Optional[str], Optional[str]]:
    """
    Wrapper around get_llm_response that logs usage to LLMUsageLog.

    Returns the same (text, error) tuple as get_llm_response.
    """
    from plane.app.views.external.base import get_llm_response

    start = time.monotonic()
    text, error = get_llm_response(task, prompt, api_key, model, provider, base_url)
    latency_ms = round((time.monotonic() - start) * 1000, 2)

    # Estimate tokens
    prompt_text = (task or "") + "\n" + (prompt or "")
    prompt_tokens = estimate_tokens(prompt_text)
    completion_tokens = estimate_tokens(text) if text else 0
    total_tokens = prompt_tokens + completion_tokens

    # Estimate cost
    cost = estimate_cost(model, prompt_tokens, completion_tokens)

    # Log asynchronously to avoid blocking the response
    try:
        from plane.db.models import LLMUsageLog

        LLMUsageLog.objects.create(
            user=user if user and not user.is_anonymous else None,
            workspace=workspace,
            project=project,
            provider=provider,
            model=model,
            base_url=base_url,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            estimated_cost_cents=cost,
            latency_ms=latency_ms,
            endpoint=endpoint,
            success=text is not None,
            error_message=error,
        )
    except Exception as exc:
        # Never let logging failure break the actual LLM response
        log_exception(exc)

    return text, error
