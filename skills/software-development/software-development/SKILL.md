---
name: software-development
description: "Umbrella skill for systematic development, git workflows, and autonomous agent orchestration."
version: 1.0.0
author: "Hermes (Curator)"
license: MIT
metadata:
  hermes:
    tags: [software-development, git, github, agentic-development, tdd, simplify, code-review]
---

# Software Development & Agentic Orchestration

This umbrella skill captures the protocols for building, reviewing, and maintaining code, leveraging both manual rigor and autonomous agent delegation.

## 1. Systematic Development Lifecycle
- **TDD Loop**: Red-Green-Refactor. Always write a failing test before implementation.
- **Root-Cause Analysis**: Documentation of failures (Spikes) before fixing.
- **Kanban Orchestration**: Goal -> Decomposition -> Task Execution via `~/.hermes/kanban/`.

## 2. GitHub & Git Operations
- **Workspace Hygiene**: Use isolated worktrees (`hermes --worktree`) for parallel agent development.
- **PR Lifecycle**: Branch creation -> `gh pr create` -> Automated Review -> Merge.
- **Authentication**: Use `gh auth login` or ed25519 SSH keys.

## 3. Parallel Agentic Cleanup (Simplify)
Review recent changes with three focused reviewers in parallel to improve reuse, quality, and efficiency.
- **Trigger**: "simplify my changes", "/simplify".
- **Execution**: 
  1. Capture diff (`git diff HEAD`).
  2. Launch Reviewer 1 (Reuse), Reviewer 2 (Quality), Reviewer 3 (Efficiency) via `delegate_task` batch mode.
  3. Aggregate findings, resolve conflicts (Correctness > Readability > Perf), and apply fixes.

## 4. Subagent Delegation
- **Coding Agents**: Use `delegate_task` or specialized CLI tools (Claude Code, Codex).
- **Context Injection**: Use `read_file` and `search_files` to prep subagent environment.
- **Reconciliation**: Verify subagent work via tests and linting.
