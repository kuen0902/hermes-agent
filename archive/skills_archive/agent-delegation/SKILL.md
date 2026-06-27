---
name: agent-delegation
description: "Umbrella skill for delegating coding and research tasks to specialized autonomous sub-agents (Claude Code, OpenAI Codex, OpenCode)."
version: 1.0.0
author: Hermes
license: MIT
metadata:
  hermes:
    tags: [delegation, agents, claude-code, codex, opencode, sub-agents]
---

# Agent Delegation Framework

This umbrella skill captures patterns for offloading heavy-lifting tasks (coding, PR reviews, large refactors) to autonomous sub-agents.

## 1. Coding Agents
- **Claude Code**: High-reasoning agent for feature implementation, PR creation, and codebase exploration.
- **OpenAI Codex**: Legacy but robust patterns for code generation and refactoring.
- **OpenCode**: Open-source delegation for PR reviews and targeted coding tasks.

## 2. Delegation Patterns
- **Context Injection**: Best practices for preparing the work directory and passing relevant file paths to sub-agents.
- **Verification**: Post-delegation checks (tests, linting) to ensure the sub-agent's output meets quality standards.
- **Looping**: Iterative refinement between the parent (Hermes) and the sub-agent.
