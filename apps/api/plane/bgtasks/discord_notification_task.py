# Copyright (c) 2024-present ClaudePlane contributors
# SPDX-License-Identifier: AGPL-3.0-only

"""
Discord notification background task.

Posts Plane events (issue created, updated, commented, etc.) to a
Discord channel via webhook URL. Supports rich embeds with color-coded
priority indicators.
"""

import json
import logging
import os

import requests
from celery import shared_task

from plane.utils.exception_logger import log_exception

logger = logging.getLogger(__name__)

# Priority to Discord embed color mapping (decimal RGB)
PRIORITY_COLORS = {
    "urgent": 0xFF0000,  # Red
    "high": 0xFF8C00,    # Dark Orange
    "medium": 0xFFD700,  # Gold
    "low": 0x3CB371,     # Medium Sea Green
    "none": 0x808080,    # Gray
}

# Event type to emoji mapping
EVENT_EMOJIS = {
    "issue.created": "📝",
    "issue.updated": "✏️",
    "issue.completed": "✅",
    "issue.deleted": "🗑️",
    "comment.created": "💬",
    "cycle.created": "🔄",
    "cycle.completed": "🏁",
    "module.created": "📦",
}


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=30,
    autoretry_for=(requests.exceptions.RequestException,),
)
def send_discord_notification(
    self,
    webhook_url: str,
    event_type: str,
    payload: dict,
):
    """
    Send a Discord webhook notification for a Plane event.

    Args:
        webhook_url: Discord webhook URL
        event_type: Type of event (e.g., "issue.created")
        payload: Event data including issue details
    """
    if not webhook_url:
        logger.warning("Discord webhook URL not configured, skipping notification")
        return

    try:
        embed = _build_discord_embed(event_type, payload)
        discord_payload = {
            "username": "ClaudePlane",
            "avatar_url": "https://avatars.githubusercontent.com/u/76263028",
            "embeds": [embed],
        }

        response = requests.post(
            webhook_url,
            json=discord_payload,
            headers={"Content-Type": "application/json"},
            timeout=10,
        )
        response.raise_for_status()
        logger.info(f"Discord notification sent for {event_type}")

    except requests.exceptions.RequestException as exc:
        logger.error(f"Failed to send Discord notification: {exc}")
        raise  # Let Celery retry


def _build_discord_embed(event_type: str, payload: dict) -> dict:
    """
    Build a Discord embed object from a Plane event payload.

    Returns a dict conforming to the Discord embed structure.
    """
    emoji = EVENT_EMOJIS.get(event_type, "📌")
    event_label = event_type.replace(".", " ").title()

    issue = payload.get("issue", {})
    project = payload.get("project", {})
    workspace = payload.get("workspace", {})
    actor = payload.get("actor", {})

    title = f"{emoji} {event_label}"
    description_parts = []

    if issue.get("name"):
        identifier = issue.get("identifier", "")
        description_parts.append(f"**{identifier}**: {issue['name']}")

    if issue.get("description_stripped"):
        desc = issue["description_stripped"][:300]
        description_parts.append(f"\n{desc}")

    priority = issue.get("priority", "none")
    color = PRIORITY_COLORS.get(priority, 0x808080)

    fields = []
    if priority and priority != "none":
        fields.append({"name": "Priority", "value": priority.title(), "inline": True})
    if issue.get("state_name"):
        fields.append({"name": "State", "value": issue["state_name"], "inline": True})
    if project.get("name"):
        fields.append({"name": "Project", "value": project["name"], "inline": True})

    embed = {
        "title": title,
        "description": "\n".join(description_parts) if description_parts else "No details available",
        "color": color,
        "fields": fields,
        "footer": {
            "text": f"ClaudePlane • {workspace.get('name', 'Workspace')}",
        },
    }

    if actor.get("display_name"):
        embed["author"] = {"name": actor["display_name"]}

    return embed


@shared_task
def send_discord_test_notification(webhook_url: str):
    """Send a test notification to verify Discord webhook configuration."""
    payload = {
        "username": "ClaudePlane",
        "avatar_url": "https://avatars.githubusercontent.com/u/76263028",
        "embeds": [{
            "title": "🔔 ClaudePlane Connected!",
            "description": "Discord notifications are working correctly.",
            "color": 0x7C3AED,
            "fields": [
                {"name": "Status", "value": "✅ Connected", "inline": True},
                {"name": "Source", "value": "ClaudePlane", "inline": True},
            ],
            "footer": {"text": "ClaudePlane Discord Integration"},
        }],
    }

    response = requests.post(
        webhook_url,
        json=payload,
        headers={"Content-Type": "application/json"},
        timeout=10,
    )
    response.raise_for_status()
    return {"status": "sent", "status_code": response.status_code}
