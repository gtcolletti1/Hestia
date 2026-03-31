"""Todoist REST API v2 integration client."""

import logging
from dataclasses import dataclass

import httpx

logger = logging.getLogger(__name__)

TODOIST_API_BASE = "https://api.todoist.com/rest/v2"


@dataclass
class TodoistClient:
    """Async wrapper around the Todoist REST API v2."""

    api_token: str
    _base_url: str = TODOIST_API_BASE

    @property
    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_token}",
            "Content-Type": "application/json",
        }

    # ── Projects ─────────────────────────────────────────────────────────

    async def get_projects(self) -> list[dict]:
        """Return all projects for the authenticated user."""
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{self._base_url}/projects",
                headers=self._headers,
            )
            resp.raise_for_status()
            return resp.json()

    # ── Tasks ────────────────────────────────────────────────────────────

    async def get_tasks(self, project_id: str) -> list[dict]:
        """Return all active tasks in a project."""
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{self._base_url}/tasks",
                headers=self._headers,
                params={"project_id": project_id},
            )
            resp.raise_for_status()
            return [self._map_task(t) for t in resp.json()]

    async def create_task(self, project_id: str, content: str) -> dict:
        """Create a new task in the given project."""
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{self._base_url}/tasks",
                headers=self._headers,
                json={"project_id": project_id, "content": content},
            )
            resp.raise_for_status()
            return self._map_task(resp.json())

    async def complete_task(self, task_id: str) -> None:
        """Mark a task as completed."""
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{self._base_url}/tasks/{task_id}/close",
                headers=self._headers,
            )
            resp.raise_for_status()

    async def delete_task(self, task_id: str) -> None:
        """Permanently delete a task."""
        async with httpx.AsyncClient() as client:
            resp = await client.delete(
                f"{self._base_url}/tasks/{task_id}",
                headers=self._headers,
            )
            resp.raise_for_status()

    # ── Mapping ──────────────────────────────────────────────────────────

    @staticmethod
    def _map_task(todoist_task: dict) -> dict:
        """Map a Todoist task to the local ListItem-compatible format."""
        due = todoist_task.get("due")
        return {
            "external_id": todoist_task["id"],
            "title": todoist_task["content"],
            "description": todoist_task.get("description", ""),
            "is_completed": todoist_task.get("is_completed", False),
            "priority": todoist_task.get("priority", 1),
            "due_date": due["date"] if due else None,
            "labels": todoist_task.get("labels", []),
            "source": "todoist",
        }
