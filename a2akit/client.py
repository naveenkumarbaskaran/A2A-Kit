"""AgentClient — client for calling A2A agents."""

from __future__ import annotations
from dataclasses import dataclass
from typing import Any, AsyncIterator
import json

from .card import AgentCard
from .task import Task


@dataclass
class TaskResponse:
    """Response from an A2A task submission."""

    task_id: str
    status: str
    messages: list[dict]
    raw: dict

    @property
    def text(self) -> str:
        """Extract text from agent's last message."""
        for msg in reversed(self.messages):
            if msg["role"] == "agent":
                for part in msg.get("parts", []):
                    if part.get("kind") == "text":
                        return part["text"]
        return ""

    @property
    def data(self) -> dict | None:
        """Extract data from agent's last message."""
        for msg in reversed(self.messages):
            if msg["role"] == "agent":
                for part in msg.get("parts", []):
                    if part.get("kind") == "data":
                        return part["data"]
        return None


class AgentClient:
    """
    Client for interacting with A2A protocol agents.
    
    Handles discovery, task submission, polling, and streaming.
    """

    def __init__(self, base_url: str, headers: dict[str, str] | None = None):
        self.base_url = base_url.rstrip("/")
        self.headers = headers or {}
        self._card: AgentCard | None = None

    async def discover(self) -> AgentCard:
        """Fetch and parse the agent's card from /.well-known/agent.json"""
        # In production, this would use aiohttp/httpx
        # For the SDK, we provide the parsing logic
        url = f"{self.base_url}/.well-known/agent.json"
        card_data = await self._get(url)
        self._card = AgentCard.from_dict(card_data)
        return self._card

    async def send_task(
        self,
        message: str,
        skill: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> TaskResponse:
        """Submit a task to the agent."""
        payload = {"message": message}
        if skill:
            payload["skill"] = skill
        if metadata:
            payload["metadata"] = metadata

        url = f"{self.base_url}/tasks"
        result = await self._post(url, payload)

        return TaskResponse(
            task_id=result["id"],
            status=result["status"],
            messages=result.get("messages", []),
            raw=result,
        )

    async def get_task(self, task_id: str) -> TaskResponse:
        """Poll task status."""
        url = f"{self.base_url}/tasks/{task_id}"
        result = await self._get(url)
        return TaskResponse(
            task_id=result["id"],
            status=result["status"],
            messages=result.get("messages", []),
            raw=result,
        )

    async def stream_task(self, task_id: str) -> AsyncIterator[dict]:
        """Subscribe to task SSE stream."""
        url = f"{self.base_url}/tasks/{task_id}/stream"
        async for event in self._stream(url):
            yield event

    async def _get(self, url: str) -> dict:
        """HTTP GET — override in subclass for real HTTP."""
        raise NotImplementedError("Subclass with aiohttp/httpx for real HTTP")

    async def _post(self, url: str, data: dict) -> dict:
        """HTTP POST — override in subclass for real HTTP."""
        raise NotImplementedError("Subclass with aiohttp/httpx for real HTTP")

    async def _stream(self, url: str) -> AsyncIterator[dict]:
        """SSE stream — override in subclass for real HTTP."""
        raise NotImplementedError("Subclass with aiohttp/httpx for real HTTP")
        yield  # pragma: no cover


class InMemoryClient(AgentClient):
    """
    Client that talks directly to an AgentServer in-memory.
    
    Useful for testing without network.
    """

    def __init__(self, server):
        super().__init__(base_url="http://localhost")
        self.server = server

    async def discover(self) -> AgentCard:
        card_data = await self.server.handle_discovery()
        self._card = AgentCard.from_dict(card_data)
        return self._card

    async def send_task(
        self,
        message: str,
        skill: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> TaskResponse:
        payload = {"message": message}
        if skill:
            payload["skill"] = skill
        if metadata:
            payload["metadata"] = metadata

        result = await self.server.handle_task_submit(payload)
        return TaskResponse(
            task_id=result["id"],
            status=result["status"],
            messages=result.get("messages", []),
            raw=result,
        )

    async def get_task(self, task_id: str) -> TaskResponse:
        result = await self.server.handle_task_status(task_id)
        if not result:
            raise ValueError(f"Task {task_id} not found")
        return TaskResponse(
            task_id=result["id"],
            status=result["status"],
            messages=result.get("messages", []),
            raw=result,
        )
