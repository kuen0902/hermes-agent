---
name: gaming
description: "Umbrella skill for game server management, automated gameplay, and emulator automation."
version: 1.0.0
author: "Hermes Agent"
license: MIT
metadata:
  hermes:
    tags: [gaming, minecraft, pokemon, emulator, server-management]
---

# Gaming & Interactive Automation

This umbrella skill covers workflows for hosting game servers, automating gameplay via emulators, and managing gaming infrastructure.

## 1. Game Server Management
- **Minecraft Modpacks**: Detailed SOP for hosting Forge/NeoForge servers from zip packs. Includes Java version management, JVM tuning, and automated backups. See `references/minecraft_server.md`.
- **Server Health**: Rules for MOTD, whitelisting, and performance monitoring.

## 2. Automated Gameplay & Emulation
- **Pokemon Emulation**: Headless gameplay loop using `pokemon-agent` (PyBoy). Combines RAM-state observation with vision-based verification. See `references/pokemon_agent.md`.
- **Loop**: Observe -> Orient -> Decide -> Act -> Verify.

## 3. Remote Access & Dashboards
- Patterns for SSH reverse tunnels (localhost.run) to provide live dashboards to remote users.
