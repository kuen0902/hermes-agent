# Hermes Directory

Welcome to your Hermes configuration and data directory.

## Directory Structure

- **bin/**: Core binaries (including `tirith`).
- **config.yaml**: Main configuration file.
- **data/**: Application databases and state files.
- **logs/**: System and agent logs.
- **maintenance/**: System health and troubleshooting scripts.
- **memories/**: Agent's long-term memory storage.
- **run/**: Process IDs and lock files.
- **scripts/**: Task-specific scripts (stock monitors, etc.).
- **skills/**: Agent skill definitions.
- **SOUL.md**: The core persona and logic of the Hermes agent.

## Quick Start

- To fix workspace paths: `python3 maintenance/fix_workspace.py`
- To stop Hermes: `./maintenance/kill_hermes.sh`

> [!TIP]
> Keep the root directory clean by moving any new temporary scripts into `maintenance/` or `scripts/`.
