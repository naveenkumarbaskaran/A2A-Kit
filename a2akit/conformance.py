"""Conformance test suite for A2A protocol compliance."""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any

from .card import AgentCard
from .task import TaskStatus


@dataclass
class ConformanceResult:
    """Result of a single conformance check."""

    name: str
    passed: bool
    detail: str = ""


@dataclass
class ConformanceReport:
    """Full conformance test report."""

    results: list[ConformanceResult] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return all(r.passed for r in self.results)

    @property
    def score(self) -> str:
        p = sum(1 for r in self.results if r.passed)
        return f"{p}/{len(self.results)}"

    def summary(self) -> str:
        lines = []
        for r in self.results:
            icon = "✓" if r.passed else "✗"
            lines.append(f"  {icon} {r.name}")
            if r.detail and not r.passed:
                lines.append(f"    → {r.detail}")
        status = "PASSED" if self.passed else "FAILED"
        lines.append(f"\n{status}: {self.score} checks")
        return "\n".join(lines)


def check_agent_card(card_data: dict) -> list[ConformanceResult]:
    """Validate an agent card against the A2A specification."""
    results = []

    # Required fields
    results.append(ConformanceResult(
        name="Card has 'name' field",
        passed="name" in card_data and bool(card_data["name"]),
        detail="Missing or empty 'name'" if "name" not in card_data else "",
    ))

    results.append(ConformanceResult(
        name="Card has 'description' field",
        passed="description" in card_data and bool(card_data["description"]),
        detail="Missing or empty 'description'" if "description" not in card_data else "",
    ))

    results.append(ConformanceResult(
        name="Card has 'skills' array",
        passed="skills" in card_data and isinstance(card_data.get("skills"), list),
        detail="Missing or invalid 'skills' array",
    ))

    # Skills validation
    skills = card_data.get("skills", [])
    if skills:
        all_have_id = all("id" in s for s in skills)
        results.append(ConformanceResult(
            name="All skills have 'id' field",
            passed=all_have_id,
            detail="Some skills missing 'id'",
        ))

        all_have_desc = all("description" in s for s in skills)
        results.append(ConformanceResult(
            name="All skills have 'description' field",
            passed=all_have_desc,
            detail="Some skills missing 'description'",
        ))

    # Capabilities
    caps = card_data.get("capabilities", {})
    results.append(ConformanceResult(
        name="Capabilities object present",
        passed="capabilities" in card_data,
        detail="Missing 'capabilities' — defaults will be assumed",
    ))

    return results


def check_task_response(task_data: dict) -> list[ConformanceResult]:
    """Validate a task response against the A2A specification."""
    results = []

    results.append(ConformanceResult(
        name="Task has 'id' field",
        passed="id" in task_data and bool(task_data["id"]),
    ))

    results.append(ConformanceResult(
        name="Task has 'status' field",
        passed="status" in task_data,
    ))

    status = task_data.get("status", "")
    valid_statuses = {s.value for s in TaskStatus}
    results.append(ConformanceResult(
        name="Task status is valid A2A state",
        passed=status in valid_statuses,
        detail=f"Got '{status}', expected one of: {valid_statuses}",
    ))

    results.append(ConformanceResult(
        name="Task has 'messages' array",
        passed="messages" in task_data and isinstance(task_data.get("messages"), list),
    ))

    # Message format
    messages = task_data.get("messages", [])
    for i, msg in enumerate(messages):
        results.append(ConformanceResult(
            name=f"Message[{i}] has 'role'",
            passed="role" in msg and msg["role"] in ("user", "agent"),
            detail=f"Got role='{msg.get('role')}'",
        ))
        results.append(ConformanceResult(
            name=f"Message[{i}] has 'parts' array",
            passed="parts" in msg and isinstance(msg.get("parts"), list),
        ))

    return results


def run_conformance(card_data: dict, task_data: dict | None = None) -> ConformanceReport:
    """Run full conformance suite against card and optionally a task response."""
    report = ConformanceReport()
    report.results.extend(check_agent_card(card_data))
    if task_data:
        report.results.extend(check_task_response(task_data))
    return report
