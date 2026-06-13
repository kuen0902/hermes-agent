---
name: kanban
description: "Umbrella skill for Kanban orchestration, task decomposition, and isolated worker implementation."
version: 1.0.0
author: Hermes
license: MIT
metadata:
  hermes:
    tags: [kanban, orchestration, worker, project-management, delegation]
---

# Kanban Workflow & Orchestration

This umbrella skill captures the playbook for managing complex tasks through the Kanban system.

## 1. Orchestration (The "Don't Do It Yourself" Rule)
- Always decompose high-level goals into bite-sized tasks.
- Use `delegate_task` or autonomous subagents for implementation.
- Maintain the board state at `~/.hermes/kanban/`.

## 2. Worker Lifecycle
- **Discovery**: Read context and previous items.
- **Implementation**: Work on one item at a time.
- **Reconciliation**: Update status and hand back to the orchestrator.

## 3. Isolated Implementation Lanes (Codex/Claude)
- Use narrow implementation lanes (like `kanban-codex-lane`) for specialized coding tasks where Hermes keeps ownership of the lifecycle but delegates the raw content generation.
- **Pattern**: `hermes chat -q "Implement X" --source kanban`.
