"""Task — lifecycle management for A2A tasks."""

from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional
import uuid
import time


class TaskStatus(Enum):
    """A2A task status states."""

    SUBMITTED = "submitted"
    WORKING = "working"
    INPUT_REQUIRED = "input-required"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELED = "canceled"

    @classmethod
    def valid_transitions(cls) -> dict["TaskStatus", list["TaskStatus"]]:
        return {
            cls.SUBMITTED: [cls.WORKING, cls.FAILED, cls.CANCELED],
            cls.WORKING: [cls.COMPLETED, cls.FAILED, cls.INPUT_REQUIRED, cls.CANCELED],
            cls.INPUT_REQUIRED: [cls.WORKING, cls.FAILED, cls.CANCELED],
            cls.COMPLETED: [],
            cls.FAILED: [],
            cls.CANCELED: [],
        }

    def can_transition_to(self, target: "TaskStatus") -> bool:
        return target in self.valid_transitions().get(self, [])


@dataclass
class TextPart:
    """Text content in a task message."""

    text: str

    def to_dict(self) -> dict:
        return {"kind": "text", "text": self.text}


@dataclass
class DataPart:
    """Structured data in a task message."""

    data: dict[str, Any]

    def to_dict(self) -> dict:
        return {"kind": "data", "data": self.data}


@dataclass
class FilePart:
    """File content in a task message."""

    name: str
    mime_type: str
    data: bytes

    def to_dict(self) -> dict:
        import base64
        return {
            "kind": "file",
            "name": self.name,
            "mimeType": self.mime_type,
            "data": base64.b64encode(self.data).decode(),
        }


@dataclass
class Message:
    """A message in the task conversation."""

    role: str  # "user" or "agent"
    parts: list[TextPart | DataPart | FilePart] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "role": self.role,
            "parts": [p.to_dict() for p in self.parts],
        }


@dataclass
class Task:
    """
    A2A Task — represents a unit of work between agents.
    
    Lifecycle: SUBMITTED → WORKING → COMPLETED/FAILED
    """

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    status: TaskStatus = TaskStatus.SUBMITTED
    messages: list[Message] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    history: list[dict] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)

    def transition(self, new_status: TaskStatus) -> None:
        """Transition task to new status with validation."""
        if not self.status.can_transition_to(new_status):
            raise InvalidTransitionError(
                f"Cannot transition from {self.status.value} to {new_status.value}"
            )
        self.history.append({
            "from": self.status.value,
            "to": new_status.value,
            "timestamp": time.time(),
        })
        self.status = new_status
        self.updated_at = time.time()

    def add_message(self, role: str, text: str) -> None:
        """Add a text message to the task."""
        self.messages.append(Message(role=role, parts=[TextPart(text=text)]))
        self.updated_at = time.time()

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "status": self.status.value,
            "messages": [m.to_dict() for m in self.messages],
            "metadata": self.metadata,
            "history": self.history,
            "createdAt": self.created_at,
            "updatedAt": self.updated_at,
        }

    @classmethod
    def from_message(cls, text: str, **kwargs) -> "Task":
        """Create a new task from a user message."""
        task = cls(**kwargs)
        task.add_message("user", text)
        return task

    @property
    def is_terminal(self) -> bool:
        """Check if task is in a terminal state."""
        return self.status in (
            TaskStatus.COMPLETED,
            TaskStatus.FAILED,
            TaskStatus.CANCELED,
        )


class InvalidTransitionError(Exception):
    """Raised when attempting an invalid task state transition."""
    pass
