# Copyright (c) 2024-present ClaudePlane contributors
# SPDX-License-Identifier: AGPL-3.0-only

"""
LLM JSON response parser utility.

Robustly extracts JSON from LLM responses that may contain markdown
code fences, explanatory text, or other non-JSON content. Provides
a single reusable function used by all AI endpoints.
"""

import json
import re
from typing import Any, Dict, Optional


def parse_llm_json(text: str, fallback_key: str = "raw_response") -> Dict[str, Any]:
    """
    Parse JSON from an LLM response, handling common formatting issues.

    LLMs often wrap JSON in markdown code fences or include explanatory
    text before/after the JSON. This function handles all those cases.

    Args:
        text: Raw LLM response text
        fallback_key: Key to use if JSON parsing fails entirely

    Returns:
        Parsed dict, or {fallback_key: text} if parsing fails
    """
    if not text:
        return {fallback_key: ""}

    cleaned = text.strip()

    # Strategy 1: Try direct parse first
    try:
        return json.loads(cleaned)
    except (json.JSONDecodeError, ValueError):
        pass

    # Strategy 2: Strip markdown code fences
    #   ```json\n{...}\n``` or ```\n{...}\n```
    fence_pattern = re.compile(r'```(?:json)?\s*\n?([\s\S]*?)\n?\s*```', re.DOTALL)
    match = fence_pattern.search(cleaned)
    if match:
        try:
            return json.loads(match.group(1).strip())
        except (json.JSONDecodeError, ValueError):
            pass

    # Strategy 3: Find the first { ... } block (greedy for outermost)
    brace_pattern = re.compile(r'\{[\s\S]*\}', re.DOTALL)
    match = brace_pattern.search(cleaned)
    if match:
        try:
            return json.loads(match.group(0))
        except (json.JSONDecodeError, ValueError):
            pass

    # Strategy 4: Find the first [ ... ] block (for array responses)
    bracket_pattern = re.compile(r'\[[\s\S]*\]', re.DOTALL)
    match = bracket_pattern.search(cleaned)
    if match:
        try:
            parsed = json.loads(match.group(0))
            return {"items": parsed} if isinstance(parsed, list) else parsed
        except (json.JSONDecodeError, ValueError):
            pass

    # Strategy 5: Try removing common prefixes like "Here's the JSON:"
    for prefix in ["Here's", "Here is", "The JSON", "Response:", "Output:", "Result:"]:
        if cleaned.lower().startswith(prefix.lower()):
            remainder = cleaned[len(prefix):].strip().lstrip(":")
            try:
                return json.loads(remainder)
            except (json.JSONDecodeError, ValueError):
                pass

    # All strategies failed - return raw text
    return {fallback_key: text}


def safe_get(data: Dict[str, Any], *keys: str, default: Any = None) -> Any:
    """
    Safely traverse nested dict keys.

    Example: safe_get(data, "suggestions", "priority", default="none")
    """
    current = data
    for key in keys:
        if isinstance(current, dict):
            current = current.get(key, default)
        else:
            return default
    return current
