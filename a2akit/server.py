"""AgentServer — HTTP server implementing A2A protocol."""

from __future__ import annotations
from typing import Callable, Any
import asyncio
import json
from functools import wraps

from .card import AgentCard
from .task import Task, TaskStatus, TextPart, DataPart, Message


def skill(skill_id: str):
    """Decorator to register a function as an A2A skill."""
    def decorator(func: Callable):
        func._a2a_skill_id = skill_id
        @wraps(func)
        async def wrapper(*args, **kwargs):
            if asyncio.iscoroutinefunction(func):
                return await func(*args, **kwargs)
            return func(*args, **kwargs)
        wrapper._a2a_skill_id = skill_id
        return wrapper
    return decorator


class AgentServer:
    """
    A2A Protocol Server.
    
    Handles:
    - Agent card discovery (GET /.well-known/agent.json)
    - Task submission (POST /tasks)
    - Task status (GET /tasks/{id})
    - Task streaming (GET /tasks/{id}/stream)
    """

    def __init__(self, card: AgentCard, port: int = 8080):
        self.card = card
        self.port = port
        self._skills: dict[str, Callable] = {}
        self._tasks: dict[str, Task] = {}
        self._stream_queues: dict[str, asyncio.Queue] = {}

    def skill(self, skill_id: str):
        """Register a skill handler via decorator."""
        def decorator(func: Callable):
            self._skills[skill_id] = func
            return func
        return decorator

    def register_skill(self, skill_id: str, handler: Callable) -> None:
        """Register a skill handler programmatically."""
        self._skills[skill_id] = handler

    async def handle_discovery(self) -> dict:
        """Handle GET /.well-known/agent.json"""
        return self.card.to_dict()

    async def handle_task_submit(self, request: dict) -> dict:
        """
        Handle POST /tasks — create and execute a task.
        
        Request: {"message": "...", "skill": "optional_skill_id", "metadata": {}}
        """
        message_text = request.get("message", "")
        skill_id = request.get("skill")
        metadata = request.get("metadata", {})

        task = Task.from_message(message_text, metadata=metadata)
        self._tasks[task.id] = task

        # Route to skill
        handler = self._resolve_skill(skill_id, message_text)
        if not handler:
            task.transition(TaskStatus.FAILED)
            task.add_message("agent", f"No skill found for: {skill_id or message_text}")
            return task.to_dict()

        # Execute
        task.transition(TaskStatus.WORKING)
        try:
            result = await self._execute_skill(handler, task)
            task.transition(TaskStatus.COMPLETED)
            if isinstance(result, str):
                task.add_message("agent", result)
            elif isinstance(result, dict):
                task.messages.append(
                    Message(role="agent", parts=[DataPart(data=result)])
                )
        except Exception as e:
            task.transition(TaskStatus.FAILED)
            task.add_message("agent", f"Error: {str(e)}")

        return task.to_dict()

    async def handle_task_status(self, task_id: str) -> dict | None:
        """Handle GET /tasks/{id}"""
        task = self._tasks.get(task_id)
        return task.to_dict() if task else None

    async def handle_task_stream(self, task_id: str):
        """Handle GET /tasks/{id}/stream — yields SSE events."""
        queue = asyncio.Queue()
        self._stream_queues[task_id] = queue

        while True:
            event = await queue.get()
            yield f"data: {json.dumps(event)}\n\n"
            if event.get("status") in ("completed", "failed", "canceled"):
                break

        del self._stream_queues[task_id]

    def _resolve_skill(self, skill_id: str | None, message: str) -> Callable | None:
        """Find the appropriate skill handler."""
        if skill_id and skill_id in self._skills:
            return self._skills[skill_id]
        # Default: first skill if only one registered
        if len(self._skills) == 1:
            return next(iter(self._skills.values()))
        return None

    async def _execute_skill(self, handler: Callable, task: Task) -> Any:
        """Execute a skill handler, supporting both sync and async."""
        if asyncio.iscoroutinefunction(handler):
            return await handler(task)
        return handler(task)

    def _emit_stream_event(self, task_id: str, event: dict) -> None:
        """Push an SSE event to stream subscribers."""
        queue = self._stream_queues.get(task_id)
        if queue:
            queue.put_nowait(event)

    def run(self, port: int | None = None):
        """Start the A2A server (placeholder — use with aiohttp/fastapi)."""
        self.port = port or self.port
        print(f"A2A Agent '{self.card.name}' ready at http://0.0.0.0:{self.port}")
        print(f"  Discovery: http://0.0.0.0:{self.port}/.well-known/agent.json")
        print(f"  Skills: {list(self._skills.keys())}")
