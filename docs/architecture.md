# A2A-Kit Architecture

## Protocol Overview

The Agent-to-Agent (A2A) protocol enables AI agents to discover and communicate with each other through a standardized HTTP-based interface.

```mermaid
graph TB
    subgraph "Discovery Layer"
        Card[Agent Card<br>/.well-known/agent.json]
        Reg[Agent Registry]
    end

    subgraph "Transport Layer"
        HTTP[HTTP/HTTPS]
        SSE[Server-Sent Events]
    end

    subgraph "Task Layer"
        Submit[Task Submission]
        Status[Status Polling]
        Stream[Event Streaming]
    end

    subgraph "Execution Layer"
        Router[Skill Router]
        Handler[Skill Handler]
        State[State Machine]
    end

    Card --> Reg
    Reg --> HTTP
    HTTP --> Submit
    HTTP --> Status
    SSE --> Stream
    Submit --> Router
    Router --> Handler
    Handler --> State

    style Card fill:#9b59b6,color:#fff
    style Router fill:#e74c3c,color:#fff
    style State fill:#3498db,color:#fff
```

## Task State Machine

```mermaid
stateDiagram-v2
    [*] --> Submitted: POST /tasks
    Submitted --> Working: Agent starts processing
    Working --> Completed: Success
    Working --> Failed: Error
    Working --> InputRequired: Need user input
    InputRequired --> Working: User provides input
    Working --> Canceled: Cancel request
    Submitted --> Canceled: Cancel before start
    Submitted --> Failed: Immediate failure
    InputRequired --> Failed: Timeout
    InputRequired --> Canceled: User cancels

    Completed --> [*]
    Failed --> [*]
    Canceled --> [*]
```

## Communication Sequence

```mermaid
sequenceDiagram
    participant C as Client Agent
    participant R as Registry
    participant S as Server Agent

    Note over C,S: Phase 1: Discovery
    C->>R: Find agents with skill "forecast"
    R-->>C: [Agent Card: Weather Agent]

    Note over C,S: Phase 2: Task Submission
    C->>S: POST /tasks {message: "Weather in Berlin"}
    S-->>C: {id: "abc", status: "submitted"}

    Note over C,S: Phase 3: Execution (streaming)
    C->>S: GET /tasks/abc/stream
    S-->>C: event: {status: "working", text: "Fetching data..."}
    S-->>C: event: {status: "working", text: "Analyzing..."}
    S-->>C: event: {status: "completed", text: "Sunny, 24°C"}
```

## Module Architecture

```mermaid
graph LR
    subgraph "a2akit package"
        card[card.py<br>AgentCard, Skill]
        task[task.py<br>Task, TaskStatus]
        server[server.py<br>AgentServer]
        client[client.py<br>AgentClient]
        registry[registry.py<br>AgentRegistry]
        conf[conformance.py<br>Test Suite]
    end

    server --> card
    server --> task
    client --> card
    client --> task
    registry --> card
    conf --> card
    conf --> task

    style server fill:#e74c3c,color:#fff
    style client fill:#3498db,color:#fff
    style registry fill:#2ecc71,color:#fff
```

## Multi-Agent Topology

```mermaid
graph TB
    subgraph "Agent Network"
        A1[Maintenance Analyst<br>Skills: search, costs, teco]
        A2[Weather Agent<br>Skills: forecast, alerts]
        A3[Procurement Agent<br>Skills: purchase_orders]
        A4[Supervisor Agent<br>Skills: orchestrate]
    end

    subgraph "Registry"
        REG[(Agent Registry)]
    end

    A1 -.->|register| REG
    A2 -.->|register| REG
    A3 -.->|register| REG
    A4 -->|discover| REG
    A4 -->|delegate task| A1
    A4 -->|delegate task| A2
    A4 -->|delegate task| A3
```

## Performance

| Operation | Latency | Notes |
|-----------|---------|-------|
| Card discovery | < 5ms | JSON parse only |
| Task submission | < 10ms | Routing + handler call |
| State transition | < 1ms | In-memory validation |
| Registry lookup | < 1ms | Dict/set operations |
| Conformance suite | < 50ms | All checks combined |

## Protocol Compliance Matrix

| Feature | A2A Spec | A2A-Kit | Notes |
|---------|----------|---------|-------|
| Agent Card | Required | ✅ | Full `AgentCard` dataclass |
| Task CRUD | Required | ✅ | Create, read, status |
| State machine | Required | ✅ | With transition validation |
| Multi-part messages | Required | ✅ | Text, Data, File parts |
| SSE streaming | Optional | ✅ | Queue-based implementation |
| Push notifications | Optional | 🔄 | Interface defined |
| Authentication | Optional | ✅ | Header passthrough |
| Error schema | Required | ✅ | Standard error responses |
