---
name: github
description: "Umbrella skill for GitHub repository management, authentication, PR workflows, and code review."
version: 1.0.0
author: Hermes
license: MIT
metadata:
  hermes:
    tags: [github, git, pr, code-review, repo-management, auth]
---

# GitHub Operations & Workflow

This umbrella skill captures the full lifecycle of working with GitHub—from initial authentication and repository management to PR submission and automated code review.

## 1. Authentication & Setup
- **Method 1 (gh CLI)**: Use `gh auth login` or `gh auth setup-git`.
- **Method 2 (Git-Only)**: Use Personal Access Tokens (PAT) with `git config --global credential.helper store`.
- **Method 3 (SSH)**: Generate ed25519 keys and add to GitHub settings.

## 2. Repository & Issue Management
- **Repo Operations**: Clone, create, fork, and manage remotes/releases.
- **Issue Triage**: Create, label, assign, and search issues via the `gh` CLI or REST API.

## 3. Pull Request (PR) Workflow
- **Lifecycle**: Branch creation -> commits -> `gh pr create` -> CI monitoring -> Merge.
- **Code Review**: Perform automated diff analysis, leave inline comments, and approve/reject PRs.

## 4. Codebase Inspection
- Use `pygount` to inspect LOC, language ratios, and code complexity before starting major refactors.
