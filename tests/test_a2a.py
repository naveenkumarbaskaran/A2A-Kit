"""Tests for A2A-Kit."""

import pytest
import asyncio
from a2akit import (
    AgentCard, Skill, AgentCapabilities,
    Task, TaskStatus, TextPart, DataPart,
    AgentServer, AgentRegistry,
)
from a2akit.client import InMemoryClient
from a2akit.task import InvalidTransitionError
from a2akit.conformance import run_conformance, check_agent_card


# ─── Agent Card Tests ───────────────────────────────────────────

class TestAgentCard:
    def test_card_creation(self):
        card = AgentCard(
            name="Test Agent",
            description="A test agent",
            skills=[Skill(id="greet", description="Say hello")],
        )
        assert card.name == "Test Agent"
        assert len(card.skills) == 1

    def test_card_to_dict(self):
        card = AgentCard(
            name="Test",
            description="Desc",
            capabilities=AgentCapabilities(streaming=True),
            skills=[Skill(id="s1", description="Skill 1")],
        )
        d = card.to_dict()
        assert d["name"] == "Test"
        assert d["capabilities"]["streaming"] is True
        assert d["skills"][0]["id"] == "s1"

    def test_card_from_dict(self):
        data = {
            "name": "Parsed Agent",
            "description": "From JSON",
            "capabilities": {"streaming": True, "pushNotifications": False},
            "skills": [{"id": "analyze", "description": "Analyze data"}],
        }
        card = AgentCard.from_dict(data)
        assert card.name == "Parsed Agent"
        assert card.capabilities.streaming is True
        assert card.skills[0].id == "analyze"

    def test_card_validation_errors(self):
        card = AgentCard(name="", description="", skills=[])
        errors = card.validate()
        assert len(errors) >= 3  # name, description, skills

    def test_card_validation_passes(self):
        card = AgentCard(
            name="Valid",
            description="Valid agent",
            skills=[Skill(id="do_thing", description="Does thing")],
        )
        assert card.validate() == []


# ─── Task Lifecycle Tests ───────────────────────────────────────

class TestTaskLifecycle:
    def test_task_creation(self):
        task = Task.from_message("Hello")
        assert task.status == TaskStatus.SUBMITTED
        assert len(task.messages) == 1
        assert task.messages[0].role == "user"

    def test_valid_transitions(self):
        task = Task()
        task.transition(TaskStatus.WORKING)
        assert task.status == TaskStatus.WORKING

        task.transition(TaskStatus.COMPLETED)
        assert task.status == TaskStatus.COMPLETED
        assert len(task.history) == 2

    def test_invalid_transition_raises(self):
        task = Task()
        with pytest.raises(InvalidTransitionError):
            task.transition(TaskStatus.COMPLETED)  # Can't skip WORKING

    def test_terminal_states(self):
        task = Task(status=TaskStatus.COMPLETED)
        assert task.is_terminal is True

        task2 = Task(status=TaskStatus.WORKING)
        assert task2.is_terminal is False

    def test_input_required_flow(self):
        task = Task()
        task.transition(TaskStatus.WORKING)
        task.transition(TaskStatus.INPUT_REQUIRED)
        assert task.status == TaskStatus.INPUT_REQUIRED

        task.transition(TaskStatus.WORKING)
        task.transition(TaskStatus.COMPLETED)
        assert task.is_terminal is True


# ─── Server Tests ───────────────────────────────────────────────

class TestAgentServer:
    @pytest.fixture
    def server(self):
        card = AgentCard(
            name="Test Server",
            description="Server for tests",
            skills=[Skill(id="echo", description="Echoes input")],
        )
        srv = AgentServer(card=card)

        @srv.skill("echo")
        async def echo_handler(task: Task):
            user_msg = task.messages[0].parts[0].text
            return f"Echo: {user_msg}"

        return srv

    @pytest.mark.asyncio
    async def test_discovery(self, server):
        result = await server.handle_discovery()
        assert result["name"] == "Test Server"
        assert len(result["skills"]) == 1

    @pytest.mark.asyncio
    async def test_task_submit(self, server):
        result = await server.handle_task_submit({"message": "Hello world"})
        assert result["status"] == "completed"
        # Check agent responded
        agent_msgs = [m for m in result["messages"] if m["role"] == "agent"]
        assert len(agent_msgs) == 1
        assert "Echo: Hello world" in agent_msgs[0]["parts"][0]["text"]

    @pytest.mark.asyncio
    async def test_task_status(self, server):
        result = await server.handle_task_submit({"message": "Test"})
        task_id = result["id"]
        status = await server.handle_task_status(task_id)
        assert status["status"] == "completed"

    @pytest.mark.asyncio
    async def test_unknown_task(self, server):
        result = await server.handle_task_status("nonexistent")
        assert result is None


