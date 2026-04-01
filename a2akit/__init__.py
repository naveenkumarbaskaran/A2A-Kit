"""A2A-Kit — Production-ready SDK for the Agent-to-Agent protocol."""

from .card import AgentCard, Skill, AgentCapabilities
from .task import Task, TaskStatus, TextPart, DataPart
from .server import AgentServer, skill
from .client import AgentClient
from .registry import AgentRegistry

__version__ = "0.1.0"
__all__ = [
    "AgentCard",
    "Skill",
    "AgentCapabilities",
    "Task",
    "TaskStatus",
    "TextPart",
    "DataPart",
    "AgentServer",
    "AgentClient",
    "AgentRegistry",
    "skill",
]
