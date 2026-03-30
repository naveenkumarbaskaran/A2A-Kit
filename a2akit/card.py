"""Agent Card — capability declaration for A2A protocol."""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Skill:
    """A single skill/capability an agent exposes."""

    id: str
    description: str
    examples: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        d = {"id": self.id, "description": self.description}
        if self.examples:
            d["examples"] = self.examples
        if self.tags:
            d["tags"] = self.tags
        return d


@dataclass
class AgentCapabilities:
    """Declares what protocol features the agent supports."""

    streaming: bool = False
    push_notifications: bool = False
    state_transition_history: bool = False

    def to_dict(self) -> dict:
        return {
            "streaming": self.streaming,
            "pushNotifications": self.push_notifications,
            "stateTransitionHistory": self.state_transition_history,
        }


@dataclass
class AgentCard:
    """
    Agent Card — the identity and capability declaration for an A2A agent.
    
    Served at `/.well-known/agent.json` for discovery.
    """

    name: str
    description: str
    url: str = ""
    version: str = "1.0.0"
    capabilities: AgentCapabilities = field(default_factory=AgentCapabilities)
    skills: list[Skill] = field(default_factory=list)
    authentication: Optional[dict] = None

    def to_dict(self) -> dict:
        d = {
            "name": self.name,
            "description": self.description,
            "url": self.url,
            "version": self.version,
            "capabilities": self.capabilities.to_dict(),
            "skills": [s.to_dict() for s in self.skills],
        }
        if self.authentication:
            d["authentication"] = self.authentication
        return d

    @classmethod
    def from_dict(cls, data: dict) -> "AgentCard":
        caps = data.get("capabilities", {})
        skills = [
            Skill(id=s["id"], description=s.get("description", ""))
            for s in data.get("skills", [])
        ]
        return cls(
            name=data["name"],
            description=data.get("description", ""),
            url=data.get("url", ""),
            version=data.get("version", "1.0.0"),
            capabilities=AgentCapabilities(
                streaming=caps.get("streaming", False),
                push_notifications=caps.get("pushNotifications", False),
                state_transition_history=caps.get("stateTransitionHistory", False),
            ),
            skills=skills,
            authentication=data.get("authentication"),
        )

    def validate(self) -> list[str]:
        """Validate card has required fields. Returns list of errors."""
        errors = []
        if not self.name:
            errors.append("Agent card must have a name")
        if not self.description:
            errors.append("Agent card must have a description")
        if not self.skills:
            errors.append("Agent card must declare at least one skill")
        for skill in self.skills:
            if not skill.id:
                errors.append("Each skill must have an id")
            if not skill.description:
                errors.append(f"Skill '{skill.id}' must have a description")
        return errors
