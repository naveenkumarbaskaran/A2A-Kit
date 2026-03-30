"""AgentRegistry — multi-agent discovery and routing."""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional

from .card import AgentCard


@dataclass
class RegisteredAgent:
    """An agent registered in the discovery registry."""

    url: str
    card: AgentCard
    healthy: bool = True
    last_check: float = 0.0


class AgentRegistry:
    """
    Agent Discovery Registry.
    
    Maintains a catalog of known A2A agents and enables
    discovery by skill, name, or capability.
    """

    def __init__(self):
        self._agents: dict[str, RegisteredAgent] = {}

    def register(self, url: str, card: AgentCard | None = None) -> None:
        """Register an agent by URL. Optionally provide pre-fetched card."""
        if card is None:
            # In production, would fetch from url/.well-known/agent.json
            raise ValueError("Card must be provided (async fetch not available in sync context)")
        self._agents[url] = RegisteredAgent(url=url, card=card)

    def unregister(self, url: str) -> None:
        """Remove an agent from the registry."""
        self._agents.pop(url, None)

    def discover(
        self,
        skill: str | None = None,
        name: str | None = None,
        streaming: bool | None = None,
    ) -> list[AgentCard]:
        """
        Find agents matching criteria.
        
        Args:
            skill: Filter by skill ID
            name: Filter by agent name (substring match)
            streaming: Filter by streaming capability
        """
        results = []
        for agent in self._agents.values():
            if not agent.healthy:
                continue
            card = agent.card

            if skill and not any(s.id == skill for s in card.skills):
                continue
            if name and name.lower() not in card.name.lower():
                continue
            if streaming is not None and card.capabilities.streaming != streaming:
                continue

            results.append(card)
        return results

    def list_all(self) -> list[AgentCard]:
        """List all registered agent cards."""
        return [a.card for a in self._agents.values()]

    def get_by_url(self, url: str) -> AgentCard | None:
        """Get a specific agent's card by URL."""
        agent = self._agents.get(url)
        return agent.card if agent else None

    @property
    def count(self) -> int:
        return len(self._agents)
