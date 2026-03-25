"""
Management command to sync GitHub repositories as Plane projects.

Usage:
    python manage.py sync_github_repos --workspace <slug> --github-user <username>
    python manage.py sync_github_repos --workspace <slug> --github-user <username> --token <gh-token>
"""
import subprocess
import json
import logging

from django.core.management.base import BaseCommand
from django.db import IntegrityError

from plane.db.models import Project, Workspace, ProjectMember, User

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Sync GitHub repositories as Plane projects for a workspace"

    def add_arguments(self, parser):
        parser.add_argument(
            "--workspace",
            type=str,
            required=True,
            help="Plane workspace slug",
        )
        parser.add_argument(
            "--github-user",
            type=str,
            required=True,
            help="GitHub username to fetch repos from",
        )
        parser.add_argument(
            "--token",
            type=str,
            default=None,
            help="GitHub personal access token (optional, uses gh CLI auth if omitted)",
        )
        parser.add_argument(
            "--admin-email",
            type=str,
            default=None,
            help="Email of the Plane user to set as project admin",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be created without making changes",
        )

    def _fetch_repos(self, github_user, token=None):
        """Fetch repos using gh CLI or GitHub API."""
        try:
            cmd = [
                "gh", "api",
                f"/users/{github_user}/repos",
                "--paginate",
                "-q", ".[] | {name, full_name, description, html_url, language, private, archived, topics}",
            ]
            if token:
                cmd.extend(["--header", f"Authorization: token {token}"])

            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=30
            )
            if result.returncode != 0:
                self.stderr.write(f"gh CLI error: {result.stderr}")
                return []

            repos = []
            for line in result.stdout.strip().split("\n"):
                if line.strip():
                    repos.append(json.loads(line))
            return repos
        except FileNotFoundError:
            self.stderr.write("gh CLI not found. Install it or provide --token.")
            return []
        except Exception as e:
            self.stderr.write(f"Error fetching repos: {e}")
            return []

    def _generate_identifier(self, name, existing_identifiers):
        """Generate a unique project identifier from repo name."""
        # Take first letters of words, uppercase, max 5 chars
        parts = name.replace("-", " ").replace("_", " ").split()
        if len(parts) >= 2:
            identifier = "".join(p[0] for p in parts[:5]).upper()
        else:
            identifier = name[:5].upper()

        # Ensure uniqueness
        base = identifier
        counter = 1
        while identifier in existing_identifiers:
            identifier = f"{base[:4]}{counter}"
            counter += 1

        return identifier

    def handle(self, *args, **options):
        workspace_slug = options["workspace"]
        github_user = options["github_user"]
        token = options.get("token")
        admin_email = options.get("admin_email")
        dry_run = options.get("dry_run", False)

        # Get workspace
        try:
            workspace = Workspace.objects.get(slug=workspace_slug)
        except Workspace.DoesNotExist:
            self.stderr.write(f"Workspace '{workspace_slug}' not found")
            return

        # Get admin user if specified
        admin_user = None
        if admin_email:
            try:
                admin_user = User.objects.get(email=admin_email)
            except User.DoesNotExist:
                self.stderr.write(f"User '{admin_email}' not found")
                return

        # Fetch repos
        self.stdout.write(f"Fetching repos for {github_user}...")
        repos = self._fetch_repos(github_user, token)

        if not repos:
            self.stdout.write("No repositories found.")
            return

        self.stdout.write(f"Found {len(repos)} repositories")

        # Get existing projects and identifiers
        existing_projects = set(
            Project.objects.filter(workspace=workspace).values_list("name", flat=True)
        )
        existing_identifiers = set(
            Project.objects.filter(workspace=workspace).values_list("identifier", flat=True)
        )

        created = 0
        skipped = 0

        for repo in repos:
            name = repo["name"]

            if repo.get("archived", False):
                self.stdout.write(f"  SKIP (archived): {name}")
                skipped += 1
                continue

            if name in existing_projects:
                self.stdout.write(f"  SKIP (exists): {name}")
                skipped += 1
                continue

            description = repo.get("description") or ""
            language = repo.get("language") or "Unknown"
            url = repo.get("html_url", "")
            is_private = repo.get("private", False)

            # Build rich description
            full_description = f"{description}\n\n"
            full_description += f"**GitHub:** {url}\n"
            full_description += f"**Language:** {language}\n"
            if repo.get("topics"):
                topics = repo["topics"] if isinstance(repo["topics"], list) else []
                if topics:
                    full_description += f"**Topics:** {', '.join(topics)}\n"

            identifier = self._generate_identifier(name, existing_identifiers)

            if dry_run:
                self.stdout.write(
                    f"  WOULD CREATE: {name} [{identifier}] - {description[:60]}"
                )
            else:
                try:
                    project = Project.objects.create(
                        workspace=workspace,
                        name=name,
                        identifier=identifier,
                        description=full_description,
                        network=1 if is_private else 2,  # 1=secret, 2=public
                        created_by=admin_user if admin_user else workspace.owner,
                    )

                    # Add admin as project member
                    if admin_user:
                        ProjectMember.objects.create(
                            project=project,
                            workspace=workspace,
                            member=admin_user,
                            role=20,  # ADMIN
                            created_by=admin_user,
                        )

                    existing_identifiers.add(identifier)
                    existing_projects.add(name)
                    self.stdout.write(f"  CREATED: {name} [{identifier}]")
                    created += 1
                except IntegrityError as e:
                    self.stderr.write(f"  ERROR creating {name}: {e}")
                except Exception as e:
                    self.stderr.write(f"  ERROR creating {name}: {e}")

            skipped_or_created = "would create" if dry_run else "created"

        self.stdout.write(
            f"\nDone! {skipped_or_created if dry_run else 'Created'}: {created}, Skipped: {skipped}"
        )
