---
name: systematic-development
description: "Umbrella skill for the 4-phase systematic development lifecycle: planning, TDD, debugging, and implementation."
version: 1.0.0
author: Hermes
license: MIT
metadata:
  hermes:
    tags: [software-development, tdd, debugging, planning, subagents, code-review]
---

# Systematic Software Development

This umbrella skill defines the "Scientific Method" for software engineering—prioritizing root-cause analysis, test-driven implementation, and structured planning.

## 1. Planning & Design
- **Drafting**: Use `writing-plans` to create bite-sized tasks and identify dependencies.
- **Verification**: Use `spike` for throwaway experiments to validate architectural assumptions.
- **Lifecycle**: Draft -> Review -> Refine -> Implementation.

## 2. Implementation Workflow (TDD)
- **The Red-Green-Refactor Loop**: Always write a failing test first.
- **Subagent Delegation**: Dispatch complex implementation lanes to autonomous subagents for parallel execution.

## 3. Systematic Debugging
- **Phase 1: Root Cause Investigation**: Never propose a fix until you can explain WHY it fails.
- **Phase 2: Pattern Analysis**: Find working examples before patching.
- **Phase 3: Minimal Testing**: Test hypotheses with the smallest possible change.

## 4. Debugging Tools & Environments
- **Python**: Use `debugpy` / `pdb` for remote or interactive inspection.
- **Node.js**: Use `--inspect` and Chrome DevTools Protocol.
- **TUI**: Patterns for debugging Ink-based user interfaces.
