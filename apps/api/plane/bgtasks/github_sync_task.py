# Copyright (c) 2024-present ClaudePlane contributors
# SPDX-License-Identifier: AGPL-3.0-only

"""
GitHub reverse sync background task.

When an issue is created or updated in Plane, this task can create
or update the corresponding GitHub issue for bidirectional sync.
Requires GITHUB_TOKEN and GITHUB_REPO environment variables.
"""

import json
import logging
import os

import requests
from celery import shared_task

from plane.utils.exception_logger import log_exception

logger = logging.getLogger(__name__)

GITHUB_API_BASE = "https://api.github.com"


def _get_github_config():
    """Read GitHub sync configuration from environment."""
    token = os.environ.get("GITHUB_SYNC_TOKEN", "")
    default_repo = os.environ.get("GITHUB_SYNC_REPO", "")  # format: "owner/repo"
    return token, default_repo


def _priority_to_labels(priority: str) -> list:
    """Map Plane priority levels to GitHub label names."""
    mapping = {
        "urgent": ["priority: critical"],
        "high": ["priority: high"],
        "medium": ["priority: medium"],
        "low": ["priority: low"],
        "none": [],
    }
    return mapping.get(priority, [])


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=30,
    autoretry_for=(requests.exceptions.RequestException,),
)
def sync_issue_to_github(
    self,
    issue_data: dict,
    action: str = "create",
    github_repo: str = None,
):
    """
    Sync a Plane issue to GitHub.

    Args:
        issue_data: Dict with issue fields (name, description_stripped, priority, etc.)
        action: "create" or "update"
        github_repo: Optional "owner/repo" override. Falls back to GITHUB_SYNC_REPO env var.
    """
    token, default_repo = _get_github_config()
    repo = github_repo or default_repo

    if not token:
        logger.warning("GITHUB_SYNC_TOKEN not set, skipping GitHub sync")
        return {"status": "skipped", "reason": "no token"}

    if not repo:
        logger.warning("GITHUB_SYNC_REPO not set, skipping GitHub sync")
        return {"status": "skipped", "reason": "no repo"}

    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github.v3+json",
        "Content-Type": "application/json",
    }

    issue_name = issue_data.get("name", "Untitled Issue")
    description = issue_data.get("description_stripped", "")
    priority = issue_data.get("priority", "none")
    external_id = issue_data.get("external_id")
    plane_id = issue_data.get("id", "")
    plane_identifier = issue_data.get("identifier", "")

    # Build GitHub issue body
    body_parts = []
    if description:
        body_parts.append(description)
    body_parts.append(f"\n---\n_Synced from ClaudePlane: {plane_identifier or plane_id}_")
    body = "\n\n".join(body_parts)

    labels = _priority_to_labels(priority)

    try:
        if action == "update" and external_id:
            # Update existing GitHub issue
            url = f"{GITHUB_API_BASE}/repos/{repo}/issues/{external_id}"
            payload = {
                "title": f"[{plane_identifier}] {issue_name}" if plane_identifier else issue_name,
                "body": body,
                "labels": labels,
            }
            response = requests.patch(url, headers=headers, json=payload, timeout=15)
            response.raise_for_status()
            logger.info(f"Updated GitHub issue #{external_id} for Plane issue {plane_id}")
            return {
                "status": "updated",
                "github_issue_number": external_id,
                "url": response.json().get("html_url"),
            }

        else:
            # Create new GitHub issue
            url = f"{GITHUB_API_BASE}/repos/{repo}/issues"
            payload = {
                "title": f"[{plane_identifier}] {issue_name}" if plane_identifier else issue_name,
                "body": body,
                "labels": labels,
            }
            response = requests.post(url, headers=headers, json=payload, timeout=15)
            response.raise_for_status()

            gh_issue = response.json()
            github_number = gh_issue.get("number")
            logger.info(f"Created GitHub issue #{github_number} for Plane issue {plane_id}")

            return {
                "status": "created",
                "github_issue_number": github_number,
                "url": gh_issue.get("html_url"),
            }

    except requests.exceptions.RequestException as exc:
        logger.error(f"GitHub sync failed for issue {plane_id}: {exc}")
        raise  # Let Celery retry
    except Exception as exc:
        log_exception(exc)
        return {"status": "error", "error": str(exc)}