# ─── Client Tests ───────────────────────────────────────────────

class TestInMemoryClient:
    @pytest.fixture
    def client(self):
        card = AgentCard(
            name="Memory Agent",
            description="In-memory test",
            skills=[Skill(id="upper", description="Uppercases text")],
        )
        srv = AgentServer(card=card)

        @srv.skill("upper")
        async def upper_handler(task: Task):
            text = task.messages[0].parts[0].text
            return text.upper()

        return InMemoryClient(srv)

    @pytest.mark.asyncio
    async def test_discover(self, client):
        card = await client.discover()
        assert card.name == "Memory Agent"

    @pytest.mark.asyncio
    async def test_send_task(self, client):
        resp = await client.send_task("hello world")
        assert resp.status == "completed"
        assert resp.text == "HELLO WORLD"

    @pytest.mark.asyncio
    async def test_get_task(self, client):
        resp = await client.send_task("test")
        task = await client.get_task(resp.task_id)
        assert task.status == "completed"


# ─── Registry Tests ─────────────────────────────────────────────

class TestRegistry:
    def test_register_and_discover(self):
        registry = AgentRegistry()
        card = AgentCard(
            name="Weather",
            description="Weather info",
            skills=[Skill(id="forecast", description="Get forecast")],
        )
        registry.register("http://weather:8080", card=card)
        assert registry.count == 1

        results = registry.discover(skill="forecast")
        assert len(results) == 1
        assert results[0].name == "Weather"

    def test_discover_no_match(self):
        registry = AgentRegistry()
        card = AgentCard(
            name="Math",
            description="Math",
            skills=[Skill(id="calculate", description="Calc")],
        )
        registry.register("http://math:8080", card=card)

        results = registry.discover(skill="weather")
        assert len(results) == 0

    def test_discover_by_name(self):
        registry = AgentRegistry()
        registry.register("http://a:80", card=AgentCard(
            name="Order Analyst", description="Orders",
            skills=[Skill(id="s1", description="d")],
        ))
        registry.register("http://b:80", card=AgentCard(
            name="Weather Bot", description="Weather",
            skills=[Skill(id="s2", description="d")],
        ))

        results = registry.discover(name="order")
        assert len(results) == 1
        assert results[0].name == "Order Analyst"

    def test_unregister(self):
        registry = AgentRegistry()
        card = AgentCard(name="X", description="X", skills=[Skill(id="x", description="x")])
        registry.register("http://x:80", card=card)
        assert registry.count == 1
        registry.unregister("http://x:80")
        assert registry.count == 0


# ─── Conformance Tests ──────────────────────────────────────────

class TestConformance:
    def test_valid_card_passes(self):
        card_data = {
            "name": "Valid Agent",
            "description": "A valid agent",
            "capabilities": {"streaming": False},
            "skills": [{"id": "s1", "description": "Does something"}],
        }
        report = run_conformance(card_data)
        assert report.passed is True

    def test_invalid_card_fails(self):
        card_data = {"name": "", "skills": []}
        report = run_conformance(card_data)
        assert report.passed is False

    def test_valid_task_passes(self):
        card_data = {
            "name": "Agent",
            "description": "Desc",
            "capabilities": {},
            "skills": [{"id": "s", "description": "d"}],
        }
        task_data = {
            "id": "abc-123",
            "status": "completed",
            "messages": [
                {"role": "user", "parts": [{"kind": "text", "text": "hi"}]},
                {"role": "agent", "parts": [{"kind": "text", "text": "hello"}]},
            ],
        }
        report = run_conformance(card_data, task_data)
        assert report.passed is True
