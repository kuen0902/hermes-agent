---
name: communication
description: "Umbrella skill for email, social media, and messaging platform interactions."
version: 1.0.0
author: "Hermes (Curator)"
license: MIT
metadata:
  hermes:
    tags: [email, social-media, messaging, platform, x, twitter, telegram, slack]
---

# Communication & Messaging Orchestration

This umbrella skill captures the patterns for interacting with people and platforms across different communication protocols.

## 1. Terminal-Based Email (Himalaya)
- **Monitoring**: Watch inboxes and list latest messages via `himalaya`.
- **Management**: Read, draft, and send emails using terminal-centric workflows.

## 2. Social Media Interactions
- **X (Twitter)**: Monitoring feeds, posting updates, and interacting with posts via CLI/APIs.
- **Yuanbao**: Platform-specific interactions and message routing.

## 3. Platform Specifics (Telegram/Slack/Discord)
- **Identity Routing**: Handling multiple bot tokens and target channels.
- **Message Formatting**: Escaping Markdown characters for robust delivery.
