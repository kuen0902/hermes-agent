---
name: agentic-development
description: Umbrella skill for systematic software development, kanban orchestration, and autonomous agent delegation.
category: autonomous-ai-agents
version: 1.0.0
author: Hermes (Curator)
license: MIT
metadata:
  hermes:
    tags: [systematic-development, kanban, delegation, subagents, project-management, tdd]
---

# Agentic Development & Orchestration

This umbrella skill defines the framework for autonomous software development—integrating systematic planning, task decomposition (Kanban), and multi-agent delegation.

## 1. Systematic Development Lifecycle
- **Planning**: Bite-sized task creation and architectural validation (Spikes).
- **TDD Loop**: Red-Green-Refactor. Always write a failing test first.
- **Root-Cause Analysis**: Never fix without explaining why it failed.

## 2. Kanban & Task Decomposition
- **Orchestration**: Goal -> Decomposition -> Task Execution.
- **Isolated Lanes**: Using specialized workers for parallel implementation.
- **Board State**: Lifecycle management in `~/.hermes/kanban/`.

## 3. Autonomous Delegation
- **Coding Agents**: Leveraging Claude Code, Codex, or OpenCode for heavy lifting.
- **Context Injection**: Preparing the environment for high-quality subagent output.
- **Reconciliation**: Verifying subagent work via tests, linting, and manual exploration.

## 4. Feedback Loops & QA
- **Exploratory QA**: Systematic dogfooding and console audits.
- **Review**: Iterative refinement between parent and child agents.
